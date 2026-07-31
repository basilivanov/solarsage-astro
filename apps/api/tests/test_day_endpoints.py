
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_DAY_ENDPOINTS
# ROLE: Legacy TodayService unit canaries plus the small day HTTP boundary.
# DEPENDENCIES: local modules and the public Today convergence envelope.
# GRACE_ANCHORS: [DAY_HTTP_BOUNDARY]
# SLICE: W-TODAY-CONVERGENCE-REWRITE
# ############################################################################

# AI_HEADER
# module: M-API-DAY.tests
# canon: docs/GRACE_CANON.md §6
# wave: W-TODAY-CONVERGENCE-REWRITE (P4-D2)
# purpose: Preserve TodayService unit canaries and test the new day HTTP boundary.

# START_MODULE_CONTRACT: M-API-DAY.tests
# purpose: Test stable TodayService internals and the GET /api/day/:date
#   authentication/validation/envelope boundary.
# owns:
#   - apps/api/tests/test_day_endpoints.py
# dependencies:
#   - M-API-DAY
#   - M-AUTH-TG.dependencies
#   - M-CONTRACTS.today-convergence
# END_MODULE_CONTRACT: M-API-DAY.tests

# START_MODULE_MAP: M-API-DAY.tests
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - TODAY_SERVICE_CANARIES: unchanged legacy service unit coverage.
#   - DAY_HTTP_BOUNDARY: auth, invalid date, and new envelope route contract.
# owned_tests:
#   - self
# END_MODULE_MAP: M-API-DAY.tests

import json
from datetime import date as Date
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TodayPayloadCache, User, UserProfile
from app.schemas.normalization import AstroSignal
from app.services.today_service import TODAY_CONTENT_VERSION, TodayService


def test_today_service_formats_top_flags_for_users() -> None:
    """TopFlags should be localized user text, not raw technical signal labels."""
    top_flags = TodayService._build_top_flags([
        AstroSignal(
            type="aspect",
            planet="Transit_Sun",
            target_planet="Natal_Mercury",
            aspect_type="trine",
            orb=0.4,
            strength=0.95,
        ),
        AstroSignal(
            type="aspect",
            planet="Transit_Mars",
            target_planet="Natal_Saturn",
            aspect_type="square",
            orb=1.2,
            strength=0.88,
        ),
        AstroSignal(
            type="planet_in_house",
            planet="Natal_Moon",
            house=4,
            strength=0.7,
        ),
    ])

    assert [flag.title for flag in top_flags] == [
        "Солнце тригон Меркурий",
        "Марс квадратура Сатурн",
        "Луна в 4 доме",
    ]
    for flag in top_flags:
        assert "Transit_" not in flag.title
        assert "Natal_" not in flag.title
        assert "Sun trine Mercury" not in flag.title
        assert "Orb:" not in flag.summary
        assert "Strength:" not in flag.summary
        assert "0.4" not in flag.summary
        assert "0.95" not in flag.summary


@pytest.mark.asyncio
async def test_today_service_ignores_cached_payload_with_old_content_version(db_session: AsyncSession) -> None:
    service = TodayService(db_session)
    assert TODAY_CONTENT_VERSION == 12

    user = User(tg_user_id=919191)
    db_session.add(user)
    await db_session.flush()

    old_payload = {
        "meta": {
            "schemaVersion": "today/v1",
            "contractVersion": 2,
            "calculationVersion": 1,
            "normalizationVersion": 1,
            "scoringVersion": 1,
            "promptVersion": 1,
            "contentVersion": 1,
            "generatedAt": "2026-07-05T18:53:25Z",
            "cached": False,
        },
        "date": "2026-07-07",
        "title": "Сегодня",
        "subtitle": None,
        "headline": "Old payload",
        "access": {
            "state": "full",
            "reason": "active_subscription",
            "referralDaysLeft": None,
            "subscriptionActive": True,
            "accessUntil": None,
        },
        "dayStatus": "steady",
        "dayQuality": None,
        "topFlags": [
            {
                "iconName": "Sun-trine",
                "title": "Sun trine Mercury",
                "summary": "Orb: 0.4°, Strength: 0.95",
                "hint": None,
            }
        ],
        "reading": {"paragraphs": ["old"]},
        "notes": "old",
        "whyThisHappens": {"sections": []},
        "weekStrip": [],
        "microcopy": [],
        "yesterdayEcho": None,
        "actions": None,
    }
    db_session.add(TodayPayloadCache(
        user_id=user.id,
        target_date=Date(2026, 7, 7),
        profile_hash="profile-hash",
        payload_json=json.dumps(old_payload),
    ))
    await db_session.commit()

    cached = await service._get_cached_payload(user.id, Date(2026, 7, 7), "profile-hash")

    assert cached is None


