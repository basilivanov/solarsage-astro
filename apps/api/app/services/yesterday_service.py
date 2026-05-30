# ############################################################################
# AI_HEADER
# module: M-YESTERDAY-SERVICE
# wave: W-8.2
# purpose: Yesterday closure service
# ############################################################################

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
