# ############################################################################
# AI_HEADER: MODULE_CHECKIN_SERVICE
# ROLE: Core service layer for evening checkin records and streak metrics calculation.
# DEPENDENCIES: sqlalchemy, app.db.models, app.schemas.checkin
# GRACE_ANCHORS: [CHECKIN_MUTATIONS, CHECKIN_METRICS, CHECKIN_HELPERS]
# WAVE: W-8.1
# ############################################################################

# START_MODULE_CONTRACT: M-CHECKIN-SERVICE
# purpose: Manage evening checkins, calculate user streak metrics, and format responses.
# owns:
#   - apps/api/app/services/checkin_service.py
# inputs:
#   - AsyncSession DB session, user_id, target_date, mood, accuracy, energy, tags, note
# outputs:
#   - EveningCheckin, CheckinMetrics, CheckinResponse
# dependencies:
#   - M-DB-SESSION (AsyncSession)
#   - M-DB-MODELS (EveningCheckin, TodaySnapshot, User, UserProfile)
#   - M-SCHEMAS-CHECKIN (CheckinMetrics, CheckinResponse)
# side_effects:
#   - inserts/updates EveningCheckin rows
# emitted_logs: checkin.lineage_bound, checkin.lineage_absent, checkin.lineage_preserved
# failure_policy: propagates DB errors
# END_MODULE_CONTRACT: M-CHECKIN-SERVICE

# START_MODULE_MAP: M-CHECKIN-SERVICE
# public_entrypoints:
#   - CheckinService
#   - CheckinService.create_checkin
#   - CheckinService.get_checkin
#   - CheckinService.local_today
#   - CheckinService.local_yesterday
#   - CheckinService.calculate_streak
#   - CheckinService.metrics
#   - CheckinService.to_response
# semantic_blocks:
#   - CHECKIN_HELPERS: pure conversion and date utility functions
#   - CHECKIN_SERVICE_CLASS: CheckinService business logic class
#   - CHECKIN_LINEAGE: server-owned snapshot impression selection and telemetry
# owned_tests:
#   - apps/api/tests/test_checkin.py
#   - apps/api/tests/test_checkin_endpoints.py
#   - apps/api/tests/test_checkin_snapshot_lineage.py
# END_MODULE_MAP: M-CHECKIN-SERVICE

from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from typing import Literal, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log_block, log_event
from app.db.models import EveningCheckin, TodaySnapshot, User, UserProfile
from app.schemas.checkin import CheckinMetrics, CheckinResponse


LEGACY_MOOD_TO_SCORE = {
    "bad": 2,
    "neutral": 3,
    "good": 4,
    "great": 5,
}
SCORE_TO_LEGACY_MOOD = {
    1: "bad",
    2: "bad",
    3: "neutral",
    4: "good",
    5: "great",
}


# START_BLOCK: CHECKIN_HELPERS
def utc_now() -> datetime:
    return datetime.now(UTC)


def _safe_zoneinfo(tz: str | None) -> ZoneInfo:
    if not tz:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(tz)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _row_mood(row: EveningCheckin) -> int:
    if row.mood_score is not None:
        return row.mood_score
    if row.mood.isdigit():
        return int(row.mood)
    return LEGACY_MOOD_TO_SCORE.get(row.mood, 3)


