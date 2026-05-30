# AI_HEADER
# module: M-DAY-SERVICE
# canon: docs/GRACE_CANON.md §6; docs/05_API_contracts_и_TodayPayload.md
# wave: W-1.3 (fixture-backed), W-3.4 (real pipeline)
# purpose: TodayService returns TodayPayload for a given user and date.

# START_MODULE_CONTRACT: M-DAY-SERVICE
# purpose: Get TodayPayload for a user and date.
#          W-1.3: returns fixture-backed payload.
#          W-3.4: calls calculation_service → solarsage_client.
#          W-4.3: calls semantic_layer_service.
#          W-5.1: calls llm_service.
# owns:
#   - apps/api/app/services/today_service.py
# inputs:
#   - user_id: UUID
#   - target_date: date
#   - access_state: ContentAccessState
#   - db: AsyncSession
# outputs:
#   - TodayPayload
# dependencies:
#   - M-DB-SESSION (AsyncSession)
#   - M-CONTRACTS.today (TodayPayload)
#   - M-ACCESS (ContentAccessState)
# invariants:
#   - W-1.3: loads fixture from apps/api/app/fixtures/day_*.json.
#   - W-3.4: calls calculation pipeline.
#   - meta.cached is always false in W-1.3 (real cache in W-3.4).
# failure_policy:
#   - fixture not found → fallback to day_generic.json.
#   - W-3.4: calculation error → 500.
# non_goals:
#   - no caching (W-3.4)
#   - no LLM generation (W-5.1)
# END_MODULE_CONTRACT

# START_MODULE_MAP: M-DAY-SERVICE
# public_entrypoints:
#   - TodayService.get_today_payload
# semantic_blocks:
#   - FIXTURE_LOADER: load fixture from disk
#   - PAYLOAD_BUILDER: construct TodayPayload
# owned_tests:
#   - apps/api/tests/test_today_service.py (W-1.3)
# END_MODULE_MAP

from __future__ import annotations

import json
from datetime import date as Date
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.access import ContentAccessState
from app.schemas.today import TodayPayload

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# START_BLOCK: FIXTURE_LOADER
class TodayService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_today_payload(
        self,
        user_id,
        target_date: Date,
        access_state: ContentAccessState,
    ) -> TodayPayload:
        """
        Get TodayPayload for a user and date.

        W-1.3: returns fixture-backed payload.
        W-3.4: calls calculation_service → solarsage_client.
        W-4.3: calls semantic_layer_service.
        W-5.1: calls llm_service.
        """
        # W-1.3: load fixture
        fixture_path = FIXTURES_DIR / f"day_{target_date.isoformat()}.json"
        if not fixture_path.exists():
            # Fallback to generic fixture
            fixture_path = FIXTURES_DIR / "day_generic.json"

        with open(fixture_path) as f:
            fixture_data = json.load(f)

        # Override date and access
        fixture_data["date"] = target_date.isoformat()
        fixture_data["access"] = access_state.model_dump(by_alias=True)
        fixture_data["meta"]["cached"] = False  # Real cache in W-3.4

        return TodayPayload.model_validate(fixture_data)
# END_BLOCK: FIXTURE_LOADER
