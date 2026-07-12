# ############################################################################
# AI_HEADER: TEST_HORIZON_PIPELINE_SERVICE — B3.W1 pure orchestrator proof.
# ROLE: Proves HorizonPipelineService composition, honesty, fail-closed, order, and purity contracts.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-HORIZON-PIPELINE-SERVICE
# purpose: Validate the pure HorizonPipelineService boundary over accepted B2A/B2B services and synthetic real-shaped data.
# owns:
#   - apps/api/tests/test_horizon_pipeline_service.py
# inputs: B2 testkits, injected dependency spies, and strict internal pipeline schemas.
# outputs: Assertions over built/unavailable results, fail-closed errors, call order, immutability, and import shape.
# dependencies: json/pathlib/pytest/pydantic, horizon pipeline service, existing B2 schemas/services/testkits.
# side_effects: repository source read for import-shape guard only.
# emitted_logs: none.
# invariants:
#   - No prebuilt horizons block is supplied to real-composition tests.
#   - Selected downstream failures propagate and never return unavailable.
#   - Inputs remain byte-equivalent before and after building.
# failure_policy: test failure on any orchestration, validation, privacy, or dependency-shape regression.
# END_MODULE_CONTRACT: M-TEST-HORIZON-PIPELINE-SERVICE

# START_MODULE_MAP: M-TEST-HORIZON-PIPELINE-SERVICE
# public_entrypoints:
#   - test_real_composition_three_stories_distinct_and_deterministic
#   - test_unavailable_preserves_reason_and_skips_downstream
#   - test_downstream_boundaries_fail_closed
#   - test_call_order_once_and_validator_uses_input_evidence
#   - test_result_schema_invariants_and_hidden_inputs
#   - test_dependency_shape_has_no_external_runtime_imports
# semantic_blocks:
#   - PIPELINE_TEST_HELPERS: deterministic input and spy helpers.
#   - PIPELINE_REAL_COMPOSITION: real B2 service composition checks.
#   - PIPELINE_FAILURE_AND_ORDER: unavailable, fail-closed, and call-order checks.
#   - PIPELINE_SCHEMA_AND_IMPORT_GUARDS: strict model and forbidden import checks.
# owned_tests:
#   - apps/api/tests/test_horizon_pipeline_service.py
# END_MODULE_MAP: M-TEST-HORIZON-PIPELINE-SERVICE

# START_BLOCK: PIPELINE_TEST_HELPERS
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Mapping, Sequence

import pytest
from pydantic import ValidationError

from app.schemas.activation import ActivationEvidence, ActivationLayer
from app.schemas.horizon_content_canon import HorizonSphereVerdict
from app.schemas.horizon_guidance import HorizonGuidanceContext
from app.schemas.horizon_pipeline import HorizonPipelineResult
from app.schemas.horizon_selection import HorizonSelectionResult
from app.schemas.horizon_tone import HorizonToneResult
from app.schemas.natal import NatalContextData
from app.schemas.personal_fact_pack import PersonalFactPack
from app.schemas.scoring_v2 import ScoringV2Result
from app.schemas.today_horizons import TodayV2HorizonsBlock, TodayV2ProductSphereKey
from app.services.horizon_guidance_service import HorizonGuidanceService
from app.services.horizon_pipeline_service import HorizonPipelineService
from app.services.horizon_selection_service import HorizonSelectionService
from app.services.horizon_tone_service import HorizonToneService
from app.services.personal_fact_pack_service import PersonalFactPackService

from ._horizon_content_testkit import (
    build_communication_natal,
    build_relationship_natal,
    build_selected_story,
    build_sphere_verdicts,
    build_structure_natal,
)
from ._horizon_selection_testkit import build_activation, build_layer, build_scoring, build_story


def _json_bytes(value: object) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _story_inputs(story: str, natal: NatalContextData):
    activations, mapping, _, _ = build_story(story)
    layer = build_layer(activations)
    scoring = build_scoring(activations, mapping)
    selection = HorizonSelectionService().select(activation_layer=layer, scoring_result=scoring)
    assert selection.selection is not None
    verdicts = _verdicts_for_selection(selection, build_sphere_verdicts())
    return layer, scoring, natal, verdicts, selection


