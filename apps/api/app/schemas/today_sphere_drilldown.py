# ############################################################################
# AI_HEADER: MODULE_SCHEMAS_TODAY-SPHERE-DRILLDOWN — deterministic sphere evidence wire.
# ROLE: Defines the owner/full-access drilldown projection for one published
#   Today convergence snapshot and one canonical sphere.
# ############################################################################

# START_MODULE_CONTRACT: M-SCHEMAS-TODAY-SPHERE-DRILLDOWN
# purpose: Define the strict deterministic sphere drilldown payload.
# owns:
#   - apps/api/app/schemas/today_sphere_drilldown.py
# inputs: validated snapshot projection fields.
# outputs: camelCase TodaySphereDrilldownPayload and compact convergence block.
# dependencies: CamelModel and Today convergence event schemas.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - events use the existing TodayConvergenceEvent wire shape.
#   - convergence contains only deterministic evidence identifiers and metadata.
#   - narrative/LLM fields are not present in this contract.
# failure_policy: Pydantic rejects malformed enum, event, and sphere values.
# END_MODULE_CONTRACT: M-SCHEMAS-TODAY-SPHERE-DRILLDOWN

# START_MODULE_MAP: M-SCHEMAS-TODAY-SPHERE-DRILLDOWN
# public_entrypoints:
#   - TodaySphereDrilldownConvergence
#   - TodaySphereDrilldownPayload
# semantic_blocks:
#   - DRILLDOWN_TYPES: deterministic top-level and convergence wire models.
# owned_tests:
#   - apps/api/tests/test_today_sphere_drilldown_api.py
# END_MODULE_MAP: M-SCHEMAS-TODAY-SPHERE-DRILLDOWN

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas._base import CamelModel
from app.schemas.today_convergence import (
    BirthMode,
    CanonicalSphere,
    DayTone,
    EvidenceLevel,
    Polarity,
    TodayConvergenceEvent,
)


# START_BLOCK: DRILLDOWN_TYPES
class TodaySphereDrilldownConvergence(CamelModel):
    id: str
    primary_sphere: CanonicalSphere
    secondary_sphere: CanonicalSphere | None
    polarity: Polarity
    evidence_level: EvidenceLevel
    event_ids: list[str] = Field(..., min_length=2)


class TodaySphereDrilldownPayload(CamelModel):
    snapshot_id: str
    sphere: CanonicalSphere
    state: Literal["convergence_today", "quiet_day"]
    day_tone: DayTone
    birth_time_mode: BirthMode
    events: list[TodayConvergenceEvent]
    convergence: TodaySphereDrilldownConvergence | None
# END_BLOCK: DRILLDOWN_TYPES

