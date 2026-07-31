# ############################################################################
# AI_HEADER: TEST_TODAY-SNAPSHOT-LINEAGE-POSTGRES — real PostgreSQL lineage proof.
# ROLE: Proves packet-34 trigger/index/update/concurrency semantics in exact temporary schemas.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-SNAPSHOT-LINEAGE-POSTGRES
# purpose: Validate migration 0029 and TodaySnapshotService against isolated PostgreSQL schemas.
# owns:
#   - apps/api/tests/test_today_snapshot_lineage_postgres.py
# inputs: TODAY_TEST_POSTGRES_URL and generated schema names.
# outputs: Evidence for trigger guards, chain/fork rules, immutable first-seen fields,
#   concurrent impressions, and upgrade/downgrade index restoration.
# dependencies: PostgreSQL async SQLAlchemy, Alembic Operations, packet-34 migration/service/models.
# side_effects: Creates/drops exact temporary schemas containing only users and today_snapshots.
# emitted_logs: service events are intentionally not asserted here.
# invariants: missing/non-PostgreSQL URL fails closed; no public/dev tables; no SQLite proof.
# failure_policy: pytest fails explicitly when TODAY_TEST_POSTGRES_URL is absent or non-PostgreSQL.
# END_MODULE_CONTRACT: M-TEST-TODAY-SNAPSHOT-LINEAGE-POSTGRES

# START_MODULE_MAP: M-TEST-TODAY-SNAPSHOT-LINEAGE-POSTGRES
# public_entrypoints:
#   - test_migration_restores_ordinary_index_on_downgrade
#   - test_postgres_trigger_rejects_cross_scope_and_immutable_updates
#   - test_postgres_chain_works_and_fork_is_rejected
#   - test_postgres_concurrent_impressions_preserve_first_timestamp
#   - test_postgres_day_and_lookahead_surfaces_are_independent
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-SNAPSHOT-LINEAGE-POSTGRES

from __future__ import annotations

import asyncio
import importlib.util
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import insert, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.models import TodaySnapshot, User
from app.services.today_convergence_snapshot import TodayConvergenceSnapshotDocument
from app.services.today_snapshot_service import TodaySnapshotLineageError, TodaySnapshotService


POSTGRES_URL = os.getenv("TODAY_TEST_POSTGRES_URL")
pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[3]
OBSERVED_AT = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)


