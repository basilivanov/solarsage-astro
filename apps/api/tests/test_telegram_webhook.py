# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_TELEGRAM_WEBHOOK
# ROLE: Contract tests for the Telegram /start webhook responder.
# DEPENDENCIES: pytest, pytest-asyncio, httpx, unittest.mock
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TELEGRAM-WEBHOOK
# purpose: Prove the webhook secret gate is fail-closed and constant-time
#   (missing/wrong/empty-config secret -> 403), /start in a private chat gets
#   the exact canonical start copy and inline WebApp button (payload included),
#   all other valid updates get an empty 200, the start text matches the repo
#   bot-profile byte-exactly, and no PII/raw update reaches the logs.
# owns:
#   - apps/api/tests/test_telegram_webhook.py
# inputs: HTTP posts to /api/telegram/webhook via async_client
# outputs: pytest assertions
# dependencies: conftest fixtures (async_client), repo bot-profile.json
# side_effects: none (endpoint is stateless; no DB)
# emitted_logs: n/a (tests)
# invariants:
#   - no real Bot API call; the secret value never appears in assertions
# failure_policy: assertion failure on contract violation
# END_MODULE_CONTRACT: M-TEST-TELEGRAM-WEBHOOK

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.api.telegram_webhook import START_TEXT, START_BUTTON_TEXT

REPO_ROOT = Path(__file__).resolve().parents[3]
WEBHOOK = "/api/telegram/webhook"
SECRET = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


@pytest.fixture()
def secret_configured(monkeypatch):
    monkeypatch.setattr(settings, "telegram_webhook_secret", SECRET)
    monkeypatch.setattr(settings, "app_domain", "astro.vasiliy-ivanov.ru")


def _start_update(chat_id: int = 123456789, text: str = "/start", chat_type: str = "private") -> dict:
    return {"update_id": 1, "message": {
        "message_id": 1, "text": text,
        "chat": {"id": chat_id, "type": chat_type},
        "from": {"id": 987654321, "first_name": "Smoke", "username": "pii_user"},
    }}


@pytest.mark.asyncio
async def test_missing_secret_header_rejected(async_client: AsyncClient, secret_configured) -> None:
    resp = await async_client.post(WEBHOOK, json=_start_update())
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_wrong_secret_header_rejected(async_client: AsyncClient, secret_configured) -> None:
    resp = await async_client.post(
        WEBHOOK, json=_start_update(),
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_empty_configured_secret_fails_closed(async_client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "telegram_webhook_secret", "")
    resp = await async_client.post(
        WEBHOOK, json=_start_update(),
        headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_start_returns_exact_copy_and_button(async_client: AsyncClient, secret_configured) -> None:
    resp = await async_client.post(
        WEBHOOK, json=_start_update(chat_id=424242),
        headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["method"] == "sendMessage"
    assert body["chat_id"] == 424242
    assert body["text"] == START_TEXT
    button = body["reply_markup"]["inline_keyboard"][0][0]
    assert button["text"] == START_BUTTON_TEXT
    assert button["web_app"]["url"] == "https://astro.vasiliy-ivanov.ru/day/today"


@pytest.mark.asyncio
async def test_start_with_payload_also_answered(async_client: AsyncClient, secret_configured) -> None:
    resp = await async_client.post(
        WEBHOOK, json=_start_update(text="/start 8541896258"),
        headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
    )
    assert resp.status_code == 200
    assert resp.json()["method"] == "sendMessage"


@pytest.mark.asyncio
async def test_group_start_is_ack_empty(async_client: AsyncClient, secret_configured) -> None:
    resp = await async_client.post(
        WEBHOOK, json=_start_update(chat_type="group"),
        headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
    )
    assert resp.status_code == 200
    assert resp.json() == {}


@pytest.mark.asyncio
async def test_non_start_private_message_ack_empty(async_client: AsyncClient, secret_configured) -> None:
    resp = await async_client.post(
        WEBHOOK, json=_start_update(text="привет"),
        headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
    )
    assert resp.status_code == 200
    assert resp.json() == {}


@pytest.mark.asyncio
async def test_non_message_update_ack_empty(async_client: AsyncClient, secret_configured) -> None:
    resp = await async_client.post(
        WEBHOOK, json={"update_id": 2, "poll": {"id": "x"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
    )
    assert resp.status_code == 200
    assert resp.json() == {}


@pytest.mark.asyncio
async def test_callback_query_happy_path(async_client: AsyncClient, secret_configured, make_initdata, db_session) -> None:
    # Create user with tg_user_id 987654321
    raw_init = make_initdata(user_id=987654321, username="test_cq_user")
    await async_client.post("/api/auth/telegram", json={"initData": raw_init})

    cq_update = {
        "update_id": 100,
        "callback_query": {
            "id": "cq_12345",
            "from": {"id": 987654321, "first_name": "Test"},
            "data": "fb:acc:2026-07-22:3",
        },
    }
    resp = await async_client.post(
        WEBHOOK, json=cq_update,
        headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "method": "answerCallbackQuery",
        "callback_query_id": "cq_12345",
        "text": "Записал ✨",
    }


@pytest.mark.asyncio
async def test_callback_query_invalid_data_or_unknown_user(async_client: AsyncClient, secret_configured) -> None:
    # Invalid data format
    cq_invalid = {
        "update_id": 101,
        "callback_query": {
            "id": "cq_12345",
            "from": {"id": 999999999, "first_name": "Test"},
            "data": "invalid_data",
        },
    }
    resp = await async_client.post(
        WEBHOOK, json=cq_invalid,
        headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
    )
    assert resp.status_code == 200
    assert resp.json() == {}

    # Valid data format, but user not found in DB
    cq_unknown_user = {
        "update_id": 102,
        "callback_query": {
            "id": "cq_12345",
            "from": {"id": 888888888, "first_name": "Unknown"},
            "data": "fb:acc:2026-07-22:2",
        },
    }
    resp = await async_client.post(
        WEBHOOK, json=cq_unknown_user,
        headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
    )
    assert resp.status_code == 200
    assert resp.json() == {}


@pytest.mark.asyncio
async def test_malformed_json_rejected(async_client: AsyncClient, secret_configured) -> None:
    resp = await async_client.post(
        WEBHOOK,
        content=b"{not json",
        headers={"X-Telegram-Bot-Api-Secret-Token": SECRET, "Content-Type": "application/json"},
    )
    assert resp.status_code == 400


def test_start_text_matches_repo_bot_profile() -> None:
    # The runtime start copy must equal the repo canonical start_copy.text.
    profile = json.loads((REPO_ROOT / "scripts" / "telegram" / "bot-profile.json").read_text(encoding="utf-8"))
    assert START_TEXT == profile["start_copy"]["text"]
    assert START_BUTTON_TEXT == profile["start_copy"]["cta"]["text"]


@pytest.mark.asyncio
async def test_no_pii_or_raw_update_in_logs(async_client: AsyncClient, secret_configured, caplog) -> None:
    with caplog.at_level("DEBUG"):
        resp = await async_client.post(
            WEBHOOK, json=_start_update(),
            headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
        )
    assert resp.status_code == 200
    assert "987654321" not in caplog.text
    assert "pii_user" not in caplog.text
    assert SECRET not in caplog.text
