# ############################################################################
# AI_HEADER: HORIZON_GUIDANCE_SCHEMA — frozen internal B2B2 guidance context and typed errors.
# ROLE: Defines the strict input context for deterministic guidance and closed error types.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-GUIDANCE-SCHEMA
# purpose: Own the HorizonGuidanceContext input model and typed HorizonGuidanceError/
#          HorizonClaimValidationError used across B2B2 services.
# owns:
#   - apps/api/app/schemas/horizon_guidance.py
# inputs: Accepted B2B1 selection, fact-pack, tone, and sphere-verdict outputs.
# outputs: Strict frozen context model for HorizonGuidanceService.build().
# dependencies: pydantic, B2A/B2B content-canon/selection/fact/tone schemas.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - All models are frozen and forbid extra fields.
#   - Error stringifications never include human claim body, raw evidence, debug, natal values, or profile.
# failure_policy: raises Pydantic ValidationError on invalid context; HorizonGuidanceError on guidance failures.
# END_MODULE_CONTRACT: M-HORIZON-GUIDANCE-SCHEMA

# START_MODULE_MAP: M-HORIZON-GUIDANCE-SCHEMA
# public_entrypoints:
#   - HorizonGuidanceContext
#   - HorizonGuidanceError
#   - HorizonClaimValidationError
#   - HorizonTimingPresentation
# semantic_blocks:
#   - GUIDANCE_TYPES: typed error classes.
#   - GUIDANCE_TIMING_PRESENTATION: recomputed frozen timing labels.
#   - GUIDANCE_CONTEXT_MODEL: frozen context input.
# owned_tests:
#   - apps/api/tests/test_horizon_guidance_service.py
#   - apps/api/tests/test_horizon_claim_validator.py
# END_MODULE_MAP: M-HORIZON-GUIDANCE-SCHEMA

# START_BLOCK: GUIDANCE_TYPES
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.horizon_content_canon import HorizonSphereVerdict
from app.schemas.horizon_selection import SelectedHorizonTriple
from app.schemas.horizon_tone import HorizonToneResult
from app.schemas.personal_fact_pack import PersonalFactPack
from app.schemas.today_horizons import (
    TodayV2HorizonTiming,
    TodayV2ProductSphereKey,
)


class HorizonGuidanceError(ValueError):
    """Compact typed error for guidance construction failures.

    Stringifies only code/path/opaque ID — never human claim body,
    raw evidence, debug, natal values, or profile.
    """

    def __init__(
        self,
        code: str,
        path: str = "",
        item_id: str | None = None,
    ) -> None:
        self.code = code
        self.path = path
        parts = [code]
        if path:
            parts.append(path)
        super().__init__(" | ".join(parts))


class HorizonClaimValidationError(ValueError):
    """Compact typed error for claim validation failures.

    Same privacy contract as HorizonGuidanceError.
    """

    def __init__(
        self,
        code: str,
        path: str = "",
        item_id: str | None = None,
    ) -> None:
        self.code = code
        self.path = path
        parts = [code]
        if path:
            parts.append(path)
        super().__init__(" | ".join(parts))


# END_BLOCK: GUIDANCE_TYPES


# START_BLOCK: GUIDANCE_TIMING_PRESENTATION
class HorizonTimingPresentation(BaseModel):
    """Recomputed timing labels for deterministic claim validation.

    Every field is derived from raw anchor timing + formatter.
    Used by both the guidance service (to build public timing) and the
    validator (to independently recompute expected values).
    """

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    public_timing: TodayV2HorizonTiming
    active_from_label: str
    active_until_label: str
    exact_at_label: str | None
    valid_until_label: str
    timezone_suffix: str


# END_BLOCK: GUIDANCE_TIMING_PRESENTATION

# Resolve forward references for Pydantic
HorizonTimingPresentation.model_rebuild()

# START_BLOCK: GUIDANCE_CONTEXT_MODEL
class HorizonGuidanceContext(BaseModel):
    """Frozen internal input for deterministic guidance construction.

    Carries all accepted B2B1 outputs needed to build a public horizons block.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
    )

    schema_version: Literal["horizon-guidance-context.v1"]
    selection: SelectedHorizonTriple
    fact_pack: PersonalFactPack
    tone_result: HorizonToneResult
    sphere_verdicts: dict[
        TodayV2ProductSphereKey,
        HorizonSphereVerdict,
    ]

    @model_validator(mode="after")
    def validate_context(self) -> "HorizonGuidanceContext":
        # START_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-SCHEMA.HorizonGuidanceContext.validate_context
        # purpose: Enforce strict alignment of selection, fact-pack, tone, and timing invariants.
        # inputs: self - parsed context candidate.
        # returns: self when all alignment checks pass.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError with structural reason only.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-GUIDANCE-SCHEMA.HorizonGuidanceContext.validate_context
        items = self.selection.items
        selected_ids = tuple(item.activation_id for item in items)
        if list(self.selection.unique_anchor_activation_ids) != list(selected_ids):
            raise ValueError(
                "HorizonGuidanceContext: selection.unique_anchor_activation_ids"
                " must equal ordered selected IDs"
            )

        if self.fact_pack.selected_activation_ids != selected_ids:
            raise ValueError(
                "HorizonGuidanceContext: fact_pack.selected_activation_ids"
                " must equal ordered selected IDs"
            )

        tone_items = self.tone_result.items
        if [t.horizon for t in tone_items] != ["long", "medium", "fast"]:
            raise ValueError(
                "HorizonGuidanceContext: tone items must be long/medium/fast"
            )

        for i, tone_item in enumerate(tone_items):
            if len(tone_item.activation_ids) != 1:
                raise ValueError(
                    "HorizonGuidanceContext: each tone item must have exactly one activation ID"
                )
            if tone_item.activation_ids[0] != selected_ids[i]:
                raise ValueError(
                    "HorizonGuidanceContext: tone activation ID must equal selected anchor ID"
                )

        timezones = {item.timing.timezone for item in items}
        if len(timezones) != 1:
            raise ValueError(
                "HorizonGuidanceContext: all three anchor timing timezones must be equal"
            )

        target_locals = {item.timing.target_local for item in items}
        target_utcs = {item.timing.target_utc for item in items}
        if len(target_locals) != 1 or len(target_utcs) != 1:
            raise ValueError(
                "HorizonGuidanceContext: mismatched target_local or target_utc"
            )

        return self


# END_BLOCK: GUIDANCE_CONTEXT_MODEL


__all__ = [
    "HorizonGuidanceContext",
    "HorizonGuidanceError",
    "HorizonClaimValidationError",
    "HorizonTimingPresentation",
]
