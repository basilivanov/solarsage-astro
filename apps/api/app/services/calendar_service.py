# ############################################################################
# AI_HEADER: MODULE_CALENDAR_SERVICE
# ROLE: CalendarService — generates 3-month calendar grid with neutral statuses.
# DEPENDENCIES: sqlalchemy, app.schemas.calendar, app.schemas.access
# GRACE_ANCHORS: [CALENDAR_GENERATION, NEUTRAL_STATUS_ROTATION, ACCESS_STUB]
# ############################################################################

# START_MODULE_CONTRACT: M-CALENDAR-SERVICE
# purpose: Generate CalendarPayload for prev/current/next month grid.
#   W-1.4: neutral statuses (5-day rotation pattern).
#   W-4.3: real statuses from semantic_layers.
#   W-ACCESS.1: real access logic.
# owns:
#   - apps/api/app/services/calendar_service.py
# inputs:
#   - user_id: int
#   - month: str (YYYY-MM format)
#   - db: AsyncSession
# outputs:
#   - CalendarPayload
# dependencies:
#   - M-DB-SESSION (AsyncSession)
#   - M-CONTRACTS.calendar (CalendarPayload, CalendarDay, CalendarMeta, AllowedRange)
#   - M-CONTRACTS.access (ContentAccessState)
#   - M-ACCESS (AccessService stub)
# invariants:
#   - Returns exactly 3 months: prev, current, next
#   - Each day has neutral status in W-1.4 (5-day cycle)
#   - Access state is stub (state=full) in W-1.4
#   - Allowed range is ±2 years from current date
# failure_policy:
#   - Invalid month format handled by caller (calendar.py)
#   - Out of range handled by caller
# non_goals:
#   - no real status calculation (W-4.3)
#   - no real access logic (W-ACCESS.1)
# END_MODULE_CONTRACT: M-CALENDAR-SERVICE

# START_MODULE_MAP: M-CALENDAR-SERVICE
# public_entrypoints:
#   - CalendarService.get_calendar
# semantic_blocks:
#   - CALENDAR_GENERATION: generate 3-month grid
#   - NEUTRAL_STATUS_ROTATION: 5-day cycle pattern
#   - ACCESS_STUB: stub access state (full)
# owned_tests:
#   - apps/api/tests/test_calendar_endpoints.py (W-1.4)
# END_MODULE_MAP: M-CALENDAR-SERVICE

from __future__ import annotations

import uuid
from calendar import monthrange
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.access import ContentAccessState
from app.schemas.calendar import AllowedRange, CalendarDay, CalendarMeta, CalendarPayload
from app.schemas.today import DayStatus


# START_BLOCK: CALENDAR_GENERATION
class CalendarService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_calendar(self, user_id: uuid.UUID, month: str) -> CalendarPayload:
        """
        Get 3-month calendar grid (prev/curr/next).

        W-1.4: neutral statuses (rotation pattern), access stub.
        W-4.3: real statuses from semantic_layers.
        W-ACCESS.1: real access logic.
        """
        # Parse requested month
        requested_date = datetime.strptime(month, "%Y-%m")
        today = datetime.now(UTC).date()

        # Calculate prev/curr/next months
        prev_month = self._add_months(requested_date, -1)
        curr_month = requested_date
        next_month = self._add_months(requested_date, 1)

        # Generate all days for 3 months
        days = []
        for month_date in [prev_month, curr_month, next_month]:
            days.extend(await self._generate_month_days(month_date, curr_month, today, user_id))

        # Calculate allowed range (±2 years from now)
        now = datetime.now(UTC)
        allowed_from = datetime(now.year - 2, 1, 1).date()
        allowed_to = datetime(now.year + 2, 12, 31).date()

        # Generate title (e.g., "May 2026")
        title = curr_month.strftime("%B %Y")

        return CalendarPayload(
            meta=CalendarMeta(
                schema_version="calendar/v1",
                contract_version=1,
                generated_at=datetime.now(UTC).isoformat() + "Z",
            ),
            month=month,
            title=title,
            allowed_range=AllowedRange(
                from_=allowed_from.isoformat(),
                to=allowed_to.isoformat(),
            ),
            days=days,
        )

    async def _generate_month_days(
        self,
        month_date: datetime,
        current_month: datetime,
        today,
        user_id: uuid.UUID,
    ) -> list[CalendarDay]:
        """Generate days for one month."""
        year = month_date.year
        month = month_date.month
        _, num_days = monthrange(year, month)

        days = []
        for day in range(1, num_days + 1):
            date = datetime(year, month, day).date()
            is_current_month = (year == current_month.year and month == current_month.month)
            is_today = (date == today)

            # W-1.4: neutral status rotation
            status = self._neutral_status(date)

            # W-1.4: access stub (always full)
            access = await self._get_access_stub(user_id, date)

            # Disabled if outside current month (for UI purposes)
            disabled = not is_current_month

            days.append(CalendarDay(
                date=date.isoformat(),
                day_number=day,
                is_current_month=is_current_month,
                is_today=is_today,
                disabled=disabled,
                day_status=status,
                access=access.model_dump(by_alias=True),  # Convert to dict for Pydantic
            ))

        return days
# END_BLOCK: CALENDAR_GENERATION

    # START_BLOCK: NEUTRAL_STATUS_ROTATION
    def _neutral_status(self, date) -> DayStatus:
        """
        W-1.4: neutral status rotation.
        W-4.3: real status from semantic layer.

        Pattern: supportive → steady → steady → tense → steady (5-day cycle)
        """
        day_of_year = date.timetuple().tm_yday
        cycle_position = day_of_year % 5

        if cycle_position == 0:
            return "supportive"
        elif cycle_position == 3:
            return "tense"
        else:
            return "steady"
    # END_BLOCK: NEUTRAL_STATUS_ROTATION

    # START_BLOCK: ACCESS_STUB
    async def _get_access_stub(self, user_id: uuid.UUID, date) -> ContentAccessState:
        """
        W-1.4: access stub (always full).
        W-ACCESS.1: real access logic from AccessService.
        """
        return ContentAccessState(
            state="full",
            reason="active_referral_days",
            referral_days_left=14,
            subscription_active=False,
            access_until=None,
        )
    # END_BLOCK: ACCESS_STUB

    def _add_months(self, date: datetime, months: int) -> datetime:
        """Add months to date, handling year rollover."""
        month = date.month + months
        year = date.year

        while month > 12:
            month -= 12
            year += 1
        while month < 1:
            month += 12
            year -= 1

        return datetime(year, month, 1)
