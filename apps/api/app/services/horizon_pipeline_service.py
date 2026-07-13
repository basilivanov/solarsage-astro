# ############################################################################
# AI_HEADER: HORIZON_PIPELINE_SERVICE — pure B3.W1 horizon orchestration boundary.
# ROLE: Composes accepted B2 services into one validated optional horizons result without I/O.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-PIPELINE-SERVICE
# purpose: Orchestrate selection, personal facts, tone, deterministic guidance, and claim validation.
# owns:
#   - apps/api/app/services/horizon_pipeline_service.py
# inputs: Existing ActivationLayer, ScoringV2Result, NatalContextData, and explicit product-sphere verdicts.
# outputs: HorizonPipelineResult containing either validated TodayV2HorizonsBlock or honest unavailable diagnostics.
# dependencies: typing, existing B1/B2 schemas and deterministic horizon services.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - No DB, settings, HTTP, sidecar, natal service, scoring runtime, LLM, clock, random, or network dependency.
#   - Downstream consistency failures after a selected triple propagate; they are never converted to unavailable.
#   - Dependencies are called exactly once in the documented order for successful selected results.
# failure_policy: ordinary no-selection returns unavailable; selected-pipeline errors propagate from typed dependencies.
# END_MODULE_CONTRACT: M-HORIZON-PIPELINE-SERVICE

# START_MODULE_MAP: M-HORIZON-PIPELINE-SERVICE
# public_entrypoints:
#   - HorizonPipelineService.build
# semantic_blocks:
#   - HORIZON_PIPELINE_DEPENDENCY_PROTOCOLS: minimal pure dependency shapes.
#   - HORIZON_PIPELINE_SERVICE: deterministic orchestration boundary.
# owned_tests:
#   - apps/api/tests/test_horizon_pipeline_service.py
#   - apps/api/tests/test_horizon_coverage.py
#   - apps/api/tests/test_horizon_pipeline_benchmark.py
# END_MODULE_MAP: M-HORIZON-PIPELINE-SERVICE

# START_BLOCK: HORIZON_PIPELINE_DEPENDENCY_PROTOCOLS
from __future__ import annotations

from typing import Mapping, Protocol, Sequence

from app.schemas.activation import ActivationEvidence, ActivationLayer
from app.schemas.horizon_content_canon import HorizonSphereVerdict
from app.schemas.horizon_guidance import HorizonGuidanceContext
from app.schemas.horizon_pipeline import HorizonPipelineResult
from app.schemas.horizon_selection import HorizonSelectionResult, SelectedHorizonTriple
from app.schemas.horizon_tone import HorizonToneResult
from app.schemas.natal import NatalContextData
from app.schemas.personal_fact_pack import PersonalFactPack
from app.schemas.scoring_v2 import ScoringV2Result
from app.schemas.today_horizons import TodayV2HorizonsBlock, TodayV2ProductSphereKey
from app.services.horizon_claim_validator import HorizonClaimValidator
from app.services.horizon_guidance_service import HorizonGuidanceService
from app.services.horizon_selection_service import HorizonSelectionService
from app.services.horizon_tone_service import HorizonToneService
from app.services.personal_fact_pack_service import PersonalFactPackService


class _SelectionDependency(Protocol):
    def select(
        self,
        *,
        activation_layer: ActivationLayer,
        scoring_result: ScoringV2Result,
    ) -> HorizonSelectionResult:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-PIPELINE-SERVICE._SelectionDependency.select
        # purpose: Describe the selection dependency call shape used by the orchestrator.
        # inputs: activation_layer and scoring_result.
        # returns: HorizonSelectionResult.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: dependency-defined exceptions propagate.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-PIPELINE-SERVICE._SelectionDependency.select
        ...


class _FactPackDependency(Protocol):
    def build(
        self,
        *,
        selection: SelectedHorizonTriple,
        activation_layer: ActivationLayer,
        scoring_result: ScoringV2Result,
        natal_context: NatalContextData,
    ) -> PersonalFactPack:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-PIPELINE-SERVICE._FactPackDependency.build
        # purpose: Describe the personal fact-pack dependency call shape used after selection.
        # inputs: selection, activation_layer, scoring_result, natal_context.
        # returns: PersonalFactPack.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: dependency-defined exceptions propagate.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-PIPELINE-SERVICE._FactPackDependency.build
        ...