def _migration_module():
    path = ROOT / "apps/api/alembic/versions/0029_today_snapshot_lineage_guards.py"
    spec = importlib.util.spec_from_file_location("today_snapshot_lineage_migration", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("migration module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _document(target_date: date, *, input_hash: str = "i" * 64, state: str = "quiet_day"):
    return TodayConvergenceSnapshotDocument(
        target_date=target_date,
        timezone="UTC",
        profile_hash="p" * 64,
        input_hash=input_hash,
        canon_hash="c" * 64,
        formula_version="formula-1",
        calculation_version="calc-1",
        ephemeris_artifact_id="artifact-1",
        birth_time_mode="exact",
        birth_time_range={"start": "14:30", "end": "14:30"},
        canonical_input_json={"target": target_date.isoformat()},
        deterministic_result_json={"state": state},
    )


async def _set_schema(db: AsyncSession, schema: str) -> None:
    await db.execute(text(f'SET search_path TO "{schema}"'))


async def _create_context():
    if not POSTGRES_URL:
        pytest.fail("TODAY_TEST_POSTGRES_URL is required for real PostgreSQL acceptance")
    engine = create_async_engine(POSTGRES_URL, poolclass=NullPool)
    schema = f"today_lineage_test_{uuid4().hex}"
    async with engine.begin() as conn:
        if conn.dialect.name != "postgresql":
            pytest.fail(f"TODAY_TEST_POSTGRES_URL must point to PostgreSQL, got {conn.dialect.name}")
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        await conn.execute(text(f'SET search_path TO "{schema}"'))
        await conn.run_sync(User.__table__.create)
        await conn.run_sync(TodaySnapshot.__table__.create)
        await conn.execute(text('DROP INDEX "ix_today_snapshots_supersedes_snapshot_id"'))
        await conn.execute(text('CREATE INDEX "ix_today_snapshots_supersedes_snapshot_id" ON today_snapshots (supersedes_snapshot_id)'))

        def apply_upgrade(sync_conn) -> None:
            migration = _migration_module()
            operations = Operations(MigrationContext.configure(sync_conn))
            original_op = migration.op
            migration.op = operations
            try:
                migration.upgrade()
            finally:
                migration.op = original_op

        await conn.run_sync(apply_upgrade)
    return engine, schema


async def _drop_context(engine, schema: str) -> None:
    async with engine.begin() as conn:
        await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    await engine.dispose()


@pytest.fixture
async def postgres_context():
    context = await _create_context()
    try:
        yield context
    finally:
        await _drop_context(*context)


@pytest.fixture
def session_factory(postgres_context):
    engine, _schema = postgres_context
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _user(session_factory, schema: str) -> UUID:
    async with session_factory() as db:
        await _set_schema(db, schema)
        user = User(tg_user_id=uuid4().int % 2_000_000_000)
        db.add(user)
        await db.commit()
        return user.id


async def _publish(session_factory, schema: str, user_id: UUID, value):
    async with session_factory() as db:
        await _set_schema(db, schema)
        return await TodaySnapshotService(db).publish_or_load(user_id, value)


@pytest.mark.asyncio
async def test_migration_restores_ordinary_index_on_downgrade():
    engine, schema = await _create_context()
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f'SET search_path TO "{schema}"'))
            result = await conn.execute(
                text("SELECT indexdef FROM pg_indexes WHERE schemaname = :schema AND indexname = :name"),
                {"schema": schema, "name": "ix_today_snapshots_supersedes_snapshot_id"},
            )
            indexdef = result.scalar_one()
            assert "UNIQUE INDEX" in indexdef
            assert "supersedes_snapshot_id IS NOT NULL" in indexdef
            preserved_id = uuid4()
            owner_id = uuid4()
            await conn.execute(insert(User).values(id=owner_id, tg_user_id=uuid4().int % 2_000_000_000))
            await conn.execute(
                insert(TodaySnapshot).values(
                    id=preserved_id, user_id=owner_id, target_date=OBSERVED_AT.date(), timezone="UTC",
                    profile_hash="p" * 64, input_hash="i" * 64, canon_hash="c" * 64,
                    formula_version="formula-1", calculation_version="calc-1", ephemeris_artifact_id="artifact-1",
                    birth_time_mode="exact", birth_time_range={}, deterministic_result_json={"state": "quiet_day"},
                    canonical_input_json={},
                )
            )

            def apply_downgrade(sync_conn) -> None:
                migration = _migration_module()
                operations = Operations(MigrationContext.configure(sync_conn))
                original_op = migration.op
                migration.op = operations
                try:
                    migration.downgrade()
                finally:
                    migration.op = original_op

            await conn.run_sync(apply_downgrade)
            restored = await conn.execute(
                text("SELECT indexdef FROM pg_indexes WHERE schemaname = :schema AND indexname = :name"),
                {"schema": schema, "name": "ix_today_snapshots_supersedes_snapshot_id"},
            )
            assert "UNIQUE INDEX" not in restored.scalar_one()
            assert await conn.scalar(select(TodaySnapshot.id).where(TodaySnapshot.id == preserved_id)) == preserved_id
    finally:
        await _drop_context(engine, schema)


