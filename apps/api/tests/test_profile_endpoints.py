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
    }
    r1 = await async_client.put("/api/profile", json=payload)
    assert r1.status_code == 200, r1.text
    body = r1.json()
    assert body["firstName"] == "Ada"
    assert body["birth"]["birthday"] == "1985-12-10"
    assert body["birth"]["birthTz"] == "Europe/London"

    r2 = await async_client.get("/api/profile")
    assert r2.status_code == 200
    assert r2.json() == body


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
