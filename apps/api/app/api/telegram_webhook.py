# ############################################################################
# AI_HEADER: MODULE_API_TELEGRAM_WEBHOOK
# ROLE: Telegram Bot webhook responder — canonical /start without Ductor.
# DEPENDENCIES: fastapi, hmac, app.core.config
# GRACE_ANCHORS: [TELEGRAM_WEBHOOK]
# ############################################################################

# START_MODULE_CONTRACT: M-API-TELEGRAM-WEBHOOK
# purpose: Receive Telegram Bot API webhook updates and answer private /start
#   messages with the canonical start copy and inline WebApp button, and process
#   feedback callback queries via FeedbackService.
# owns:
#   - apps/api/app/api/telegram_webhook.py
# inputs:
#   - POST /api/telegram/webhook with X-Telegram-Bot-Api-Secret-Token header
# outputs:
#   - Bot API method JSON (sendMessage or answerCallbackQuery); empty JSON otherwise
# dependencies:
#   - M-CONFIG (settings.telegram_webhook_secret, settings.app_domain)
#   - M-DB-SESSION (get_session)
#   - M-FEEDBACK-SERVICE (FeedbackService)
# side_effects: creates/updates day_feedback records via FeedbackService on callback_query
# emitted_logs: feedback.received
# invariants:
#   - Secret check is constant-time (hmac.compare_digest) and fail-closed:
#     an empty configured secret rejects every request with 403.
#   - Only private message updates whose text starts with "/start" (payload
#     included) get a sendMessage reply; every other valid update gets 200 {}.
#   - Callback queries with fb:acc:YYYY-MM-DD:N trigger day_feedback upsert and
#     answerCallbackQuery.
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

from datetime import date as Date
import hmac
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import log_event
from app.db.models import User
from app.db.session import get_session
from app.services.feedback_service import FeedbackService

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
async def telegram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-API-TELEGRAM-WEBHOOK.telegram_webhook
    # purpose: Verify the Telegram secret header (constant-time, fail-closed)
    #   and answer private /start messages with canonical start copy or process
    #   feedback callback queries; ack every other valid update with {}.
    # inputs: raw HTTP request (header + JSON update body), db session.
    # returns: Bot API method JSON or empty dict.
    # side_effects: creates/updates DayFeedback records on callback_query.
    # emitted_logs: feedback.received
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

    # Handle callback_query
    callback_query = update.get("callback_query")
    if isinstance(callback_query, dict):
        cq_id = callback_query.get("id")
        from_user = callback_query.get("from")
        data = callback_query.get("data")
        if not isinstance(cq_id, str) or not isinstance(from_user, dict) or not isinstance(data, str):
            return {}

        tg_user_id = from_user.get("id")
        if not isinstance(tg_user_id, int):
            return {}

        parts = data.split(":")
        # Expected format: fb:acc:YYYY-MM-DD:N
        if len(parts) != 4 or parts[0] != "fb" or parts[1] != "acc":
            return {}

        try:
            target_date = Date.fromisoformat(parts[2])
            accuracy = int(parts[3])
        except ValueError:
            return {}

        if accuracy not in (1, 2, 3):
            return {}

        stmt = select(User).where(User.tg_user_id == tg_user_id)
        user = (await db.execute(stmt)).scalar_one_or_none()
        if user is None:
            return {}

        service = FeedbackService(db)
        await service.upsert(user.id, target_date, accuracy, source="tg_bot")
        await db.commit()

        log_event("feedback.received", payload={"accuracy": accuracy, "source": "tg_bot"})

        return {
            "method": "answerCallbackQuery",
            "callback_query_id": cq_id,
            "text": "Записал ✨",
        }

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
