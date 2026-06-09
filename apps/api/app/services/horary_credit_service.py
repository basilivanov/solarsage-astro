# ############################################################################
# AI_HEADER: MODULE_HORARY_CREDIT_SERVICE
# ROLE: Core credit ledger logic for Horary questions.
# DEPENDENCIES: sqlalchemy, app.db.models
# GRACE_ANCHORS: [WEEK_RESOLUTION, BALANCE_CHECK, CREDIT_SPEND]
# ############################################################################

# START_MODULE_CONTRACT: M-HORARY-CREDIT-SERVICE
# purpose: Partition access weeks, calculate balances, and deduct credits atomically.
# owns:
#   - apps/api/app/services/horary_credit_service.py
# inputs:
#   - db: AsyncSession, user_id: UUID, now: datetime
# outputs:
#   - HoraryCredit, HoraryCreditSpend, HoraryQuotaRead
# invariants:
#   - weekly-free credits are resolved lazily and do not pre-create future weeks.
#   - spent order is strictly: weekly-free -> expiring bonus -> paid.
# END_MODULE_CONTRACT: M-HORARY-CREDIT-SERVICE

# START_MODULE_MAP: M-HORARY-CREDIT-SERVICE
# public_entrypoints:
#   - resolve_current_access_week
#   - get_or_create_current_weekly_free
#   - get_balance
#   - select_spendable_credit
#   - spend_credit_for_question
# END_MODULE_MAP: M-HORARY-CREDIT-SERVICE

from __future__ import annotations

import json
import logging
import uuid
from datetime import date as Date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AccessLedger, HoraryCredit, HoraryCreditSpend, HoraryQuestion
from app.schemas.horary import HoraryQuotaRead

logger = logging.getLogger(__name__)


class HoraryCreditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve_current_access_week(self, user_id: uuid.UUID, now: datetime) -> tuple[datetime, datetime] | None:
        # START_FUNCTION_CONTRACT: M-HORARY-CREDIT-SERVICE.resolve_current_access_week
        # purpose: Map continuous access dates to 7-day intervals and find the current week.
        # inputs: user_id (UUID), now (datetime)
        # returns: tuple[datetime, datetime] or None
        # side_effects: queries database (AccessLedger)
        # emitted_logs: none
        # error_behavior: propagates database exceptions
        # END_FUNCTION_CONTRACT: M-HORARY-CREDIT-SERVICE.resolve_current_access_week
        
        # 1. Fetch all entries
        result = await self.db.execute(
            select(AccessLedger)
            .where(AccessLedger.user_id == user_id)
            .order_by(AccessLedger.start_date)
        )
        entries = result.scalars().all()
        if not entries:
            return None

        # 2. Merge overlapping or adjacent intervals
        intervals = []
        current_start = entries[0].start_date
        current_end = entries[0].end_date

        for entry in entries[1:]:
            if entry.start_date <= current_end + timedelta(days=1):
                current_end = max(current_end, entry.end_date)
            else:
                intervals.append((current_start, current_end))
                current_start = entry.start_date
                current_end = entry.end_date
        intervals.append((current_start, current_end))

        # 3. Find week containing `now`
        for start_date, end_date in intervals:
            interval_start = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
            next_day = end_date + timedelta(days=1)
            interval_end = datetime(next_day.year, next_day.month, next_day.day, tzinfo=timezone.utc)

            current = interval_start
            while current < interval_end:
                week_end = current + timedelta(days=7)
                if week_end > interval_end:
                    week_end = interval_end
                
                if current <= now < week_end:
                    return current, week_end
                current = week_end

        return None

    async def get_or_create_current_weekly_free(self, user_id: uuid.UUID, now: datetime) -> HoraryCredit | None:
        # START_FUNCTION_CONTRACT: M-HORARY-CREDIT-SERVICE.get_or_create_current_weekly_free
        # purpose: Lazily resolve and instantiate subscription_weekly_free row for active week.
        # inputs: user_id (UUID), now (datetime)
        # returns: HoraryCredit or None
        # side_effects: queries and optionally inserts HoraryCredit
        # emitted_logs: none
        # error_behavior: propagates database exceptions
        # END_FUNCTION_CONTRACT: M-HORARY-CREDIT-SERVICE.get_or_create_current_weekly_free
        
        week = await self.resolve_current_access_week(user_id, now)
        if not week:
            return None
        
        week_start, week_end = week

        # Check if already exists
        result = await self.db.execute(
            select(HoraryCredit)
            .where(
                and_(
                    HoraryCredit.user_id == user_id,
                    HoraryCredit.source == "subscription_weekly_free",
                    HoraryCredit.access_week_start == week_start,
                    HoraryCredit.access_week_end == week_end,
                )
            )
        )
        credit = result.scalar_one_or_none()

        if not credit:
            credit = HoraryCredit(
                user_id=user_id,
                source="subscription_weekly_free",
                amount=1,
                used_amount=0,
                access_week_start=week_start,
                access_week_end=week_end,
                expires_at=week_end,
            )
            self.db.add(credit)
            await self.db.flush()

        return credit

    async def get_balance(self, user_id: uuid.UUID, now: datetime) -> HoraryQuotaRead:
        # START_FUNCTION_CONTRACT: M-HORARY-CREDIT-SERVICE.get_balance
        # purpose: Calculate aggregate counts for weekly-free, paid, and bonus credits.
        # inputs: user_id (UUID), now (datetime)
        # returns: HoraryQuotaRead
        # side_effects: queries database (HoraryCredit, AccessLedger)
        # emitted_logs: none
        # error_behavior: propagates database exceptions
        # END_FUNCTION_CONTRACT: M-HORARY-CREDIT-SERVICE.get_balance
        
        # Resolve weekly free credit first
        weekly_credit = await self.get_or_create_current_weekly_free(user_id, now)

        weekly_free_available = False
        weekly_free_expires_at = None
        next_weekly_free_at = None

        if weekly_credit:
            weekly_free_available = weekly_credit.used_amount < weekly_credit.amount
            if weekly_credit.access_week_end:
                weekly_free_expires_at = weekly_credit.access_week_end.isoformat()

            # Determine next weekly free at if access is continuous
            week_end = weekly_credit.access_week_end
            if week_end:
                next_week_start_date = Date(week_end.year, week_end.month, week_end.day)
                access_check = await self.db.execute(
                    select(AccessLedger)
                    .where(
                        and_(
                            AccessLedger.user_id == user_id,
                            AccessLedger.start_date <= next_week_start_date,
                            AccessLedger.end_date >= next_week_start_date,
                        )
                    )
                )
                if access_check.scalars().first():
                    next_weekly_free_at = week_end.isoformat()

        # Fetch other active credits
        result = await self.db.execute(
            select(HoraryCredit)
            .where(
                and_(
                    HoraryCredit.user_id == user_id,
                    HoraryCredit.used_amount < HoraryCredit.amount,
                    HoraryCredit.source != "subscription_weekly_free",
                )
            )
        )
        credits = result.scalars().all()

        bonus_credits = 0
        paid_credits = 0

        for c in credits:
            expires = None
            if c.expires_at:
                expires = c.expires_at.replace(tzinfo=timezone.utc) if c.expires_at.tzinfo is None else c.expires_at
            
            if expires and expires <= now:
                continue  # expired
            
            avail = c.amount - c.used_amount
            if c.source == "paid":
                paid_credits += avail
            else:
                bonus_credits += avail

        return HoraryQuotaRead(
            weekly_free_available=weekly_free_available,
            weekly_free_expires_at=weekly_free_expires_at,
            next_weekly_free_at=next_weekly_free_at,
            bonus_credits=bonus_credits,
            paid_credits=paid_credits,
            can_purchase=True,
        )

    async def select_spendable_credit(self, user_id: uuid.UUID, now: datetime, lock: bool = False) -> HoraryCredit | None:
        # START_FUNCTION_CONTRACT: M-HORARY-CREDIT-SERVICE.select_spendable_credit
        # purpose: Resolve candidate credits and sort them in priority order.
        # inputs: user_id (UUID), now (datetime), lock (bool)
        # returns: HoraryCredit or None
        # side_effects: queries database (with optional lock)
        # emitted_logs: none
        # error_behavior: propagates database exceptions
        # END_FUNCTION_CONTRACT: M-HORARY-CREDIT-SERVICE.select_spendable_credit
        
        # Fetch all candidate credits with remaining balance
        stmt = select(HoraryCredit).where(
            and_(
                HoraryCredit.user_id == user_id,
                HoraryCredit.used_amount < HoraryCredit.amount,
            )
        )
        if lock:
            stmt = stmt.with_for_update()

        result = await self.db.execute(stmt)
        candidates = result.scalars().all()

        # Filter and sort
        weekly_frees = []
        bonuses = []
        paids = []

        for c in candidates:
            expires = None
            if c.expires_at:
                expires = c.expires_at.replace(tzinfo=timezone.utc) if c.expires_at.tzinfo is None else c.expires_at

            if c.source == "subscription_weekly_free":
                # Must be currently active
                if c.access_week_start and c.access_week_end:
                    start = c.access_week_start.replace(tzinfo=timezone.utc) if c.access_week_start.tzinfo is None else c.access_week_start
                    end = c.access_week_end.replace(tzinfo=timezone.utc) if c.access_week_end.tzinfo is None else c.access_week_end
                    if start <= now < end:
                        weekly_frees.append(c)
            elif c.source == "paid":
                if expires is None or expires > now:
                    paids.append(c)
            else:
                if expires is None or expires > now:
                    bonuses.append(c)

        # 1. Weekly free is first
        if weekly_frees:
            return weekly_frees[0]

        # 2. Bonuses sorted by expires_at (nearest first, NULLs last)
        if bonuses:
            bonuses.sort(key=lambda x: (x.expires_at is None, x.expires_at.replace(tzinfo=timezone.utc) if x.expires_at and x.expires_at.tzinfo is None else x.expires_at))
            return bonuses[0]

        # 3. Paid sorted by created_at (oldest first)
        if paids:
            paids.sort(key=lambda x: x.created_at)
            return paids[0]

        return None

    async def spend_credit_for_question(
        self,
        user_id: uuid.UUID,
        question_id: uuid.UUID,
        idempotency_key: str,
        now: datetime,
    ) -> HoraryCreditSpend:
        # START_FUNCTION_CONTRACT: M-HORARY-CREDIT-SERVICE.spend_credit_for_question
        # purpose: Deduct a single credit atom and insert transaction spend row.
        # inputs: user_id (UUID), question_id (UUID), idempotency_key (str), now (datetime)
        # returns: HoraryCreditSpend
        # side_effects: inserts spend record and updates HoraryCredit row
        # emitted_logs: none
        # error_behavior: raises ValueError if no credit available, propagates DB exceptions
        # END_FUNCTION_CONTRACT: M-HORARY-CREDIT-SERVICE.spend_credit_for_question
        
        # 1. Fetch candidate credit
        credit = await self.select_spendable_credit(user_id, now, lock=True)
        if not credit:
            raise ValueError("No spendable horary credits found")

        # 2. Increment used amount
        credit.used_amount += 1

        # 3. Create spend record
        spend = HoraryCreditSpend(
            user_id=user_id,
            credit_id=credit.id,
            question_id=question_id,
            amount=1,
            idempotency_key=idempotency_key,
            created_at=now,
        )
        self.db.add(spend)
        return spend
