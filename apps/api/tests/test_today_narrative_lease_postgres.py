# ############################################################################
# AI_HEADER: TEST_TODAY-NARRATIVE-LEASE-POSTGRES — real PostgreSQL lease proof.
# ROLE: Proves single-flight acquire/recovery/CAS behavior against an isolated
#       temporary schema containing only the frozen narrative persistence tables.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-NARRATIVE-LEASE-POSTGRES
# purpose: Validate TodayNarrativeLeaseService concurrency and persistence with
#   real PostgreSQL locking and unique-constraint behavior.
# owns:
#   - apps/api/tests/test_today_narrative_lease_postgres.py
# inputs: TODAY_TEST_POSTGRES_URL and isolated User/TodaySnapshot/narrative tables.
# outputs: Evidence for one winner, recovery, stale CAS, cooldown/retry, and isolation.
# dependencies: PostgreSQL async SQLAlchemy, frozen ORM models, TodayNarrativeLeaseService.
# side_effects: Creates/drops one uniquely named temporary schema; no app tables,
#   provider calls, or external network.
# emitted_logs: none asserted here; unit tests assert event payloads.
# invariants: no SQLite, no migration/schema edits, one row per snapshot/prompt key.
# failure_policy: explicit failure when TODAY_TEST_POSTGRES_URL is absent or non-PostgreSQL.
# END_MODULE_CONTRACT: M-TEST-TODAY-NARRATIVE-LEASE-POSTGRES

# START_MODULE_MAP: M-TEST-TODAY-NARRATIVE-LEASE-POSTGRES
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - ISOLATED_SCHEMA: temporary PostgreSQL-only schema and frozen tables.
#   - SINGLE_FLIGHT: concurrent insert conflict and row count proof.
#   - RECOVERY_AND_CAS: lease expiry, attempt identity, stale completion.
#   - RETRY: unavailable cooldown and due retry transition.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-NARRATIVE-LEASE-POSTGRES

from __future__ import annotations

import asyncio
import os
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.models import TodaySnapshot, TodaySnapshotNarrative, User
from app.services.today_narrative_lease_service import (
    NarrativeLeaseCompletion,
    NarrativeLeaseSkip,
    TodayNarrativeLeaseError,
    TodayNarrativeLeaseService,
)


POSTGRES_URL = os.getenv("TODAY_TEST_POSTGRES_URL")
pytestmark = pytest.mark.integration

NOW = datetime(2026, 7, 31, 9, 0, tzinfo=timezone.utc)
DURATION = timedelta(minutes=5)
PROMPT_VERSION = "today-narrative-v1"


async def set_schema(db: AsyncSession, schema: str) -> None:
    await db.execute(text(f'SET search_path TO "{schema}"'))


@pytest.fixture(scope="module")
async def postgres_context():
    if not POSTGRES_URL:
        pytest.fail("TODAY_TEST_POSTGRES_URL is required for real PostgreSQL acceptance")

    engine = create_async_engine(POSTGRES_URL, echo=False, poolclass=NullPool)
    schema = f"today_narrative_test_{uuid4().hex}"
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
        await conn.run_sync(TodaySnapshotNarrative.__table__.create)

    yield engine, schema

    async with engine.begin() as conn:
        await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    await engine.dispose()


@pytest.fixture
def session_factory(postgres_context):
    engine, _schema = postgres_context
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_snapshot(session_factory, schema: str, *, snapshot_id: UUID | None = None) -> UUID:
    async with session_factory() as db:
        await set_schema(db, schema)
        user = User(tg_user_id=uuid4().int % 2_000_000_000)
        db.add(user)
        await db.flush()
        snapshot = TodaySnapshot(
            id=snapshot_id or uuid4(),
            user_id=user.id,
            target_date=date(2026, 7, 31),
            timezone="UTC",
            profile_hash="p" * 64,
            input_hash="i" * 64,
            canon_hash="c" * 64,
            formula_version="formula-1",
            calculation_version="calc-1",
            ephemeris_artifact_id="artifact-1",
            birth_time_mode="exact",
            birth_time_range={"start": "09:00", "end": "09:00"},
            deterministic_result_json={"state": "quiet_day"},
            canonical_input_json={"snapshot": "canonical"},
            published_at=NOW,
        )
        db.add(snapshot)
        await db.commit()
        return snapshot.id


async def acquire(session_factory, schema: str, snapshot_id: UUID, now: datetime = NOW):
    async with session_factory() as db:
        await set_schema(db, schema)
        return await TodayNarrativeLeaseService(db).acquire(
            snapshot_id, PROMPT_VERSION, now, DURATION
        )


