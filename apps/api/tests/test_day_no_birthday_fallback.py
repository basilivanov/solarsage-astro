# AI_HEADER
# module: M-TEST-DAY-NO-BIRTHDAY-FALLBACK
# wave: W-NATAL-FULL (Wave 3 — day pipeline reuse)
# purpose: Tests for day endpoint — onboarding gate, birth coords requirement,
#          and proof that TodayService uses NatalContextService (not direct natal sidecar).

from __future__ import annotations

import uuid
from datetime import date as Date, time
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models import User, UserProfile
from app.schemas.access import ContentAccessState
from app.services.today_service import TodayService

from .test_horary_endpoints import _login


# ── Shared mock sidecar data (valid against SolarSageNatalResponse) ──────

MOCK_SIDECAR_NATAL = {
    "house_system": "Placidus",
    "planets": [
        {"name": "Sun", "longitude": 286.93, "sign": "Capricorn", "house": 11, "retrograde": False, "speed": 1.0},
        {"name": "Moon", "longitude": 119.63, "sign": "Gemini", "house": 4, "retrograde": False, "speed": 1.0},
        {"name": "Mercury", "longitude": 277.10, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 1.0},
        {"name": "Venus", "longitude": 333.55, "sign": "Pisces", "house": 12, "retrograde": False, "speed": 1.0},
        {"name": "Mars", "longitude": 137.95, "sign": "Cancer", "house": 5, "retrograde": True, "speed": -0.5},
        {"name": "Jupiter", "longitude": 193.95, "sign": "Libra", "house": 7, "retrograde": False, "speed": 0.2},
        {"name": "Saturn", "longitude": 327.02, "sign": "Aquarius", "house": 12, "retrograde": False, "speed": 0.1},
    ],
    "houses": [
        {"number": i, "longitude": float((i - 1) * 30), "sign": "Aries" if i == 1 else "Taurus"}
        for i in range(1, 13)
    ],
    "special_points": [
        {"name": "ASC", "longitude": 341.9, "sign": "Pisces", "house": None},
        {"name": "MC", "longitude": 260.5, "sign": "Sagittarius", "house": None},
    ],
}

MOCK_SIDECAR_TRANSITS = {
    "planets": [
        {"name": "Sun", "longitude": 80.0, "sign": "Gemini", "retrograde": False, "speed": 1.0},
        {"name": "Moon", "longitude": 200.0, "sign": "Libra", "retrograde": False, "speed": 1.0},
        {"name": "Mars", "longitude": 140.0, "sign": "Leo", "retrograde": False, "speed": 0.8},
    ],
}


