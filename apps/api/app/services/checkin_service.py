# ############################################################################
# AI_HEADER: MODULE_CHECKIN_SERVICE
# ROLE: Evening checkin service — create and get checkins.
# DEPENDENCIES: sqlalchemy, app.db.models
# GRACE_ANCHORS: [CREATE_CHECKIN, GET_CHECKIN]
# WAVE: W-8.1
# ############################################################################

# START_MODULE_CONTRACT: M-CHECKIN-SERVICE
# purpose: Create and get evening checkins.
# owns:
#   - apps/api/app/services/checkin_service.py
# inputs:
#   - user_id, target_date, mood, notes
# outputs:
#   - EveningCheckin or None
# dependencies:
#   - M-DB-MODELS (EveningCheckin)
# side_effects:
#   - creates/updates rows in evening_checkins table
# invariants:
#   - one checkin per user per date (upsert)
# failure_policy:
#   - returns None if checkin not found
# END_MODULE_CONTRACT: M-CHECKIN-SERVICE

# START_MODULE_MAP: M-CHECKIN-SERVICE
# public_entrypoints:
#   - create_checkin
#   - get_checkin
# semantic_blocks:
#   - CREATE_CHECKIN: create or update checkin (upsert)
#   - GET_CHECKIN: get checkin for specific date
# END_MODULE_MAP: M-CHECKIN-SERVICE

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
        # START_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE.create_checkin
        # purpose: Create or update evening checkin (upsert).
        # inputs: user_id (UUID), target_date (date), mood (str), notes (str | None)
        # returns: EveningCheckin with id, date, mood, notes
        # side_effects: creates/updates row in evening_checkins table
        # emitted_logs: none
        # error_behavior: DB errors propagate
        # END_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE.create_checkin
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
        # START_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE.get_checkin
        # purpose: Get checkin for specific user and date.
        # inputs: user_id (UUID), target_date (date)
        # returns: EveningCheckin or None if not found
        # side_effects: reads from DB
        # emitted_logs: none
        # error_behavior: returns None on not found; never raises
        # END_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE.get_checkin
        """Get checkin for specific date."""
        result = await self.db.execute(
            select(EveningCheckin).where(
                EveningCheckin.user_id == user_id,
                EveningCheckin.target_date == target_date,
            )
        )
        return result.scalar_one_or_none()
