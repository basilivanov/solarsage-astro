# ############################################################################
# AI_HEADER: MODULE_MICROCOPY_SERVICE
# ROLE: Microcopy service with miss tracking (W-9.1, W-9.2)
# DEPENDENCIES: sqlalchemy, app.db.models.MicrocopyMiss
# GRACE_ANCHORS: [MICROCOPY_DICTIONARY, GET_MICROCOPY, TRACK_MISS, WEEKLY_REPORT]
# WAVE: W-9.1, W-9.2
# ############################################################################

# START_MODULE_CONTRACT: M-MICROCOPY-SERVICE
# purpose: Provide microcopy strings by key, track missing keys for later addition.
# owns:
#   - apps/api/app/services/microcopy_service.py
# inputs:
#   - key: str (microcopy key)
#   - context: str | None (optional context for tracking)
#   - db: AsyncSession (for miss tracking)
# outputs:
#   - get(key, context) -> str: microcopy string or fallback [key]
#   - get_weekly_report() -> list[dict]: weekly report of missed keys
# dependencies:
#   - M-DB-MODELS (MicrocopyMiss)
# side_effects:
#   - writes to microcopy_misses table when key not found
# invariants:
#   - missing keys return fallback format: [key]
#   - hit_count increments on repeated misses
# failure_policy:
#   - DB errors during tracking are logged but do not block microcopy retrieval
# non_goals:
#   - no dynamic dictionary loading (MVP uses hardcoded dict)
# END_MODULE_CONTRACT: M-MICROCOPY-SERVICE

from datetime import datetime, timedelta, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.models import MicrocopyMiss


class MicrocopyService:
    """Microcopy service with miss tracking. W-9.1, W-9.2."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dictionary = self._load_dictionary()

    def _load_dictionary(self) -> dict[str, str]:
        """
        Load microcopy dictionary.

        W-9.1: MVP uses hardcoded dictionary.
        """
        return {
            "day.supportive.headline": "День возможностей",
            "day.steady.headline": "Спокойный день",
            "day.tense.headline": "День вызовов",
        }

    async def get(self, key: str, context: str | None = None) -> str:
        """
        Get microcopy by key.

        W-9.2: Track misses if key not found.

        Args:
            key: Microcopy key
            context: Optional context for tracking

        Returns:
            Microcopy string or fallback [key]
        """
        if key in self.dictionary:
            return self.dictionary[key]

        # W-9.2: Track miss
        try:
            await self._track_miss(key, context)
        except Exception as e:
            logger.error(f"Failed to track microcopy miss: {e}", extra={"key": key})

        # Return fallback
        return f"[{key}]"

    async def _track_miss(self, key: str, context: str | None) -> None:
        """
        Track missing microcopy key.

        W-9.2: Upsert logic — increment hit_count if exists, create if new.
        """
        # Check if already tracked
        result = await self.db.execute(
            select(MicrocopyMiss).where(MicrocopyMiss.key == key)
        )
        miss = result.scalar_one_or_none()

        if miss:
            # Update existing
            miss.last_seen = datetime.now(UTC)
            miss.hit_count += 1
        else:
            # Create new
            miss = MicrocopyMiss(
                key=key,
                context=context,
                first_seen=datetime.now(UTC),
                last_seen=datetime.now(UTC),
                hit_count=1,
            )
            self.db.add(miss)

        await self.db.commit()

    async def get_weekly_report(self) -> list[dict]:
        """
        Get weekly report of missed keys.

        W-9.2: Returns misses from last 7 days, ordered by hit_count desc.

        Returns:
            List of {key, hit_count, first_seen, last_seen}
        """
        week_ago = datetime.now(UTC) - timedelta(days=7)

        result = await self.db.execute(
            select(MicrocopyMiss)
            .where(MicrocopyMiss.last_seen >= week_ago)
            .order_by(MicrocopyMiss.hit_count.desc())
        )
        misses = result.scalars().all()

        return [
            {
                "key": miss.key,
                "hit_count": miss.hit_count,
                "first_seen": miss.first_seen.isoformat(),
                "last_seen": miss.last_seen.isoformat(),
            }
            for miss in misses
        ]
