# ############################################################################
# AI_HEADER: TEST_TODAY-SNAPSHOT-POSTGRES — real PostgreSQL publication proof.
# ROLE: Proves atomic conflict reuse, immutable JSON, and owner lookup in an
#       isolated temporary schema; never touches application/dev/prod tables.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-SNAPSHOT-POSTGRES
# purpose: Validate TodaySnapshotService against real PostgreSQL transactions and unique constraints.
# owns:
#   - apps/api/tests/test_today_snapshot_postgres.py
# inputs: TODAY_TEST_POSTGRES_URL and one temporary schema containing only users and today_snapshots.
# outputs: Concurrent publication, immutable storage, owner lookup, and identity-isolation evidence.
# dependencies: PostgreSQL async SQLAlchemy, User/TodaySnapshot tables, TodaySnapshotService.
# side_effects: Creates and drops one uniquely named temporary schema; no production/dev tables.
# emitted_logs: none (service events are not asserted here).
# invariants: no SQLite, no check-then-insert, no production schema, no migration execution.
# failure_policy: explicit failure when URL is absent or non-PostgreSQL.
# END_MODULE_CONTRACT: M-TEST-TODAY-SNAPSHOT-POSTGRES

# START_MODULE_MAP: M-TEST-TODAY-SNAPSHOT-POSTGRES
# public_entrypoints:
#   - test_postgres_concurrent_publication_has_one_row
#   - test_postgres_stored_row_has_exact_lineage_and_json
#   - test_postgres_conflict_reuse_preserves_original_json
#   - test_postgres_caller_json_mutation_does_not_change_storage
#   - test_postgres_owned_lookup_hides_foreign_and_missing_rows
#   - test_postgres_changed_input_hash_publishes_distinct_identity
# semantic_blocks:
#   - ISOLATED_SCHEMA: temporary PostgreSQL-only users/today_snapshots setup.
#   - CONCURRENT_PUBLICATION: independent sessions and one winner.
#   - IMMUTABLE_STORAGE: conflict and caller mutation proofs.
#   - OWNED_LOOKUP: owner-scoped hit/miss and identity separation.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-SNAPSHOT-POSTGRES

from __future__ import annotations

import asyncio
import os
from copy import deepcopy
from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.models import TodaySnapshot, User
from app.services.today_convergence_snapshot import TodayConvergenceSnapshotDocument
from app.services.today_snapshot_service import TodaySnapshotService


POSTGRES_URL = os.getenv("TODAY_TEST_POSTGRES_URL")
pytestmark = pytest.mark.integration


def document() -> TodayConvergenceSnapshotDocument:
    return TodayConvergenceSnapshotDocument(
        target_date=date(2026, 7, 31),
        timezone="Europe/Moscow",
        profile_hash="p" * 64,
        input_hash="i" * 64,
        canon_hash="c" * 64,
        formula_version="formula-1",
        calculation_version="calc-1",
        ephemeris_artifact_id="artifact-1",
        birth_time_mode="exact",
        birth_time_range={"start": "14:30", "end": "14:30"},
        canonical_input_json={"nested": {"input": [1, 2]}},
        deterministic_result_json={"state": "quiet_day", "selected": {"convergences": []}},
    )


async def set_schema(db: AsyncSession, schema: str) -> None:
    await db.execute(text(f'SET search_path TO "{schema}"'))


@pytest.fixture(scope="module")
async def postgres_context():
    if not POSTGRES_URL:
        pytest.fail("TODAY_TEST_POSTGRES_URL is required for real PostgreSQL acceptance")

    engine = create_async_engine(POSTGRES_URL, echo=False, poolclass=NullPool)
    schema = f"today_snapshot_test_{uuid4().hex}"
    async with engine.begin() as conn:
        if conn.dialect.name != "postgresql":
            pytest.fail(
                "TODAY_TEST_POSTGRES_URL must point to PostgreSQL, "
                f"got dialect '{conn.dialect.name}'"
            )
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        await conn.execute(text(f'SET search_path TO "{schema}"'))
        await conn.run_sync(User.__table__.create)
        await conn.run_sync(TodaySnapshot.__table__.create)

    yield engine, schema

    async with engine.begin() as conn:
        await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    await engine.dispose()


@pytest.fixture
def session_factory(postgres_context):
    engine, _schema = postgres_context
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_user(session_factory, schema: str) -> UUID:
    async with session_factory() as db:
        await set_schema(db, schema)
        user = User(tg_user_id=uuid4().int % 2_000_000_000)
        db.add(user)
        await db.commit()
        return user.id


async def publish(session_factory, schema: str, user_id: UUID, value: TodayConvergenceSnapshotDocument):
    async with session_factory() as db:
        await set_schema(db, schema)
        return await TodaySnapshotService(db).publish_or_load(user_id, value)


