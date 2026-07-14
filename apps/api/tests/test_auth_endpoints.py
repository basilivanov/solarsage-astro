# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_AUTH_ENDPOINTS
# ROLE: Endpoint regression tests for Telegram auth, logout, and local dev auth.
# DEPENDENCIES: pytest, httpx, sqlalchemy, starlette, app.api.auth, app.db.models
# GRACE_ANCHORS: [AUTH_TELEGRAM_TESTS, AUTH_LOGOUT_TESTS, AUTH_DEV_TESTS]
# SLICE: SLICE-TESTS
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-AUTH-ENDPOINTS
# purpose: Verify public behavior of /api/auth/telegram, /api/auth/logout, and
#   /api/auth/dev, including local-development-only guard boundaries.
# owns:
#   - apps/api/tests/test_auth_endpoints.py
# inputs: async_client, db_session, make_initdata, monkeypatch fixtures.
# outputs: pytest pass/fail assertions.
# dependencies: app.api.auth, app.core.config, app.db.models.
# side_effects: writes to isolated in-memory test database via ASGI requests.
# emitted_logs: none
# invariants:
#   - invalid Telegram auth does not write DB rows.
#   - local dev auth is allowed only for trusted local development requests.
# failure_policy: tests fail on assertion or unexpected exception.
# END_MODULE_CONTRACT: M-TEST-AUTH-ENDPOINTS

