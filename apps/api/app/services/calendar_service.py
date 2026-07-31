# ############################################################################
# AI_HEADER: MODULE_CALENDAR_SERVICE
# ROLE: CalendarService — projects a 3-month grid from published snapshots and access.
# DEPENDENCIES: sqlalchemy, app.schemas.calendar, app.schemas.access, snapshot models
# GRACE_ANCHORS: [CALENDAR_GENERATION, SNAPSHOT_INDEX, REAL_ACCESS]
# ############################################################################

# START_MODULE_CONTRACT: M-CALENDAR-SERVICE
# purpose: Generate CalendarPayload for a prev/current/next month grid from
#   published TodaySnapshot heads and real access projections.
# owns:
#   - apps/api/app/services/calendar_service.py
# inputs:
#   - user_id: int
#   - month: str (YYYY-MM format)
#   - today: resolved user-local date for isToday and allowed-range semantics
#   - db: AsyncSession
# outputs:
#   - CalendarPayload
# dependencies:
#   - M-DB-SESSION (AsyncSession)
#   - M-CONTRACTS.calendar (CalendarPayload, CalendarDay, CalendarMeta, AllowedRange)
#   - M-CONTRACTS.access (ContentAccessState)
#   - M-DB-MODELS (TodaySnapshot, AccessLedger)
#   - M-LUNAR-FACTS-SERVICE (LunarFactsService)
# invariants:
#   - Returns exactly 3 months: prev, current, next
#   - Snapshot states are read-only projections: hero, ordinary, or not-computed
#   - Missing published snapshots never trigger a calculation
#   - Allowed range is ±2 years from the explicitly provided local date
#   - isToday and allowed range derive from the same explicitly provided date
#   - Superseded snapshot rows are excluded by a local NOT EXISTS query.
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
#   - SNAPSHOT_INDEX: load published, non-superseded snapshot heads
#   - REAL_ACCESS: bulk-load and project access state without per-day queries
# owned_tests:
#   - apps/api/tests/test_calendar_endpoints.py (W-1.4)
#   - apps/api/tests/test_user_local_date_consumers.py
# END_MODULE_MAP: M-CALENDAR-SERVICE

from __future__ import annotations

import json
import uuid
from calendar import monthrange
from datetime import UTC, date as Date, datetime
from typing import Literal

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db.models import AccessLedger, SemanticLayerCache, TodayPayloadCache, TodaySnapshot, UserProfile
from app.schemas.access import ContentAccessState
from app.schemas.calendar import AllowedRange, CalendarDay, CalendarMeta, CalendarPayload
from app.schemas.today import DayStatus
from app.core.config import settings
from app.clients.solarsage_client import get_solarsage_client
from app.services.natal_context_service import NatalContextService
from app.services.normalization_service import NormalizationService
from app.services.semantic_service import SemanticService
from app.services.today_service import TODAY_CONTENT_VERSION
from app.services.day_scoring_signals import filter_day_scored_signals
from app.services.lunar_facts_service import LunarFactsService
from app.services.access_service import AccessService  # noqa: F401 - legacy method compatibility