@pytest.mark.asyncio
async def test_day_not_onboarded_without_birth_coords(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    await _login(async_client, make_initdata, user_id=401)

    user_id = (
        await db_session.execute(select(User.id).where(User.tg_user_id == 401))
    ).scalar_one()
    profile = (
        await db_session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    ).scalar_one()
    profile.is_onboarded = True
    profile.birthday = Date(1990, 6, 15)
    profile.birth_tz = "Europe/Moscow"
    profile.birthday_lat = Decimal("55.75580")
    profile.birthday_lon = Decimal("37.61730")
    profile.birth_lat = None
    profile.birth_lon = None
    await db_session.commit()

    r = await async_client.get("/api/day/today")
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "NOT_ONBOARDED"


@pytest.mark.asyncio
async def test_day_passes_with_real_birth_coords(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    """Day endpoint returns 200 when profile has birth coords.

    W-NATAL-FULL: TodayService now uses NatalContextService, not direct
    get_natal(). This test mocks the sidecar client at the context service
    level and verifies the endpoint works end-to-end.
    """
    await _login(async_client, make_initdata, user_id=402)

    user_id = (
        await db_session.execute(select(User.id).where(User.tg_user_id == 402))
    ).scalar_one()
    profile = (
        await db_session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    ).scalar_one()
    profile.is_onboarded = True
    profile.birthday = Date(1990, 6, 15)
    profile.birth_time = time(12, 0)
    profile.birth_tz = "Europe/Moscow"
    profile.current_tz = "Europe/Moscow"
    profile.gender = "female"
    profile.birth_lat = Decimal("55.75580")
    profile.birth_lon = Decimal("37.61730")
    profile.birthday_lat = Decimal("40.71280")
    profile.birthday_lon = Decimal("-74.00600")
    await db_session.commit()

    with patch("app.services.natal_context_service.get_solarsage_client") as mock_ctx_factory, \
         patch("app.services.today_service.get_solarsage_client") as mock_day_factory, \
         patch("app.services.today_service.NormalizationService") as mock_normalization_class, \
         patch("app.services.today_service.ScoringService") as mock_scoring_class, \
         patch("app.services.today_service.SemanticService") as mock_semantic_class, \
         patch("app.services.today_service.LLMService") as mock_llm_class, \
         patch("app.services.today_service.TodayImportantService") as mock_important_class, \
         patch.object(TodayService, "_get_yesterday_signals", new=AsyncMock(return_value=None)), \
         patch.object(TodayService, "_cache_semantic_layer", new=AsyncMock(return_value=None)), \
         patch.object(TodayService, "_cache_payload", new=AsyncMock(return_value=None)), \
         patch.object(TodayService, "_prefetch_week", new=AsyncMock(return_value=None)):

        # NatalContextService sidecar mock (for natal context)
        mock_ctx_client = AsyncMock()
        mock_ctx_client.get_natal.return_value = MOCK_SIDECAR_NATAL
        mock_ctx_factory.return_value = mock_ctx_client

        # TodayService sidecar mock (for transits only)
        mock_day_client = AsyncMock()
        mock_day_client.get_transits.return_value = MOCK_SIDECAR_TRANSITS
        mock_day_factory.return_value = mock_day_client

        mock_normalization = mock_normalization_class.return_value
        mock_normalization.normalize_day.return_value = []

        mock_scoring = mock_scoring_class.return_value
        mock_scoring.score_day.return_value = {
            "day_status": "steady",
            "sphere_scores": {},
            "top_signals": [],
        }

        mock_semantic = mock_semantic_class.return_value
        mock_semantic.build_semantic_layer.return_value = {}
        mock_semantic.build_why_contexts.return_value = []

        mock_llm = mock_llm_class.return_value
        mock_llm.generate_headline = AsyncMock(return_value="OK")
        mock_llm.generate_reading = AsyncMock(return_value=["OK"])
        mock_llm.generate_notes = AsyncMock(return_value="OK")
        mock_llm.generate_why_sections = AsyncMock(return_value=[])

        mock_important = mock_important_class.return_value
        mock_important.build_items.return_value = []

        r = await async_client.get("/api/day/today")
        assert r.status_code == 200

        # W-NATAL-FULL proof: TodayService does NOT call get_natal() directly.
        # It uses NatalContextService which handles natal sidecar calls.
        # The day_client only calls get_transits().
        mock_day_client.get_natal.assert_not_called()
        mock_day_client.get_transits.assert_called()


@pytest.mark.asyncio
async def test_today_service_raises_without_birth_coords(db_session) -> None:
    user_id = uuid.uuid4()
    profile = UserProfile(
        user_id=user_id,
        birthday=Date(1990, 6, 15),
        birth_tz="Europe/Moscow",
        birth_lat=None,
        birth_lon=None,
        birthday_lat=Decimal("55.75580"),
        birthday_lon=Decimal("37.61730"),
    )
    db_session.add(profile)
    await db_session.commit()

    service = TodayService(db_session)
    access_state = ContentAccessState(
        state="full",
        reason="active_subscription",
        referralDaysLeft=None,
        subscriptionActive=None,
        accessUntil=None,
    )

    with pytest.raises(HTTPException) as exc:
        await service.get_today_payload(user_id, Date(2026, 6, 9), access_state)

    assert exc.value.status_code == 409
    assert exc.value.detail == {
        "message": "Birth coordinates are required",
        "missingFields": ["birth_lat", "birth_lon"],
    }
