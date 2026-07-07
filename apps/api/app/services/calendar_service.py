# ############################################################################
# AI_HEADER: MODULE_CALENDAR_SERVICE
# ROLE: CalendarService — generates 3-month calendar grid with real statuses and access.
# DEPENDENCIES: sqlalchemy, app.schemas.calendar, app.schemas.access
# GRACE_ANCHORS: [CALENDAR_GENERATION, REAL_STATUS_LOOKUP, REAL_ACCESS]
# ############################################################################

# START_MODULE_CONTRACT: M-CALENDAR-SERVICE
# purpose: Generate CalendarPayload for prev/current/next month grid with
#   cached/computed real day statuses and real access decisions.
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
#   - M-ACCESS (AccessService)
# invariants:
#   - Returns exactly 3 months: prev, current, next
#   - Full-access days use cached/computed real status when available
#   - Locked/preview days may return no day status
#   - Allowed range is ±2 years from current date
# failure_policy:
#   - Invalid month format handled by caller (calendar.py)
#   - Out of range handled by caller
# non_goals:
#   - no calendar UI rendering
# END_MODULE_CONTRACT: M-CALENDAR-SERVICE

# START_MODULE_MAP: M-CALENDAR-SERVICE
# public_entrypoints:
#   - CalendarService.get_calendar
# semantic_blocks:
#   - CALENDAR_GENERATION: generate 3-month grid
#   - REAL_STATUS_LOOKUP: cache-backed day status lookup/computation
#   - REAL_ACCESS: access state from AccessService
# owned_tests:
#   - apps/api/tests/test_calendar_endpoints.py (W-1.4)
# END_MODULE_MAP: M-CALENDAR-SERVICE

from __future__ import annotations

import json
import uuid
from calendar import monthrange
from datetime import UTC, date as Date, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.calendar import AllowedRange, CalendarDay, CalendarMeta, CalendarPayload
from app.schemas.today import DayStatus
from app.clients.solarsage_client import get_solarsage_client
from app.db.models import SemanticLayerCache, TodayPayloadCache, UserProfile
from app.services.access_service import AccessService
from app.services.natal_context_service import NatalContextService
from app.services.normalization_service import NormalizationService
from app.services.scoring_service import ScoringService
from app.services.semantic_service import SemanticService
from app.services.today_service import TODAY_CONTENT_VERSION


# START_BLOCK: CALENDAR_GENERATION
class CalendarService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._request_profile: UserProfile | None = None
        self._request_profile_hash: str | None = None
        self._request_natal_context: dict | None = None

    async def get_calendar(self, user_id: uuid.UUID, month: str) -> CalendarPayload:
        # START_FUNCTION_CONTRACT: F-M-CALENDAR-SERVICE.get_calendar
        # purpose: Get 3-month calendar grid with day statuses and access.
        # inputs: user_id (UUID), month (str YYYY-MM)
        # returns: CalendarPayload with prev/curr/next month days
        # side_effects: reads from DB for access and semantic layer
        # emitted_logs: calendar.viewed
        # error_behavior: invalid month format handled by caller
        # END_FUNCTION_CONTRACT: F-M-CALENDAR-SERVICE.get_calendar
        """
        Get 3-month calendar grid (prev/curr/next).

        Uses real access decisions. Full-access days return a cached or
        computed real status when the pipeline can produce one.
        """
        # Parse requested month
        requested_date = datetime.strptime(month, "%Y-%m")
        today = datetime.now(UTC).date()
        await self._prepare_request_context(user_id)

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

            access = await AccessService(self.db).can_access_day(user_id, date)
            status = await self._get_day_status(user_id, date, access.state)

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

    async def _prepare_request_context(self, user_id: uuid.UUID) -> None:
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        self._request_profile = result.scalar_one_or_none()
        if self._request_profile:
            self._request_profile_hash = NatalContextService.compute_profile_hash(self._request_profile)

    async def _get_day_status(
        self,
        user_id: uuid.UUID,
        target_date: Date,
        access_state: str,
    ) -> DayStatus | None:
        cached = await self._get_cached_day_status(user_id, target_date)
        if cached is not None:
            return cached

        if access_state != "full":
            return None

        return await self._compute_and_cache_day_status(user_id, target_date)

    async def _get_cached_day_status(
        self,
        user_id: uuid.UUID,
        target_date: Date,
    ) -> DayStatus | None:
        semantic_result = await self.db.execute(
            select(SemanticLayerCache).where(
                SemanticLayerCache.user_id == user_id,
                SemanticLayerCache.target_date == target_date,
            )
        )
        semantic_entry = semantic_result.scalar_one_or_none()
        if semantic_entry:
            data = json.loads(semantic_entry.semantic_json)
            status = data.get("day_status")
            if status in ("supportive", "steady", "tense"):
                return status

        if not self._request_profile_hash:
            return None

        payload_result = await self.db.execute(
            select(TodayPayloadCache).where(
                TodayPayloadCache.user_id == user_id,
                TodayPayloadCache.target_date == target_date,
                TodayPayloadCache.profile_hash == self._request_profile_hash,
            )
        )
        payload_entry = payload_result.scalar_one_or_none()
        if not payload_entry:
            return None

        data = json.loads(payload_entry.payload_json)
        meta = data.get("meta") or {}
        content_version = meta.get("contentVersion", meta.get("content_version"))
        if content_version != TODAY_CONTENT_VERSION:
            return None

        status = data.get("dayStatus") or data.get("day_status")
        if status in ("supportive", "steady", "tense"):
            return status
        return None

    async def _compute_and_cache_day_status(
        self,
        user_id: uuid.UUID,
        target_date: Date,
    ) -> DayStatus | None:
        if not self._request_profile:
            return None

        try:
            if self._request_natal_context is None:
                self._request_natal_context = (
                    await NatalContextService(self.db).get_or_build_natal_context(user_id)
                ).model_dump(by_alias=False)

            target_tz = self._request_profile.current_tz or self._request_profile.birth_tz or "UTC"
            transits = await get_solarsage_client().get_transits(
                target_date=target_date.isoformat(),
                target_time="12:00",
                target_tz=target_tz,
            )
            signals = NormalizationService().normalize_day(self._request_natal_context, transits)
            scoring = ScoringService().score_day(signals)
            status = scoring["day_status"]
            semantic_layer = SemanticService().build_semantic_layer(
                status,
                scoring["sphere_scores"],
            )
            try:
                self.db.add(SemanticLayerCache(
                    user_id=user_id,
                    target_date=target_date,
                    semantic_json=semantic_layer.model_dump_json(),
                ))
                await self.db.commit()
            except IntegrityError:
                await self.db.rollback()
                return await self._get_cached_day_status(user_id, target_date)
            return status
        except Exception:
            await self.db.rollback()
            return None

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