@pytest.mark.asyncio
async def test_postgres_concurrent_publication_has_one_row(postgres_context, session_factory) -> None:
    _engine, schema = postgres_context
    user_id = await create_user(session_factory, schema)

    first, second = await asyncio.gather(
        publish(session_factory, schema, user_id, document()),
        publish(session_factory, schema, user_id, document()),
    )

    assert {first.outcome, second.outcome} == {"published", "conflict_reused"}
    assert first.snapshot.id == second.snapshot.id
    async with session_factory() as db:
        await set_schema(db, schema)
        count = await db.scalar(
            select(func.count()).select_from(TodaySnapshot).where(TodaySnapshot.user_id == user_id)
        )
    assert count == 1


@pytest.mark.asyncio
async def test_postgres_stored_row_has_exact_lineage_and_json(postgres_context, session_factory) -> None:
    _engine, schema = postgres_context
    user_id = await create_user(session_factory, schema)
    value = document()
    publication = await publish(session_factory, schema, user_id, value)

    async with session_factory() as db:
        await set_schema(db, schema)
        stored = await db.scalar(select(TodaySnapshot).where(TodaySnapshot.id == publication.snapshot.id))

    assert stored is not None
    assert stored.user_id == user_id
    assert stored.target_date == value.target_date
    assert stored.timezone == value.timezone
    assert stored.profile_hash == value.profile_hash
    assert stored.input_hash == value.input_hash
    assert stored.canon_hash == value.canon_hash
    assert stored.formula_version == value.formula_version
    assert stored.calculation_version == value.calculation_version
    assert stored.ephemeris_artifact_id == value.ephemeris_artifact_id
    assert stored.birth_time_mode == value.birth_time_mode
    assert stored.birth_time_range == value.birth_time_range
    assert stored.canonical_input_json == value.canonical_input_json
    assert stored.deterministic_result_json == value.deterministic_result_json
    assert stored.published_at is not None


@pytest.mark.asyncio
async def test_postgres_conflict_reuse_preserves_original_json(postgres_context, session_factory) -> None:
    _engine, schema = postgres_context
    user_id = await create_user(session_factory, schema)
    original = document()
    first = await publish(session_factory, schema, user_id, original)
    mutated = TodayConvergenceSnapshotDocument(
        **{**vars(original), "deterministic_result_json": {"state": "convergence_today"}}
    )
    second = await publish(session_factory, schema, user_id, mutated)

    assert second.outcome == "conflict_reused"
    assert second.snapshot.id == first.snapshot.id
    async with session_factory() as db:
        await set_schema(db, schema)
        stored = await db.scalar(select(TodaySnapshot).where(TodaySnapshot.id == first.snapshot.id))
    assert stored.deterministic_result_json == original.deterministic_result_json


@pytest.mark.asyncio
async def test_postgres_caller_json_mutation_does_not_change_storage(postgres_context, session_factory) -> None:
    _engine, schema = postgres_context
    user_id = await create_user(session_factory, schema)
    value = document()
    original_input = deepcopy(value.canonical_input_json)
    publication = await publish(session_factory, schema, user_id, value)
    value.canonical_input_json["nested"]["input"].append(999)
    value.deterministic_result_json["state"] = "convergence_today"

    async with session_factory() as db:
        await set_schema(db, schema)
        stored = await db.scalar(select(TodaySnapshot).where(TodaySnapshot.id == publication.snapshot.id))
    assert stored.canonical_input_json == original_input
    assert stored.deterministic_result_json == {"state": "quiet_day", "selected": {"convergences": []}}


@pytest.mark.asyncio
async def test_postgres_owned_lookup_hides_foreign_and_missing_rows(postgres_context, session_factory) -> None:
    _engine, schema = postgres_context
    owner_id = await create_user(session_factory, schema)
    foreign_id = await create_user(session_factory, schema)
    publication = await publish(session_factory, schema, owner_id, document())

    async with session_factory() as db:
        await set_schema(db, schema)
        service = TodaySnapshotService(db)
        assert (await service.load_owned(owner_id, publication.snapshot.id)) is not None
        assert (await service.load_owned(foreign_id, publication.snapshot.id)) is None
        assert (await service.load_owned(owner_id, uuid4())) is None


@pytest.mark.asyncio
async def test_postgres_changed_input_hash_publishes_distinct_identity(postgres_context, session_factory) -> None:
    _engine, schema = postgres_context
    user_id = await create_user(session_factory, schema)
    first = await publish(session_factory, schema, user_id, document())
    changed = TodayConvergenceSnapshotDocument(**{**vars(document()), "input_hash": "j" * 64})
    second = await publish(session_factory, schema, user_id, changed)

    assert first.outcome == "published"
    assert second.outcome == "published"
    assert first.snapshot.id != second.snapshot.id
    async with session_factory() as db:
        await set_schema(db, schema)
        count = await db.scalar(
            select(func.count()).select_from(TodaySnapshot).where(TodaySnapshot.user_id == user_id)
        )
    assert count == 2
