# ############################################################################
# AI_HEADER: TODAY_HORIZON_INTEGRATION_SERVICE — request-local Today horizon bridge.
# ROLE: Derives safe product-sphere verdicts from final concrete advice, calls the
#       pure HorizonPipelineService once, and emits one sanitized pipeline log.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-HORIZON-INTEGRATION-SERVICE
# purpose: Integrate the accepted pure horizon pipeline into TodayService using
#          already computed ActivationLayer, ScoringV2Result, NatalContextData,
#          and ConcreteAdviceBlock objects.
# owns:
#   - apps/api/app/services/today_horizon_integration_service.py
# inputs: ActivationLayer, ScoringV2Result, NatalContextData, ConcreteAdviceBlock.
# outputs: HorizonPipelineResult from HorizonPipelineService.build unchanged.
# dependencies: time, typing, schemas, app.core.logging, HorizonPipelineService.
# side_effects: emits one sanitized day.payload_built structured event per call.
# emitted_logs: day.payload_built
# invariants:
#   - Verdict mapping reads only ConcreteAdviceRow.key and ConcreteAdviceRow.verdict.
#   - HorizonPipelineService receives exact caller-owned activation/scoring/natal identities.
#   - No DB, FastAPI, settings, sidecar, natal service, scoring runtime, LLM, ORM, or network import.
# failure_policy: verdict/pipeline errors are logged once with closed reason and re-raised unchanged.
# END_MODULE_CONTRACT: M-TODAY-HORIZON-INTEGRATION-SERVICE

# START_MODULE_MAP: M-TODAY-HORIZON-INTEGRATION-SERVICE
# public_entrypoints:
#   - HorizonVerdictMappingError
#   - derive_sphere_verdicts
#   - TodayHorizonIntegrationService.build
# semantic_blocks:
#   - VERDICT_MAPPING: closed key+verdict-only mapping derivation.
#   - SAFE_PIPELINE_LOGGING: sanitized structured event emission.
#   - TODAY_HORIZON_INTEGRATION: thin pipeline orchestration bridge.
# owned_tests:
#   - apps/api/tests/test_today_horizon_integration_service.py
# END_MODULE_MAP: M-TODAY-HORIZON-INTEGRATION-SERVICE

# START_BLOCK: VERDICT_MAPPING
from __future__ import annotations

from time import monotonic
from typing import Mapping

from app.core.logging import log_block, log_event
from app.schemas.activation import ActivationLayer
from app.schemas.horizon_content_canon import HorizonSphereVerdict, PRODUCT_SPHERE_ORDER
from app.schemas.horizon_pipeline import HorizonPipelineResult
from app.schemas.natal import NatalContextData
from app.schemas.scoring_v2 import ScoringV2Result
from app.schemas.today import ConcreteAdviceBlock
from app.schemas.today_horizons import TodayV2ProductSphereKey
from app.services.horizon_pipeline_service import HorizonPipelineService


class HorizonVerdictMappingError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"HorizonVerdictMappingError:{code}")


def derive_sphere_verdicts(
    concrete_advice: ConcreteAdviceBlock,
) -> dict[TodayV2ProductSphereKey, HorizonSphereVerdict]:
    # START_FUNCTION_CONTRACT: F-M-TODAY-HORIZON-INTEGRATION-SERVICE.derive_sphere_verdicts
    # purpose: Derive the exact 12-key product-sphere verdict map from advice row key/verdict only.
    # inputs: concrete_advice - final ConcreteAdviceBlock returned by TodayInterpretationService.
    # returns: canonical-order mapping from product sphere key to verdict.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises HorizonVerdictMappingError with closed code for missing, duplicate, or unknown keys.
    # END_FUNCTION_CONTRACT: F-M-TODAY-HORIZON-INTEGRATION-SERVICE.derive_sphere_verdicts
    allowed = set(PRODUCT_SPHERE_ORDER)
    collected: dict[TodayV2ProductSphereKey, HorizonSphereVerdict] = {}
    for row in concrete_advice.rows:
        key = row.key
        if key not in allowed:
            raise HorizonVerdictMappingError("unknown_sphere")
        if key in collected:
            raise HorizonVerdictMappingError("duplicate_sphere")
        collected[key] = row.verdict
    if set(collected) != allowed:
        raise HorizonVerdictMappingError("missing_spheres")
    return {key: collected[key] for key in PRODUCT_SPHERE_ORDER}


# END_BLOCK: VERDICT_MAPPING


