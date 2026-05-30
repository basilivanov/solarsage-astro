# AI_HEADER
# module: M-ACCESS
# canon: docs/GRACE_CANON.md §6
# wave: W-1.3 (stub), W-ACCESS.1 (real)
# purpose: Access control service for content gating.

# START_MODULE_CONTRACT: M-ACCESS.service
# purpose: Check if user can access a specific day.
#          W-1.3: stub always returns state=full.
#          W-ACCESS.1: real logic with access_ledger, referral_days, subscriptions.
# owns:
#   - apps/api/app/services/access_service.py
# inputs:
#   - user_id: UUID
#   - target_date: date
#   - db: AsyncSession
# outputs:
#   - ContentAccessState
# dependencies:
#   - M-DB-SESSION (AsyncSession)
#   - M-CONTRACTS.access (ContentAccessState)
# invariants:
#   - W-1.3: always returns state=full (stub).
#   - W-ACCESS.1: checks access_ledger, referral_days, subscriptions.
# failure_policy:
#   - never raises; returns locked state if access denied.
# non_goals:
#   - no payment processing (lives in M-PAYMENT)
# END_MODULE_CONTRACT

# START_MODULE_MAP: M-ACCESS.service
# public_entrypoints:
#   - AccessService.can_access_day
# semantic_blocks:
#   - ACCESS_CHECK: stub returning full access
# owned_tests:
#   - apps/api/tests/test_access_service.py (W-ACCESS.1)
# END_MODULE_MAP

from __future__ import annotations

from datetime import date as Date

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.access import ContentAccessState


# START_BLOCK: ACCESS_CHECK
class AccessService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def can_access_day(self, user_id, target_date: Date) -> ContentAccessState:
        """
        Check if user can access a specific day.

        W-1.3: stub returning state=full.
        W-ACCESS.1: real logic with access_ledger, referral_days, subscriptions.
        """
        # W-1.3: stub always returns full access
        return ContentAccessState(
            state="full",
            reason=None,
            referral_days_left=None,
            subscription_active=None,
            access_until=None,
        )
# END_BLOCK: ACCESS_CHECK
