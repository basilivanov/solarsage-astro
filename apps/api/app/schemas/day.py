# ############################################################################
# AI_HEADER: MODULE_SCHEMAS_DAY
# ROLE: Pydantic schemas for relative day status models and zone indicator metadata.
# DEPENDENCIES: pydantic, app.schemas._base.CamelModel
# ############################################################################

# START_MODULE_CONTRACT: M-SCHEMAS-DAY
# purpose: Relative day status schema definitions (baseline statistics, status enum, zone band and marker).
# owns:
#   - apps/api/app/schemas/day.py
# inputs: none
# outputs: RelativeStatusBaseline, RelativeDayStatusRead
# dependencies: app.schemas._base.CamelModel
# side_effects: none (pure schema)
# emitted_logs: none
# failure_policy: Pydantic ValidationError on schema mismatch
# END_MODULE_CONTRACT: M-SCHEMAS-DAY

# START_MODULE_MAP: M-SCHEMAS-DAY
# public_entrypoints:
#   - RelativeStatusBaseline
#   - RelativeDayStatusRead
# semantic_blocks: none
# owned_tests: none
# END_MODULE_MAP: M-SCHEMAS-DAY

from __future__ import annotations

from typing import Literal
from pydantic import Field

from app.schemas._base import CamelModel


class RelativeStatusBaseline(CamelModel):
    support_mean: float = Field(..., description="14-day mean support score")
    support_std: float = Field(..., description="14-day std support score")
    tension_mean: float = Field(..., description="14-day mean tension score")
    tension_std: float = Field(..., description="14-day std tension score")
    days: int = Field(..., description="Number of historical days in baseline (0..14)")


class RelativeDayStatusRead(CamelModel):
    mode: Literal["absolute", "relative"] = Field(..., description="Calculation mode: fallback absolute or z-score relative")
    status: Literal["usual", "softer", "tenser", "hard", "strong"] = Field(..., description="Relative day status code")
    label: str = Field(..., description="Localized human label e.g. Обычный день, Легче, чем обычно, Напряжённее обычного, Тяжёлый день, Сильный день")
    z_support: float = Field(..., description="Z-score for today's support score")
    z_tension: float = Field(..., description="Z-score for today's tension score")
    support_band: list[float] = Field(default_factory=list, description="Support normal range [mean-std, mean+std]")
    tension_band: list[float] = Field(default_factory=list, description="Tension normal range [mean-std, mean+std]")
    support_marker: float = Field(default=0.5, description="Normalized support position 0..1 for UI zone indicator")
    tension_marker: float = Field(default=0.5, description="Normalized tension position 0..1 for UI zone indicator")
    baseline: RelativeStatusBaseline = Field(..., description="Historical baseline statistics")
