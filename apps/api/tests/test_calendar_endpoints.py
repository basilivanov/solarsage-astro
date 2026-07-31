# ############################################################################
# AI_HEADER: TEST_CALENDAR_ENDPOINTS — snapshot-indexed calendar API coverage.
# ROLE: Proves calendar wire states, access/lunar preservation, and no cold work.
# ############################################################################

# START_MODULE_CONTRACT: TEST-CALENDAR-ENDPOINTS
# purpose: Verify GET /api/calendar against the P4-D3A snapshot-index contract.
# owns:
#   - apps/api/tests/test_calendar_endpoints.py
# inputs: async client, in-memory DB, Telegram initData, published snapshots.
# outputs: endpoint regression evidence for auth, validation, state projection,
#   supersession heads, access/lunar preservation, and no sidecar/scoring calls.
# dependencies: M-CALENDAR-API, M-CALENDAR-SERVICE, TodaySnapshot, test fixtures.
# side_effects: in-memory database writes and mocked calculation boundaries.
# emitted_logs: none (test harness).
# invariants: missing dates remain not-computed; legacy dayStatus is absent.
# failure_policy: assertion failure blocks the calendar snapshot-index slice.
# END_MODULE_CONTRACT: TEST-CALENDAR-ENDPOINTS

# START_MODULE_MAP: TEST-CALENDAR-ENDPOINTS
# public_entrypoints:
#   - test_calendar_requires_auth
#   - test_calendar_requires_onboarding
#   - test_calendar_invalid_month_format
#   - test_calendar_out_of_range
#   - test_calendar_snapshot_state_matrix_and_preserved_fields
# semantic_blocks:
#   - AUTH_REQUIRED: verify 401 without session.
#   - VALIDATION: verify onboarding, format, and range errors.
#   - SNAPSHOT_STATE_MATRIX: hero/ordinary/not-computed and head selection.
#   - NO_COLD_CALCULATION: prove no legacy compute, sidecar, or scoring calls.
# owned_tests:
#   - self
# END_MODULE_MAP: TEST-CALENDAR-ENDPOINTS

from __future__ import annotations

from datetime import UTC, date as Date, datetime
from hashlib import sha256
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TodaySnapshot, User, UserProfile


NOW = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)


# START_BLOCK: TEST_DATA
async def _onboard_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
    user_id: int,
) -> User:
    raw = make_initdata(user_id=user_id)
    login = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert login.status_code == 200

    profile_response = await async_client.put(
        "/api/profile",
        json={
            "firstName": "Test User",
            "gender": "male",
            "birth": {
                "birthday": "1990-01-15",
                "birthTime": "14:30:00",
                "birthTimeMode": "exact",
                "birthCity": "Moscow",
                "birthLat": 55.7558,
                "birthLon": 37.6173,
                "birthTz": "Europe/Moscow",
            },
        },
    )
    assert profile_response.status_code == 200

    user = (
        await db_session.execute(select(User).where(User.tg_user_id == user_id))
    ).scalar_one()
    await db_session.execute(
        update(UserProfile).where(UserProfile.user_id == user.id).values(is_onboarded=True)
    )
    await db_session.commit()
    return user


def _snapshot(
    user_id,
    target_date: Date,
    *,
    state: str,
    day_tone: str = "steady",
    spheres: list[str] | None = None,
    impulses: list[dict[str, str]] | None = None,
    supersedes_snapshot_id=None,
    published_at: datetime = NOW,
) -> TodaySnapshot:
    snapshot_id = uuid4()
    input_hash = sha256(f"{snapshot_id}:{target_date}".encode()).hexdigest()
    return TodaySnapshot(
        id=snapshot_id,
        user_id=user_id,
        target_date=target_date,
        timezone="UTC",
        profile_hash="p" * 64,
        input_hash=input_hash,
        canon_hash="c" * 64,
        formula_version="today-convergence-2",
        calculation_version="calc-1",
        ephemeris_artifact_id="artifact-1",
        birth_time_mode="exact",
        birth_time_range={"start": "14:30", "end": "14:30"},
        deterministic_result_json={
            "state": state,
            "day_tone": day_tone,
            "selected": {
                "selected_spheres": spheres or [],
                "impulses": impulses or [],
            },
        },
        canonical_input_json={"target_date": target_date.isoformat()},
        published_at=published_at,
        supersedes_snapshot_id=supersedes_snapshot_id,
    )
