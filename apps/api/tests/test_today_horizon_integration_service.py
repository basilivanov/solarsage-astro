# ############################################################################
# AI_HEADER: TEST_TODAY_HORIZON_INTEGRATION_SERVICE — B3.W2 Today horizon bridge proof.
# ROLE: Proves verdict mapping, exact pipeline reuse, safe logs, and fail-closed behavior.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE
# purpose: Validate the thin TodayHorizonIntegrationService boundary over final concrete advice and the W1 pipeline.
# owns:
#   - apps/api/tests/test_today_horizon_integration_service.py
# inputs: Synthetic B2 story data, 12 typed ConcreteAdvice rows, injected pipeline/log spies.
# outputs: pytest assertions for W2 mapping, logging, purity, dependency shape, and failures.
# dependencies: ast/json/contextlib/pytest, horizon W1/B2 testkits, Today integration service.
# side_effects: source read for import/access guard only.
# emitted_logs: none.
# invariants:
#   - Real composition tests use exactly 12 typed advice rows.
#   - Verdict mapping reads only row.key and row.verdict.
#   - Logs never expose input copy, activation ids, profile strings, or exception text.
# failure_policy: pytest failure on any W2 contract regression.
# END_MODULE_CONTRACT: M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE

# START_MODULE_MAP: M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE
# public_entrypoints:
#   - pytest tests
# semantic_blocks:
#   - INTEGRATION_TEST_HELPERS: deterministic inputs, fake pipeline, log capture.
#   - REAL_PIPELINE_MAPPING: real W1 pipeline mapping and immutability checks.
#   - FAILURE_AND_LOGGING: unavailable/error logging and exact exception behavior.
#   - SOURCE_GUARDS: import and AST field-access guards.
# owned_tests:
#   - apps/api/tests/test_today_horizon_integration_service.py
# END_MODULE_MAP: M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE

# START_BLOCK: INTEGRATION_TEST_HELPERS
from __future__ import annotations

import ast
from contextlib import contextmanager
import json
from pathlib import Path
from typing import Any, Mapping

import pytest

from app.schemas.activation import ActivationLayer
from app.schemas.horizon_content_canon import HorizonSphereVerdict, PRODUCT_SPHERE_ORDER
from app.schemas.horizon_pipeline import HorizonPipelineResult
from app.schemas.natal import NatalContextData
from app.schemas.scoring_v2 import ScoringV2Result
from app.schemas.today import (
    ConcreteAdviceBlock,
    ConcreteAdviceCounts,
    ConcreteAdviceEvidence,
    ConcreteAdviceRow,
)
from app.schemas.today_horizons import TodayV2ProductSphereKey
from app.services.horizon_pipeline_service import HorizonPipelineService
from app.services.horizon_selection_service import HorizonSelectionService
from app.services.today_horizon_integration_service import (
    HorizonVerdictMappingError,
    TodayHorizonIntegrationService,
    derive_sphere_verdicts,
)

from ._horizon_content_testkit import build_communication_natal, build_relationship_natal, build_structure_natal
from ._horizon_selection_testkit import build_activation, build_layer, build_scoring, build_story


def _json_bytes(value: object) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _advice(
    *,
    order: tuple[TodayV2ProductSphereKey, ...] = PRODUCT_SPHERE_ORDER,
    verdicts: Mapping[TodayV2ProductSphereKey, HorizonSphereVerdict] | None = None,
    copy_marker: str = "",
) -> ConcreteAdviceBlock:
    verdicts = verdicts or {
        key: ("good", "neutral", "caution", "avoid")[index % 4]
        for index, key in enumerate(PRODUCT_SPHERE_ORDER)
    }
    rows = [
        ConcreteAdviceRow(
            key=key,
            label=f"Label {key}{copy_marker}",
            icon_name="circle",
            rank=index,
            verdict=verdicts[key],
            confidence="high",
            text=f"Human copy {key}{copy_marker}",
            evidence=[ConcreteAdviceEvidence(kind="day_status", title=f"Evidence {key}{copy_marker}")],
        )
        for index, key in enumerate(order, start=1)
    ]
    return ConcreteAdviceBlock(
        rows=rows,
        counts=ConcreteAdviceCounts(
            good=sum(1 for row in rows if row.verdict == "good"),
            caution=sum(1 for row in rows if row.verdict == "caution"),
            avoid=sum(1 for row in rows if row.verdict == "avoid"),
            neutral=sum(1 for row in rows if row.verdict == "neutral"),
        ),
    )


