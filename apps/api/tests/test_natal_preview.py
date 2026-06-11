
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_NATAL_PREVIEW
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for natal_preview.py behavior
# owns:
#   - apps/api/tests/test_natal_preview.py
# inputs: Query params, models
# outputs: Records / query results
# dependencies: local modules
# side_effects: Database reads/writes; Network calls to API
# emitted_logs: n/a (tests)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# AI_HEADER
# module: M-TEST-NATAL-PREVIEW
# wave: W-NATAL-FULL
# purpose: Tests for GET /api/natal/preview — profile validation, gender wording,
#          sidecar error handling, response structure.

import uuid
from datetime import date as Date, time
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import AsyncClient


# ── Shared mock sidecar data (valid against SolarSageNatalResponse) ──────

MOCK_SIDECAR_NATAL = {
    "house_system": "Placidus",
    "planets": [
        {"name": "Sun", "longitude": 10.0, "sign": "Aries", "house": 1, "retrograde": False, "speed": 1.0},
        {"name": "Moon", "longitude": 40.0, "sign": "Taurus", "house": 2, "retrograde": False, "speed": 1.0},
        {"name": "Mercury", "longitude": 70.0, "sign": "Gemini", "house": 3, "retrograde": False, "speed": 1.0},
        {"name": "Venus", "longitude": 100.0, "sign": "Cancer", "house": 4, "retrograde": False, "speed": 1.0},
        {"name": "Mars", "longitude": 130.0, "sign": "Leo", "house": 5, "retrograde": True, "speed": -0.5},
        {"name": "Jupiter", "longitude": 200.0, "sign": "Libra", "house": 7, "retrograde": False, "speed": 0.2},
        {"name": "Saturn", "longitude": 300.0, "sign": "Aquarius", "house": 11, "retrograde": False, "speed": 0.1},
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
    raw = make_initdata(user_id=user_id, username=f"natal{user_id}")
    r = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert r.status_code == 200, r.text


async def _set_profile(
    db_session,
    user_id,
    *,
    gender=None,
    birth_lat=Decimal("55.7558"),
    birth_lon=Decimal("37.6173"),
):
    from app.services.profile_service import read_profile

    profile = await read_profile(db_session, user_id)
    profile.first_name = "Test"
    profile.birth_city = "Moscow"
    profile.birthday = Date(1990, 1, 15)
    profile.birth_time = time(12, 0)
    profile.birth_tz = "Europe/Moscow"
    profile.gender = gender
    profile.birth_lat = birth_lat
    profile.birth_lon = birth_lon
    await db_session.commit()
    return profile


def _mock_sidecar():
    """Return a context manager that patches the sidecar client in NatalContextService."""
    return patch("app.services.natal_context_service.get_solarsage_client")


@pytest.mark.asyncio
async def test_natal_preview_returns_409_without_gender(async_client: AsyncClient, make_initdata, db_session):
    await _login(async_client, make_initdata, user_id=30101)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user

    tg = TelegramUser(id=30101, username="natal30101", first_name="Test")
    user, _ = await get_or_create_user(db_session, tg)
    await _set_profile(db_session, user.id, gender=None)

    response = await async_client.get("/api/natal/preview")

    assert response.status_code == 409
    body = response.json()
    assert "gender" in body["detail"]["missingFields"]


@pytest.mark.asyncio
async def test_natal_preview_returns_409_without_birth_coords(async_client: AsyncClient, make_initdata, db_session):
    await _login(async_client, make_initdata, user_id=30102)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user

    tg = TelegramUser(id=30102, username="natal30102", first_name="Test")
    user, _ = await get_or_create_user(db_session, tg)
    await _set_profile(db_session, user.id, gender="male", birth_lat=None, birth_lon=None)

    response = await async_client.get("/api/natal/preview")

    assert response.status_code == 409
    body = response.json()
    assert "birth_lat" in body["detail"]["missingFields"]
    assert "birth_lon" in body["detail"]["missingFields"]


@pytest.mark.asyncio
async def test_natal_preview_returns_safe_error_on_sidecar_failure(async_client: AsyncClient, make_initdata, db_session):
    await _login(async_client, make_initdata, user_id=30103)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user

    tg = TelegramUser(id=30103, username="natal30103", first_name="Test")
    user, _ = await get_or_create_user(db_session, tg)
    await _set_profile(db_session, user.id, gender="male")

    with _mock_sidecar() as mock_factory:
        mock_client = AsyncMock()
        mock_client.get_natal.side_effect = httpx.ConnectError("raw sidecar boom text")
        mock_factory.return_value = mock_client

        response = await async_client.get("/api/natal/preview")

    assert response.status_code == 502
    body = response.json()
    assert body["detail"]["code"] == "SOLARSAGE_UNAVAILABLE"
    assert body["detail"]["message"]
    assert "raw sidecar boom text" not in str(body)


@pytest.mark.asyncio
async def test_natal_preview_price_is_99900(async_client: AsyncClient, make_initdata, db_session):
    await _login(async_client, make_initdata, user_id=30104)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user

    tg = TelegramUser(id=30104, username="natal30104", first_name="Test")
    user, _ = await get_or_create_user(db_session, tg)
    await _set_profile(db_session, user.id, gender="male")

    with _mock_sidecar() as mock_factory:
        mock_client = AsyncMock()
        mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
        mock_factory.return_value = mock_client

        response = await async_client.get("/api/natal/preview")

    assert response.status_code == 200
    assert response.json()["fullReportPriceKopecks"] == 99900


@pytest.mark.asyncio
async def test_natal_preview_male_gender_wording(async_client: AsyncClient, make_initdata, db_session):
    await _login(async_client, make_initdata, user_id=30105)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user

    tg = TelegramUser(id=30105, username="natal30105", first_name="Test")
    user, _ = await get_or_create_user(db_session, tg)
    await _set_profile(db_session, user.id, gender="male")

    with _mock_sidecar() as mock_factory:
        mock_client = AsyncMock()
        mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
        mock_factory.return_value = mock_client

        response = await async_client.get("/api/natal/preview")

    assert response.status_code == 200
    body = response.json()
    text = " ".join([
        body["personalHook"],
        *(item["description"] for item in body["highlights"]),
        *(item["description"] for item in body["spheres"]),
        *(item["description"] for item in body["planets"]),
        *(item["description"] for item in body["chapters"]),
        *body["salesBullets"],
    ])
    assert "ты собран" in text
    assert "ты собрана" not in text


@pytest.mark.asyncio
async def test_natal_preview_female_gender_wording(async_client: AsyncClient, make_initdata, db_session):
    await _login(async_client, make_initdata, user_id=30106)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user

    tg = TelegramUser(id=30106, username="natal30106", first_name="Test")
    user, _ = await get_or_create_user(db_session, tg)
    await _set_profile(db_session, user.id, gender="female")

    with _mock_sidecar() as mock_factory:
        mock_client = AsyncMock()
        mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
        mock_factory.return_value = mock_client

        response = await async_client.get("/api/natal/preview")

    assert response.status_code == 200
    body = response.json()
    text = " ".join([
        body["personalHook"],
        *(item["description"] for item in body["highlights"]),
        *(item["description"] for item in body["spheres"]),
        *(item["description"] for item in body["planets"]),
        *(item["description"] for item in body["chapters"]),
        *body["salesBullets"],
    ])
    assert "ты собрана" in text
    assert "ты собран:" not in text


@pytest.mark.asyncio
async def test_natal_preview_calculation_stats_bucket_350(async_client: AsyncClient, make_initdata, db_session):
    await _login(async_client, make_initdata, user_id=30107)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user
    from app.services.natal_service import _build_calculation_stats

    tg = TelegramUser(id=30107, username="natal30107", first_name="Test")
    user, _ = await get_or_create_user(db_session, tg)
    await _set_profile(db_session, user.id, gender="male")

    chart_data = {
        "planets": [{"name": f"P{i}", "longitude": float(i), "latitude": 0.0, "speed": 1.0, "sign": "Aries", "house": 1} for i in range(120)],
        "houses": [{"number": i, "cusp": float((i - 1) * 30)} for i in range(1, 121)],
        "special_points": [{"name": f"SP{i}", "longitude": float(i), "sign": "Aries"} for i in range(120)],
    }
    scores = {
        "sphere_scores": {f"sphere_{i}": 1.0 for i in range(10)},
        "top_signals": [{"id": f"sig_{i}"} for i in range(100)],
    }

    stats = _build_calculation_stats(chart_data, scores)

    assert stats.total_factors_count >= 350
    assert stats.display_label == "350+ факторов карты"


@pytest.mark.asyncio
async def test_natal_preview_calculation_stats_bucket_exact(async_client: AsyncClient, make_initdata, db_session):
    await _login(async_client, make_initdata, user_id=30108)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user
    from app.services.natal_service import _build_calculation_stats

    tg = TelegramUser(id=30108, username="natal30108", first_name="Test")
    user, _ = await get_or_create_user(db_session, tg)
    await _set_profile(db_session, user.id, gender="male")

    chart_data = {
        "planets": [
            {"name": "Sun", "longitude": 0.0},
            {"name": "Moon", "longitude": 120.0},
        ],
        "houses": [{"number": 1, "cusp": 0.0}, {"number": 2, "cusp": 180.0}],
        "special_points": [{"name": "ASC", "longitude": 0.0}],
    }
    scores = {
        "sphere_scores": {"career": 1.0},
        "top_signals": [{"id": "sig_1"}, {"id": "sig_2"}],
    }

    stats = _build_calculation_stats(chart_data, scores)

    assert stats.total_factors_count == 9
    assert stats.display_label == "9 факторов карты"


@pytest.mark.asyncio
async def test_natal_preview_returns_8_chapters(async_client: AsyncClient, make_initdata, db_session):
    await _login(async_client, make_initdata, user_id=30109)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user

    tg = TelegramUser(id=30109, username="natal30109", first_name="Test")
    user, _ = await get_or_create_user(db_session, tg)
    await _set_profile(db_session, user.id, gender="male")

    with _mock_sidecar() as mock_factory:
        mock_client = AsyncMock()
        mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
        mock_factory.return_value = mock_client

        response = await async_client.get("/api/natal/preview")

    assert response.status_code == 200
    chapters = response.json()["chapters"]
    assert len(chapters) == 8
    assert all(chapter["locked"] is True for chapter in chapters)


@pytest.mark.asyncio
async def test_natal_preview_returns_at_least_5_spheres(async_client: AsyncClient, make_initdata, db_session):
    await _login(async_client, make_initdata, user_id=30110)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user

    tg = TelegramUser(id=30110, username="natal30110", first_name="Test")
    user, _ = await get_or_create_user(db_session, tg)
    await _set_profile(db_session, user.id, gender="male")

    with _mock_sidecar() as mock_factory:
        mock_client = AsyncMock()
        mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
        mock_factory.return_value = mock_client

        response = await async_client.get("/api/natal/preview")

    assert response.status_code == 200
    assert len(response.json()["spheres"]) >= 5
