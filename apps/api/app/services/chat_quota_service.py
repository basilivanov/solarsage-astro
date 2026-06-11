# ############################################################################
# AI_HEADER: MODULE_CHAT_QUOTA_SERVICE
# ROLE: Chat quota service
# DEPENDENCIES: sqlalchemy, app.db.models
# GRACE_ANCHORS: [GET_OR_CREATE_QUOTA, CHECK_QUOTA, INCREMENT_USAGE, INCREASE_LIMIT]
# WAVE: W-CHAT-4
# ############################################################################

# START_MODULE_CONTRACT: M-CHAT-QUOTA-SERVICE
# purpose: Business logic for chat quota tracking and enforcement
# owns:
#   - apps/api/app/services/chat_quota_service.py
# inputs:
#   - db: AsyncSession
#   - user_id: UUID
#   - additional: int (for limit increase)
# outputs:
#   - ChatQuota: quota record
#   - bool: quota availability check result
# dependencies:
#   - M-DB-MODELS (ChatQuota)
# side_effects:
#   - creates/updates rows in chat_quotas
#   - auto-resets quota when expired
# invariants:
#   - one quota per user (unique constraint)
#   - messages_used <= messages_limit enforced
#   - quota resets monthly (30 days)
# failure_policy:
#   - ValueError if quota exceeded
# non_goals:
#   - no billing integration in this module (handled by payment_service)
# END_MODULE_CONTRACT: M-CHAT-QUOTA-SERVICE

# START_MODULE_MAP: M-CHAT-QUOTA-SERVICE
# public_entrypoints:
#   - get_or_create_quota
#   - check_quota
#   - increment_usage
#   - increase_limit
# semantic_blocks:
#   - GET_OR_CREATE_QUOTA: get or create quota
#   - CHECK_QUOTA: check quota availability
#   - INCREMENT_USAGE: increment message count
#   - INCREASE_LIMIT: increase quota limit
# END_MODULE_MAP: M-CHAT-QUOTA-SERVICE

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, UTC
import uuid

from app.db.models import ChatQuota


class ChatQuotaService:
    """Chat quota service. W-CHAT-4."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # START_BLOCK: GET_OR_CREATE_QUOTA
    async def get_or_create_quota(self, user_id: uuid.UUID) -> ChatQuota:
        """Get or create quota for user."""
        result = await self.db.execute(
            select(ChatQuota).where(ChatQuota.user_id == user_id)
        )
        quota = result.scalar_one_or_none()

        if not quota:
            # Create new quota (resets monthly)
            quota = ChatQuota(
                user_id=user_id,
                messages_used=0,
                messages_limit=10,  # Free tier
                reset_at=datetime.now(UTC) + timedelta(days=30),
            )
            self.db.add(quota)
            await self.db.commit()
            await self.db.refresh(quota)

        return quota
    # END_BLOCK: GET_OR_CREATE_QUOTA

    # START_BLOCK: CHECK_QUOTA
    async def check_quota(self, user_id: uuid.UUID) -> bool:
        """Check if user has quota remaining."""
        quota = await self.get_or_create_quota(user_id)

        # Reset if expired
        now = datetime.now(UTC)
        # Handle both timezone-aware and naive datetimes
        reset_at = quota.reset_at
        if reset_at.tzinfo is None:
            # If reset_at is naive, make it aware (assume UTC)
            from zoneinfo import ZoneInfo
            reset_at = reset_at.replace(tzinfo=ZoneInfo("UTC"))

        if now >= reset_at:
            quota.messages_used = 0
            quota.reset_at = now + timedelta(days=30)
            await self.db.commit()

        return quota.messages_used < quota.messages_limit
    # END_BLOCK: CHECK_QUOTA

    # START_BLOCK: INCREMENT_USAGE
    async def increment_usage(self, user_id: uuid.UUID) -> None:
        """Increment message usage."""
        quota = await self.get_or_create_quota(user_id)
        quota.messages_used += 1
        await self.db.commit()
    # END_BLOCK: INCREMENT_USAGE

    # START_BLOCK: INCREASE_LIMIT
    async def increase_limit(self, user_id: uuid.UUID, additional: int) -> None:
        """
        Increase quota limit (e.g., after subscription purchase).

        W-CHAT-4: Integration with billing.
        """
        quota = await self.get_or_create_quota(user_id)
        quota.messages_limit += additional
        await self.db.commit()
    # END_BLOCK: INCREASE_LIMIT
