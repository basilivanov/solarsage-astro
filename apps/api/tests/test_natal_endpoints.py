# AI_HEADER
# module: M-TEST-NATAL-ENDPOINTS
# wave: W-NATAL-FULL
# purpose: Focused endpoint tests for natal preview chart contract and report id validation.

import uuid
from datetime import date, time
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


MOCK_SIDECAR_NATAL = {
    "house_system": "Placidus",
    "planets": [
        {"name": "Sun", "longitude": 10.0, "sign": "Aries", "house": 1, "retrograde": False, "speed": 1.0},
        {"name": "Moon", "longitude": 130.0, "sign": "Leo", "house": 5, "retrograde": False, "speed": 1.0},
        {"name": "Mercury", "longitude": 100.0, "sign": "Cancer", "house": 4, "retrograde": False, "speed": 1.0},
        {"name": "Venus", "longitude": 190.0, "sign": "Libra", "house": 7, "retrograde": False, "speed": 1.0},
        {"name": "Mars", "longitude": 280.0, "sign": "Capricorn", "house": 10, "retrograde": True, "speed": -0.5},
    ],
    "houses": [
        {"number": i, "longitude": float((i - 1) * 30), "sign": "Aries" if i == 1 else "Taurus"}
        for i in range(1, 13)
    ],
    "special_points": [
        {"name": "ASC", "longitude": 15.0, "sign": "Aries", "house": None},
        {"name": "MC", "longitude": 280.0, "sign": "Capricorn", "house": None},
    ],
}


async def _login(async_client: AsyncClient, make_initdata, *, user_id: int) -> None:
    raw = make_initdata(user_id=user_id, username=f"natalendpoint{user_id}")
    response = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert response.status_code == 200, response.text


async def _set_profile(db_session: AsyncSession, user_id, *, gender="female"):
    from app.services.profile_service import read_profile

    profile = await read_profile(db_session, user_id)
    profile.first_name = "Test"
    profile.birth_city = "Moscow"
    profile.birthday = date(1990, 1, 15)
    profile.birth_time = time(12, 0)
    profile.birth_tz = "Europe/Moscow"
    profile.gender = gender
    profile.birth_lat = Decimal("55.75580")
    profile.birth_lon = Decimal("37.61730")
    await db_session.commit()
    return profile


@pytest.mark.asyncio
async def test_natal_preview_exposes_chart_from_natal_context(
    async_client: AsyncClient,
    make_initdata,
    db_session: AsyncSession,
):
    from app.services.profile_service import get_or_create_user
    from app.services.telegram_auth import TelegramUser

    await _login(async_client, make_initdata, user_id=70701)
    tg = TelegramUser(id=70701, username="natalendpoint70701", first_name="Test")
    user, _ = await get_or_create_user(db_session, tg)
    await _set_profile(db_session, user.id, gender="female")

    with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
        mock_client = AsyncMock()
        mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
        mock_factory.return_value = mock_client

        response = await async_client.get("/api/natal/preview")

    assert response.status_code == 200, response.text
    body = response.json()
    chart = body["chart"]
    assert chart is not None
    assert chart["houseSystem"] == "Placidus"
    assert chart["planets"][0] == {
        "name": "Sun",
        "sign": "Aries",
        "degree": 10.0,
        "house": 1,
        "retrograde": False,
        "longitude": 10.0,
    }
    assert len(chart["houses"]) == 12
    assert chart["houses"][0] == {
        "number": 1,
        "sign": "Aries",
        "degree": 0.0,
        "longitude": 0.0,
    }
    assert {"name": "ASC", "sign": "Aries", "degree": 15.0, "longitude": 15.0} in chart["angles"]
    assert any(
        aspect["planetA"] == "Sun"
        and aspect["planetB"] == "Moon"
        and aspect["aspectType"] == "trine"
        for aspect in chart["aspects"]
    )
    assert chart["planets"] != []
    assert chart["angles"] != []


@pytest.mark.asyncio
async def test_natal_report_non_uuid_id_returns_stable_404(
    async_client: AsyncClient,
    make_initdata,
):
    from app.core.config import settings

    await _login(async_client, make_initdata, user_id=70702)

    original = settings.natal_report_enabled
    settings.natal_report_enabled = True
    try:
        response = await async_client.get("/api/natal/report/not-a-uuid")
    finally:
        settings.natal_report_enabled = original

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "REPORT_NOT_FOUND"


@pytest.mark.asyncio
async def test_natal_report_section_non_uuid_id_returns_stable_404(
    async_client: AsyncClient,
    make_initdata,
):
    from app.core.config import settings

    await _login(async_client, make_initdata, user_id=70703)

    original = settings.natal_report_enabled
    settings.natal_report_enabled = True
    try:
        response = await async_client.get("/api/natal/report/not-a-uuid/section/portrait")
    finally:
        settings.natal_report_enabled = original

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "REPORT_NOT_FOUND"