@pytest.mark.asyncio
async def test_postgres_trigger_rejects_cross_scope_and_immutable_updates(postgres_context, session_factory):
    _engine, schema = postgres_context
    owner_id = await _user(session_factory, schema)
    foreign_id = await _user(session_factory, schema)
    today = OBSERVED_AT.date()
    parent = await _publish(session_factory, schema, owner_id, _document(today))

    async with session_factory() as db:
        await _set_schema(db, schema)
        bad_child = _document(today, input_hash="x" * 64)
        with pytest.raises(IntegrityError):
            await db.execute(
                insert(TodaySnapshot).values(
                    id=uuid4(), user_id=foreign_id, target_date=bad_child.target_date,
                    timezone=bad_child.timezone, profile_hash=bad_child.profile_hash,
                    input_hash=bad_child.input_hash, canon_hash=bad_child.canon_hash,
                    formula_version=bad_child.formula_version, calculation_version=bad_child.calculation_version,
                    ephemeris_artifact_id=bad_child.ephemeris_artifact_id, birth_time_mode=bad_child.birth_time_mode,
                    birth_time_range=bad_child.birth_time_range, deterministic_result_json=bad_child.deterministic_result_json,
                    canonical_input_json=bad_child.canonical_input_json, supersedes_snapshot_id=parent.snapshot.id,
                )
            )
        await db.rollback()
        await _set_schema(db, schema)
        with pytest.raises(IntegrityError):
            await db.execute(
                insert(TodaySnapshot).values(
                    id=uuid4(), user_id=owner_id, target_date=today + timedelta(days=1), timezone="UTC",
                    profile_hash="p" * 64, input_hash="z" * 64, canon_hash="c" * 64,
                    formula_version="formula-1", calculation_version="calc-1", ephemeris_artifact_id="artifact-1",
                    birth_time_mode="exact", birth_time_range={}, deterministic_result_json={"state": "quiet_day"},
                    canonical_input_json={}, supersedes_snapshot_id=parent.snapshot.id,
                )
            )
        await db.rollback()
        await _set_schema(db, schema)
        cycle_id = uuid4()
        with pytest.raises(IntegrityError):
            await db.execute(
                insert(TodaySnapshot).values(
                    id=cycle_id, user_id=owner_id, target_date=today, timezone="UTC",
                    profile_hash="p" * 64, input_hash="s" * 64, canon_hash="c" * 64,
                    formula_version="formula-1", calculation_version="calc-1", ephemeris_artifact_id="artifact-1",
                    birth_time_mode="exact", birth_time_range={}, deterministic_result_json={"state": "quiet_day"},
                    canonical_input_json={}, supersedes_snapshot_id=cycle_id,
                )
            )
        await db.rollback()
        await _set_schema(db, schema)
        with pytest.raises(IntegrityError):
            await db.execute(
                update(TodaySnapshot)
                .where(TodaySnapshot.id == parent.snapshot.id)
                .values(deterministic_result_json={"state": "convergence_today"})
            )
        await db.rollback()
        await _set_schema(db, schema)
        with pytest.raises(IntegrityError):
            await db.execute(
                update(TodaySnapshot).where(TodaySnapshot.id == parent.snapshot.id).values(id=uuid4())
            )
        await db.rollback()
        await _set_schema(db, schema)
        await db.execute(update(TodaySnapshot).where(TodaySnapshot.id == parent.snapshot.id).values(first_day_seen_at=OBSERVED_AT))
        await db.commit()
        await _set_schema(db, schema)
        with pytest.raises(IntegrityError):
            await db.execute(
                update(TodaySnapshot).where(TodaySnapshot.id == parent.snapshot.id).values(first_day_seen_at=OBSERVED_AT + timedelta(hours=1))
            )
        await db.rollback()
        await _set_schema(db, schema)
        with pytest.raises(IntegrityError):
            await db.execute(
                update(TodaySnapshot).where(TodaySnapshot.id == parent.snapshot.id).values(first_day_seen_at=None)
            )
        await db.rollback()