# START_BLOCK: CALENDAR_GENERATION
class CalendarService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._request_profile: UserProfile | None = None
        self._request_profile_hash: str | None = None
        self._request_natal_context: dict | None = None
        self._lunar_facts = LunarFactsService()

    async def get_calendar(
        self, user_id: uuid.UUID, month: str, *, today: Date
    ) -> CalendarPayload:
        # START_FUNCTION_CONTRACT: F-M-CALENDAR-SERVICE.get_calendar
        # purpose: Get 3-month calendar grid from the published snapshot index.
        # inputs: user_id (UUID), month (str YYYY-MM), today (resolved local date)
        # returns: CalendarPayload with prev/curr/next month days and wire states.
        # side_effects: reads published snapshots, access ledger, and lunar facts.
        # emitted_logs: calendar.viewed
        # error_behavior: invalid month format handled by caller; today is required
        # END_FUNCTION_CONTRACT: F-M-CALENDAR-SERVICE.get_calendar
        """
        Get 3-month calendar grid (prev/curr/next).

        The semantic state is a read-only projection of published snapshot
        heads. Missing dates remain ``not-computed`` and never enter the day
        calculation pipeline.
        """
        # Parse requested month
        requested_date = datetime.strptime(month, "%Y-%m")

        # Calculate prev/curr/next months
        prev_month = self._add_months(requested_date, -1)
        curr_month = requested_date
        next_month = self._add_months(requested_date, 1)

        snapshot_index = await self._load_snapshot_index(
            user_id,
            start_date=Date(prev_month.year, prev_month.month, 1),
            end_date=Date(
                next_month.year,
                next_month.month,
                monthrange(next_month.year, next_month.month)[1],
            ),
        )
        access_entries = await self._load_access_entries(user_id)

        # Generate all days for 3 months
        days = []
        for month_date in [prev_month, curr_month, next_month]:
            days.extend(
                await self._generate_month_days(
                    month_date,
                    curr_month,
                    today,
                    snapshot_index=snapshot_index,
                    access_entries=access_entries,
                )
            )

        # Calculate allowed range (±2 years from the user's local today).
        allowed_from = Date(today.year - 2, 1, 1)
        allowed_to = Date(today.year + 2, 12, 31)

        # Generate title (e.g., "May 2026")
        title = curr_month.strftime("%B %Y")

        return CalendarPayload(
            meta=CalendarMeta(
                schema_version="calendar/v2",
                contract_version=2,
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
        *,
        snapshot_index: dict[Date, TodaySnapshot],
        access_entries: list[AccessLedger],
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

            access = self._access_for_date(access_entries, date, today)
            day_state = self._day_state(snapshot_index.get(date))
            lunar = self._lunar_facts.facts_for_date(date)

            # Disabled if outside current month (for UI purposes)
            disabled = not is_current_month

            days.append(CalendarDay(
                date=date.isoformat(),
                day_number=day,
                is_current_month=is_current_month,
                is_today=is_today,
                disabled=disabled,
                day_state=day_state,
                access=access.model_dump(by_alias=True),  # Convert to dict for Pydantic
                lunar=lunar,
            ))

        return days
# END_BLOCK: CALENDAR_GENERATION

    # START_BLOCK: SNAPSHOT_INDEX
    async def _load_snapshot_index(
        self,
        user_id: uuid.UUID,
        *,
        start_date: Date,
        end_date: Date,
    ) -> dict[Date, TodaySnapshot]:
        # START_FUNCTION_CONTRACT: F-M-CALENDAR-SERVICE._load_snapshot_index
        # purpose: Load published, non-superseded snapshot heads for one calendar range.
        # inputs: user_id and inclusive start/end dates.
        # returns: One newest head snapshot per target date.
        # side_effects: one indexed TodaySnapshot SELECT; no calculation calls.
        # emitted_logs: none
        # error_behavior: database errors propagate.
        # END_FUNCTION_CONTRACT: F-M-CALENDAR-SERVICE._load_snapshot_index
        child = aliased(TodaySnapshot)
        statement = (
            select(TodaySnapshot)
            .where(
                TodaySnapshot.user_id == user_id,
                TodaySnapshot.target_date >= start_date,
                TodaySnapshot.target_date <= end_date,
                TodaySnapshot.published_at.is_not(None),
                ~exists(
                    select(1).where(
                        child.user_id == user_id,
                        child.supersedes_snapshot_id == TodaySnapshot.id,
                    )
                ),
            )
            .order_by(
                TodaySnapshot.target_date,
                TodaySnapshot.published_at.desc(),
                TodaySnapshot.id.desc(),
            )
        )
        result = await self.db.execute(statement)
        index: dict[Date, TodaySnapshot] = {}
        for snapshot in result.scalars().all():
            index.setdefault(snapshot.target_date, snapshot)
        return index
    # END_BLOCK: SNAPSHOT_INDEX

    # START_BLOCK: REAL_ACCESS
    async def _load_access_entries(self, user_id: uuid.UUID) -> list[AccessLedger]:
        # START_FUNCTION_CONTRACT: F-M-CALENDAR-SERVICE._load_access_entries
        # purpose: Load the user's access window once for the three-month projection.
        # inputs: user_id (UUID).
        # returns: Access ledger rows ordered by start and end date.
        # side_effects: one access-ledger SELECT.
        # emitted_logs: none
        # error_behavior: database errors propagate.
        # END_FUNCTION_CONTRACT: F-M-CALENDAR-SERVICE._load_access_entries
        result = await self.db.execute(
            select(AccessLedger)
            .where(AccessLedger.user_id == user_id)
            .order_by(AccessLedger.start_date, AccessLedger.end_date)
        )
        return list(result.scalars().all())

    @staticmethod
    def _access_for_date(
        entries: list[AccessLedger],
        target_date: Date,
        current_date: Date,
    ) -> ContentAccessState:
        # START_FUNCTION_CONTRACT: F-M-CALENDAR-SERVICE._access_for_date
        # purpose: Project one ContentAccessState from a bulk-loaded access window.
        # inputs: access ledger rows, target date, and resolved local current date.
        # returns: full, preview, or locked access projection.
        # side_effects: none.
        # emitted_logs: none
        # error_behavior: never raises for an empty access window.
        # END_FUNCTION_CONTRACT: F-M-CALENDAR-SERVICE._access_for_date
        for entry in entries:
            if entry.start_date <= target_date <= entry.end_date:
                days_left = (entry.end_date - target_date).days + 1
                if entry.entry_type == "referral_bonus":
                    return ContentAccessState(
                        state="full",
                        reason="active_referral_days",
                        referral_days_left=days_left,
                        subscription_active=None,
                        access_until=entry.end_date.isoformat(),
                    )
                return ContentAccessState(
                    state="full",
                    reason="active_subscription",
                    referral_days_left=None,
                    subscription_active=True,
                    access_until=entry.end_date.isoformat(),
                )

        if not entries:
            if target_date <= current_date:
                return ContentAccessState(state="preview", reason="expired_access")
            return ContentAccessState(state="locked", reason="outside_access_window")

        last_entry = max(entries, key=lambda entry: entry.end_date)
        if target_date > last_entry.end_date and target_date > current_date:
            return ContentAccessState(
                state="locked",
                reason="outside_access_window",
                access_until=last_entry.end_date.isoformat(),
            )
        return ContentAccessState(
            state="preview",
            reason="expired_access",
            access_until=last_entry.end_date.isoformat(),
        )

    @staticmethod
    def _day_state(snapshot: TodaySnapshot | None) -> Literal["hero", "ordinary", "not-computed"]:
        # START_FUNCTION_CONTRACT: F-M-CALENDAR-SERVICE._day_state
        # purpose: Map one published deterministic snapshot to the calendar wire state.
        # inputs: optional published snapshot head.
        # returns: hero, ordinary, or not-computed.
        # side_effects: none.
        # emitted_logs: none
        # error_behavior: a published state other than convergence is ordinary.
        # END_FUNCTION_CONTRACT: F-M-CALENDAR-SERVICE._day_state
        if snapshot is None:
            return "not-computed"
        result = snapshot.deterministic_result_json
        state = result.get("state") if isinstance(result, dict) else None
        return "hero" if state == "convergence_today" else "ordinary"
    # END_BLOCK: REAL_ACCESS

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
        if not self._request_profile_hash and self._request_profile:
            self._request_profile_hash = NatalContextService.compute_profile_hash(self._request_profile)

        if not self._request_profile_hash:
            return None

        from app.services.cache_key_service import expected_cache_identity

        current_cache_key = expected_cache_identity(
            user_id=user_id,
            target_date=target_date.isoformat(),
            profile_hash=self._request_profile_hash,
        )

        # 1. Check TodayPayloadCache with versioned identity
        payload_result = await self.db.execute(
            select(TodayPayloadCache).where(
                TodayPayloadCache.user_id == user_id,
                TodayPayloadCache.target_date == target_date,
                TodayPayloadCache.profile_hash == self._request_profile_hash,
                TodayPayloadCache.cache_key_hash == current_cache_key.cache_key_hash,
            )
        )
        payload_entry = payload_result.scalar_one_or_none()
        if payload_entry:
            data = self._load_json_object(payload_entry.payload_json)
            meta = data.get("meta") or {}
            content_version = meta.get("contentVersion", meta.get("content_version"))
            if content_version == TODAY_CONTENT_VERSION:
                status = data.get("dayStatus") or data.get("day_status")
                if status in ("supportive", "steady", "tense"):
                    return status

        # 2. Check SemanticLayerCache with full version identity
        semantic_result = await self.db.execute(
            select(SemanticLayerCache).where(
                SemanticLayerCache.user_id == user_id,
                SemanticLayerCache.target_date == target_date,
            )
        )
        semantic_entry = semantic_result.scalar_one_or_none()
        if semantic_entry:
            data = self._load_json_object(semantic_entry.semantic_json)
            if "content_version" in data:
                # Validate ALL identity fields; missing/wrong = miss (no defaults)
                identity_ok = (
                    data.get("content_version") == TODAY_CONTENT_VERSION
                    and data.get("profile_hash") == self._request_profile_hash
                    and data.get("cache_key_hash") == current_cache_key.cache_key_hash
                    and data.get("calculation_version") == current_cache_key.calculation_version
                    and data.get("activation_layer_version") == current_cache_key.activation_layer_version
                    and data.get("scoring_version") == str(current_cache_key.scoring_version)
                    and data.get("canon_versions_hash") == current_cache_key.canon_versions_hash
                    and data.get("llm_prompt_version") == current_cache_key.llm_prompt_version
                    and data.get("frontend_payload_version") == current_cache_key.frontend_payload_version
                )
                if identity_ok:
                    inner_sem = data.get("semantic_layer") or {}
                    status = inner_sem.get("day_status")
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
        if not self._request_profile_hash:
            self._request_profile_hash = NatalContextService.compute_profile_hash(self._request_profile)

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
            day_signals = filter_day_scored_signals(signals)

            # W5: Fetch sidecar activation layer when V2 may be computed
            from app.services.day_scoring_runtime_service import should_compute_v2
            from app.services.activation_layer_service import ActivationLayerService
            from app.services.day_scoring_runtime_service import DayScoringRuntimeService
            from app.core.logging import log_event, log_block

            # Build current_location only when all three fields are present
            current_location = None
            p = self._request_profile
            if (p.current_lat is not None and p.current_lon is not None
                    and p.current_tz is not None):
                current_location = {
                    "lat": float(p.current_lat),
                    "lon": float(p.current_lon),
                    "tz": p.current_tz,
                }

            # Fetch sidecar activation-layer
            sidecar_layer = None
            if should_compute_v2() and p.birthday and p.birth_lat is not None and p.birth_lon is not None and p.birth_tz:
                try:
                    sidecar_layer = await get_solarsage_client().get_activation_layer(
                        birth_date=p.birthday.isoformat(),
                        birth_time=p.birth_time.strftime("%H:%M") if p.birth_time else "12:00",
                        birth_lat=float(p.birth_lat),
                        birth_lon=float(p.birth_lon),
                        birth_tz=p.birth_tz,
                        target_date=target_date.isoformat(),
                        target_time="12:00",
                        target_tz=target_tz,
                        house_system=self._request_natal_context.get("house_system", "PLACIDUS"),
                        current_location=current_location,
                    )
                except Exception:
                    if settings.solarsage_v2_enabled:
                        raise  # Fail loudly when V2 is enabled
                    with log_block(slice="W-DAY", module="M-CALENDAR-SERVICE", block="V2_SHADOW"):
                        log_event(
                            "scoring.v2_diff",
                            level="warning",
                            msg="Calendar V2 shadow mode: sidecar activation-layer failed, using local fallback",
                            payload={
                                "date": target_date.isoformat(),
                                "fallback": "local_activation",
                            },
                            error={
                                "kind": "SidecarError",
                            },
                        )

            activation_layer = ActivationLayerService().build(
                natal_context=self._request_natal_context,
                transits=transits,
                day_signals=day_signals,
                target_date=target_date,
                target_time="12:00",
                target_tz=target_tz,
                house_system=self._request_natal_context.get("house_system", "PLACIDUS"),
                sidecar_activation_layer=sidecar_layer,
            )
            runtime = DayScoringRuntimeService()
            dual = runtime.compute(
                day_signals=day_signals,
                activation_layer=activation_layer,
                user_id=user_id,
                target_date=target_date.isoformat(),
            )

            # Build write cache key from canonical runtime identity.
            # Use the resolver so V1-selected scoring produces the same
            # identity as a subsequent read even when the activation object
            # itself carries the V2 calculation version.
            from app.services.cache_key_service import build_today_cache_key, resolve_today_runtime_identity
            identity = resolve_today_runtime_identity(
                selected_scoring_version=dual.selected_scoring_version,
                activation_layer_version=activation_layer.activation_layer_version,
            )
            cache_key = build_today_cache_key(
                user_id=user_id,
                target_date=target_date.isoformat(),
                profile_hash=self._request_profile_hash,
                calculation_version=identity.calculation_version,
                activation_layer_version=identity.activation_layer_version,
                scoring_version=identity.scoring_version,
                content_version=identity.content_version,
                frontend_payload_version=identity.frontend_payload_version,
            )
            status = dual.selected_result["day_status"]
            scoring_result = dual.selected_result

            semantic_layer = SemanticService().build_semantic_layer(
                status,
                scoring_result["sphere_scores"],
            )
            if hasattr(semantic_layer, "model_dump_json"):
                sem_json_str = semantic_layer.model_dump_json()
                sem_data = json.loads(sem_json_str)
            else:
                sem_data = semantic_layer.model_dump()

            cache_data = {
                "profile_hash": self._request_profile_hash,
                "content_version": TODAY_CONTENT_VERSION,
                "semantic_layer": sem_data,
                "cache_key_hash": cache_key.cache_key_hash,
                "calculation_version": cache_key.calculation_version,
                "activation_layer_version": cache_key.activation_layer_version,
                "scoring_version": str(cache_key.scoring_version),
                "canon_versions_hash": cache_key.canon_versions_hash,
                "llm_prompt_version": cache_key.llm_prompt_version,
                "frontend_payload_version": cache_key.frontend_payload_version,
            }
            try:
                semantic_result = await self.db.execute(
                    select(SemanticLayerCache).where(
                        SemanticLayerCache.user_id == user_id,
                        SemanticLayerCache.target_date == target_date,
                    )
                )
                semantic_entry = semantic_result.scalar_one_or_none()
                if semantic_entry:
                    semantic_entry.semantic_json = json.dumps(cache_data)
                    semantic_entry.created_at = datetime.now(UTC)
                else:
                    self.db.add(SemanticLayerCache(
                        user_id=user_id,
                        target_date=target_date,
                        semantic_json=json.dumps(cache_data),
                    ))
                await self.db.commit()
            except IntegrityError:
                await self.db.rollback()
                return await self._get_cached_day_status(user_id, target_date)
            return status
        except IntegrityError:
            await self.db.rollback()
            return await self._get_cached_day_status(user_id, target_date)
        except Exception:
            await self.db.rollback()
            # If V2 is enabled, sidecar failures must propagate
            if settings.solarsage_v2_enabled:
                raise
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

    @staticmethod
    def _load_json_object(raw: str) -> dict:
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
        return data if isinstance(data, dict) else {}