def _story(story: str, natal: NatalContextData) -> tuple[ActivationLayer, ScoringV2Result, NatalContextData]:
    activations, mapping, _, _ = build_story(story)
    return build_layer(activations), build_scoring(activations, mapping), natal


class _PipelineSpy:
    def __init__(self, result: HorizonPipelineResult | None = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls = 0
        self.kwargs: dict[str, Any] | None = None

    def build(
        self,
        *,
        activation_layer: ActivationLayer,
        scoring_result: ScoringV2Result,
        natal_context: NatalContextData,
        sphere_verdicts: Mapping[TodayV2ProductSphereKey, HorizonSphereVerdict],
    ) -> HorizonPipelineResult:
        # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.PipelineSpy.build
        # purpose: Capture exact pipeline call identity and optionally return or raise a deterministic result.
        # inputs: activation_layer, scoring_result, natal_context, sphere_verdicts from integration service.
        # returns: configured HorizonPipelineResult when no configured exception exists.
        # side_effects: increments call counter and stores call kwargs for assertions.
        # emitted_logs: none.
        # error_behavior: raises configured exception by identity.
        # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.PipelineSpy.build
        self.calls += 1
        self.kwargs = {
            "activation_layer": activation_layer,
            "scoring_result": scoring_result,
            "natal_context": natal_context,
            "sphere_verdicts": dict(sphere_verdicts),
        }
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


class _LogCapture:
    def __init__(self) -> None:
        self.blocks: list[dict[str, str]] = []
        self.events: list[tuple[str, dict[str, Any]]] = []

    @contextmanager
    def block(self, *, slice: str, module: str, block: str, operation_id: str = ""):
        # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.LogCapture.block
        # purpose: Stand in for log_block and record its public envelope fields.
        # inputs: slice, module, block, operation_id log envelope values.
        # returns: context manager yielding control to the tested code.
        # side_effects: appends one captured block envelope.
        # emitted_logs: none.
        # error_behavior: propagates body exceptions unchanged.
        # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.LogCapture.block
        self.blocks.append({"slice": slice, "module": module, "block": block, "operation_id": operation_id})
        yield

    def event(self, event: str, **kwargs: Any) -> None:
        # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.LogCapture.event
        # purpose: Stand in for log_event and record sanitized event payloads.
        # inputs: event name and log keyword payload.
        # returns: none.
        # side_effects: appends one captured event tuple.
        # emitted_logs: none.
        # error_behavior: none.
        # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.LogCapture.event
        self.events.append((event, kwargs))


def _patch_logs(monkeypatch: pytest.MonkeyPatch) -> _LogCapture:
    capture = _LogCapture()
    module = "app.services.today_horizon_integration_service"
    monkeypatch.setattr(f"{module}.log_block", capture.block)
    monkeypatch.setattr(f"{module}.log_event", capture.event)
    return capture


def _built_result() -> HorizonPipelineResult:
    layer, scoring, natal = _story("structure_boundaries_control", build_structure_natal())
    return HorizonPipelineService().build(
        activation_layer=layer,
        scoring_result=scoring,
        natal_context=natal,
        sphere_verdicts=derive_sphere_verdicts(_advice()),
    )


def _unavailable_result() -> HorizonPipelineResult:
    activations, mapping, _, _ = build_story("structure_boundaries_control")
    inputs = [activations[0], activations[2]]
    scoring = build_scoring(inputs, {key: mapping[key] for key in ("long-structure", "fast-structure")})
    return HorizonPipelineService().build(
        activation_layer=build_layer(inputs),
        scoring_result=scoring,
        natal_context=build_structure_natal(),
        sphere_verdicts=derive_sphere_verdicts(_advice()),
    )


# END_BLOCK: INTEGRATION_TEST_HELPERS


# START_BLOCK: REAL_PIPELINE_MAPPING
def test_three_accepted_b2_stories_build_real_pipeline_results() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.test_three_accepted_b2_stories_build_real_pipeline_results
    # purpose: Prove three accepted B2 stories produce built W1 horizon results through the W2 bridge.
    # inputs: deterministic structure, communication, and relationship story fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: pytest assertion failure on regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.test_three_accepted_b2_stories_build_real_pipeline_results
    cases = [
        ("structure_boundaries_control", build_structure_natal()),
        ("communication_learning_documents", build_communication_natal()),
        ("relationships_values_closeness", build_relationship_natal()),
    ]
    signatures: set[tuple[str, tuple[str, ...]]] = set()
    for story, natal in cases:
        layer, scoring, natal_context = _story(story, natal)
        advice = _advice()
        before = (_json_bytes(layer), _json_bytes(scoring), _json_bytes(natal_context), _json_bytes(advice))
        result = TodayHorizonIntegrationService().build(
            activation_layer=layer,
            scoring_result=scoring,
            natal_context=natal_context,
            concrete_advice=advice,
        )
        after = (_json_bytes(layer), _json_bytes(scoring), _json_bytes(natal_context), _json_bytes(advice))
        assert before == after
        assert result.status == "built"
        assert result.selection_reason == "selected"
        assert result.horizons is not None
        assert result.horizons.guidance_mode == "deterministic"
        assert [item.horizon for item in result.horizons.items] == ["long", "medium", "fast"]
        signatures.add((result.horizons.intro.headline, tuple(item.activation_ids[0] for item in result.horizons.items)))
    assert len(signatures) == 3


def test_row_order_and_non_mapping_fields_do_not_affect_result() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.test_row_order_and_non_mapping_fields_do_not_affect_result
    # purpose: Prove verdict derivation reads row key/verdict only and ignores row order/copy fields.
    # inputs: canonical, reversed, and noisy ConcreteAdviceBlock variants.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: pytest assertion failure on regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.test_row_order_and_non_mapping_fields_do_not_affect_result
    layer, scoring, natal = _story("structure_boundaries_control", build_structure_natal())
    canonical = _advice()
    permuted = _advice(order=tuple(reversed(PRODUCT_SPHERE_ORDER)))
    noisy = _advice(copy_marker=" RAW_COPY_SENTINEL")
    for row in noisy.rows:
        row.label = f"RAW_LABEL_SENTINEL {row.key}"
        row.icon_name = "raw-icon"
        row.confidence = "low"
        row.text = f"RAW_TEXT_SENTINEL {row.key}"
        row.evidence = [ConcreteAdviceEvidence(kind="day_status", title="RAW_EVIDENCE_SENTINEL")]

    base_mapping = derive_sphere_verdicts(canonical)
    assert derive_sphere_verdicts(permuted) == base_mapping
    assert derive_sphere_verdicts(noisy) == base_mapping

    service = TodayHorizonIntegrationService()
    base = service.build(
        activation_layer=layer,
        scoring_result=scoring,
        natal_context=natal,
        concrete_advice=canonical,
    )
    changed = service.build(
        activation_layer=layer,
        scoring_result=scoring,
        natal_context=natal,
        concrete_advice=noisy,
    )
    assert base.model_dump_json() == changed.model_dump_json()


def test_mapping_rejects_missing_duplicate_and_unknown_keys() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.test_mapping_rejects_missing_duplicate_and_unknown_keys
    # purpose: Prove verdict mapping fails closed for missing, duplicate, and unknown product sphere rows.
    # inputs: malformed ConcreteAdviceBlock variants.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: pytest assertion failure if sanitized mapping errors are not raised.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.test_mapping_rejects_missing_duplicate_and_unknown_keys
    missing = _advice(order=PRODUCT_SPHERE_ORDER[:-1])
    with pytest.raises(HorizonVerdictMappingError) as missing_error:
        derive_sphere_verdicts(missing)
    assert missing_error.value.code == "missing_spheres"
    assert str(missing_error.value) == "HorizonVerdictMappingError:missing_spheres"

    duplicate_rows = [*_advice().rows, _advice().rows[0]]
    duplicate = ConcreteAdviceBlock.model_construct(rows=duplicate_rows, counts=_advice().counts)
    with pytest.raises(HorizonVerdictMappingError) as duplicate_error:
        derive_sphere_verdicts(duplicate)
    assert duplicate_error.value.code == "duplicate_sphere"

    unknown_row = ConcreteAdviceRow.model_construct(key="unknown", verdict="neutral")
    unknown = ConcreteAdviceBlock.model_construct(rows=[unknown_row], counts=_advice().counts)
    with pytest.raises(HorizonVerdictMappingError) as unknown_error:
        derive_sphere_verdicts(unknown)
    assert unknown_error.value.code == "unknown_sphere"


# END_BLOCK: REAL_PIPELINE_MAPPING


# START_BLOCK: FAILURE_AND_LOGGING
def test_unavailable_result_preserves_reason_and_logs_once(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.test_unavailable_result_preserves_reason_and_logs_once
    # purpose: Prove unavailable pipeline results are returned unchanged and logged once with safe fields.
    # inputs: monkeypatched log capture and injected unavailable pipeline result.
    # returns: none.
    # side_effects: monkeypatches integration module logging functions for this test.
    # emitted_logs: none.
    # error_behavior: pytest assertion failure on regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.test_unavailable_result_preserves_reason_and_logs_once
    capture = _patch_logs(monkeypatch)
    unavailable = _unavailable_result()
    spy = _PipelineSpy(result=unavailable)
    layer, scoring, natal = _story("structure_boundaries_control", build_structure_natal())

    result = TodayHorizonIntegrationService(pipeline_service=spy).build(
        activation_layer=layer,
        scoring_result=scoring,
        natal_context=natal,
        concrete_advice=_advice(),
    )

    assert result is unavailable
    assert result.status == "unavailable"
    assert result.selection_reason == "missing_medium"
    assert len(capture.events) == 1
    event, kwargs = capture.events[0]
    assert event == "day.payload_built"
    assert capture.blocks == [{"slice": "W-DAY", "module": "M-TODAY-SERVICE", "block": "HORIZON_PIPELINE", "operation_id": ""}]
    assert kwargs["payload"] == {
        "status": "unavailable",
        "reason": "missing_medium",
        "selected_count": 0,
        "horizon_ids": [],
        "guidance_mode": None,
    }
    assert kwargs["level"] == "info"
    assert kwargs["msg"] == "Today horizon pipeline completed"
    assert isinstance(kwargs["duration_ms"], float)
    assert kwargs["duration_ms"] == round(kwargs["duration_ms"], 3)
    dumped_log = json.dumps(capture.events, ensure_ascii=False)
    assert "long-structure" not in dumped_log
    assert "fact-" not in dumped_log
    assert "action-" not in dumped_log


def test_built_log_is_safe_and_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.test_built_log_is_safe_and_exact
    # purpose: Prove built pipeline logging uses exactly the public sanitized allowlist.
    # inputs: monkeypatched log capture, built result spy, and copy-sentinel advice.
    # returns: none.
    # side_effects: monkeypatches integration module logging functions for this test.
    # emitted_logs: none.
    # error_behavior: pytest assertion failure on unsafe or missing log payloads.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.test_built_log_is_safe_and_exact
    capture = _patch_logs(monkeypatch)
    built = _built_result()
    spy = _PipelineSpy(result=built)
    layer, scoring, natal = _story("structure_boundaries_control", build_structure_natal())

    result = TodayHorizonIntegrationService(pipeline_service=spy).build(
        activation_layer=layer,
        scoring_result=scoring,
        natal_context=natal,
        concrete_advice=_advice(copy_marker=" RAW_COPY_SENTINEL"),
    )

    assert result is built
    assert len(capture.events) == 1
    _, kwargs = capture.events[0]
    assert kwargs["payload"] == {
        "status": "built",
        "reason": "selected",
        "selected_count": 3,
        "horizon_ids": ["long", "medium", "fast"],
        "guidance_mode": "deterministic",
    }
    assert kwargs["level"] == "info"
    assert kwargs["msg"] == "Today horizon pipeline completed"
    assert isinstance(kwargs["duration_ms"], float)
    assert kwargs["duration_ms"] == round(kwargs["duration_ms"], 3)
    dumped_log = json.dumps(capture.events, ensure_ascii=False)
    assert "long-structure" not in dumped_log
    assert "fact-" not in dumped_log
    assert "action-" not in dumped_log
    assert "RAW_COPY_SENTINEL" not in dumped_log
    assert "PROFILE_NAME_SENTINEL" not in dumped_log


def test_mapping_failure_logs_exact_event_and_skips_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.test_mapping_failure_logs_exact_event_and_skips_pipeline
    # purpose: Prove malformed advice fails before pipeline invocation and emits one exact sanitized failure event.
    # inputs: missing-sphere advice containing raw copy sentinels, log capture, and injected pipeline spy.
    # returns: none.
    # side_effects: monkeypatches integration logging functions for this test.
    # emitted_logs: none.
    # error_behavior: pytest assertion failure if mapping code, call count, or log privacy changes.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.test_mapping_failure_logs_exact_event_and_skips_pipeline
    capture = _patch_logs(monkeypatch)
    spy = _PipelineSpy(result=_built_result())
    layer, scoring, natal = _story("structure_boundaries_control", build_structure_natal())
    marker = " RAW_LABEL_TEXT_EVIDENCE_PROFILE_UNKNOWN_KEY_SENTINEL"
    malformed = _advice(order=PRODUCT_SPHERE_ORDER[:-1], copy_marker=marker)

    with pytest.raises(HorizonVerdictMappingError) as exc_info:
        TodayHorizonIntegrationService(pipeline_service=spy).build(
            activation_layer=layer,
            scoring_result=scoring,
            natal_context=natal,
            concrete_advice=malformed,
        )

    assert exc_info.value.code == "missing_spheres"
    assert spy.calls == 0
    assert capture.blocks == [
        {"slice": "W-DAY", "module": "M-TODAY-SERVICE", "block": "HORIZON_PIPELINE", "operation_id": ""}
    ]
    assert len(capture.events) == 1
    event, kwargs = capture.events[0]
    assert event == "day.payload_built"
    assert kwargs == {
        "level": "error",
        "msg": "Today horizon pipeline completed",
        "payload": {
            "status": "failed",
            "reason": "verdict_mapping_invalid",
            "selected_count": 0,
            "horizon_ids": [],
            "guidance_mode": None,
        },
        "duration_ms": 0.0,
    }
    dumped = json.dumps({"blocks": capture.blocks, "events": capture.events}, ensure_ascii=False)
    assert "RAW_LABEL_TEXT_EVIDENCE_PROFILE_UNKNOWN_KEY_SENTINEL" not in dumped
    assert "shopping" not in dumped


def test_pipeline_exception_re_raised_by_identity_and_logs_failed_once(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.test_pipeline_exception_re_raised_by_identity_and_logs_failed_once
    # purpose: Prove pipeline errors log one sanitized failure and re-raise the exact exception object.
    # inputs: monkeypatched log capture and injected pipeline exception spy.
    # returns: none.
    # side_effects: monkeypatches integration module logging functions for this test.
    # emitted_logs: none.
    # error_behavior: pytest assertion failure if exception identity or safe log contract changes.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.test_pipeline_exception_re_raised_by_identity_and_logs_failed_once
    capture = _patch_logs(monkeypatch)
    error = RuntimeError("RAW_EXCEPTION_TEXT_SENTINEL")
    spy = _PipelineSpy(error=error)
    layer, scoring, natal = _story("structure_boundaries_control", build_structure_natal())

    with pytest.raises(RuntimeError) as exc_info:
        TodayHorizonIntegrationService(pipeline_service=spy).build(
            activation_layer=layer,
            scoring_result=scoring,
            natal_context=natal,
            concrete_advice=_advice(),
        )

    assert exc_info.value is error
    assert spy.calls == 1
    assert len(capture.events) == 1
    _, kwargs = capture.events[0]
    assert kwargs["payload"] == {
        "status": "failed",
        "reason": "pipeline_error",
        "selected_count": 0,
        "horizon_ids": [],
        "guidance_mode": None,
    }
    assert kwargs["level"] == "error"
    assert kwargs["msg"] == "Today horizon pipeline completed"
    assert isinstance(kwargs["duration_ms"], float)
    assert kwargs["duration_ms"] == round(kwargs["duration_ms"], 3)
    assert "RAW_EXCEPTION_TEXT_SENTINEL" not in json.dumps(capture.events, ensure_ascii=False)


def test_pipeline_receives_exact_identities_once() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.test_pipeline_receives_exact_identities_once
    # purpose: Prove the integration bridge calls the injected pipeline exactly once with existing object identities.
    # inputs: deterministic activation/scoring/natal/advice fixtures and a pipeline spy.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: pytest assertion failure on extra calls, mutation, or identity mismatch.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.test_pipeline_receives_exact_identities_once
    built = _built_result()
    spy = _PipelineSpy(result=built)
    layer, scoring, natal = _story("structure_boundaries_control", build_structure_natal())
    advice = _advice()
    before = (_json_bytes(layer), _json_bytes(scoring), _json_bytes(natal), _json_bytes(advice))

    result = TodayHorizonIntegrationService(pipeline_service=spy).build(
        activation_layer=layer,
        scoring_result=scoring,
        natal_context=natal,
        concrete_advice=advice,
    )

    after = (_json_bytes(layer), _json_bytes(scoring), _json_bytes(natal), _json_bytes(advice))
    assert result is built
    assert spy.calls == 1
    assert spy.kwargs is not None
    assert spy.kwargs["activation_layer"] is layer
    assert spy.kwargs["scoring_result"] is scoring
    assert spy.kwargs["natal_context"] is natal
    assert list(spy.kwargs["sphere_verdicts"]) == list(PRODUCT_SPHERE_ORDER)
    assert before == after


# END_BLOCK: FAILURE_AND_LOGGING


# START_BLOCK: SOURCE_GUARDS
def test_source_import_and_mapping_access_guards() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.test_source_import_and_mapping_access_guards
    # purpose: Prove the integration source has no forbidden dependencies and maps advice via key/verdict only.
    # inputs: today_horizon_integration_service.py source text.
    # returns: none.
    # side_effects: reads source file for AST inspection.
    # emitted_logs: none.
    # error_behavior: pytest assertion failure on forbidden import or row-field access.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-HORIZON-INTEGRATION-SERVICE.test_source_import_and_mapping_access_guards
    source_path = Path(__file__).resolve().parents[1] / "app/services/today_horizon_integration_service.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    forbidden_attrs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "row":
            if node.attr not in {"key", "verdict"}:
                forbidden_attrs.add(node.attr)
    forbidden_imports = {
        "sqlalchemy",
        "fastapi",
        "app.core.config",
        "app.clients.solarsage_client",
        "app.services.natal_context_service",
        "app.services.day_scoring_runtime_service",
        "app.services.llm_service",
        "app.services.today_interpretation_service",
        "app.db.models",
    }
    assert imported & forbidden_imports == set()
    assert not any(module.startswith("sqlalchemy") or module.startswith("fastapi") for module in imported)
    assert forbidden_attrs == set()


# END_BLOCK: SOURCE_GUARDS
