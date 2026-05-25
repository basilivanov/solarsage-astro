"""Endpoint tests for /api/auth/telegram and /api/auth/logout (Option A)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Session as SessionRow, User


@pytest.mark.asyncio
async def test_login_happy_path(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    raw = make_initdata(user_id=555, first_name="Alan", username="alan")
    r = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["isNewUser"] is True
    assert body["userId"]
    assert "expiresAt" in body

    # Cookie set with HttpOnly + SameSite=Lax (Secure asserted in a
    # dedicated test that toggles SESSION_COOKIE_SECURE).
    raw_cookie = r.headers.get("set-cookie", "")
    assert settings.session_cookie_name in raw_cookie
    assert "HttpOnly" in raw_cookie
    assert "SameSite=lax" in raw_cookie.lower() or "samesite=lax" in raw_cookie.lower()

    # users + sessions rows landed; tokens are stored hashed (sha256-hex 64).
    user = (
        await db_session.execute(select(User).where(User.tg_user_id == 555))
    ).scalar_one()
    assert user.tg_username == "alan"

    sessions = (await db_session.execute(select(SessionRow))).scalars().all()
    assert len(sessions) == 1
    assert len(sessions[0].token_hash) == 64
    assert sessions[0].user_id == user.id


@pytest.mark.asyncio
async def test_login_secure_flag_when_enabled(
    async_client: AsyncClient,
    make_initdata,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "session_cookie_secure", True)
    raw = make_initdata(user_id=12, username="ada")
    r = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert r.status_code == 200
    set_cookie = r.headers["set-cookie"]
    assert "Secure" in set_cookie
    assert "HttpOnly" in set_cookie


@pytest.mark.asyncio
async def test_login_idempotent_user_upsert(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    raw1 = make_initdata(user_id=9, first_name="First", username="first")
    r1 = await async_client.post("/api/auth/telegram", json={"initData": raw1})
    assert r1.status_code == 200
    assert r1.json()["isNewUser"] is True

    raw2 = make_initdata(user_id=9, first_name="Second", username="ada")
    r2 = await async_client.post("/api/auth/telegram", json={"initData": raw2})
    assert r2.status_code == 200
    assert r2.json()["isNewUser"] is False

    users = (await db_session.execute(select(User))).scalars().all()
    assert len(users) == 1
    assert users[0].tg_username == "ada"
    sessions = (await db_session.execute(select(SessionRow))).scalars().all()
    assert len(sessions) == 2  # one per login (Option A spec)


@pytest.mark.asyncio
async def test_login_400_on_invalid_hmac_no_db_write(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    raw = make_initdata(user_id=314)
    bad = raw.replace("hash=", "hash=0", 1)
    if bad == raw:
        bad = raw[:-1] + ("0" if raw[-1] != "0" else "1")
    r = await async_client.post("/api/auth/telegram", json={"initData": bad})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_HMAC"

    users = (await db_session.execute(select(User))).scalars().all()
    sessions = (await db_session.execute(select(SessionRow))).scalars().all()
    assert users == []
    assert sessions == []


@pytest.mark.asyncio
async def test_login_401_on_expired_initdata(
    async_client: AsyncClient,
    make_initdata,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import time as _time
    monkeypatch.setattr(settings, "telegram_auth_max_age_seconds", 60)
    raw = make_initdata(user_id=1, auth_date=int(_time.time()) - 3600)
    r = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "INITDATA_EXPIRED"


@pytest.mark.asyncio
async def test_logout_revokes_and_clears_cookie(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    raw = make_initdata(user_id=42, username="ada")
    r = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert r.status_code == 200

    r2 = await async_client.post("/api/auth/logout")
    assert r2.status_code == 204
    set_cookie = r2.headers.get("set-cookie", "")
    assert settings.session_cookie_name in set_cookie
    assert "max-age=0" in set_cookie.lower() or "Max-Age=0" in set_cookie

    sessions = (await db_session.execute(select(SessionRow))).scalars().all()
    assert len(sessions) == 1
    assert sessions[0].revoked_at is not None


@pytest.mark.asyncio
async def test_revoked_session_is_unauthorized(
    async_client: AsyncClient,
    make_initdata,
) -> None:
    raw = make_initdata(user_id=42, username="ada")
    r = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert r.status_code == 200

    r2 = await async_client.post("/api/auth/logout")
    assert r2.status_code == 204

    # Re-issue the same cookie (httpx client cleared it on logout); we
    # construct the request explicitly with the previous token hashed-server-side.
    # Simpler: any subsequent /api/profile with no cookie is 401 MISSING.
    r3 = await async_client.get("/api/profile")
    assert r3.status_code == 401
    assert r3.json()["detail"]["code"] == "MISSING"


@pytest.mark.asyncio
async def test_revoked_token_is_explicitly_revoked(
    async_client: AsyncClient,
    make_initdata,
) -> None:
    """Replay the exact same cookie post-logout: must yield 401 REVOKED."""
    raw = make_initdata(user_id=99, username="bob")
    r = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert r.status_code == 200
    cookie_value = async_client.cookies.get(settings.session_cookie_name)
    assert cookie_value

    r2 = await async_client.post("/api/auth/logout")
    assert r2.status_code == 204

    # Manually re-set the cookie and try /api/profile.
    async_client.cookies.set(settings.session_cookie_name, cookie_value)
    r3 = await async_client.get("/api/profile")
    assert r3.status_code == 401
    assert r3.json()["detail"]["code"] == "REVOKED"