def _verdicts_for_selection(
    selection: HorizonSelectionResult,
    base: Mapping[TodayV2ProductSphereKey, HorizonSphereVerdict],
) -> dict[TodayV2ProductSphereKey, HorizonSphereVerdict]:
    assert selection.selection is not None
    selected_spheres = {sphere for anchor in selection.selection.items for sphere in anchor.product_spheres}
    return {sphere: base.get(sphere, "neutral") for sphere in sorted(selected_spheres)}


def _complete_fixture() -> tuple[
    ActivationLayer,
    ScoringV2Result,
    NatalContextData,
    dict[TodayV2ProductSphereKey, HorizonSphereVerdict],
    HorizonSelectionResult,
    PersonalFactPack,
    HorizonToneResult,
    TodayV2HorizonsBlock,
]:
    layer, scoring, natal, verdicts, selection_result = _story_inputs(
        "structure_boundaries_control", build_structure_natal()
    )
    assert selection_result.selection is not None
    fact_pack = PersonalFactPackService().build(
        selection=selection_result.selection,
        activation_layer=layer,
        scoring_result=scoring,
        natal_context=natal,
    )
    tone = HorizonToneService().assess(selection=selection_result.selection, sphere_verdicts=verdicts)
    context = HorizonGuidanceContext(
        schema_version="horizon-guidance-context.v1",
        selection=selection_result.selection,
        fact_pack=fact_pack,
        tone_result=tone,
        sphere_verdicts=verdicts,
    )
    block = HorizonGuidanceService().build(context=context)
    return layer, scoring, natal, verdicts, selection_result, fact_pack, tone, block


class _CountingDependency:
    def __init__(self, name: str, calls: list[str]) -> None:
        self.name = name
        self.calls = calls
        self.count = 0

    def _record(self) -> None:
        self.count += 1
        self.calls.append(self.name)


class _SelectionSpy(_CountingDependency):
    def __init__(self, calls: list[str], result: HorizonSelectionResult) -> None:
        super().__init__("selection", calls)
        self.result = result
        self.layer: ActivationLayer | None = None
        self.scoring: ScoringV2Result | None = None

    def select(self, *, activation_layer: ActivationLayer, scoring_result: ScoringV2Result) -> HorizonSelectionResult:
        # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE._SelectionSpy.select
        # purpose: Record the selection dependency invocation and return the configured result.
        # inputs: activation_layer and scoring_result from the orchestrator.
        # returns: HorizonSelectionResult.
        # side_effects: records call count, order, and exact input object references.
        # emitted_logs: none.
        # error_behavior: none.
        # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE._SelectionSpy.select
        self._record()
        self.layer = activation_layer
        self.scoring = scoring_result
        return self.result


class _FactSpy(_CountingDependency):
    def __init__(self, calls: list[str], fact_pack: PersonalFactPack | None = None, error: Exception | None = None) -> None:
        super().__init__("fact", calls)
        self.fact_pack = fact_pack
        self.error = error

    def build(
        self,
        *,
        selection,
        activation_layer: ActivationLayer,
        scoring_result: ScoringV2Result,
        natal_context: NatalContextData,
    ) -> PersonalFactPack:
        # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE._FactSpy.build
        # purpose: Record fact-pack invocation and optionally raise an exact injected error.
        # inputs: selection, activation_layer, scoring_result, natal_context.
        # returns: configured PersonalFactPack.
        # side_effects: records call count and order.
        # emitted_logs: none.
        # error_behavior: raises configured exception unchanged.
        # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE._FactSpy.build
        self._record()
        if self.error is not None:
            raise self.error
        assert self.fact_pack is not None
        return self.fact_pack


class _ToneSpy(_CountingDependency):
    def __init__(self, calls: list[str], tone: HorizonToneResult | None = None, error: Exception | None = None) -> None:
        super().__init__("tone", calls)
        self.tone = tone
        self.error = error

    def assess(
        self,
        *,
        selection,
        sphere_verdicts: Mapping[TodayV2ProductSphereKey, HorizonSphereVerdict],
    ) -> HorizonToneResult:
        # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE._ToneSpy.assess
        # purpose: Record tone invocation and optionally raise an exact injected error.
        # inputs: selection and sphere_verdicts.
        # returns: configured HorizonToneResult.
        # side_effects: records call count and order.
        # emitted_logs: none.
        # error_behavior: raises configured exception unchanged.
        # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE._ToneSpy.assess
        self._record()
        if self.error is not None:
            raise self.error
        assert self.tone is not None
        return self.tone


