# ############################################################################
# AI_HEADER: MODULE_API_TELEGRAM_WEBHOOK
# ROLE: Telegram Bot webhook responder — canonical /start without Ductor.
# DEPENDENCIES: fastapi, hmac, app.core.config
# GRACE_ANCHORS: [TELEGRAM_WEBHOOK]
# ############################################################################

# START_MODULE_CONTRACT: M-API-TELEGRAM-WEBHOOK
# purpose: Receive Telegram Bot API webhook updates and answer ONLY private
#   /start messages with the canonical start copy and an inline WebApp button.
#   Telegram executes the returned sendMessage itself, so no outbound Bot API
#   call is needed from this host.
# owns:
#   - apps/api/app/api/telegram_webhook.py
# inputs:
#   - POST /api/telegram/webhook with X-Telegram-Bot-Api-Secret-Token header
# outputs:
#   - Bot API method JSON (sendMessage) for /start; empty JSON otherwise
# dependencies:
#   - M-CONFIG (settings.telegram_webhook_secret, settings.app_domain)
# side_effects: none (stateless; no DB, no network, no file access)
# emitted_logs: none (no PII and no raw update bodies are logged anywhere)
# invariants:
#   - Secret check is constant-time (hmac.compare_digest) and fail-closed:
#     an empty configured secret rejects every request with 403.
#   - Only private message updates whose text starts with "/start" (payload
#     included) get a sendMessage reply; every other valid update gets 200 {}.
#   - The start text is the canonical start_copy, sync-tested against
#     scripts/telegram/bot-profile.json.
#   - The button opens https://<APP_DOMAIN>/day/today as a WebApp.
# failure_policy:
#   - missing/wrong secret header -> 403; malformed JSON -> 400.
# END_MODULE_CONTRACT: M-API-TELEGRAM-WEBHOOK

# START_MODULE_MAP: M-API-TELEGRAM-WEBHOOK
# public_entrypoints:
#   - telegram_webhook
# semantic_blocks:
#   - START_COPY: canonical start text and button
#   - WEBHOOK_ENDPOINT: secret gate and update handling
# owned_tests:
#   - apps/api/tests/test_telegram_webhook.py
# END_MODULE_MAP: M-API-TELEGRAM-WEBHOOK

import hmac
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings

router = APIRouter(tags=["telegram"])

# START_BLOCK: START_COPY
# Canonical start copy — the single runtime source; the test suite proves it
# matches scripts/telegram/bot-profile.json start_copy.text byte-exactly.
START_TEXT = (
    "Привет! ✨ Это твой день по натальной карте — что поддержит сегодня и где лучше не спешить. "
    "Нажми кнопку — начнём."
)
START_BUTTON_TEXT = "Мой день ✨"
# END_BLOCK: START_COPY


# START_BLOCK: WEBHOOK_ENDPOINT
@router.post("/api/telegram/webhook")
async def telegram_webhook(request: Request) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-API-TELEGRAM-WEBHOOK.telegram_webhook
    # purpose: Verify the Telegram secret header (constant-time, fail-closed)
    #   and answer private /start messages with the canonical start copy plus
    #   an inline WebApp button; ack every other valid update with {}.
    # inputs: raw HTTP request (header + JSON update body).
    # returns: Bot API method JSON or empty dict.
    # side_effects: none.
    # emitted_logs: none — no PII, no raw update bodies.
    # error_behavior: 403 on missing/wrong secret; 400 on malformed JSON.
    # END_FUNCTION_CONTRACT: F-M-API-TELEGRAM-WEBHOOK.telegram_webhook
    configured = settings.telegram_webhook_secret
    provided = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not configured or not provided or not hmac.compare_digest(provided, configured):
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        update = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Malformed JSON") from None
    if not isinstance(update, dict):
        raise HTTPException(status_code=400, detail="Malformed JSON")

    message = update.get("message")
    if not isinstance(message, dict):
        return {}
    chat = message.get("chat")
    text = message.get("text")
    if not isinstance(chat, dict) or chat.get("type") != "private":
        return {}
    if not isinstance(text, str) or not text.startswith("/start"):
        return {}
    chat_id = chat.get("id")
    if not isinstance(chat_id, int):
        return {}

    return {
        "method": "sendMessage",
        "chat_id": chat_id,
        "text": START_TEXT,
        "reply_markup": {
            "inline_keyboard": [[
                {"text": START_BUTTON_TEXT, "web_app": {"url": f"https://{settings.app_domain}/day/today"}}
            ]]
        },
    }
# END_BLOCK: WEBHOOK_ENDPOINT