def _row_tags(row: EveningCheckin) -> list[str]:
    try:
        parsed = json.loads(row.tags_json or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
# END_BLOCK: CHECKIN_HELPERS


# START_BLOCK: CHECKIN_LINEAGE
async def _load_snapshot_lineage(
    db: AsyncSession,
    user_id: uuid.UUID,
    target_date: date,
) -> tuple[uuid.UUID, datetime, Literal["day", "lookahead"]] | None:
    # START_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE._load_snapshot_lineage
    # purpose: Select the first server-recorded impression for owner/date.
    # inputs: db, authenticated user_id, check-in target_date.
    # returns: snapshot UUID, first-seen timestamp, and day/lookahead surface; or None.
    # side_effects: two read-only snapshot queries at most.
    # emitted_logs: none.
    # error_behavior: propagates database errors.
    # END_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE._load_snapshot_lineage
    base = (
        TodaySnapshot.user_id == user_id,
        TodaySnapshot.target_date == target_date,
        TodaySnapshot.published_at.is_not(None),
    )
    day = (
        await db.execute(
            select(TodaySnapshot)
            .where(*base, TodaySnapshot.first_day_seen_at.is_not(None))
            .order_by(
                TodaySnapshot.first_day_seen_at.desc(),
                TodaySnapshot.published_at.desc(),
                TodaySnapshot.id.desc(),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if day is not None:
        return day.id, cast(datetime, day.first_day_seen_at), "day"

    lookahead = (
        await db.execute(
            select(TodaySnapshot)
            .where(*base, TodaySnapshot.first_lookahead_seen_at.is_not(None))
            .order_by(
                TodaySnapshot.first_lookahead_seen_at.desc(),
                TodaySnapshot.published_at.desc(),
                TodaySnapshot.id.desc(),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if lookahead is None:
        return None
    return lookahead.id, cast(datetime, lookahead.first_lookahead_seen_at), "lookahead"


def _log_lineage_event(
    event: Literal[
        "checkin.lineage_bound",
        "checkin.lineage_absent",
        "checkin.lineage_preserved",
    ],
    payload: dict[str, object],
) -> None:
    # START_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE._log_lineage_event
    # purpose: Emit sanitized check-in lineage telemetry without affecting submit.
    # inputs: event name and packet-approved payload.
    # returns: None.
    # side_effects: writes one structured log event when logging is available.
    # emitted_logs: checkin.lineage_bound, checkin.lineage_absent, checkin.lineage_preserved.
    # error_behavior: swallows logging failures after the business mutation.
    # END_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE._log_lineage_event
    try:
        with log_block(
            slice="W-TODAY-CONVERGENCE-W3",
            module="M-CHECKIN-SERVICE",
            block="CHECKIN_LINEAGE",
        ):
            log_event(event, msg="checkin snapshot lineage", payload=payload)
    except Exception:
        return
# END_BLOCK: CHECKIN_LINEAGE


# START_BLOCK: CHECKIN_SERVICE_CLASS
class CheckinService:
    """Evening check-in service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_checkin(
        self,
        user_id: uuid.UUID,
        target_date: date,
        mood: int,
        accuracy: int | None,
        energy: int | None,
        tags: list[str] | None,
        note: str | None,
        observed_spheres: list[str] | None,
    ) -> EveningCheckin:
        # START_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE.create_checkin
        # purpose: Create or update evening checkin for target date.
        # inputs: user_id, target_date, mood, accuracy, energy, tags, note, observed_spheres
        # returns: EveningCheckin
        # side_effects: inserts/updates EveningCheckin row and reads snapshot lineage
        # emitted_logs: checkin.lineage_bound, checkin.lineage_absent, checkin.lineage_preserved
        # error_behavior: propagates DB exceptions
        # END_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE.create_checkin
        result = await self.db.execute(
            select(EveningCheckin).where(
                EveningCheckin.user_id == user_id,
                EveningCheckin.target_date == target_date,
            )
        )
        checkin = result.scalar_one_or_none()

        filled_at = utc_now()
        streak = await self.calculate_streak(user_id, target_date)
        tags_list = tags or []
        is_new = checkin is None
        lineage = await _load_snapshot_lineage(self.db, user_id, target_date) if is_new else None

        if is_new:
            checkin = EveningCheckin(
                user_id=user_id,
                target_date=target_date,
                mood=SCORE_TO_LEGACY_MOOD[mood],
                notes=note,
            )
            if lineage is not None:
                checkin.forecast_snapshot_id, checkin.prediction_seen_at, checkin.prediction_seen_surface = lineage
            self.db.add(checkin)
        else:
            checkin = cast(EveningCheckin, checkin)
            checkin.mood = SCORE_TO_LEGACY_MOOD[mood]
            checkin.notes = note

        checkin = cast(EveningCheckin, checkin)
        checkin.mood_score = mood
        checkin.accuracy = accuracy
        checkin.energy = energy
        checkin.tags_json = json.dumps(tags_list, ensure_ascii=False)
        checkin.note = note
        checkin.observed_spheres = list(observed_spheres) if observed_spheres is not None else None
        checkin.streak = streak
        checkin.filled_at = filled_at

        await self.db.commit()
        await self.db.refresh(checkin)
        if is_new:
            if lineage is None:
                _log_lineage_event("checkin.lineage_absent", {"reason": "no_impression"})
            else:
                _log_lineage_event("checkin.lineage_bound", {"surface": lineage[2]})
        else:
            _log_lineage_event(
                "checkin.lineage_preserved",
                {"has_lineage": checkin.forecast_snapshot_id is not None},
            )
        return checkin

    async def get_checkin(
        self,
        user_id: uuid.UUID,
        target_date: date,
    ) -> EveningCheckin | None:
        # START_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE.get_checkin
        # purpose: Retrieve checkin row for target_date.
        # inputs: user_id (UUID), target_date (date)
        # returns: EveningCheckin or None
        # side_effects: none
        # error_behavior: propagates DB exceptions
        # END_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE.get_checkin
        result = await self.db.execute(
            select(EveningCheckin).where(
                EveningCheckin.user_id == user_id,
                EveningCheckin.target_date == target_date,
            )
        )
        return result.scalar_one_or_none()

    async def local_today(self, user: User) -> date:
        # START_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE.local_today
        # purpose: Calculate current local date for user timezone.
        # inputs: user (User)
        # returns: date
        # side_effects: none
        # error_behavior: none
        # END_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE.local_today
        tz = _safe_zoneinfo(self._profile_timezone(user.profile))
        return utc_now().astimezone(tz).date()

    async def local_yesterday(self, user: User) -> date:
        # START_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE.local_yesterday
        # purpose: Calculate yesterday's local date for user timezone.
        # inputs: user (User)
        # returns: date
        # side_effects: none
        # error_behavior: none
        # END_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE.local_yesterday
        return await self.local_today(user) - timedelta(days=1)

    async def calculate_streak(self, user_id: uuid.UUID, target_date: date) -> int:
        # START_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE.calculate_streak
        # purpose: Calculate consecutive checkin streak up to target_date.
        # inputs: user_id (UUID), target_date (date)
        # returns: int streak count
        # side_effects: none
        # error_behavior: propagates DB exceptions
        # END_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE.calculate_streak
        dates = await self._checkin_dates_through(user_id, target_date)
        streak = 1
        cursor = target_date - timedelta(days=1)
        for existing_date in dates:
            if existing_date == target_date:
                continue
            if existing_date == cursor:
                streak += 1
                cursor -= timedelta(days=1)
                continue
            if existing_date < cursor:
                break
        return streak

    async def metrics(
        self,
        user_id: uuid.UUID,
        from_date: date | None,
        to_date: date | None,
        *,
        fallback_to_date: date,
    ) -> CheckinMetrics:
        # START_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE.metrics
        # purpose: Calculate aggregated checkin metrics for date range.
        # inputs: user_id, from_date, to_date, fallback_to_date
        # returns: CheckinMetrics
        # side_effects: none
        # error_behavior: propagates DB exceptions
        # END_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE.metrics
        lower = from_date or date.min
        upper = to_date or fallback_to_date
        rows = (
            await self.db.execute(
                select(EveningCheckin)
                .where(
                    EveningCheckin.user_id == user_id,
                    EveningCheckin.target_date >= lower,
                    EveningCheckin.target_date <= upper,
                )
                .order_by(EveningCheckin.target_date.asc())
            )
        ).scalars().all()

        total = len(rows)
        moods = [_row_mood(row) for row in rows]
        energies = [row.energy for row in rows if row.energy is not None]
        accuracies = [row.accuracy for row in rows if row.accuracy is not None]

        tag_frequency: Counter[str] = Counter()
        for row in rows:
            tag_frequency.update(_row_tags(row))

        all_dates = [row.target_date for row in rows]
        return CheckinMetrics(
            total_checkins=total,
            current_streak=self._current_streak_from_dates(all_dates, upper),
            longest_streak=self._longest_streak_from_dates(all_dates),
            average_mood=(sum(moods) / total) if total else 0,
            average_energy=(sum(energies) / len(energies)) if energies else None,
            average_accuracy=(
                sum(accuracies) / len(accuracies) if accuracies else None
            ),
            mood_distribution=dict(Counter(str(mood) for mood in moods)),
            accuracy_distribution=dict(Counter(str(value) for value in accuracies)),
            tag_frequency=dict(tag_frequency),
        )

    def to_response(self, row: EveningCheckin) -> CheckinResponse:
        # START_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE.to_response
        # purpose: Convert EveningCheckin ORM model to CheckinResponse schema.
        # inputs: row (EveningCheckin)
        # returns: CheckinResponse
        # side_effects: none
        # error_behavior: none
        # END_FUNCTION_CONTRACT: F-M-CHECKIN-SERVICE.to_response
        return CheckinResponse(
            id=row.id,
            target_date=row.target_date,
            mood=_row_mood(row),
            accuracy=row.accuracy,
            energy=row.energy,
            tags=_row_tags(row),
            note=row.note if row.note is not None else row.notes,
            streak=row.streak or 1,
            filled_at=_as_utc(row.filled_at or row.created_at),
            created_at=_as_utc(row.created_at) or utc_now(),
            observed_spheres=row.observed_spheres,
            forecast_snapshot_id=row.forecast_snapshot_id,
            prediction_seen_at=_as_utc(row.prediction_seen_at),
            prediction_seen_surface=row.prediction_seen_surface,
        )

    async def _checkin_dates_through(
        self,
        user_id: uuid.UUID,
        target_date: date,
    ) -> list[date]:
        return list(
            (
                await self.db.execute(
                    select(EveningCheckin.target_date)
                    .where(
                        EveningCheckin.user_id == user_id,
                        EveningCheckin.target_date <= target_date,
                    )
                    .order_by(EveningCheckin.target_date.desc())
                )
            ).scalars()
        )

    @staticmethod
    def _profile_timezone(profile: UserProfile | None) -> str | None:
        if profile is None:
            return None
        return profile.current_tz or profile.birth_tz

    @staticmethod
    def _current_streak_from_dates(dates: list[date], anchor_date: date) -> int:
        if not dates:
            return 0
        unique_dates = set(dates)
        if anchor_date not in unique_dates:
            return 0
        ordered = sorted(unique_dates, reverse=True)
        streak = 1
        cursor = anchor_date - timedelta(days=1)
        for item in ordered[1:]:
            if item == cursor:
                streak += 1
                cursor -= timedelta(days=1)
            elif item < cursor:
                break
        return streak

    @staticmethod
    def _longest_streak_from_dates(dates: list[date]) -> int:
        if not dates:
            return 0
        longest = 1
        current = 1
        ordered = sorted(set(dates))
        for previous, current_date in zip(ordered, ordered[1:]):
            if current_date == previous + timedelta(days=1):
                current += 1
            else:
                longest = max(longest, current)
                current = 1
        return max(longest, current)
# END_BLOCK: CHECKIN_SERVICE_CLASS
