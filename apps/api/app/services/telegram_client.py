# ############################################################################
# AI_HEADER: MODULE_SERVICES_TELEGRAM_CLIENT
# ROLE: Minimal outbound client for Telegram Bot API
# DEPENDENCIES: httpx, app.core.config
# GRACE_ANCHORS: [TELEGRAM_CLIENT]
# ############################################################################

# START_MODULE_CONTRACT: M-TELEGRAM-CLIENT
# purpose: Send outbound messages to Telegram Bot API.
# owns:
#   - apps/api/app/services/telegram_client.py
# inputs:
#   - chat_id (int), text (str), optional reply_markup (dict)
# outputs:
#   - None
# dependencies:
#   - httpx
#   - M-CONFIG (settings)
# side_effects:
#   - HTTP POST to api.telegram.org
# emitted_logs: none
# failure_policy:
#   - raises TelegramClientError on non-200 or ok: false response
# END_MODULE_CONTRACT: M-TELEGRAM-CLIENT

# START_MODULE_MAP: M-TELEGRAM-CLIENT
# public_entrypoints:
#   - send_message
# semantic_blocks:
#   - TELEGRAM_CLIENT: Outbound Telegram Bot API caller
# END_MODULE_MAP: M-TELEGRAM-CLIENT

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class TelegramClientError(Exception):
    """Raised when Telegram Bot API call fails."""
    pass


async def send_message(
    chat_id: int,
    text: str,
    reply_markup: dict[str, Any] | None = None,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TELEGRAM-CLIENT.send_message
    # purpose: Send a text message to chat_id with optional reply_markup via Telegram Bot API.
    # inputs: chat_id (int), text (str), reply_markup (dict | None)
    # returns: None
    # side_effects: POST request to Telegram Bot API
    # error_behavior: raises TelegramClientError on HTTP error or ok=false
    # END_FUNCTION_CONTRACT: F-M-TELEGRAM-CLIENT.send_message
    token = settings.telegram_bot_token
    if not token:
        raise TelegramClientError("TELEGRAM_BOT_TOKEN is not configured")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(url, json=payload)
        except Exception as exc:
            raise TelegramClientError(f"HTTP request to Telegram failed: {exc}") from exc

        if resp.status_code != 200:
            raise TelegramClientError(f"Telegram returned HTTP {resp.status_code}: {resp.text}")

        try:
            data = resp.json()
        except Exception as exc:
            raise TelegramClientError(f"Invalid JSON from Telegram: {exc}") from exc

        if not data.get("ok"):
            description = data.get("description", "Unknown Telegram error")
            raise TelegramClientError(f"Telegram API error: {description}")
