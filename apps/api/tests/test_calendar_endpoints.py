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
    assert payload["meta"]["contractVersion"] == 2
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
    """Calendar days preserve real access, scored status, and populated lunar fields."""
    # Login + onboard
    user = await _onboard_user(async_client, db_session, make_initdata, user_id=7781)

    from app.db.models import SemanticLayerCache, UserProfile
    from app.services.natal_context_service import NatalContextService
    from app.services.today_service import TODAY_CONTENT_VERSION
    from app.services.access_service import AccessService

    await AccessService(db_session).grant_subscription(
        user.id,
        start_date=Date(2026, 5, 1),
        days=1,
    )

    profile = (
        await db_session.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    ).scalar_one()
    profile_hash = NatalContextService.compute_profile_hash(profile)

    from app.services.cache_key_service import build_today_cache_key
    from app.services.day_scoring_runtime_service import selected_scoring_version_for_flags

    for month in (4, 5, 6):
        from calendar import monthrange

        for day_number in range(1, monthrange(2026, month)[1] + 1):
            target_date = Date(2026, month, day_number)
            day_status = "supportive" if target_date == Date(2026, 5, 1) else "steady"
            ck = build_today_cache_key(
                user_id=user.id,
                target_date=target_date.isoformat(),
                profile_hash=profile_hash,
                scoring_version=selected_scoring_version_for_flags(),
            )
            db_session.add(SemanticLayerCache(
                user_id=user.id,
                target_date=target_date,
                semantic_json=json.dumps({
                    "profile_hash": profile_hash,
                    "content_version": TODAY_CONTENT_VERSION,
                    "semantic_layer": {
                        "day_status": day_status,
                        "day_theme": "Test",
                        "sphere_themes": [],
                        "top_keywords": [],
                    },
                    "cache_key_hash": ck.cache_key_hash,
                    "calculation_version": ck.calculation_version,
                    "activation_layer_version": ck.activation_layer_version,
                    "scoring_version": str(ck.scoring_version),
                    "canon_versions_hash": ck.canon_versions_hash,
                    "llm_prompt_version": ck.llm_prompt_version,
                    "frontend_payload_version": ck.frontend_payload_version,
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

        assert set(day["lunar"]) == {
            "phase",
            "phaseIndex",
            "phaseLabel",
            "illumination",
            "moonSign",
            "moonSignLabel",
            "lunarDay",
            "voidOfCourse",
        }
        assert day["lunar"]["phase"] in {
            "new_moon",
            "waxing_crescent",
            "first_quarter",
            "waxing_gibbous",
            "full_moon",
            "waning_gibbous",
            "last_quarter",
            "waning_crescent",
        }
        assert 0 <= day["lunar"]["phaseIndex"] <= 7
        assert isinstance(day["lunar"]["phaseLabel"], str)
        assert 0 <= day["lunar"]["illumination"] <= 100
        assert isinstance(day["lunar"]["moonSign"], str)
        assert isinstance(day["lunar"]["moonSignLabel"], str)
        assert 1 <= day["lunar"]["lunarDay"] <= 30
        assert day["lunar"]["voidOfCourse"] in (True, False)

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
    from app.services.natal_context_service import NatalContextService
    from app.services.today_service import TODAY_CONTENT_VERSION

    profile = (
        await db_session.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    ).scalar_one()
    profile_hash = NatalContextService.compute_profile_hash(profile)

    target_date = Date(2026, 5, 3)
    db_session.add(SemanticLayerCache(
        user_id=user.id,
        target_date=target_date,
        semantic_json=json.dumps({
            "profile_hash": profile_hash,
            "content_version": TODAY_CONTENT_VERSION,
            "semantic_layer": {
                "day_status": "tense",
                "day_theme": "winner",
                "sphere_themes": [],
                "top_keywords": [],
            }
        }),
    ))
    await db_session.commit()
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
         patch("app.services.day_scoring_runtime_service.DayScoringRuntimeService") as runtime_mock, \
         patch("app.services.calendar_service.SemanticService") as semantic:
        normalization.return_value.normalize_day.return_value = []
        dual_result_mock = Mock()
        dual_result_mock.selected_result = {
            "day_status": "supportive",
            "sphere_scores": {},
            "top_signals": [],
        }
        dual_result_mock.selected_scoring_version = 1
        runtime_mock.return_value.compute.return_value = dual_result_mock
        semantic.return_value.build_semantic_layer.return_value = mock_semantic_layer

        status = await service._compute_and_cache_day_status(user.id, target_date)

    assert status == "supportive"

    reread_status = await service._get_cached_day_status(user.id, target_date)
    assert reread_status == "supportive"


@pytest.mark.asyncio
async def test_calendar_cached_day_status_ignores_old_today_payload_content_version(
    db_session: AsyncSession,
) -> None:
    from app.db.models import TodayPayloadCache, User
    from app.services.calendar_service import CalendarService

    user = User(tg_user_id=7783)
    db_session.add(user)
    await db_session.flush()

    db_session.add(TodayPayloadCache(
        user_id=user.id,
        target_date=Date(2026, 7, 7),
        profile_hash="profile-hash",
        payload_json=json.dumps({
            "meta": {"contentVersion": 1},
            "dayStatus": "tense",
        }),
    ))
    await db_session.commit()

    service = CalendarService(db_session)
    service._request_profile_hash = "profile-hash"

    status = await service._get_cached_day_status(user.id, Date(2026, 7, 7))

    assert status is None


@pytest.mark.asyncio
async def test_calendar_cached_day_status_ignores_old_today_payload_snake_case_content_version(
    db_session: AsyncSession,
) -> None:
    from app.db.models import TodayPayloadCache, User
    from app.services.calendar_service import CalendarService

    user = User(tg_user_id=7785)
    db_session.add(user)
    await db_session.flush()

    db_session.add(TodayPayloadCache(
        user_id=user.id,
        target_date=Date(2026, 7, 7),
        profile_hash="profile-hash",
        payload_json=json.dumps({
            "meta": {"content_version": 1},
            "day_status": "tense",
        }),
    ))
    await db_session.commit()

    service = CalendarService(db_session)
    service._request_profile_hash = "profile-hash"

    status = await service._get_cached_day_status(user.id, Date(2026, 7, 7))

    assert status is None


@pytest.mark.asyncio
async def test_calendar_cached_day_status_reads_current_today_payload_content_version(
    db_session: AsyncSession,
) -> None:
    from app.db.models import TodayPayloadCache, User
    from app.services.calendar_service import CalendarService
    from app.services.today_service import TODAY_CONTENT_VERSION
    from app.services.cache_key_service import build_today_cache_key
    from app.services.day_scoring_runtime_service import selected_scoring_version_for_flags

    user = User(tg_user_id=7784)
    db_session.add(user)
    await db_session.flush()

    ck = build_today_cache_key(
        user_id=user.id,
        target_date="2026-07-07",
        profile_hash="profile-hash",
        scoring_version=selected_scoring_version_for_flags(),
    )

    db_session.add(TodayPayloadCache(
        user_id=user.id,
        target_date=Date(2026, 7, 7),
        profile_hash="profile-hash",
        cache_key_hash=ck.cache_key_hash,
        calculation_version=ck.calculation_version,
        scoring_version=str(ck.scoring_version),
        canon_versions_hash=ck.canon_versions_hash,
        llm_prompt_version=ck.llm_prompt_version,
        frontend_payload_version=ck.frontend_payload_version,
        payload_json=json.dumps({
            "meta": {"contentVersion": TODAY_CONTENT_VERSION},
            "dayStatus": "supportive",
        }),
    ))
    await db_session.commit()

    service = CalendarService(db_session)
    service._request_profile_hash = "profile-hash"

    status = await service._get_cached_day_status(user.id, Date(2026, 7, 7))

    assert status == "supportive"


@pytest.mark.asyncio
async def test_calendar_cached_day_status_ignores_unversioned_semantic_layer(
    db_session: AsyncSession,
) -> None:
    from app.db.models import SemanticLayerCache, User
    from app.services.calendar_service import CalendarService

    user = User(tg_user_id=7787)
    db_session.add(user)
    await db_session.flush()

    db_session.add(SemanticLayerCache(
        user_id=user.id,
        target_date=Date(2026, 7, 7),
        semantic_json=json.dumps({
            "day_status": "tense",
            "day_theme": "legacy unversioned",
            "sphere_themes": [],
            "top_keywords": [],
        }),
    ))
    await db_session.commit()

    service = CalendarService(db_session)
    service._request_profile_hash = "profile-hash"

    status = await service._get_cached_day_status(user.id, Date(2026, 7, 7))

    assert status is None


@pytest.mark.asyncio
async def test_calendar_scoring_ignores_natal_signals(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    """Verify that calendar day status computation uses filter_day_scored_signals.
    If full mixed signals are scored, it would result in a different status
    compared to scoring only filtered day signals.
    """
    user = await _onboard_user(async_client, db_session, make_initdata, user_id=7786)

    from app.db.models import UserProfile
    from app.services.calendar_service import CalendarService

    profile = (
        await db_session.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    ).scalar_one()

    service = CalendarService(db_session)
    service._request_profile = profile
    service._request_natal_context = {"planets": [], "houses": []}

    # Set up transit/natal signals:
    # 1. A Transit signal: Transit_Mars square Saturn (tense)
    # 2. A Natal signal: Natal_Venus conjunct Jupiter (supportive)
    # If both are scored, they might cancel out or result in 'steady'.
    # If only transit is scored, it will be 'tense'.
    from app.schemas.normalization import AstroSignal

    mixed_signals = [
        AstroSignal(
            type="aspect",
            planet="Transit_Mars",
            target_planet="Saturn",
            aspect_type="square",
            orb=1.0,
            strength=1.0,
        ),
        AstroSignal(
            type="aspect",
            planet="Transit_Sun",
            target_planet="Jupiter",
            aspect_type="square",
            orb=1.0,
            strength=1.0,
        ),
        AstroSignal(
            type="aspect",
            planet="Natal_Venus",
            target_planet="Jupiter",
            aspect_type="trine",
            orb=0.5,
            strength=1.0,
        ),
        AstroSignal(
            type="aspect",
            planet="Natal_Moon",
            target_planet="Sun",
            aspect_type="trine",
            orb=0.5,
            strength=1.0,
        )
    ]

    mock_client = AsyncMock()
    mock_client.get_transits.return_value = {"planets": []}

    with patch("app.services.calendar_service.get_solarsage_client", return_value=mock_client), \
         patch("app.services.calendar_service.NormalizationService") as normalization:
        # Return mixed signals containing the static Natal signal
        normalization.return_value.normalize_day.return_value = mixed_signals

        # Compute status
        status = await service._compute_and_cache_day_status(user.id, Date(2026, 5, 4))

    # The result must be tense because Natal_Venus (the supportive aspect) was filtered out,
    # leaving only Transit_Mars square Saturn.
    assert status == "tense"
