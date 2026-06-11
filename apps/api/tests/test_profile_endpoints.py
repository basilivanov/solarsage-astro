
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_PROFILE_ENDPOINTS
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Module — apps/api/tests/test_profile_endpoints.py
# owns:
#   - apps/api/tests/test_profile_endpoints.py
# inputs: varies
# outputs: varies
# dependencies: local modules
# side_effects: varies
# emitted_logs: n/a
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

"""Endpoint tests for /api/profile (W-1.2)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


_BANNED_KEYS = frozenset(
    {
        "tg_user_id",
        "tgUserId",
        "token_hash",
        "tokenHash",
        "init_data",
        "initData",
        "hash",
        "email",
        "phone",
        "phone_number",
    }
)


async def _login(async_client: AsyncClient, make_initdata, *, user_id: int = 42) -> None:
    raw = make_initdata(user_id=user_id, username="ada")
    r = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_profile_requires_session(async_client: AsyncClient) -> None:
    r = await async_client.get("/api/profile")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "MISSING"


@pytest.mark.asyncio
async def test_get_profile_creates_empty(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=42)
    r = await async_client.get("/api/profile")
    assert r.status_code == 200
    body = r.json()
    assert body["firstName"] is None
    assert body["birth"]["birthday"] is None
    assert body["birth"]["birthTz"] is None


@pytest.mark.asyncio
async def test_put_profile_round_trip(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=42)
    payload = {
        "firstName": "Ada",
        "birth": {
            "birthday": "1985-12-10",
            "birthTime": "12:00:00",
            "birthCity": "London",
            "birthLat": 51.5074,
            "birthLon": -0.1278,
            "birthTz": "Europe/London",
        },
        "currentLocation": {
            "city": "Lisbon, Portugal",
            "lat": 38.7223,
            "lon": -9.1393,
            "tz": "Europe/Lisbon",
        },
        "birthdayLocation": {
            "city": "London, UK",
            "lat": 51.5074,
            "lon": -0.1278,
            "tz": "Europe/London",
        },
    }
    r1 = await async_client.put("/api/profile", json=payload)
    assert r1.status_code == 200, r1.text
    body = r1.json()
    assert body["firstName"] == "Ada"
    assert body["birth"]["birthday"] == "1985-12-10"
    assert body["birth"]["birthTz"] == "Europe/London"
    assert body["currentLocation"]["city"] == "Lisbon, Portugal"
    assert body["currentLocation"]["lat"] == pytest.approx(38.7223)
    assert body["currentLocation"]["tz"] == "Europe/Lisbon"
    assert body["birthdayLocation"]["city"] == "London, UK"

    r2 = await async_client.get("/api/profile")
    assert r2.status_code == 200
    assert r2.json()["currentLocation"]["city"] == "Lisbon, Portugal"
    assert r2.json()["birthdayLocation"]["city"] == "London, UK"


@pytest.mark.asyncio
async def test_put_profile_invalid_tz_is_422(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=42)
    r = await async_client.put(
        "/api/profile",
        json={"birth": {"birthTz": "Mars/Olympus"}},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_put_profile_lat_without_lon_is_422(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=42)
    r = await async_client.put(
        "/api/profile",
        json={"birth": {"birthLat": 51.0}},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_put_profile_birthday_before_1900_is_422(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=42)
    r = await async_client.put(
        "/api/profile",
        json={"birth": {"birthday": "1899-12-31"}},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_put_profile_lat_out_of_range_is_422(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=42)
    r = await async_client.put(
        "/api/profile",
        json={"birth": {"birthLat": 200.0, "birthLon": 0.0}},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_n_privacy_no_forbidden_keys_in_response(
    async_client: AsyncClient, make_initdata
) -> None:
    """N-PRIVACY: ProfileRead must not echo tg_user_id / tokens / etc."""
    await _login(async_client, make_initdata, user_id=12345)
    r = await async_client.get("/api/profile")
    assert r.status_code == 200
    body = r.json()

    def _walk(obj: object) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                assert k not in _BANNED_KEYS, f"forbidden key in response: {k}"
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(body)
    # And the literal tg_user_id value must not appear anywhere.
    import json as _json

    assert "12345" not in _json.dumps(body)


@pytest.mark.asyncio
async def test_put_profile_location_lat_without_lon_is_422(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=42)
    r = await async_client.put(
        "/api/profile",
        json={"currentLocation": {"city": "Berlin", "lat": 52.52}},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_put_profile_location_invalid_tz_is_422(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=42)
    r = await async_client.put(
        "/api/profile",
        json={
            "currentLocation": {
                "city": "Berlin",
                "lat": 52.52,
                "lon": 13.405,
                "tz": "Mars/Olympus",
            }
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_put_profile_location_lat_out_of_range_is_422(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=42)
    r = await async_client.put(
        "/api/profile",
        json={
            "currentLocation": {
                "city": "Nowhere",
                "lat": 200.0,
                "lon": 0.0,
                "tz": "UTC",
            }
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_put_profile_all_three_locations_with_tz(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=99)
    payload = {
        "birth": {
            "birthday": "1990-06-15",
            "birthTime": "14:30:00",
            "birthCity": "Monchegorsk, Russia",
            "birthLat": 67.93972,
            "birthLon": 32.87389,
            "birthTz": "Europe/Moscow",
        },
        "currentLocation": {
            "city": "Sochi, Russia",
            "lat": 43.59699,
            "lon": 39.72477,
            "tz": "Europe/Moscow",
        },
        "birthdayLocation": {
            "city": "Sochi, Russia",
            "lat": 43.59699,
            "lon": 39.72477,
            "tz": "Europe/Moscow",
        },
    }
    r = await async_client.put("/api/profile", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["birth"]["birthTz"] == "Europe/Moscow"
    assert body["birth"]["birthCity"] == "Monchegorsk, Russia"
    assert body["currentLocation"]["tz"] == "Europe/Moscow"
    assert body["currentLocation"]["city"] == "Sochi, Russia"
    assert body["birthdayLocation"]["tz"] == "Europe/Moscow"

    r2 = await async_client.get("/api/profile")
    assert r2.status_code == 200
    body2 = r2.json()

    assert body2["birth"]["birthTz"] == "Europe/Moscow"
    assert body2["currentLocation"]["tz"] == "Europe/Moscow"
    assert body2["birthdayLocation"]["tz"] == "Europe/Moscow"


@pytest.mark.asyncio
async def test_put_profile_location_without_tz_is_ok(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=42)
    r = await async_client.put(
        "/api/profile",
        json={
            "currentLocation": {
                "city": "Berlin",
                "lat": 52.52,
                "lon": 13.405,
            }
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["currentLocation"]["tz"] is None
    assert body["currentLocation"]["city"] == "Berlin"


@pytest.mark.asyncio
async def test_put_profile_partial_location_update_preserves_fields(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=55)

    r1 = await async_client.put(
        "/api/profile",
        json={
            "birth": {
                "birthday": "1985-03-20",
                "birthTime": "10:00:00",
                "birthCity": "London",
                "birthLat": 51.51,
                "birthLon": -0.13,
                "birthTz": "Europe/London",
            },
            "currentLocation": {
                "city": "Paris",
                "lat": 48.86,
                "lon": 2.35,
                "tz": "Europe/Paris",
            },
        },
    )
    assert r1.status_code == 200

    r2 = await async_client.put(
        "/api/profile",
        json={
            "currentLocation": {
                "city": "Berlin",
                "lat": 52.52,
                "lon": 13.41,
                "tz": "Europe/Berlin",
            }
        },
    )
    assert r2.status_code == 200
    body = r2.json()

    assert body["birth"]["birthTz"] == "Europe/London"
    assert body["birth"]["birthCity"] == "London"
    assert body["currentLocation"]["tz"] == "Europe/Berlin"
    assert body["currentLocation"]["city"] == "Berlin"


@pytest.mark.asyncio
async def test_put_profile_same_as_birth_copies_tz(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=77)
    payload = {
        "birth": {
            "birthday": "2000-01-01",
            "birthTime": "06:00:00",
            "birthCity": "Tokyo, Japan",
            "birthLat": 35.68,
            "birthLon": 139.69,
            "birthTz": "Asia/Tokyo",
        },
        "currentLocation": {
            "city": "Tokyo, Japan",
            "lat": 35.68,
            "lon": 139.69,
            "tz": "Asia/Tokyo",
        },
    }
    r = await async_client.put("/api/profile", json=payload)
    assert r.status_code == 200
    body = r.json()

    assert body["birth"]["birthTz"] == "Asia/Tokyo"
    assert body["currentLocation"]["tz"] == "Asia/Tokyo"
    assert body["currentLocation"]["city"] == "Tokyo, Japan"
