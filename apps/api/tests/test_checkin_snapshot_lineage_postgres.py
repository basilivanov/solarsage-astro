# ############################################################################
# AI_HEADER: TEST_CHECKIN_SNAPSHOT_LINEAGE_POSTGRES — real PostgreSQL lineage.
# ROLE: Verifies owner/date joins and immutable check-in lineage in an opt-in
#       temporary schema using the actual snapshot and check-in tables.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-CHECKIN-SNAPSHOT-LINEAGE-POSTGRES
# purpose: Prove snapshot-linked check-in persistence against real PostgreSQL.
# owns:
#   - apps/api/tests/test_checkin_snapshot_lineage_postgres.py
# inputs: TODAY_TEST_POSTGRES_URL and isolated temporary PostgreSQL schema.
# outputs: SQL join, day-priority, edit-preservation, null-lineage, and owner-isolation evidence.
# dependencies: SQLAlchemy asyncpg, User, TodaySnapshot, EveningCheckin, CheckinService.
# side_effects: Creates and drops one random temporary schema; no persistent rows.
# emitted_logs: checkin.lineage_bound, checkin.lineage_absent, checkin.lineage_preserved.
# invariants: no snapshot selected across owner/date; selected spheres stay in immutable JSON.
# failure_policy: skipped without TODAY_TEST_POSTGRES_URL; database failures fail the test.
# END_MODULE_CONTRACT: M-TEST-CHECKIN-SNAPSHOT-LINEAGE-POSTGRES

# START_MODULE_MAP: M-TEST-CHECKIN-SNAPSHOT-LINEAGE-POSTGRES
# public_entrypoints:
#   - test_postgres_checkin_snapshot_lineage
# semantic_blocks:
#   - TEMP_SCHEMA: isolated schema lifecycle and guaranteed cleanup.
#   - SQL_JOIN: owner/date lineage and immutable snapshot JSON recovery.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-CHECKIN-SNAPSHOT-LINEAGE-POSTGRES

from __future__ import annotations

import os
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import EveningCheckin, TodaySnapshot, User
from app.db.session import Base
from app.services.checkin_service import CheckinService


pytestmark = pytest.mark.integration
UTC = timezone.utc
TARGET_DATE = date(2026, 7, 31)


def _async_url(value: str) -> str:
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+asyncpg://", 1)
    return value


def _snapshot(user_id, snapshot_id, *, day_seen=None, lookahead_seen=None, target_date=TARGET_DATE):
    return TodaySnapshot(
        id=snapshot_id,
        user_id=user_id,
        target_date=target_date,
        timezone="UTC",
        profile_hash="p" * 64,
        input_hash=str(snapshot_id).replace("-", "")[:64].ljust(64, "0"),
        canon_hash="c" * 64,
        formula_version="today-convergence-2",
        calculation_version="calc-1",
        ephemeris_artifact_id="artifact-1",
        birth_time_mode="exact",
        birth_time_range={"start": "14:30", "end": "14:30"},
        deterministic_result_json={
            "state": "convergence_today",
            "selected": {"spheres": ["work", "finance"]},
        },
        canonical_input_json={"target": target_date.isoformat()},
        first_day_seen_at=day_seen,
        first_lookahead_seen_at=lookahead_seen,
        published_at=datetime(2026, 7, 31, 8, tzinfo=UTC),
    )


@pytest_asyncio.fixture
async def postgres_session():
    url = os.getenv("TODAY_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("TODAY_TEST_POSTGRES_URL is not configured")
    pytest.importorskip("asyncpg")

    engine = create_async_engine(_async_url(url), pool_pre_ping=True)
    schema = f"checkin_lineage_{uuid4().hex[:16]}"
    tables = [User.__table__, TodaySnapshot.__table__, EveningCheckin.__table__]
    connection = await engine.connect()
    try:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        await connection.commit()
        await connection.execute(text(f'SET search_path TO "{schema}"'))
        await connection.run_sync(lambda sync_connection: Base.metadata.create_all(sync_connection, tables=tables))
        await connection.commit()
        session_factory = async_sessionmaker(connection, expire_on_commit=False)
        async with session_factory() as session:
            yield session
    finally:
        await connection.execute(text("SET search_path TO public"))
        await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await connection.commit()
        await connection.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_checkin_snapshot_lineage(postgres_session: AsyncSession) -> None:
    owner = User(tg_user_id=uuid4().int % 2_000_000_000, tg_username="lineage_owner")
    foreign = User(tg_user_id=uuid4().int % 2_000_000_000, tg_username="lineage_foreign")
    postgres_session.add_all([owner, foreign])
    await postgres_session.flush()

    day = _snapshot(
        owner.id,
        uuid4(),
        day_seen=datetime(2026, 7, 31, 9, tzinfo=UTC),
    )
    older_day = _snapshot(
        owner.id,
        uuid4(),
        day_seen=datetime(2026, 7, 31, 7, tzinfo=UTC),
    )
    newer_lookahead = _snapshot(
        owner.id,
        uuid4(),
        lookahead_seen=datetime(2026, 7, 31, 12, tzinfo=UTC),
    )
    foreign_snapshot = _snapshot(
        foreign.id,
        uuid4(),
        day_seen=datetime(2026, 7, 31, 13, tzinfo=UTC),
    )
    postgres_session.add_all([day, older_day, newer_lookahead, foreign_snapshot])
    await postgres_session.commit()

    service = CheckinService(postgres_session)
    first = await service.create_checkin(
        owner.id,
        TARGET_DATE,
        4,
        2,
        5,
        [],
        None,
        ["work"],
    )
    assert first.forecast_snapshot_id == day.id
    assert first.prediction_seen_at == day.first_day_seen_at
    assert first.prediction_seen_surface == "day"

    join = (
        await postgres_session.execute(
            select(EveningCheckin, TodaySnapshot)
            .join(TodaySnapshot, EveningCheckin.forecast_snapshot_id == TodaySnapshot.id)
            .where(EveningCheckin.id == first.id)
        )
    ).one()
    checkin_row, snapshot_row = join
    assert snapshot_row.user_id == owner.id
    assert snapshot_row.target_date == checkin_row.target_date
    assert snapshot_row.formula_version == "today-convergence-2"
    assert snapshot_row.deterministic_result_json["selected"]["spheres"] == ["work", "finance"]
    assert checkin_row.observed_spheres == ["work"]

    second = await service.create_checkin(
        owner.id,
        TARGET_DATE,
        5,
        3,
        4,
        [],
        "edited",
        ["finance"],
    )
    assert second.forecast_snapshot_id == day.id
    assert second.prediction_seen_at == day.first_day_seen_at
    assert second.observed_spheres == ["finance"]

    no_impression_date = date(2026, 8, 1)
    no_impression = await service.create_checkin(
        owner.id, no_impression_date, 3, None, None, [], None, None
    )
    assert no_impression.forecast_snapshot_id is None
    assert no_impression.prediction_seen_at is None
    assert no_impression.prediction_seen_surface is None

    foreign_date = date(2026, 8, 2)
    foreign_only = _snapshot(
        foreign.id,
        uuid4(),
        day_seen=datetime(2026, 7, 31, 13, tzinfo=UTC),
        target_date=foreign_date,
    )
    postgres_session.add(foreign_only)
    await postgres_session.commit()
    owner_without_candidate = await service.create_checkin(
        owner.id, foreign_date, 3, None, None, [], None, None
    )
    assert owner_without_candidate.forecast_snapshot_id is None