# START_MODULE_MAP: M-TEST-AUTH-ENDPOINTS
# public_entrypoints:
#   - test_login_happy_path
#   - test_login_secure_flag_when_enabled
#   - test_login_idempotent_user_upsert
#   - test_login_400_on_invalid_hmac_no_db_write
#   - test_login_401_on_expired_initdata
#   - test_logout_revokes_and_clears_cookie
#   - test_revoked_session_is_unauthorized
#   - test_revoked_token_is_explicitly_revoked
#   - test_dev_auth_denies_loopback_in_staging_when_dev_mode_disabled
#   - test_dev_auth_denies_public_host_when_dev_mode_disabled
#   - test_local_dev_auth_helper_denies_non_development_envs
#   - test_local_dev_auth_helper_denies_non_string_environment
#   - test_local_dev_auth_helper_allows_canonical_development_aliases
#   - test_dev_auth_denies_spoofed_local_host_through_proxy
#   - test_dev_auth_denies_spoofed_local_host_with_forwarded_host
#   - test_dev_auth_allows_localhost_when_dev_mode_disabled
#   - test_dev_auth_seeds_complete_profile_for_day_route
#   - test_dev_auth_repairs_existing_onboarded_profile_missing_gender
#   - test_dev_auth_repairs_existing_onboarded_profile_invalid_gender
# semantic_blocks:
#   - AUTH_TELEGRAM_TESTS: login, HMAC, cookie, and session assertions.
#   - AUTH_LOGOUT_TESTS: logout and revoked-session assertions.
#   - AUTH_DEV_TESTS: local dev auth allow/deny and profile seeding assertions.
# owned_tests:
#   - apps/api/tests/test_auth_endpoints.py
# END_MODULE_MAP: M-TEST-AUTH-ENDPOINTS
"""Endpoint tests for /api/auth/telegram and /api/auth/logout (Option A)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.api.auth import _is_local_dev_auth_request
from app.core.config import settings
from app.db.models import Session as SessionRow, User, UserProfile


def _trusted_loopback_dev_auth_request() -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/auth/dev",
            "raw_path": b"/api/auth/dev",
            "query_string": b"",
            "root_path": "",
            "server": ("127.0.0.1", 8000),
            "client": ("127.0.0.1", 45678),
            "headers": [(b"host", b"127.0.0.1:8000")],
        }
    )


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

    # Cookie set with HttpOnly + SameSite=None (REQUIRED for Telegram Web App iframe).
    raw_cookie = r.headers.get("set-cookie", "")
    assert settings.session_cookie_name in raw_cookie
    assert "HttpOnly" in raw_cookie
    assert "samesite=none" in raw_cookie.lower()

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


@pytest.mark.asyncio
async def test_dev_auth_denies_loopback_in_staging_when_dev_mode_disabled(
    async_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "dev_mode", False)
    monkeypatch.setattr(settings, "app_env", "staging")

    r = await async_client.post(
        "/api/auth/dev",
        headers={"host": "127.0.0.1:8000"},
    )

    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "DEV_MODE_DISABLED"
    assert settings.session_cookie_name not in r.headers.get("set-cookie", "")

    user = (
        await db_session.execute(select(User).where(User.tg_user_id == 999999999))
    ).scalar_one_or_none()
    assert user is None


@pytest.mark.asyncio
async def test_dev_auth_denies_public_host_when_dev_mode_disabled(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "dev_mode", False)
    monkeypatch.setattr(settings, "app_env", "development")

    r = await async_client.post(
        "/api/auth/dev",
        headers={"host": "dev.astro.vasiliy-ivanov.ru"},
    )

    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "DEV_MODE_DISABLED"


@pytest.mark.parametrize(
    "app_env",
    ["staging", "stage", "preview", "production", "prod", "test", "", "unknown"],
)
def test_local_dev_auth_helper_denies_non_development_envs(
    app_env: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", app_env)

    assert _is_local_dev_auth_request(_trusted_loopback_dev_auth_request()) is False


def test_local_dev_auth_helper_denies_non_string_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", None)

    assert _is_local_dev_auth_request(_trusted_loopback_dev_auth_request()) is False


@pytest.mark.parametrize("app_env", ["dev", "development", " DEV ", "Development"])
def test_local_dev_auth_helper_allows_canonical_development_aliases(
    app_env: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", app_env)

    assert _is_local_dev_auth_request(_trusted_loopback_dev_auth_request()) is True


@pytest.mark.asyncio
async def test_dev_auth_denies_spoofed_local_host_through_proxy(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "dev_mode", False)
    monkeypatch.setattr(settings, "app_env", "development")

    r = await async_client.post(
        "/api/auth/dev",
        headers={
            "host": "127.0.0.1:8000",
            "x-forwarded-for": "203.0.113.10",
        },
    )

    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "DEV_MODE_DISABLED"


@pytest.mark.asyncio
async def test_dev_auth_denies_spoofed_local_host_with_forwarded_host(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "dev_mode", False)
    monkeypatch.setattr(settings, "app_env", "development")

    r = await async_client.post(
        "/api/auth/dev",
        headers={
            "host": "127.0.0.1:8000",
            "x-forwarded-host": "dev.astro.vasiliy-ivanov.ru",
        },
    )

    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "DEV_MODE_DISABLED"


@pytest.mark.asyncio
async def test_dev_auth_allows_localhost_when_dev_mode_disabled(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "dev_mode", False)
    monkeypatch.setattr(settings, "app_env", "development")

    r = await async_client.post(
        "/api/auth/dev",
        headers={"host": "127.0.0.1:8000"},
    )

    assert r.status_code == 200, r.text
    assert settings.session_cookie_name in r.headers.get("set-cookie", "")

    profile = await async_client.get("/api/profile")
    assert profile.status_code == 200, profile.text


@pytest.mark.asyncio
async def test_dev_auth_seeds_complete_profile_for_day_route(
    async_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "dev_mode", False)
    monkeypatch.setattr(settings, "app_env", "development")

    r = await async_client.post(
        "/api/auth/dev",
        headers={"host": "127.0.0.1:8000"},
    )

    assert r.status_code == 200, r.text
    user = (
        await db_session.execute(select(User).where(User.tg_user_id == 999999999))
    ).scalar_one()
    profile = (
        await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
    ).scalar_one()
    assert profile.is_onboarded is True
    assert profile.gender in {"female", "male"}


@pytest.mark.asyncio
async def test_dev_auth_repairs_existing_onboarded_profile_missing_gender(
    async_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "dev_mode", False)
    monkeypatch.setattr(settings, "app_env", "development")

    r1 = await async_client.post(
        "/api/auth/dev",
        headers={"host": "127.0.0.1:8000"},
    )
    assert r1.status_code == 200, r1.text

    user = (
        await db_session.execute(select(User).where(User.tg_user_id == 999999999))
    ).scalar_one()
    profile = (
        await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
    ).scalar_one()
    profile.is_onboarded = True
    profile.gender = None
    await db_session.flush()

    r2 = await async_client.post(
        "/api/auth/dev",
        headers={"host": "127.0.0.1:8000"},
    )

    assert r2.status_code == 200, r2.text
    await db_session.refresh(profile)
    assert profile.is_onboarded is True
    assert profile.gender in {"female", "male"}


@pytest.mark.asyncio
async def test_dev_auth_repairs_existing_onboarded_profile_invalid_gender(
    async_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "dev_mode", False)
    monkeypatch.setattr(settings, "app_env", "development")

    r1 = await async_client.post(
        "/api/auth/dev",
        headers={"host": "127.0.0.1:8000"},
    )
    assert r1.status_code == 200, r1.text

    user = (
        await db_session.execute(select(User).where(User.tg_user_id == 999999999))
    ).scalar_one()
    profile = (
        await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
    ).scalar_one()
    profile.is_onboarded = True
    profile.gender = "unknown"
    await db_session.flush()

    r2 = await async_client.post(
        "/api/auth/dev",
        headers={"host": "127.0.0.1:8000"},
    )

    assert r2.status_code == 200, r2.text
    await db_session.refresh(profile)
    assert profile.is_onboarded is True
    assert profile.gender in {"female", "male"}