class _GuidanceSpy(_CountingDependency):
    def __init__(self, calls: list[str], block: TodayV2HorizonsBlock | None = None, error: Exception | None = None) -> None:
        super().__init__("guidance", calls)
        self.block = block
        self.error = error
        self.context: HorizonGuidanceContext | None = None

    def build(self, *, context: HorizonGuidanceContext) -> TodayV2HorizonsBlock:
        # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE._GuidanceSpy.build
        # purpose: Record guidance invocation and optionally raise an exact injected error.
        # inputs: context built by the orchestrator.
        # returns: configured TodayV2HorizonsBlock.
        # side_effects: records call count, order, and context reference.
        # emitted_logs: none.
        # error_behavior: raises configured exception unchanged.
        # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE._GuidanceSpy.build
        self._record()
        self.context = context
        if self.error is not None:
            raise self.error
        assert self.block is not None
        return self.block


class _ValidatorSpy(_CountingDependency):
    def __init__(self, calls: list[str], error: Exception | None = None) -> None:
        super().__init__("validator", calls)
        self.error = error
        self.activation_evidence: Sequence[ActivationEvidence] | None = None
        self.context: HorizonGuidanceContext | None = None
        self.block: TodayV2HorizonsBlock | None = None

    def validate(
        self,
        *,
        block: TodayV2HorizonsBlock,
        context: HorizonGuidanceContext,
        activation_evidence: Sequence[ActivationEvidence],
    ) -> TodayV2HorizonsBlock:
        # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE._ValidatorSpy.validate
        # purpose: Record validator invocation and optionally raise an exact injected error.
        # inputs: block, context, activation_evidence.
        # returns: the input block when no error is configured.
        # side_effects: records call count, order, and exact input references.
        # emitted_logs: none.
        # error_behavior: raises configured exception unchanged.
        # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE._ValidatorSpy.validate
        self._record()
        self.block = block
        self.context = context
        self.activation_evidence = activation_evidence
        if self.error is not None:
            raise self.error
        return block


# END_BLOCK: PIPELINE_TEST_HELPERS


# START_BLOCK: PIPELINE_REAL_COMPOSITION
def test_real_composition_three_stories_distinct_and_deterministic() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE.test_real_composition_three_stories_distinct_and_deterministic
    # purpose: Run three distinct accepted stories through the real orchestrator and prove complete deterministic blocks.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: pytest assertion failure on pipeline regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE.test_real_composition_three_stories_distinct_and_deterministic
    cases = [
        ("structure_boundaries_control", build_structure_natal()),
        ("communication_learning_documents", build_communication_natal()),
        ("relationships_values_closeness", build_relationship_natal()),
    ]
    signatures: set[tuple[str, str, tuple[str, ...]]] = set()
    for story, natal in cases:
        layer, scoring, natal_context, verdicts, _ = _story_inputs(story, natal)
        before = (_json_bytes(layer), _json_bytes(scoring), _json_bytes(natal_context), _json_bytes(verdicts))
        first = HorizonPipelineService().build(
            activation_layer=layer,
            scoring_result=scoring,
            natal_context=natal_context,
            sphere_verdicts=verdicts,
        )
        second = HorizonPipelineService().build(
            activation_layer=layer,
            scoring_result=scoring,
            natal_context=natal_context,
            sphere_verdicts=verdicts,
        )
        after = (_json_bytes(layer), _json_bytes(scoring), _json_bytes(natal_context), _json_bytes(verdicts))
        assert before == after
        assert first.status == "built"
        assert first.selection_reason == "selected"
        assert first.horizons is not None
        assert [item.horizon for item in first.horizons.items] == ["long", "medium", "fast"]
        assert first.horizons.guidance_mode == "deterministic"
        assert first.horizons.model_dump_json() == second.horizons.model_dump_json()
        activation_ids = tuple(item.activation_ids[0] for item in first.horizons.items)
        assert set(activation_ids) <= {activation.id for activation in layer.activations}
        signatures.add((first.horizons.intro.headline, first.horizons.intro.body, activation_ids))
    assert len(signatures) == 3


