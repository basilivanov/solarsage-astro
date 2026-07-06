# ############################################################################
# AI_HEADER: TEST_CALENDAR_ENDPOINTS
# ROLE: Integration tests for GET /api/calendar endpoint (W-1.4).
# DEPENDENCIES: pytest, httpx, app.api.calendar
# GRACE_ANCHORS: [AUTH_REQUIRED, INVALID_FORMAT, OUT_OF_RANGE, HAPPY_PATH]
# ############################################################################

# START_MODULE_CONTRACT: TEST_CALENDAR_ENDPOINTS
# purpose: Verify GET /api/calendar endpoint behavior.
#   W-1.4: neutral statuses, access stub, validation.
# owns:
#   - apps/api/tests/test_calendar_endpoints.py
# inputs:
#   - async_client: AsyncClient fixture
#   - db_session: AsyncSession fixture
#   - make_initdata: fixture for Telegram auth
# outputs:
#   - test results (pass/fail)
# dependencies:
#   - M-CALENDAR-API (calendar.router)
#   - M-AUTH-TG (require_session)
#   - M-PROFILE (onboarding)
# invariants:
#   - All tests go through Telegram auth (auth-first principle)
#   - Tests verify exit criteria from W-1.4
# failure_policy:
#   - Any test failure blocks W-1.4 completion
# non_goals:
#   - no visual regression (deferred to e2e)
#   - no performance testing (deferred)
# END_MODULE_CONTRACT: TEST_CALENDAR_ENDPOINTS

# START_MODULE_MAP: TEST_CALENDAR_ENDPOINTS
# public_entrypoints:
#   - test_calendar_requires_auth
#   - test_calendar_requires_onboarding
#   - test_calendar_invalid_month_format
#   - test_calendar_out_of_range
#   - test_calendar_happy_path
#   - test_calendar_structure
# semantic_blocks:
#   - AUTH_REQUIRED: verify 401 without session
#   - INVALID_FORMAT: verify 400 for bad format
#   - OUT_OF_RANGE: verify 400 for out of range
#   - HAPPY_PATH: verify 200 with valid data
# owned_tests:
#   - self (integration tests)
# END_MODULE_MAP

from __future__ import annotations

import json
from datetime import date as Date
from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# Helper to create onboarded user
async def _onboard_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
    user_id: int
):
    """Login and create onboarded profile."""
    from app.db.models import User, UserProfile
    from sqlalchemy import select, update

    # Login
    raw = make_initdata(user_id=user_id)
    await async_client.post("/api/auth/telegram", json={"initData": raw})

    # Create profile with birth data
    await async_client.put("/api/profile", json={
        "firstName": "Test User",
        "gender": "male",
        "birth": {
            "birthday": "1990-01-15",
            "birthTime": "14:30:00",
            "birthCity": "Moscow",
            "birthLat": 55.7558,
            "birthLon": 37.6173,
            "birthTz": "Europe/Moscow"
        }
    })

    # Manually set is_onboarded=True (simulating onboarding completion)
    # Find user by tg_user_id
    stmt = select(User).where(User.tg_user_id == user_id)
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        # Update profile to set is_onboarded=True
        stmt = update(UserProfile).where(UserProfile.user_id == user.id).values(is_onboarded=True)
        await db_session.execute(stmt)
        await db_session.commit()

    return user


# START_BLOCK: AUTH_REQUIRED
@pytest.mark.asyncio
async def test_calendar_requires_auth(async_client: AsyncClient) -> None:
    """Calendar endpoint requires session cookie."""
    r = await async_client.get("/api/calendar?month=2026-05")
    assert r.status_code == 401
# END_BLOCK: AUTH_REQUIRED


# START_BLOCK: ONBOARDING_REQUIRED
@pytest.mark.asyncio
async def test_calendar_requires_onboarding(
    async_client: AsyncClient,
    make_initdata,
) -> None:
    """Calendar endpoint requires onboarded user."""
    # Login without onboarding
    raw = make_initdata(user_id=7777)
    await async_client.post("/api/auth/telegram", json={"initData": raw})

    # Try to get calendar
    r = await async_client.get("/api/calendar?month=2026-05")
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "NOT_ONBOARDED"
# END_BLOCK: ONBOARDING_REQUIRED


