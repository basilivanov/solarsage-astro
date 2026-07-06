from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EveningCheckin, User, UserProfile
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
    ) -> EveningCheckin:
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

        if checkin is None:
            checkin = EveningCheckin(
                user_id=user_id,
                target_date=target_date,
                mood=SCORE_TO_LEGACY_MOOD[mood],
                notes=note,
            )
            self.db.add(checkin)
        else:
            checkin.mood = SCORE_TO_LEGACY_MOOD[mood]
            checkin.notes = note

        checkin.mood_score = mood
        checkin.accuracy = accuracy
        checkin.energy = energy
        checkin.tags_json = json.dumps(tags_list, ensure_ascii=False)
        checkin.note = note
        checkin.streak = streak
        checkin.filled_at = filled_at

        await self.db.commit()
        await self.db.refresh(checkin)
        return checkin

    async def get_checkin(
        self,
        user_id: uuid.UUID,
        target_date: date,
    ) -> EveningCheckin | None:
        result = await self.db.execute(
            select(EveningCheckin).where(
                EveningCheckin.user_id == user_id,
                EveningCheckin.target_date == target_date,
            )
        )
        return result.scalar_one_or_none()

    async def local_today(self, user: User) -> date:
        tz = _safe_zoneinfo(self._profile_timezone(user.profile))
        return utc_now().astimezone(tz).date()

    async def local_yesterday(self, user: User) -> date:
        return await self.local_today(user) - timedelta(days=1)

    async def calculate_streak(self, user_id: uuid.UUID, target_date: date) -> int:
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
            current_streak=self._current_streak_from_dates(all_dates),
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
            created_at=_as_utc(row.created_at),
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
    def _current_streak_from_dates(dates: list[date]) -> int:
        if not dates:
            return 0
        ordered = sorted(set(dates), reverse=True)
        streak = 1
        cursor = ordered[0] - timedelta(days=1)
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
