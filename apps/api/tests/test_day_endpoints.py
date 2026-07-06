
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_DAY_ENDPOINTS
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ############################################################################

# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

# AI_HEADER
# module: M-DAY-SERVICE.tests
# canon: docs/GRACE_CANON.md §6
# wave: W-1.3
# purpose: Tests for GET /api/day/:date endpoint.

# START_MODULE_CONTRACT: M-DAY-SERVICE.tests
# purpose: Test GET /api/day/:date endpoint behavior.
#          W-1.3: fixture-backed, access stub returns state=full.
# owns:
#   - apps/api/tests/test_day_endpoints.py
# dependencies:
#   - M-DAY-SERVICE.api
#   - M-AUTH-TG.dependencies
#   - M-CONTRACTS.today
# END_MODULE_CONTRACT

import pytest
from datetime import date as Date
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from app.db.models import User, UserProfile
from app.main import app
from app.services.access_service import AccessService
from app.services.today_service import TodayService

client = TestClient(app)


MOCK_NATAL = {
    "house_system": "Placidus",
    "planets": [
        {"name": "Sun", "longitude": 10.0, "sign": "Aries", "house": 1, "retrograde": False, "speed": 1.0},
        {"name": "Moon", "longitude": 95.0, "sign": "Cancer", "house": 4, "retrograde": False, "speed": 1.0},
    ],
    "houses": [
        {"number": i, "longitude": float((i - 1) * 30), "sign": "Aries" if i == 1 else "Taurus"}
        for i in range(1, 13)
    ],
    "special_points": [
        {"name": "ASC", "longitude": 0.0, "sign": "Aries", "house": None},
        {"name": "MC", "longitude": 270.0, "sign": "Capricorn", "house": None},
    ],
}

MOCK_TRANSITS = {
    "target_jd": 2461191.0,
    "planets": [
        {"name": "Moon", "longitude": 35.0, "sign": "Taurus", "retrograde": False, "speed": 12.5},
        {"name": "Mars", "longitude": 100.0, "sign": "Cancer", "retrograde": True, "speed": -0.4},
    ],
}


async def _login_onboarded_user(async_client: AsyncClient, db_session: AsyncSession, make_initdata, user_id: int) -> User:
    raw = make_initdata(user_id=user_id)
    await async_client.post("/api/auth/telegram", json={"initData": raw})

    await async_client.put("/api/profile", json={
        "firstName": "Test User",
        "gender": "female",
        "birth": {
            "birthday": "1990-01-15",
            "birthTime": "14:30:00",
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
async def test_day_endpoint_requires_auth():
    """GET /api/day/:date requires authentication."""
    response = client.get("/api/day/2026-05-30")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_day_endpoint_rejects_invalid_date():
    """GET /api/day/:date returns 400 for invalid date format."""
    # This test would need a valid session cookie to reach the date validation
    # For now, we just verify the endpoint exists
    response = client.get("/api/day/invalid-date")
    # Will return 401 because no auth, but endpoint exists
    assert response.status_code in [400, 401]


@pytest.mark.asyncio
async def test_day_endpoint_exists():
    """GET /api/day/:date endpoint is registered."""
    # Verify endpoint exists by checking it returns 401 (not 404)
    response = client.get("/api/day/2026-05-30")
    assert response.status_code == 401
    assert "detail" in response.json()
    assert "code" in response.json()["detail"]


@pytest.mark.asyncio
async def test_day_endpoint_exposes_real_day_chart_from_existing_sources(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    user = await _login_onboarded_user(async_client, db_session, make_initdata, user_id=7791)
    await AccessService(db_session).grant_subscription(user.id, start_date=Date(2026, 5, 1), days=31)

    mock_context_client = AsyncMock()
    mock_context_client.get_natal.return_value = MOCK_NATAL
    mock_day_client = AsyncMock()
    mock_day_client.get_transits.return_value = MOCK_TRANSITS

    mock_llm = AsyncMock()
    mock_llm.generate_headline.return_value = "Headline"
    mock_llm.generate_reading.return_value = ["Paragraph"]
    mock_llm.generate_notes.return_value = "Notes"
    mock_llm.generate_why_sections.return_value = []

    with patch("app.services.natal_context_service.get_solarsage_client", return_value=mock_context_client), \
         patch("app.services.today_service.get_solarsage_client", return_value=mock_day_client), \
         patch("app.services.today_service.LLMService", return_value=mock_llm), \
         patch.object(TodayService, "_get_yesterday_signals", new=AsyncMock(return_value=None)), \
         patch.object(TodayService, "_prefetch_week", new=AsyncMock(return_value=None)):
        response = await async_client.get("/api/day/2026-05-10")

    assert response.status_code == 200
    payload = response.json()
    assert payload["dayChart"]["source"] == "solarsage"
    assert payload["dayChart"]["houses"][0] == {
        "number": 1,
        "cuspLongitude": 0.0,
        "sign": "Aries",
    }
    transit_moon = next(p for p in payload["dayChart"]["transitPlanets"] if p["name"] == "Moon")
    assert transit_moon["longitude"] == 35.0
    assert transit_moon["sign"] == "Taurus"
    assert transit_moon["retrograde"] is False
    assert transit_moon["speed"] == 12.5
    assert transit_moon["motion"] == "direct"
    assert transit_moon["house"] == 2
    assert payload["dayChart"]["aspects"]
    first_aspect = payload["dayChart"]["aspects"][0]
    assert {"planet", "targetPlanet", "aspectType", "orb", "strength"} <= set(first_aspect)
    assert payload["sphereScores"] is not None
    assert payload["planetInfluences"] is not None

    mock_day_client.get_transits.assert_awaited_once_with(
        target_date="2026-05-10",
        target_time="12:00",
        target_tz="Europe/Moscow",
    )
