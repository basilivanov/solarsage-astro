# ############################################################################
# AI_HEADER: HORIZON_PIPELINE_SCHEMA — strict internal B3.W1 pipeline result contract.
# ROLE: Models the pure horizon orchestration result without exposing debug facts or public barrels.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-PIPELINE-SCHEMA
# purpose: Define the frozen internal result returned by HorizonPipelineService.build().
# owns:
#   - apps/api/app/schemas/horizon_pipeline.py
# inputs: Existing HorizonSelectionReason/Diagnostics and optional TodayV2HorizonsBlock.
# outputs: HorizonPipelineResult with honest built/unavailable invariants.
# dependencies: typing, pydantic, app.schemas.horizon_selection, app.schemas.today_horizons.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - built means selected plus a validated public horizons block.
#   - unavailable means non-selected reason plus null horizons.
#   - diagnostics remain the bounded existing machine diagnostics only.
# failure_policy: raises Pydantic ValidationError with hidden inputs for contradictory internal states.
# END_MODULE_CONTRACT: M-HORIZON-PIPELINE-SCHEMA

# START_MODULE_MAP: M-HORIZON-PIPELINE-SCHEMA
# public_entrypoints:
#   - HorizonPipelineResult
# semantic_blocks:
#   - HORIZON_PIPELINE_TYPES: status literal aliases.
#   - HORIZON_PIPELINE_MODELS: frozen orchestration result model.
# owned_tests:
#   - apps/api/tests/test_horizon_pipeline_service.py
# END_MODULE_MAP: M-HORIZON-PIPELINE-SCHEMA

# START_BLOCK: HORIZON_PIPELINE_TYPES
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.horizon_selection import HorizonSelectionDiagnostics, HorizonSelectionReason
from app.schemas.today_horizons import TodayV2HorizonsBlock

HorizonPipelineStatus = Literal["built", "unavailable"]
HORIZON_PIPELINE_RESULT_VERSION: Literal["horizon-pipeline-result.v1"] = "horizon-pipeline-result.v1"
# END_BLOCK: HORIZON_PIPELINE_TYPES


# START_BLOCK: HORIZON_PIPELINE_MODELS
class HorizonPipelineResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    schema_version: Literal["horizon-pipeline-result.v1"] = HORIZON_PIPELINE_RESULT_VERSION
    status: HorizonPipelineStatus
    horizons: TodayV2HorizonsBlock | None = None
    selection_reason: HorizonSelectionReason
    selection_diagnostics: HorizonSelectionDiagnostics

    @model_validator(mode="after")
    def validate_result(self) -> "HorizonPipelineResult":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-PIPELINE-SCHEMA.HorizonPipelineResult.validate_result
        # purpose: Enforce the atomic built/unavailable result invariant.
        # inputs: self - parsed pipeline result candidate.
        # returns: self when status, selection reason, and horizons are aligned.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError with structural text only on contradiction.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-PIPELINE-SCHEMA.HorizonPipelineResult.validate_result
        if self.status == "built":
            if self.selection_reason != "selected" or self.horizons is None:
                raise ValueError("HorizonPipelineResult: built requires selected horizons")
        else:
            if self.selection_reason == "selected" or self.horizons is not None:
                raise ValueError("HorizonPipelineResult: unavailable requires null non-selected result")
        return self


# END_BLOCK: HORIZON_PIPELINE_MODELS


__all__ = [
    "HORIZON_PIPELINE_RESULT_VERSION",
    "HorizonPipelineStatus",
    "HorizonPipelineResult",
]