@pytest.mark.asyncio
async def test_today_service_ignores_cached_payload_with_old_snake_case_content_version(db_session: AsyncSession) -> None:
    service = TodayService(db_session)

    user = User(tg_user_id=919192)
    db_session.add(user)
    await db_session.flush()

    old_payload = {
        "meta": {
            "schema_version": "today/v1",
            "contract_version": 2,
            "calculation_version": 1,
            "normalization_version": 1,
            "scoring_version": 1,
            "prompt_version": 1,
            "content_version": 1,
            "generated_at": "2026-07-05T18:53:25Z",
            "cached": False,
        },
        "date": "2026-07-07",
        "title": "Сегодня",
        "subtitle": None,
        "headline": "Old payload",
        "access": {
            "state": "full",
            "reason": "active_subscription",
            "referral_days_left": None,
            "subscription_active": True,
            "access_until": None,
        },
        "day_status": "steady",
        "day_quality": None,
        "top_flags": [
            {
                "icon_name": "Sun-trine",
                "title": "Sun trine Mercury",
                "summary": "Orb: 0.4°, Strength: 0.95",
                "hint": None,
            }
        ],
        "reading": {"paragraphs": ["old"]},
        "notes": "old",
        "why_this_happens": {"sections": []},
        "week_strip": [],
        "microcopy": [],
        "yesterday_echo": None,
        "actions": None,
    }
    db_session.add(TodayPayloadCache(
        user_id=user.id,
        target_date=Date(2026, 7, 7),
        profile_hash="profile-hash",
        payload_json=json.dumps(old_payload),
    ))
    await db_session.commit()

    cached = await service._get_cached_payload(user.id, Date(2026, 7, 7), "profile-hash")

    assert cached is None


@pytest.mark.asyncio
async def test_today_service_ignores_malformed_cached_payload_with_old_content_version(db_session: AsyncSession) -> None:
    service = TodayService(db_session)

    user = User(tg_user_id=919193)
    db_session.add(user)
    await db_session.flush()

    db_session.add(TodayPayloadCache(
        user_id=user.id,
        target_date=Date(2026, 7, 7),
        profile_hash="profile-hash",
        payload_json=json.dumps({
            "meta": {"contentVersion": 1},
            "topFlags": [{"title": "Sun trine Mercury", "summary": "Orb: 0.4°, Strength: 0.95"}],
        }),
    ))
    await db_session.commit()

    cached = await service._get_cached_payload(user.id, Date(2026, 7, 7), "profile-hash")

    assert cached is None


async def _login_onboarded_user(async_client: AsyncClient, db_session: AsyncSession, make_initdata, user_id: int) -> User:
    raw = make_initdata(user_id=user_id)
    await async_client.post("/api/auth/telegram", json={"initData": raw})

    await async_client.put("/api/profile", json={
        "firstName": "Test User",
        "gender": "female",
        "birth": {
            "birthday": "1990-01-15",
            "birthTime": "14:30:00",
            "birthTimeMode": "exact",
            "birthCity": "Moscow",
            "birthLat": 55.7558,
            "birthLon": 37.6173,
            "birthTz": "Europe/Moscow",
        },
    })

    result = await db_session.execute(select(User).where(User.tg_user_id == user_id))
    user = result.scalar_one()
    await db_session.execute(
        update(UserProfile).where(UserProfile.user_id == user.id).values(is_onboarded=True)
    )
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_day_endpoint_requires_auth(async_client: AsyncClient):
    """GET /api/day/:date requires authentication."""
    response = await async_client.get("/api/day/2026-05-30")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_day_endpoint_rejects_invalid_date(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
):
    """GET /api/day/:date returns 422 for malformed date after auth."""
    await _login_onboarded_user(async_client, db_session, make_initdata, user_id=7790)
    response = await async_client.get("/api/day/not-a-date")
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_DATE"


@pytest.mark.asyncio
async def test_day_endpoint_returns_new_convergence_envelope(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
    monkeypatch,
):
    """The route serializes the new envelope and no legacy Today wire fields."""
    await _login_onboarded_user(async_client, db_session, make_initdata, user_id=7791)
    payload = json.loads(
        (Path(__file__).parent / "fixtures/contracts/today-convergence-full-hero-ready.json")
        .read_text(encoding="utf-8")
    )
    from app.schemas.today_convergence import TodayConvergencePayload

    typed_payload = TodayConvergencePayload.model_validate(payload)
    serve = AsyncMock(return_value=(typed_payload, None))
    monkeypatch.setattr("app.api.day._serve_day", serve)

    response = await async_client.get("/api/day/2026-05-30")

    assert response.status_code == 200
    body = response.json()
    assert body["schemaVersion"] == 1
    assert body["contentState"] == "ready"
    assert "dayStatus" not in body
    assert "topFlags" not in body
    serve.assert_awaited_once()


@pytest.mark.asyncio
async def test_day_retry_endpoint_is_registered(async_client: AsyncClient):
    response = await async_client.post("/api/day/2026-05-30/retry")
    assert response.status_code == 401
