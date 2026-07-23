# ############################################################################
# AI_HEADER: MODULE_JOBS_FEEDBACK_BROADCAST — operator-runnable feedback broadcast job.
# ROLE: Selects eligible users at local 20:00 and sends day accuracy feedback reminder
#       messages with inline keyboard via Telegram Bot API.
#       Hard-gated by FEEDBACK_BROADCAST_ENABLED.
# DEPENDENCIES: app package, DATABASE_URL env
# ############################################################################

# START_MODULE_CONTRACT: M-JOBS-FEEDBACK-BROADCAST
# purpose: Single-shot job for broadcasting evening feedback reminders to users.
# owns:
#   - apps/api/app/jobs/feedback_broadcast.py
# inputs: DATABASE_URL (+ standard app env), FEEDBACK_BROADCAST_ENABLED.
# outputs: exit 0 with sent count as structured log event; non-zero on errors.
# dependencies: app.db.session.SessionLocal, FeedbackService, telegram_client,
#   app.core.logging (log_event, bind_log_context).
# side_effects: sends Telegram messages when FEEDBACK_BROADCAST_ENABLED=true;
#   otherwise exits 0 doing nothing (structured skip event).
# emitted_logs: feedback.broadcast_skipped, feedback.reminder_sent, system.error
# invariants:
#   - Kill-switch first: disabled broadcast means zero messages, always.
#   - Cap of 500 users per run.
#   - Individual send errors are logged and skipped (continues with remaining users).
# failure_policy: exit 1 on unexpected failure.
# END_MODULE_CONTRACT: M-JOBS-FEEDBACK-BROADCAST

# START_MODULE_MAP: M-JOBS-FEEDBACK-BROADCAST
# public_entrypoints:
#   - main
# semantic_blocks:
#   - FEEDBACK_BROADCAST_JOB: kill-switch gate, broadcast run, structured outcome events
# owned_tests:
#   - apps/api/tests/test_feedback_service.py
# END_MODULE_MAP: M-JOBS-FEEDBACK-BROADCAST

from __future__ import annotations

import asyncio
from uuid import uuid4


# START_BLOCK: FEEDBACK_BROADCAST_JOB
async def _run() -> int:
    from app.core.config import settings
    from app.core.logging import log_event
    from app.db.models import UserProfile
    from app.db.session import SessionLocal
    from app.services.feedback_service import FeedbackService
    from app.services.telegram_client import send_message, TelegramClientError
    from sqlalchemy import select

    if not settings.feedback_broadcast_enabled:
        log_event(
            "feedback.broadcast_skipped",
            msg="feedback broadcast skipped: FEEDBACK_BROADCAST_ENABLED=false",
        )
        return 0

    sent_count = 0
    async with SessionLocal() as session:
        service = FeedbackService(session)
        users = await service.list_users_for_reminder(target_hour_local=20)
        # Cap at 500 users
        users = users[:500]

        for user in users:
            profile = (
                await session.execute(
                    select(UserProfile).where(UserProfile.user_id == user.id)
                )
            ).scalar_one_or_none()
            local_yesterday = service.local_yesterday(profile)
            if local_yesterday is None:
                continue

            yesterday_str = local_yesterday.isoformat()
            reply_markup = {
                "inline_keyboard": [
                    [
                        {"text": "Попал ✓", "callback_data": f"fb:acc:{yesterday_str}:3"},
                        {"text": "Частично ~", "callback_data": f"fb:acc:{yesterday_str}:2"},
                        {"text": "Мимо ×", "callback_data": f"fb:acc:{yesterday_str}:1"},
                    ]
                ]
            }
            text = "Как прошёл твой день? Вчерашний разбор — совпал с реальностью?"

            try:
                await send_message(
                    chat_id=user.tg_user_id,
                    text=text,
                    reply_markup=reply_markup,
                )
                sent_count += 1
            except TelegramClientError as exc:
                log_event(
                    "system.error",
                    level="warn",
                    msg=f"Failed to send feedback reminder: {exc}",
                    error={"kind": type(exc).__name__},
                )

            await asyncio.sleep(0.1)

    log_event(
        "feedback.reminder_sent",
        msg="feedback broadcast completed",
        payload={"count": sent_count},
    )
    return 0


def main() -> int:
    # START_FUNCTION_CONTRACT: F-M-JOBS-FEEDBACK-BROADCAST.main
    # purpose: Job entrypoint — binds log context and runs feedback broadcast.
    # inputs: process env
    # returns: 0 on success/skip, 1 on error
    # side_effects: structured log events, sends messages if enabled
    # error_behavior: logs system.error and returns 1
    # END_FUNCTION_CONTRACT: F-M-JOBS-FEEDBACK-BROADCAST.main
    from app.core.logging import bind_log_context, log_event

    bind_log_context(
        correlation_id=f"fb-bcast-{uuid4().hex[:12]}",
        slice="W-FEEDBACK",
        module="M-JOBS-FEEDBACK-BROADCAST",
        block="FEEDBACK_BROADCAST_JOB",
    )
    try:
        return asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        log_event(
            "system.error",
            level="error",
            msg="feedback broadcast job failed",
            error={"kind": type(exc).__name__},
        )
        return 1
# END_BLOCK: FEEDBACK_BROADCAST_JOB


if __name__ == "__main__":
    raise SystemExit(main())