# START_BLOCK: SAFE_PIPELINE_LOGGING
def _payload_for_result(status: str, reason: str, result: HorizonPipelineResult | None) -> dict[str, object]:
    # START_FUNCTION_CONTRACT: F-M-TODAY-HORIZON-INTEGRATION-SERVICE._payload_for_result
    # purpose: Build the exact sanitized log payload for one pipeline outcome.
    # inputs: status - built/unavailable/failed; reason - closed reason; result - optional pipeline result.
    # returns: allowlisted log payload dict.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-TODAY-HORIZON-INTEGRATION-SERVICE._payload_for_result
    horizons = result.horizons if result is not None else None
    selected_count = 3 if status == "built" else 0
    horizon_ids = [item.horizon for item in horizons.items] if horizons is not None else []
    guidance_mode = horizons.guidance_mode if horizons is not None else None
    return {
        "status": status,
        "reason": reason,
        "selected_count": selected_count,
        "horizon_ids": horizon_ids,
        "guidance_mode": guidance_mode,
    }


def _emit_pipeline_log(*, payload: Mapping[str, object], duration_ms: float) -> None:
    # START_FUNCTION_CONTRACT: F-M-TODAY-HORIZON-INTEGRATION-SERVICE._emit_pipeline_log
    # purpose: Emit one day.payload_built event through the repository logging failure policy.
    # inputs: payload - sanitized allowlisted outcome fields; duration_ms - monotonic elapsed milliseconds.
    # returns: none.
    # side_effects: writes structured log unless logging subsystem swallows failure.
    # emitted_logs: day.payload_built
    # error_behavior: logging errors are swallowed by log_event.
    # END_FUNCTION_CONTRACT: F-M-TODAY-HORIZON-INTEGRATION-SERVICE._emit_pipeline_log
    with log_block(slice="W-DAY", module="M-TODAY-SERVICE", block="HORIZON_PIPELINE"):
        log_event(
            "day.payload_built",
            level="info" if payload["status"] != "failed" else "error",
            msg="Today horizon pipeline completed",
            payload=dict(payload),
            duration_ms=round(duration_ms, 3),
        )


# END_BLOCK: SAFE_PIPELINE_LOGGING


# START_BLOCK: TODAY_HORIZON_INTEGRATION
class TodayHorizonIntegrationService:
    def __init__(self, *, pipeline_service: HorizonPipelineService | None = None) -> None:
        self._pipeline = pipeline_service if pipeline_service is not None else HorizonPipelineService()

    def build(
        self,
        *,
        activation_layer: ActivationLayer,
        scoring_result: ScoringV2Result,
        natal_context: NatalContextData,
        concrete_advice: ConcreteAdviceBlock,
    ) -> HorizonPipelineResult:
        # START_FUNCTION_CONTRACT: F-M-TODAY-HORIZON-INTEGRATION-SERVICE.TodayHorizonIntegrationService.build
        # purpose: Derive advice verdicts, call HorizonPipelineService exactly once, log one sanitized outcome, and return it unchanged.
        # inputs: existing activation_layer, scoring_result, natal_context, and concrete_advice objects from TodayService.
        # returns: exact HorizonPipelineResult object returned by the pipeline dependency.
        # side_effects: emits one sanitized day.payload_built log event.
        # emitted_logs: day.payload_built
        # error_behavior: logs failed with closed reason then re-raises the exact exception.
        # END_FUNCTION_CONTRACT: F-M-TODAY-HORIZON-INTEGRATION-SERVICE.TodayHorizonIntegrationService.build
        try:
            sphere_verdicts = derive_sphere_verdicts(concrete_advice)
        except HorizonVerdictMappingError:
            _emit_pipeline_log(
                payload=_payload_for_result("failed", "verdict_mapping_invalid", None),
                duration_ms=0.0,
            )
            raise
        started = monotonic()
        try:
            result = self._pipeline.build(
                activation_layer=activation_layer,
                scoring_result=scoring_result,
                natal_context=natal_context,
                sphere_verdicts=sphere_verdicts,
            )
        except Exception:
            elapsed = (monotonic() - started) * 1000
            _emit_pipeline_log(payload=_payload_for_result("failed", "pipeline_error", None), duration_ms=elapsed)
            raise
        elapsed = (monotonic() - started) * 1000
        _emit_pipeline_log(
            payload=_payload_for_result(result.status, result.selection_reason, result),
            duration_ms=elapsed,
        )
        return result


# END_BLOCK: TODAY_HORIZON_INTEGRATION


__all__ = ["HorizonVerdictMappingError", "TodayHorizonIntegrationService", "derive_sphere_verdicts"]
