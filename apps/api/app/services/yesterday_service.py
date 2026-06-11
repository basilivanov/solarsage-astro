# ############################################################################
# AI_HEADER: MODULE_YESTERDAY_SERVICE
# ROLE: Yesterday closure service — build yesterday's signals for delta comparison.
# DEPENDENCIES: sqlalchemy, app.services.normalization_service, app.clients.solarsage_client
# GRACE_ANCHORS: [BUILD_CLOSURE]
# WAVE: W-PHASE-1
# ############################################################################

# START_MODULE_CONTRACT: M-YESTERDAY-SERVICE
# purpose: Build yesterday's normalized signals for day-over-day delta computation.
# owns:
#   - apps/api/app/services/yesterday_service.py
# inputs:
#   - user profile with birth data
#   - target_date: date
# outputs:
#   - list[AstroSignal] or None
# dependencies:
#   - M-NORMALIZATION-SERVICE
#   - M-SOLARSAGE-CLIENT
# side_effects:
#   - calls sidecar for yesterday's transits
# failure_policy:
#   - returns None if sidecar unavailable
# END_MODULE_CONTRACT: M-YESTERDAY-SERVICE

# START_MODULE_MAP: M-YESTERDAY-SERVICE
# public_entrypoints:
#   - build_closure
# semantic_blocks:
#   - BUILD_CLOSURE: compute yesterday's normalized signals
# END_MODULE_MAP: M-YESTERDAY-SERVICE

from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
import uuid

from app.services.checkin_service import CheckinService


class YesterdayService:
    """Yesterday closure service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_closure(
        self,
        user_id: uuid.UUID,
        target_date: date,
    ) -> str:
        """
        Build closure text for yesterday.

        W-8.2: MVP version (simplified, no LLM).
        """
        checkin_service = CheckinService(self.db)
        checkin = await checkin_service.get_checkin(user_id, target_date)

        if not checkin:
            return "Вы не отметили, как прошёл день."

        # Simple closure based on mood
        mood_texts = {
            "great": "Отличный день! Рады, что всё прошло хорошо.",
            "good": "Хороший день. Продолжайте в том же духе!",
            "neutral": "Обычный день. Завтра будет лучше.",
            "bad": "Сложный день. Помните, что завтра новый день.",
        }

        closure = mood_texts.get(checkin.mood, "Спасибо за отметку.")

        if checkin.notes:
            closure += f"\n\nВаши заметки: {checkin.notes}"

        return closure
