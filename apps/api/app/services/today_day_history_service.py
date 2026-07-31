# ############################################################################
# AI_HEADER: MODULE_TODAY-DAY-HISTORY — published snapshot index for Readings history.
# ROLE: Reads owner-scoped published snapshot heads and projects compact history.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-DAY-HISTORY
# purpose: Serve Readings day-history from published TodaySnapshot rows only.
# owns:
#   - apps/api/app/services/today_day_history_service.py
# inputs: owner UUID, bounded history limit, and the owner's local access date.
# outputs: DayHistoryPayload with access projection and compact snapshot items.
# dependencies: AsyncSession, TodaySnapshot, AccessService, DayHistoryPayload.
# side_effects: reads access ledger and one indexed published-snapshot SELECT;
#   never calls sidecar, LLM, TodayService, or a calculation pipeline.
# emitted_logs: none.
# invariants:
#   - only published, non-superseded owner snapshots are eligible;
#   - rows are ordered by target_date descending and bounded by limit;
#   - locked access returns an empty item list without exposing snapshot details;
#   - history never exposes reading paragraphs or legacy dayStatus.
# failure_policy: database errors propagate; malformed persisted projection data
#   fails through the public Pydantic schema.
# END_MODULE_CONTRACT: M-TODAY-DAY-HISTORY

# START_MODULE_MAP: M-TODAY-DAY-HISTORY
# public_entrypoints:
#   - TodayDayHistoryService.get_day_history
# semantic_blocks:
#   - SNAPSHOT_INDEX: published head-snapshot query and ordering.
#   - HISTORY_PROJECTION: deterministic JSON to compact wire item.
#   - ACCESS_GATE: locked/preview/full access projection.
# owned_tests:
#   - apps/api/tests/test_today_day_history_api.py
# END_MODULE_MAP: M-TODAY-DAY-HISTORY

from __future__ import annotations

from datetime import UTC, date as Date, datetime
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db.models import TodaySnapshot
from app.schemas.today_day_history import DayHistoryItem, DayHistoryPayload
from app.services.access_service import AccessService


# START_BLOCK: SNAPSHOT_INDEX
class TodayDayHistoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_day_history(
        self,
        user_id: UUID,
        *,
        limit: int = 14,
        access_date: Date | None = None,
    ) -> DayHistoryPayload:
        # START_FUNCTION_CONTRACT: F-M-TODAY-DAY-HISTORY.get_day_history
        # purpose: Read compact owner-scoped history from published snapshot heads.
        # inputs: user_id, limit in [1, 60], optional local access date.
        # returns: DayHistoryPayload with access projection and ordered items.
        # side_effects: reads AccessLedger and published TodaySnapshot rows.
        # emitted_logs: none
        # error_behavior: invalid persisted projection data is rejected by Pydantic.
        # END_FUNCTION_CONTRACT: F-M-TODAY-DAY-HISTORY.get_day_history
        if not 1 <= limit <= 60:
            raise ValueError("limit must be between 1 and 60")

        access = await AccessService(self.db).can_access_day(
            user_id,
            access_date or datetime.now(UTC).date(),
        )
        if access.state == "locked":
            return DayHistoryPayload(items=[], access=access)

        child = aliased(TodaySnapshot)
        statement = (
            select(TodaySnapshot)
            .where(
                TodaySnapshot.user_id == user_id,
                TodaySnapshot.published_at.is_not(None),
                ~exists(
                    select(1).where(
                        child.user_id == user_id,
                        child.supersedes_snapshot_id == TodaySnapshot.id,
                    )
                ),
            )
            .order_by(
                TodaySnapshot.target_date.desc(),
                TodaySnapshot.published_at.desc(),
                TodaySnapshot.id.desc(),
            )
            .limit(limit)
        )
        result = await self.db.execute(statement)
        snapshots = result.scalars().all()
        items = [self._to_item(snapshot) for snapshot in snapshots]
        return DayHistoryPayload(items=items, access=access)
    # END_BLOCK: SNAPSHOT_INDEX

    # START_BLOCK: HISTORY_PROJECTION
    @staticmethod
    def _to_item(snapshot: TodaySnapshot) -> DayHistoryItem:
        # START_FUNCTION_CONTRACT: F-M-TODAY-DAY-HISTORY._to_item
        # purpose: Project deterministic snapshot JSON into the compact history item.
        # inputs: one published TodaySnapshot.
        # returns: DayHistoryItem with bounded selected sphere keys and impulse count.
        # side_effects: none.
        # emitted_logs: none
        # error_behavior: malformed values are rejected by DayHistoryItem validation.
        # END_FUNCTION_CONTRACT: F-M-TODAY-DAY-HISTORY._to_item
        result = snapshot.deterministic_result_json
        result_object = result if isinstance(result, dict) else {}
        selected = result_object.get("selected")
        selected_object = selected if isinstance(selected, dict) else {}

        raw_spheres = selected_object.get("selected_spheres", [])
        sphere_keys = [value for value in raw_spheres if isinstance(value, str)] if isinstance(raw_spheres, list) else []

        raw_impulses = selected_object.get("impulses", [])
        impulse_count = len(raw_impulses) if isinstance(raw_impulses, list) else 0

        return DayHistoryItem(
            date=snapshot.target_date,
            snapshot_id=str(snapshot.id),
            state=result_object.get("state"),
            day_tone=result_object.get("day_tone"),
            sphere_keys=sphere_keys[:3],
            impulse_count=impulse_count,
        )
    # END_BLOCK: HISTORY_PROJECTION
