# ############################################################################
# AI_HEADER
# module: M-CHECKIN-SERVICE
# wave: W-8.1
# purpose: Evening checkin service
# ############################################################################

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date
import uuid

from app.db.models import EveningCheckin


class CheckinService:
    """Evening checkin service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_checkin(
        self,
        user_id: uuid.UUID,
        target_date: date,
        mood: str,
        notes: str | None,
    ) -> EveningCheckin:
        """
        Create evening checkin.

        W-8.1: Upsert logic (update if exists).
        """
        # Check if exists
        result = await self.db.execute(
            select(EveningCheckin).where(
                EveningCheckin.user_id == user_id,
                EveningCheckin.target_date == target_date,
            )
        )
        checkin = result.scalar_one_or_none()

        if checkin:
            # Update existing
            checkin.mood = mood
            checkin.notes = notes
        else:
            # Create new
            checkin = EveningCheckin(
                user_id=user_id,
                target_date=target_date,
                mood=mood,
                notes=notes,
            )
            self.db.add(checkin)

        await self.db.commit()
        await self.db.refresh(checkin)

        return checkin

    async def get_checkin(
        self,
        user_id: uuid.UUID,
        target_date: date,
    ) -> EveningCheckin | None:
        """Get checkin for specific date."""
        result = await self.db.execute(
            select(EveningCheckin).where(
                EveningCheckin.user_id == user_id,
                EveningCheckin.target_date == target_date,
            )
        )
        return result.scalar_one_or_none()