# END_BLOCK: PIPELINE_REAL_COMPOSITION


# START_BLOCK: PIPELINE_FAILURE_AND_ORDER
@pytest.mark.parametrize("expected_reason", ["missing_medium", "no_coherent_triple"])
def test_unavailable_preserves_reason_and_skips_downstream(expected_reason: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE.test_unavailable_preserves_reason_and_skips_downstream
    # purpose: Prove honest no-triple results preserve the selector reason and skip all downstream services.
    # inputs: expected_reason - unavailable selector reason to exercise.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: pytest assertion failure on unavailable contract regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE.test_unavailable_preserves_reason_and_skips_downstream
    activations, mapping, _, _ = build_story("structure_boundaries_control")
    if expected_reason == "missing_medium":
        inputs = [activations[0], activations[2]]
        scoring_map = {key: mapping[key] for key in ("long-structure", "fast-structure")}
    else:
        inputs = [
            activations[0],
            build_activation(
                id="medium-unrelated",
                technique="transit_to_natal",
                technique_family="transit",
                source_planet="PLUTO",
                target_key="JUPITER",
                target_planet="JUPITER",
                strength=0.9,
                active_from="2026-03-01T00:00:00Z",
                exact_at="2026-07-12T12:00:00Z",
                active_until="2026-09-30T00:00:00Z",
            ),
            build_activation(
                id="fast-unrelated",
                technique="transit_to_natal",
                technique_family="transit",
                source_planet="MOON",
                target_key="VENUS",
                target_planet="VENUS",
                strength=0.9,
                active_from="2026-07-12T00:00:00Z",
                exact_at="2026-07-12T12:00:00Z",
                active_until="2026-07-12T23:00:00Z",
            ),
        ]
        scoring_map = {
            activations[0].id: mapping[activations[0].id],
            "medium-unrelated": ("meaning_expansion_vector", 3.0),
            "fast-unrelated": ("relationships_partnership", 3.0),
        }
    layer = build_layer(inputs)
    scoring = build_scoring(inputs, scoring_map)
    calls: list[str] = []
    result = HorizonPipelineService(
        fact_pack_service=_FactSpy(calls),
        tone_service=_ToneSpy(calls),
        guidance_service=_GuidanceSpy(calls),
        claim_validator=_ValidatorSpy(calls),
    ).build(
        activation_layer=layer,
        scoring_result=scoring,
        natal_context=build_structure_natal(),
        sphere_verdicts={},
    )
    assert result.status == "unavailable"
    assert result.horizons is None
    assert result.selection_reason == expected_reason
    assert calls == []


@pytest.mark.parametrize("boundary", ["fact", "tone", "guidance", "validator"])
def test_downstream_boundaries_fail_closed(boundary: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE.test_downstream_boundaries_fail_closed
    # purpose: Prove selected-pipeline failures propagate unchanged instead of becoming unavailable.
    # inputs: boundary - downstream dependency name to force-fail.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: pytest assertion failure if an exception is swallowed or leaks raw sentinels.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE.test_downstream_boundaries_fail_closed
    layer, scoring, natal, verdicts, selection, fact_pack, tone, block = _complete_fixture()
    calls: list[str] = []
    errors = {
        "fact": RuntimeError("fact_boundary_failed"),
        "tone": RuntimeError("tone_boundary_failed"),
        "guidance": RuntimeError("guidance_boundary_failed"),
        "validator": RuntimeError("validator_boundary_failed"),
    }
    service = HorizonPipelineService(
        selection_service=_SelectionSpy(calls, selection),
        fact_pack_service=_FactSpy(calls, fact_pack, errors["fact"] if boundary == "fact" else None),
        tone_service=_ToneSpy(calls, tone, errors["tone"] if boundary == "tone" else None),
        guidance_service=_GuidanceSpy(calls, block, errors["guidance"] if boundary == "guidance" else None),
        claim_validator=_ValidatorSpy(calls, errors["validator"] if boundary == "validator" else None),
    )
    with pytest.raises(RuntimeError) as exc:
        service.build(
            activation_layer=layer,
            scoring_result=scoring,
            natal_context=natal,
            sphere_verdicts=verdicts,
        )
    assert exc.value is errors[boundary]
    assert "RAW_EVIDENCE_SENTINEL" not in str(exc.value)
    assert "PROFILE_NAME_SENTINEL" not in str(exc.value)


def test_call_order_once_and_validator_uses_input_evidence() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE.test_call_order_once_and_validator_uses_input_evidence
    # purpose: Assert exact successful dependency order/count and validator evidence identity.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: pytest assertion failure on dependency orchestration regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE.test_call_order_once_and_validator_uses_input_evidence
    layer, scoring, natal, verdicts, selection, fact_pack, tone, block = _complete_fixture()
    calls: list[str] = []
    selection_spy = _SelectionSpy(calls, selection)
    fact_spy = _FactSpy(calls, fact_pack)
    tone_spy = _ToneSpy(calls, tone)
    guidance_spy = _GuidanceSpy(calls, block)
    validator_spy = _ValidatorSpy(calls)
    result = HorizonPipelineService(
        selection_service=selection_spy,
        fact_pack_service=fact_spy,
        tone_service=tone_spy,
        guidance_service=guidance_spy,
        claim_validator=validator_spy,
    ).build(
        activation_layer=layer,
        scoring_result=scoring,
        natal_context=natal,
        sphere_verdicts=verdicts,
    )
    assert result.status == "built"
    assert calls == ["selection", "fact", "tone", "guidance", "validator"]
    assert [selection_spy.count, fact_spy.count, tone_spy.count, guidance_spy.count, validator_spy.count] == [1, 1, 1, 1, 1]
    assert selection_spy.layer is layer
    assert selection_spy.scoring is scoring
    assert validator_spy.activation_evidence is layer.activations
    assert list(validator_spy.activation_evidence or []) == layer.activations
    assert guidance_spy.context is validator_spy.context
    assert validator_spy.block is block


# END_BLOCK: PIPELINE_FAILURE_AND_ORDER


# START_BLOCK: PIPELINE_SCHEMA_AND_IMPORT_GUARDS
def test_result_schema_invariants_and_hidden_inputs() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE.test_result_schema_invariants_and_hidden_inputs
    # purpose: Prove strict internal result invariants and hidden input errors.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: pytest assertion failure on strict schema regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE.test_result_schema_invariants_and_hidden_inputs
    _, _, _, _, selection, _, _, block = _complete_fixture()
    with pytest.raises(ValidationError) as built_error:
        HorizonPipelineResult(
            status="built",
            horizons=None,
            selection_reason="selected",
            selection_diagnostics=selection.diagnostics,
        )
    assert "SECRET_NATAL_FACT_BODY" not in str(built_error.value)
    with pytest.raises(ValidationError):
        HorizonPipelineResult(
            status="unavailable",
            horizons=block,
            selection_reason="missing_fast",
            selection_diagnostics=selection.diagnostics,
        )
    with pytest.raises(ValidationError):
        HorizonPipelineResult(
            status="unavailable",
            horizons=None,
            selection_reason="selected",
            selection_diagnostics=selection.diagnostics,
            debug_payload="SECRET_NATAL_FACT_BODY",
        )


def test_dependency_shape_has_no_external_runtime_imports() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE.test_dependency_shape_has_no_external_runtime_imports
    # purpose: Prove the orchestrator source has no forbidden runtime dependency imports or clocks.
    # inputs: none.
    # returns: none.
    # side_effects: reads one source file.
    # emitted_logs: none.
    # error_behavior: pytest assertion failure on forbidden dependency shape.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-PIPELINE-SERVICE.test_dependency_shape_has_no_external_runtime_imports
    source = Path("apps/api/app/services/horizon_pipeline_service.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden_imports = [
        "sqlalchemy",
        "random",
        "requests",
        "httpx",
        "fastapi",
        "app.core.config",
        "app.services.natal_context_service",
        "app.services.day_scoring_runtime_service",
        "app.services.llm_service",
        "app.services.today_service",
        "app.services.semantic_v2_service",
    ]
    assert sorted(module for module in imported if module in forbidden_imports or module.startswith("solarsage")) == []
    assert "datetime.now(" not in source
    assert "time.time(" not in source


# END_BLOCK: PIPELINE_SCHEMA_AND_IMPORT_GUARDS
