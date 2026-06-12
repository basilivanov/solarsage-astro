# AI_HEADER: MODULE_ACCESS_SERVICE
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
#   - M-DB-MODELS (AccessLedger)
# invariants:
#   - W-1.3: always returns state=full (stub).
#   - W-ACCESS.1: checks access_ledger, referral_days, subscriptions.
#   - Consumption order: referral_bonus first, then subscription.
# failure_policy:
#   - never raises; returns preview state if access denied.
# non_goals:
#   - no payment processing (lives in M-PAYMENT)
# END_MODULE_CONTRACT: M-ACCESS.service

# START_MODULE_MAP: M-ACCESS.service
# public_entrypoints:
#   - AccessService.can_access_day
#   - AccessService.grant_referral_bonus
#   - AccessService.grant_subscription
# semantic_blocks:
#   - ACCESS_CHECK: real logic with access_ledger
#   - ACCESS_GRANT: grant_referral_bonus, grant_subscription
# owned_tests:
#   - apps/api/tests/test_access_service.py (W-ACCESS.1)
# END_MODULE_MAP: M-ACCESS.service

from __future__ import annotations

from datetime import UTC, date as Date, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AccessLedger
from app.schemas.access import ContentAccessState


# START_BLOCK: ACCESS_CHECK
class AccessService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def can_access_day(self, user_id: UUID, target_date: Date) -> ContentAccessState:
        # START_FUNCTION_CONTRACT: F-M-ACCESS.service.can_access_day
        # purpose: Check if user can access a specific day (full/preview/locked).
        # inputs: user_id (UUID), target_date (Date)
        # returns: ContentAccessState with state, reason, access_until
        # side_effects: reads from AccessLedger table
        # emitted_logs: none (TODO: W-1.6 — add access.checked event)
        # error_behavior: never raises; returns preview state if access denied
        # END_FUNCTION_CONTRACT: F-M-ACCESS.service.can_access_day
        """
        Check if user can access a specific day.

        W-1.3: stub returning state=full.
        W-ACCESS.1: real logic with access_ledger.
        W-ACCESS.3: returns locked for days outside access window.

        Consumption order:
        1. referral_bonus entries (14 days each)
        2. subscription entries (30 days each)

        States:
        - full: day is within active access window
        - preview: access expired (past days, or no access yet for past)
        - locked: day is outside access window (future days beyond access)
        """
        # Get all access entries for user, ordered by start_date
        result = await self.db.execute(
            select(AccessLedger)
            .where(AccessLedger.user_id == user_id)
            .order_by(AccessLedger.start_date)
        )
        entries = result.scalars().all()

        if not entries:
            # No access entries
            # W-ACCESS.3: preview for past/today, locked for future
            if target_date <= datetime.now(UTC).date():
                return ContentAccessState(
                    state="preview",
                    reason="expired_access",
                    referral_days_left=None,
                    subscription_active=None,
                    access_until=None,
                )
            else:
                return ContentAccessState(
                    state="locked",
                    reason="outside_access_window",
                    referral_days_left=None,
                    subscription_active=None,
                    access_until=None,
                )

        # Check if target_date is covered by any entry
        for entry in entries:
            if entry.start_date <= target_date <= entry.end_date:
                # Found covering entry
                days_left = (entry.end_date - target_date).days

                if entry.entry_type == "referral_bonus":
                    return ContentAccessState(
                        state="full",
                        reason="active_referral_days",
                        referral_days_left=days_left,
                        subscription_active=None,
                        access_until=entry.end_date.isoformat(),
                    )
                else:  # subscription
                    return ContentAccessState(
                        state="full",
                        reason="active_subscription",
                        referral_days_left=None,
                        subscription_active=True,
                        access_until=entry.end_date.isoformat(),
                    )

        # No covering entry
        # Determine state based on target_date position
        last_entry = entries[-1]
        today = datetime.now(UTC).date()

        if target_date > last_entry.end_date:
            # After last entry
            # W-ACCESS.3: preview for past/today, locked for future
            if target_date <= today:
                # Past or today after access expired → preview
                return ContentAccessState(
                    state="preview",
                    reason="expired_access",
                    referral_days_left=None,
                    subscription_active=None,
                    access_until=last_entry.end_date.isoformat(),
                )
            else:
                # Future day beyond access → locked
                return ContentAccessState(
                    state="locked",
                    reason="outside_access_window",
                    referral_days_left=None,
                    subscription_active=None,
                    access_until=last_entry.end_date.isoformat(),
                )
        else:
            # Before first entry or between entries → preview
            return ContentAccessState(
                state="preview",
                reason="expired_access",
                referral_days_left=None,
                subscription_active=None,
                access_until=last_entry.end_date.isoformat(),
            )
# END_BLOCK: ACCESS_CHECK


# START_BLOCK: ACCESS_GRANT
    async def grant_referral_bonus(self, user_id: UUID, start_date: Date) -> None:
        # START_FUNCTION_CONTRACT: F-M-ACCESS.service.grant_referral_bonus
        # purpose: Grant 14-day referral bonus to user.
        # inputs: user_id (UUID), start_date (Date)
        # returns: None
        # side_effects: creates AccessLedger row of type referral_bonus
        # emitted_logs: none (TODO: W-1.6 — add referral.signup_credited event)
        # error_behavior: DB errors propagate
        # END_FUNCTION_CONTRACT: F-M-ACCESS.service.grant_referral_bonus
        """
        Grant 14-day referral bonus.

        Called when user signs up via referral link.
        """
        end_date = start_date + timedelta(days=13)  # 14 days total (0..13)

        entry = AccessLedger(
            user_id=user_id,
            entry_type="referral_bonus",
            days_granted=14,
            start_date=start_date,
            end_date=end_date,
        )

        self.db.add(entry)
        await self.db.commit()

    async def grant_subscription(self, user_id: UUID, start_date: Date, days: int = 30) -> None:
        # START_FUNCTION_CONTRACT: F-M-ACCESS.service.grant_subscription
        # purpose: Grant subscription access for specified days.
        # inputs: user_id (UUID), start_date (Date), days (int, default 30)
        # returns: None
        # side_effects: creates AccessLedger row of type subscription
        # emitted_logs: none (TODO: W-1.6 — add access.subscription_granted event)
        # error_behavior: DB errors propagate
        # END_FUNCTION_CONTRACT: F-M-ACCESS.service.grant_subscription
        """
        Grant subscription access.

        Called when user pays for subscription.
        """
        end_date = start_date + timedelta(days=days - 1)

        entry = AccessLedger(
            user_id=user_id,
            entry_type="subscription",
            days_granted=days,
            start_date=start_date,
            end_date=end_date,
        )

        self.db.add(entry)
        await self.db.commit()
# END_BLOCK: ACCESS_GRANT