@pytest.mark.asyncio
async def test_postgres_concurrent_acquire_has_one_claim(postgres_context, session_factory) -> None:
    _engine, schema = postgres_context
    snapshot_id = await create_snapshot(session_factory, schema)

    first, second = await asyncio.gather(
        acquire(session_factory, schema, snapshot_id),
        acquire(session_factory, schema, snapshot_id),
    )

    results = (first, second)
    assert {value.outcome for value in results if hasattr(value, "outcome")} == {"created"}
    assert {value.reason for value in results if hasattr(value, "reason")} == {"in_flight"}
    assert sum(hasattr(value, "attempt_count") for value in (first, second)) == 1
    async with session_factory() as db:
        await set_schema(db, schema)
        rows = await db.scalar(
            select(func.count()).select_from(TodaySnapshotNarrative).where(
                TodaySnapshotNarrative.snapshot_id == snapshot_id,
                TodaySnapshotNarrative.prompt_version == PROMPT_VERSION,
            )
        )
        stored = await db.scalar(
            select(TodaySnapshotNarrative).where(TodaySnapshotNarrative.snapshot_id == snapshot_id)
        )
    assert rows == 1
    assert stored is not None
    assert stored.attempt_count == 1


@pytest.mark.asyncio
async def test_postgres_expired_recovery_and_stale_first_claim(postgres_context, session_factory) -> None:
    _engine, schema = postgres_context
    snapshot_id = await create_snapshot(session_factory, schema)
    first = await acquire(session_factory, schema, snapshot_id)
    assert first.outcome == "created"

    async with session_factory() as db:
        await set_schema(db, schema)
        await db.execute(
            update(TodaySnapshotNarrative)
            .where(TodaySnapshotNarrative.snapshot_id == snapshot_id)
            .values(lease_until=NOW - timedelta(seconds=1))
        )
        await db.commit()

    second = await acquire(session_factory, schema, snapshot_id, NOW)
    assert second.outcome == "recovered"
    assert second.attempt_count == 2
    async with session_factory() as db:
        await set_schema(db, schema)
        stale = await TodayNarrativeLeaseService(db).complete_ready(first, {"winner": "stale"})
    assert stale == NarrativeLeaseCompletion(outcome="stale")

    async with session_factory() as db:
        await set_schema(db, schema)
        completed = await TodayNarrativeLeaseService(db).complete_ready(second, {"winner": "current"})
    assert completed == NarrativeLeaseCompletion(outcome="completed")
    repeat = await acquire(session_factory, schema, snapshot_id, NOW + timedelta(seconds=1))
    assert repeat == NarrativeLeaseSkip(
        narrative_id=second.narrative_id,
        snapshot_id=snapshot_id,
        prompt_version=PROMPT_VERSION,
        status="ready",
        reason="ready",
        retry_at=None,
    )


@pytest.mark.asyncio
async def test_postgres_unavailable_cooldown_and_due_retry(postgres_context, session_factory) -> None:
    _engine, schema = postgres_context
    snapshot_id = await create_snapshot(session_factory, schema)
    claim = await acquire(session_factory, schema, snapshot_id)
    assert claim.outcome == "created"
    async with session_factory() as db:
        await set_schema(db, schema)
        completed = await TodayNarrativeLeaseService(db, clock=lambda: NOW).complete_unavailable(
            claim, "provider.timeout", NOW + timedelta(minutes=10)
        )
    assert completed.outcome == "completed"

    cooldown = await acquire(session_factory, schema, snapshot_id, NOW)
    assert cooldown == NarrativeLeaseSkip(
        narrative_id=claim.narrative_id,
        snapshot_id=snapshot_id,
        prompt_version=PROMPT_VERSION,
        status="unavailable",
        reason="cooldown",
        retry_at=NOW + timedelta(minutes=10),
    )
    async with session_factory() as db:
        await set_schema(db, schema)
        await db.execute(
            update(TodaySnapshotNarrative)
            .where(TodaySnapshotNarrative.snapshot_id == snapshot_id)
            .values(next_retry_at=NOW - timedelta(seconds=1))
        )
        await db.commit()
    retry = await acquire(session_factory, schema, snapshot_id, NOW)
    assert retry.outcome == "retry"
    assert retry.attempt_count == 2


@pytest.mark.asyncio
async def test_postgres_missing_snapshot_rejects_without_narrative(postgres_context, session_factory) -> None:
    _engine, schema = postgres_context
    missing_id = uuid4()

    async with session_factory() as db:
        await set_schema(db, schema)
        with pytest.raises(TodayNarrativeLeaseError, match="snapshot_not_published"):
            await TodayNarrativeLeaseService(db).acquire(
                missing_id, PROMPT_VERSION, NOW, DURATION
            )
        await set_schema(db, schema)
        rows = await db.scalar(
            select(func.count()).select_from(TodaySnapshotNarrative).where(
                TodaySnapshotNarrative.snapshot_id == missing_id
            )
        )
    assert rows == 0