@pytest.mark.asyncio
async def test_postgres_chain_works_and_fork_is_rejected(postgres_context, session_factory):
    _engine, schema = postgres_context
    owner_id = await _user(session_factory, schema)
    today = OBSERVED_AT.date()
    parent = await _publish(session_factory, schema, owner_id, _document(today))
    async with session_factory() as db:
        await _set_schema(db, schema)
        child = await TodaySnapshotService(db).publish_superseding(
            owner_id, _document(today, input_hash="j" * 64), parent.snapshot.id, observed_at=OBSERVED_AT
        )
        await _set_schema(db, schema)
        result = await TodaySnapshotService(db).publish_superseding(
            owner_id, _document(today, input_hash="j" * 64), parent.snapshot.id, observed_at=OBSERVED_AT
        )
        assert result.snapshot.id == child.snapshot.id

        await _set_schema(db, schema)
        with pytest.raises(TodaySnapshotLineageError, match="parent_date"):
            await TodaySnapshotService(db).publish_superseding(
                owner_id,
                _document(today + timedelta(days=1), input_hash="m" * 64),
                parent.snapshot.id,
                observed_at=OBSERVED_AT,
            )
        await _set_schema(db, schema)

        with pytest.raises(IntegrityError):
            await db.execute(
                insert(TodaySnapshot).values(
                    id=uuid4(), user_id=owner_id, target_date=today, timezone="UTC",
                    profile_hash="p" * 64, input_hash="k" * 64, canon_hash="c" * 64,
                    formula_version="formula-1", calculation_version="calc-1", ephemeris_artifact_id="artifact-1",
                    birth_time_mode="exact", birth_time_range={}, deterministic_result_json={"state": "quiet_day"},
                    canonical_input_json={}, supersedes_snapshot_id=parent.snapshot.id,
                )
            )
        await db.rollback()


@pytest.mark.asyncio
async def test_postgres_concurrent_impressions_preserve_first_timestamp(postgres_context, session_factory):
    _engine, schema = postgres_context
    owner_id = await _user(session_factory, schema)
    snapshot = await _publish(session_factory, schema, owner_id, _document(OBSERVED_AT.date()))
    observed_at = OBSERVED_AT

    async def record():
        async with session_factory() as db:
            await _set_schema(db, schema)
            return await TodaySnapshotService(db).record_impression(
                owner_id, snapshot.snapshot.id, "day", observed_at=observed_at
            )

    first, second = await asyncio.gather(record(), record())
    assert {first.outcome, second.outcome} == {"recorded", "existing"}
    assert first.seen_at == second.seen_at


@pytest.mark.asyncio
async def test_postgres_day_and_lookahead_surfaces_are_independent(postgres_context, session_factory):
    _engine, schema = postgres_context
    owner_id = await _user(session_factory, schema)
    today = OBSERVED_AT.date()
    source = await _publish(session_factory, schema, owner_id, _document(today))
    target = await _publish(session_factory, schema, owner_id, _document(today + timedelta(days=1), input_hash="l" * 64))
    observed_at = OBSERVED_AT

    async with session_factory() as db:
        await _set_schema(db, schema)
        service = TodaySnapshotService(db)
        day = await service.record_impression(owner_id, source.snapshot.id, "day", observed_at=observed_at)
        await _set_schema(db, schema)
        lookahead = await service.record_impression(
            owner_id, target.snapshot.id, "lookahead", source_snapshot_id=source.snapshot.id, observed_at=observed_at
        )
        assert day is not None and lookahead is not None
        await _set_schema(db, schema)
        next_day = await service.record_impression(
            owner_id, target.snapshot.id, "day", observed_at=OBSERVED_AT + timedelta(days=1)
        )
        assert next_day is not None
        await _set_schema(db, schema)
        stored = await db.scalar(select(TodaySnapshot).where(TodaySnapshot.id == target.snapshot.id))
        assert stored.first_day_seen_at is not None
        assert stored.first_lookahead_seen_at is not None
