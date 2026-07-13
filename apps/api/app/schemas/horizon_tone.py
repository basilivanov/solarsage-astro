# ############################################################################
# AI_HEADER: HORIZON_TONE_SCHEMA — frozen internal B2B1 per-horizon tone contracts.
# ROLE: Validates deterministic machine tone assessments before later B2B guidance consumes them.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-TONE-SCHEMA
# purpose: Define strict internal tone result models with bounded rounded score provenance.
# owns:
#   - apps/api/app/schemas/horizon_tone.py
# inputs: Selected-anchor ids, product-sphere verdict provenance, and computed tone components.
# outputs: Frozen HorizonToneAssessment and HorizonToneResult models.
# dependencies: math stdlib, pydantic, content-canon verdict alias, public horizon aliases.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Items always preserve long, medium, fast order.
#   - Scores are finite, bounded, and already rounded to six decimals.
# failure_policy: raises Pydantic ValidationError for impossible tone states.
# END_MODULE_CONTRACT: M-HORIZON-TONE-SCHEMA

# START_MODULE_MAP: M-HORIZON-TONE-SCHEMA
# public_entrypoints:
#   - HorizonToneAssessment
#   - HorizonToneResult
# semantic_blocks:
#   - HORIZON_TONE_TYPES: internal score validation primitives.
#   - HORIZON_TONE_MODELS: frozen assessment/result contracts.
# owned_tests:
#   - apps/api/tests/test_horizon_tone_service.py
# END_MODULE_MAP: M-HORIZON-TONE-SCHEMA

# START_BLOCK: HORIZON_TONE_TYPES
from __future__ import annotations

import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from app.schemas.horizon_content_canon import HorizonSphereVerdict
from app.schemas.today_horizons import TodayV2HorizonId, TodayV2HorizonTone, TodayV2ProductSphereKey

HORIZON_ORDER: tuple[TodayV2HorizonId, ...] = ("long", "medium", "fast")
ActivationId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]


class HorizonToneModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


def _ensure_score(value: float, path: str, lower: float, upper: float) -> None:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-TONE-SCHEMA._ensure_score
    # purpose: Enforce finite bounded scores at canonical six-decimal serialization precision.
    # inputs: value - score; path - structural field location; lower/upper - inclusive bounds.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError for non-finite, out-of-range, or unrounded values.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-TONE-SCHEMA._ensure_score
    if not math.isfinite(value) or not lower <= value <= upper or round(value, 6) != value:
        raise ValueError(f"{path}: expected rounded finite bounded score")


# END_BLOCK: HORIZON_TONE_TYPES


# START_BLOCK: HORIZON_TONE_MODELS
class HorizonToneAssessment(HorizonToneModel):
    horizon: TodayV2HorizonId
    tone: TodayV2HorizonTone
    activation_confidence: float
    activation_component: float
    sphere_component: float
    net_score: float
    opposing_material_evidence: bool
    activation_ids: tuple[ActivationId, ...]
    sphere_keys: tuple[TodayV2ProductSphereKey, ...]

    @model_validator(mode="after")
    def validate_assessment(self) -> "HorizonToneAssessment":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-TONE-SCHEMA.HorizonToneAssessment.validate_assessment
        # purpose: Validate one horizon's bounded score fields and exact local provenance cardinality.
        # inputs: self - parsed tone assessment.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for invalid score/provenance state.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-TONE-SCHEMA.HorizonToneAssessment.validate_assessment
        _ensure_score(self.activation_confidence, "HorizonToneAssessment.activation_confidence", 0.0, 1.0)
        _ensure_score(self.activation_component, "HorizonToneAssessment.activation_component", -1.0, 1.0)
        _ensure_score(self.sphere_component, "HorizonToneAssessment.sphere_component", -1.0, 1.0)
        _ensure_score(self.net_score, "HorizonToneAssessment.net_score", -1.0, 1.0)
        if abs(self.activation_component) > self.activation_confidence:
            raise ValueError("HorizonToneAssessment: activation component exceeds confidence")
        if not self.sphere_keys and self.sphere_component != 0:
            raise ValueError("HorizonToneAssessment: sphere component lacks provenance")
        if self.opposing_material_evidence and (
            self.activation_component * self.sphere_component >= 0 or self.tone != "mixed"
        ):
            raise ValueError("HorizonToneAssessment: invalid opposing evidence state")
        if (
            len(self.activation_ids) != 1
            or not self.activation_ids[0]
            or len(self.sphere_keys) != len(set(self.sphere_keys))
        ):
            raise ValueError("HorizonToneAssessment: invalid local provenance")
        return self


class HorizonToneResult(HorizonToneModel):
    schema_version: Literal["horizon-tone.v1"]
    items: tuple[HorizonToneAssessment, HorizonToneAssessment, HorizonToneAssessment]

    @model_validator(mode="after")
    def validate_result(self) -> "HorizonToneResult":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-TONE-SCHEMA.HorizonToneResult.validate_result
        # purpose: Enforce exact long/medium/fast order and unique anchor provenance in one tone result.
        # inputs: self - parsed tone result.
        # returns: self.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for noncanonical item order or repeated anchor id.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-TONE-SCHEMA.HorizonToneResult.validate_result
        if tuple(item.horizon for item in self.items) != HORIZON_ORDER:
            raise ValueError("HorizonToneResult.items: expected long, medium, fast order")
        activation_ids = tuple(item.activation_ids[0] for item in self.items)
        if len(activation_ids) != len(set(activation_ids)):
            raise ValueError("HorizonToneResult.items: duplicate activation provenance")
        return self


# END_BLOCK: HORIZON_TONE_MODELS


__all__ = ["HorizonSphereVerdict", "HorizonToneAssessment", "HorizonToneResult"]
