# ############################################################################
# AI_HEADER: MODULE_SERVICES_FEEDBACK
# ROLE: Service for managing user day accuracy feedback and reminder broadcast selection
# DEPENDENCIES: sqlalchemy, app.db.models
# GRACE_ANCHORS: [FEEDBACK_SERVICE]
# ############################################################################

# START_MODULE_CONTRACT: M-FEEDBACK-SERVICE
# purpose: Manage DayFeedback records and query users eligible for feedback broadcast.
# owns:
#   - apps/api/app/services/feedback_service.py
# inputs:
#   - AsyncSession
# outputs:
#   - DayFeedback records, list of eligible User objects
# dependencies:
#   - M-DB-MODELS (DayFeedback, User, UserProfile, EveningCheckin)
# side_effects:
#   - DB inserts/updates on day_feedback table
# emitted_logs: none
# invariants:
#   - accuracy must be between 1 and 3 inclusive
# failure_policy:
#   - raises ValueError on invalid accuracy
# END_MODULE_CONTRACT: M-FEEDBACK-SERVICE

# START_MODULE_MAP: M-FEEDBACK-SERVICE
# public_entrypoints:
#   - FeedbackService.upsert
#   - FeedbackService.get_for_date
#   - FeedbackService.local_yesterday
#   - FeedbackService.list_users_for_reminder
# semantic_blocks:
#   - FEEDBACK_SERVICE: Core service logic
# END_MODULE_MAP: M-FEEDBACK-SERVICE

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import zoneinfo
import uuid

from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DayFeedback, EveningCheckin, User, UserProfile


class FeedbackService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert(
        self,
        user_id: uuid.UUID,
        target_date: date,
        accuracy: int,
        source: str = "tg_bot",
    ) -> DayFeedback:
        # START_FUNCTION_CONTRACT: F-M-FEEDBACK-SERVICE.upsert
        # purpose: Create or update a DayFeedback row for user and target_date.
        # inputs: user_id (UUID), target_date (date), accuracy (int 1..3), source (str)
        # returns: DayFeedback
        # side_effects: inserts or updates day_feedback row
        # error_behavior: raises ValueError if accuracy not in 1..3
        # END_FUNCTION_CONTRACT: F-M-FEEDBACK-SERVICE.upsert
        if accuracy not in (1, 2, 3):
            raise ValueError(f"Invalid accuracy: {accuracy}. Must be 1, 2, or 3.")

        stmt = select(DayFeedback).where(
            DayFeedback.user_id == user_id,
            DayFeedback.target_date == target_date,
        )
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            record = DayFeedback(
                user_id=user_id,
                target_date=target_date,
                accuracy=accuracy,
                source=source,
            )
            self.db.add(record)
        else:
            record.accuracy = accuracy
            record.source = source

        await self.db.flush()
        return record

    async def get_for_date(
        self, user_id: uuid.UUID, target_date: date
    ) -> DayFeedback | None:
        # START_FUNCTION_CONTRACT: F-M-FEEDBACK-SERVICE.get_for_date
        # purpose: Fetch DayFeedback for user and date if exists.
        # inputs: user_id (UUID), target_date (date)
        # returns: DayFeedback | None
        # END_FUNCTION_CONTRACT: F-M-FEEDBACK-SERVICE.get_for_date
        stmt = select(DayFeedback).where(
            DayFeedback.user_id == user_id,
            DayFeedback.target_date == target_date,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _profile_timezone(profile: UserProfile | None) -> str | None:
        if profile is None:
            return None
        return profile.current_tz or profile.birth_tz

    @classmethod
    def local_yesterday(cls, profile: UserProfile | None, now_utc: datetime | None = None) -> date | None:
        # START_FUNCTION_CONTRACT: F-M-FEEDBACK-SERVICE.local_yesterday
        # purpose: Calculate local yesterday date for a profile.
        # inputs: profile (UserProfile | None), optional now_utc
        # returns: date | None
        # END_FUNCTION_CONTRACT: F-M-FEEDBACK-SERVICE.local_yesterday
        tz_str = cls._profile_timezone(profile)
        if not tz_str:
            return None
        try:
            tz = zoneinfo.ZoneInfo(tz_str)
        except Exception:
            return None

        if now_utc is None:
            now_utc = datetime.now(UTC)

        local_now = now_utc.astimezone(tz)
        return (local_now - timedelta(days=1)).date()

    async def list_users_for_reminder(
        self,
        target_hour_local: int = 20,
        now_utc: datetime | None = None,
    ) -> list[User]:
        # START_FUNCTION_CONTRACT: F-M-FEEDBACK-SERVICE.list_users_for_reminder
        # purpose: Select users who should receive feedback broadcast reminder.
        # inputs: target_hour_local (int, default 20), now_utc (datetime, default now)
        # returns: list[User]
        # END_FUNCTION_CONTRACT: F-M-FEEDBACK-SERVICE.list_users_for_reminder
        if now_utc is None:
            now_utc = datetime.now(UTC)

        stmt = (
            select(User, UserProfile)
            .join(UserProfile, User.id == UserProfile.user_id)
            .where(
                UserProfile.is_onboarded.is_(True),
                (UserProfile.current_tz.isnot(None)) | (UserProfile.birth_tz.isnot(None)),
            )
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        eligible_users: list[User] = []

        for user, profile in rows:
            tz_str = self._profile_timezone(profile)
            if not tz_str:
                continue
            try:
                tz = zoneinfo.ZoneInfo(tz_str)
            except Exception:
                continue

            local_now = now_utc.astimezone(tz)
            if local_now.hour != target_hour_local:
                continue

            local_yesterday = (local_now - timedelta(days=1)).date()

            # Check if user already gave day_feedback for local_yesterday
            fb_exists = (
                await self.db.execute(
                    select(
                        exists().where(
                            DayFeedback.user_id == user.id,
                            DayFeedback.target_date == local_yesterday,
                        )
                    )
                )
            ).scalar()

            if fb_exists:
                continue

            # Check if user already gave evening_checkins with accuracy for local_yesterday
            checkin_exists = (
                await self.db.execute(
                    select(
                        exists().where(
                            EveningCheckin.user_id == user.id,
                            EveningCheckin.target_date == local_yesterday,
                            EveningCheckin.accuracy.isnot(None),
                        )
                    )
                )
            ).scalar()

            if checkin_exists:
                continue

            eligible_users.append(user)

        return eligible_users
