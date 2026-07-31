# ############################################################################
# AI_HEADER: MODULE_SCHEMAS_TODAY_DAY_HISTORY — published Today snapshot history wire contract.
# ROLE: Defines the compact Readings history payload without legacy day readings.
# ############################################################################

# START_MODULE_CONTRACT: M-SCHEMAS-TODAY-HISTORY
# purpose: Define the DayHistoryPayload returned by the published snapshot index.
# owns:
#   - apps/api/app/schemas/today_day_history.py
# inputs: validated deterministic snapshot projections and access state.
# outputs: camelCase DayHistoryPayload and DayHistoryItem models.
# dependencies: Pydantic CamelModel, ContentAccessState, Today convergence literals.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - history items contain only date, snapshotId, state, dayTone, sphereKeys, impulseCount.
#   - sphereKeys is bounded to three selected spheres.
#   - legacy reading.paragraphs and dayStatus are not part of the wire contract.
# failure_policy: Pydantic validation rejects malformed enum, count, and extra fields.
# END_MODULE_CONTRACT: M-SCHEMAS-TODAY-HISTORY

# START_MODULE_MAP: M-SCHEMAS-TODAY-HISTORY
# public_entrypoints:
#   - DayHistoryItem
#   - DayHistoryPayload
# semantic_blocks:
#   - DAY_HISTORY_TYPES: compact snapshot-indexed history models.
# owned_tests:
#   - apps/api/tests/test_today_day_history_api.py
# END_MODULE_MAP: M-SCHEMAS-TODAY-HISTORY

from __future__ import annotations

from datetime import date as Date
from typing import Literal

from pydantic import Field

from ._base import CamelModel
from .access import ContentAccessState
from .today_convergence import DayTone


# START_BLOCK: DAY_HISTORY_TYPES
class DayHistoryItem(CamelModel):
    date: Date
    snapshot_id: str
    state: Literal["convergence_today", "quiet_day"]
    day_tone: DayTone
    sphere_keys: list[str] = Field(..., max_length=3)
    impulse_count: int = Field(ge=0)


class DayHistoryPayload(CamelModel):
    items: list[DayHistoryItem]
    access: ContentAccessState
# END_BLOCK: DAY_HISTORY_TYPES