class _ToneDependency(Protocol):
    def assess(
        self,
        *,
        selection: SelectedHorizonTriple,
        sphere_verdicts: Mapping[TodayV2ProductSphereKey, HorizonSphereVerdict],
    ) -> HorizonToneResult:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-PIPELINE-SERVICE._ToneDependency.assess
        # purpose: Describe the tone dependency call shape used after fact-pack construction.
        # inputs: selection and explicit sphere_verdicts mapping.
        # returns: HorizonToneResult.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: dependency-defined exceptions propagate.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-PIPELINE-SERVICE._ToneDependency.assess
        ...


class _GuidanceDependency(Protocol):
    def build(self, *, context: HorizonGuidanceContext) -> TodayV2HorizonsBlock:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-PIPELINE-SERVICE._GuidanceDependency.build
        # purpose: Describe the deterministic guidance dependency call shape.
        # inputs: context - complete HorizonGuidanceContext.
        # returns: TodayV2HorizonsBlock.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: dependency-defined exceptions propagate.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-PIPELINE-SERVICE._GuidanceDependency.build
        ...


class _ClaimValidatorDependency(Protocol):
    def validate(
        self,
        *,
        block: TodayV2HorizonsBlock,
        context: HorizonGuidanceContext,
        activation_evidence: Sequence[ActivationEvidence],
    ) -> TodayV2HorizonsBlock:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-PIPELINE-SERVICE._ClaimValidatorDependency.validate
        # purpose: Describe the claim validator dependency call shape used as the final boundary.
        # inputs: block, context, activation_evidence.
        # returns: validated TodayV2HorizonsBlock.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: dependency-defined exceptions propagate.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-PIPELINE-SERVICE._ClaimValidatorDependency.validate
        ...


# END_BLOCK: HORIZON_PIPELINE_DEPENDENCY_PROTOCOLS


# START_BLOCK: HORIZON_PIPELINE_SERVICE
class HorizonPipelineService:
    def __init__(
        self,
        *,
        selection_service: _SelectionDependency | None = None,
        fact_pack_service: _FactPackDependency | None = None,
        tone_service: _ToneDependency | None = None,
        guidance_service: _GuidanceDependency | None = None,
        claim_validator: _ClaimValidatorDependency | None = None,
    ) -> None:
        self._selection = selection_service or HorizonSelectionService()
        self._fact_pack = fact_pack_service or PersonalFactPackService()
        self._tone = tone_service or HorizonToneService()
        self._guidance = guidance_service or HorizonGuidanceService()
        self._validator = claim_validator or HorizonClaimValidator()

    def build(
        self,
        *,
        activation_layer: ActivationLayer,
        scoring_result: ScoringV2Result,
        natal_context: NatalContextData,
        sphere_verdicts: Mapping[TodayV2ProductSphereKey, HorizonSphereVerdict],
    ) -> HorizonPipelineResult:
        # START_FUNCTION_CONTRACT: F-M-HORIZON-PIPELINE-SERVICE.HorizonPipelineService.build
        # purpose: Execute the accepted pure B2 horizon pipeline and return an atomic internal result.
        # inputs: activation_layer, scoring_result, natal_context, sphere_verdicts from the caller's existing request state.
        # returns: HorizonPipelineResult with validated horizons or honest unavailable diagnostics.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: no-selection returns unavailable; any selected downstream failure propagates unchanged.
        # END_FUNCTION_CONTRACT: F-M-HORIZON-PIPELINE-SERVICE.HorizonPipelineService.build
        selection_result = self._selection.select(
            activation_layer=activation_layer,
            scoring_result=scoring_result,
        )
        if selection_result.selection is None:
            return HorizonPipelineResult(
                status="unavailable",
                horizons=None,
                selection_reason=selection_result.reason,
                selection_diagnostics=selection_result.diagnostics,
            )

        selection = selection_result.selection
        fact_pack = self._fact_pack.build(
            selection=selection,
            activation_layer=activation_layer,
            scoring_result=scoring_result,
            natal_context=natal_context,
        )
        tone_result = self._tone.assess(
            selection=selection,
            sphere_verdicts=sphere_verdicts,
        )
        context = HorizonGuidanceContext(
            schema_version="horizon-guidance-context.v1",
            selection=selection,
            fact_pack=fact_pack,
            tone_result=tone_result,
            sphere_verdicts=dict(sphere_verdicts),
        )
        block = self._guidance.build(context=context)
        validated = self._validator.validate(
            block=block,
            context=context,
            activation_evidence=activation_layer.activations,
        )
        return HorizonPipelineResult(
            status="built",
            horizons=validated,
            selection_reason=selection_result.reason,
            selection_diagnostics=selection_result.diagnostics,
        )


# END_BLOCK: HORIZON_PIPELINE_SERVICE


__all__ = ["HorizonPipelineService"]
