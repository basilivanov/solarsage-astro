"""Test fixtures for W-1.2: in-memory DB, async client, fake initData."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.session import Base, get_session
from app.main import app

BOT_TOKEN = "123456:test-bot-token"


@pytest.fixture(autouse=True)
def _force_test_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Real bot token + insecure cookies so HMAC is enforced and httpx
    keeps the cookie across requests under http://testserver."""
    monkeypatch.setattr(settings, "telegram_bot_token", BOT_TOKEN)
    monkeypatch.setattr(settings, "app_env", "test")
    monkeypatch.setattr(settings, "telegram_auth_max_age_seconds", 3600)
    monkeypatch.setattr(settings, "session_cookie_secure", False)


@pytest_asyncio.fixture()
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture()
async def async_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """httpx.AsyncClient over ASGITransport with overridden DB dependency."""

    async def _override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


# --- fake initData --------------------------------------------------------

def _sign(parsed: dict[str, str], bot_token: str = BOT_TOKEN) -> str:
    items = sorted((k, v) for k, v in parsed.items() if k != "hash")
    data_check_string = "\n".join(f"{k}={v}" for k, v in items)
    secret = hmac.new(
        b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256
    ).digest()
    return hmac.new(
        secret, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def fake_initdata(
    user_id: int = 7777,
    *,
    username: str | None = "ada",
    first_name: str | None = "Ada",
    auth_date: int | None = None,
    extra: dict[str, str] | None = None,
    bot_token: str = BOT_TOKEN,
    sign: bool = True,
) -> str:
    user: dict[str, Any] = {"id": user_id}
    if first_name is not None:
        user["first_name"] = first_name
    if username is not None:
        user["username"] = username
    parsed = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAH-deadbeef",
        "user": json.dumps(user, separators=(",", ":")),
    }
    if extra:
        parsed.update(extra)
    if sign:
        parsed["hash"] = _sign(parsed, bot_token)
    return "&".join(f"{k}={v}" for k, v in parsed.items())


@pytest.fixture()
def make_initdata():
    """Factory fixture: tests can call make_initdata(user_id=42, ...)."""
    return fake_initdata