# START_BLOCK: INVALID_FORMAT
@pytest.mark.asyncio
async def test_calendar_invalid_month_format(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    """Invalid month format → 400 INVALID_DATE."""
    # Login + onboard
    await _onboard_user(async_client, db_session, make_initdata, user_id=7778)

    # Invalid format (not a date)
    r = await async_client.get("/api/calendar?month=invalid")
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_DATE"

    # Invalid format (wrong separator)
    r = await async_client.get("/api/calendar?month=2026/05")
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_DATE"

    # Invalid format (incomplete)
    r = await async_client.get("/api/calendar?month=2026")
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_DATE"
# END_BLOCK: INVALID_FORMAT


# START_BLOCK: OUT_OF_RANGE
@pytest.mark.asyncio
async def test_calendar_out_of_range(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    """Month out of range → 400 INVALID_DATE."""
    # Login + onboard
    await _onboard_user(async_client, db_session, make_initdata, user_id=7779)

    # Out of range (2030)
    r = await async_client.get("/api/calendar?month=2030-01")
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_DATE"

    # Out of range (2020)
    r = await async_client.get("/api/calendar?month=2020-01")
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_DATE"
# END_BLOCK: OUT_OF_RANGE


# START_BLOCK: HAPPY_PATH
@pytest.mark.asyncio
async def test_calendar_happy_path(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    """Valid month → CalendarPayload with 3-month grid."""
    # Login + onboard
    await _onboard_user(async_client, db_session, make_initdata, user_id=7780)

    # Get calendar
    r = await async_client.get("/api/calendar?month=2026-05")
    assert r.status_code == 200

    payload = r.json()

    # Verify meta
    assert payload["meta"]["schemaVersion"] == "calendar/v1"
    assert payload["meta"]["contractVersion"] == 1
    assert "generatedAt" in payload["meta"]

    # Verify month
    assert payload["month"] == "2026-05"
    assert payload["title"] == "May 2026"

    # Verify allowed range
    assert "allowedRange" in payload
    assert "from" in payload["allowedRange"]
    assert "to" in payload["allowedRange"]

    # Verify days structure
    assert "days" in payload
    assert len(payload["days"]) > 0

    # Check that we have days from 3 months (April, May, June 2026)
    dates = [day["date"] for day in payload["days"]]
    assert any(date.startswith("2026-04") for date in dates)  # April
    assert any(date.startswith("2026-05") for date in dates)  # May
    assert any(date.startswith("2026-06") for date in dates)  # June
# END_BLOCK: HAPPY_PATH


# START_BLOCK: STRUCTURE_VALIDATION
@pytest.mark.asyncio
async def test_calendar_structure(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    """Calendar days preserve real access, scored status, and nullable lunar fields."""
    # Login + onboard
    user = await _onboard_user(async_client, db_session, make_initdata, user_id=7781)

    from app.db.models import SemanticLayerCache
    from app.services.access_service import AccessService

    await AccessService(db_session).grant_subscription(
        user.id,
        start_date=Date(2026, 5, 1),
        days=1,
    )

    for month in (4, 5, 6):
        from calendar import monthrange

        for day_number in range(1, monthrange(2026, month)[1] + 1):
            target_date = Date(2026, month, day_number)
            day_status = "supportive" if target_date == Date(2026, 5, 1) else "steady"
            db_session.add(SemanticLayerCache(
                user_id=user.id,
                target_date=target_date,
                semantic_json=json.dumps({
                    "day_status": day_status,
                    "day_theme": "Test",
                    "sphere_themes": [],
                    "top_keywords": [],
                }),
            ))
    await db_session.commit()

    # Get calendar
    r = await async_client.get("/api/calendar?month=2026-05")
    assert r.status_code == 200

    payload = r.json()

    # Verify each day has required real read-model fields.
    for day in payload["days"]:
        assert "date" in day
        assert "dayNumber" in day
        assert "isCurrentMonth" in day
        assert "isToday" in day
        assert "disabled" in day
        assert "dayStatus" in day
        assert "access" in day

        # Verify status is one of the allowed values
        assert day["dayStatus"] in ["supportive", "steady", "tense"]

        assert day["lunar"] == {
            "phase": None,
            "illumination": None,
            "moonSign": None,
            "lunarDay": None,
            "voidOfCourse": None,
        }

    may_first = next(day for day in payload["days"] if day["date"] == "2026-05-01")
    assert may_first["dayStatus"] == "supportive"
    assert may_first["access"]["state"] == "full"
    assert may_first["access"]["reason"] == "active_subscription"
    assert may_first["access"]["subscriptionActive"] is True

    may_second = next(day for day in payload["days"] if day["date"] == "2026-05-02")
    assert may_second["access"]["state"] == "preview"
    assert may_second["access"]["reason"] == "expired_access"
# END_BLOCK: STRUCTURE_VALIDATION


@pytest.mark.asyncio
async def test_calendar_status_cache_duplicate_rereads_winning_row(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    user = await _onboard_user(async_client, db_session, make_initdata, user_id=7782)

    from app.db.models import SemanticLayerCache, UserProfile
    from app.services.calendar_service import CalendarService

    target_date = Date(2026, 5, 3)
    db_session.add(SemanticLayerCache(
        user_id=user.id,
        target_date=target_date,
        semantic_json=json.dumps({
            "day_status": "tense",
            "day_theme": "winner",
            "sphere_themes": [],
            "top_keywords": [],
        }),
    ))
    await db_session.commit()

    profile = (
        await db_session.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    ).scalar_one()
    service = CalendarService(db_session)
    service._request_profile = profile
    service._request_natal_context = {"planets": [], "houses": []}

    mock_client = AsyncMock()
    mock_client.get_transits.return_value = {"planets": [{"name": "Moon", "longitude": 0.0, "sign": "Aries"}]}
    mock_semantic_layer = Mock()
    mock_semantic_layer.model_dump_json.return_value = json.dumps({
        "day_status": "supportive",
        "day_theme": "loser",
        "sphere_themes": [],
        "top_keywords": [],
    })

    with patch("app.services.calendar_service.get_solarsage_client", return_value=mock_client), \
         patch("app.services.calendar_service.NormalizationService") as normalization, \
         patch("app.services.calendar_service.ScoringService") as scoring, \
         patch("app.services.calendar_service.SemanticService") as semantic:
        normalization.return_value.normalize_day.return_value = []
        scoring.return_value.score_day.return_value = {
            "day_status": "supportive",
            "sphere_scores": {},
            "top_signals": [],
        }
        semantic.return_value.build_semantic_layer.return_value = mock_semantic_layer

        status = await service._compute_and_cache_day_status(user.id, target_date)

    assert status == "tense"