# END_BLOCK: TEST_DATA


# START_BLOCK: AUTH_REQUIRED
@pytest.mark.asyncio
async def test_calendar_requires_auth(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/calendar?month=2026-05")
    assert response.status_code == 401
# END_BLOCK: AUTH_REQUIRED


# START_BLOCK: VALIDATION
@pytest.mark.asyncio
async def test_calendar_requires_onboarding(async_client: AsyncClient, make_initdata) -> None:
    login = await async_client.post(
        "/api/auth/telegram",
        json={"initData": make_initdata(user_id=7777)},
    )
    assert login.status_code == 200

    response = await async_client.get("/api/calendar?month=2026-05")
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "NOT_ONBOARDED"


@pytest.mark.asyncio
async def test_calendar_invalid_month_format(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    await _onboard_user(async_client, db_session, make_initdata, user_id=7778)

    for month in ("invalid", "2026/05", "2026"):
        response = await async_client.get(f"/api/calendar?month={month}")
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "INVALID_DATE"


@pytest.mark.asyncio
async def test_calendar_out_of_range(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    await _onboard_user(async_client, db_session, make_initdata, user_id=7779)

    for month in ("2030-01", "2020-01"):
        response = await async_client.get(f"/api/calendar?month={month}")
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "INVALID_DATE"
# END_BLOCK: VALIDATION


# START_BLOCK: SNAPSHOT_STATE_MATRIX
@pytest.mark.asyncio
async def test_calendar_snapshot_state_matrix_and_preserved_fields(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    user = await _onboard_user(async_client, db_session, make_initdata, user_id=7780)

    parent = _snapshot(user.id, Date(2026, 5, 5), state="quiet_day")
    child = _snapshot(
        user.id,
        Date(2026, 5, 5),
        state="convergence_today",
        spheres=["work", "decisions"],
        supersedes_snapshot_id=parent.id,
        published_at=datetime(2026, 7, 31, 11, 0, tzinfo=UTC),
    )
    ordinary = _snapshot(user.id, Date(2026, 5, 6), state="quiet_day")
    db_session.add_all([parent, child, ordinary])

    from app.services.access_service import AccessService

    await AccessService(db_session).grant_subscription(
        user.id,
        start_date=Date(2026, 5, 5),
        days=1,
    )
    await db_session.commit()

    from app.services.calendar_service import CalendarService

    legacy_compute = AsyncMock()
    sidecar = Mock()
    sidecar.get_transits = AsyncMock()
    with patch.object(CalendarService, "_compute_and_cache_day_status", legacy_compute), \
        patch("app.services.calendar_service.get_solarsage_client", return_value=sidecar), \
        patch("app.services.calendar_service.NormalizationService") as normalization, \
        patch("app.services.day_scoring_runtime_service.DayScoringRuntimeService") as scoring:
        response = await async_client.get("/api/calendar?month=2026-05")

    assert response.status_code == 200
    payload = response.json()
    days = {day["date"]: day for day in payload["days"]}

    assert days["2026-05-05"]["dayState"] == "hero"
    assert days["2026-05-06"]["dayState"] == "ordinary"
    assert days["2026-05-07"]["dayState"] == "not-computed"
    assert "dayStatus" not in days["2026-05-05"]

    may_fifth = days["2026-05-05"]
    assert may_fifth["access"]["state"] == "full"
    assert may_fifth["access"]["subscriptionActive"] is True
    assert set(may_fifth["lunar"]) == {
        "phase",
        "phaseIndex",
        "phaseLabel",
        "illumination",
        "moonSign",
        "moonSignLabel",
        "lunarDay",
        "voidOfCourse",
    }
    assert may_fifth["lunar"]["phase"] is not None
    assert payload["meta"]["schemaVersion"] == "calendar/v2"
    assert payload["month"] == "2026-05"
    assert len(payload["days"]) == 91

    legacy_compute.assert_not_awaited()
    normalization.assert_not_called()
    scoring.assert_not_called()
    sidecar.get_transits.assert_not_awaited()
# END_BLOCK: SNAPSHOT_STATE_MATRIX
