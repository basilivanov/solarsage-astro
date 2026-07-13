# ############################################################################
# AI_HEADER: TEST_HORIZON_TONE_SERVICE — deterministic B2B1 machine-tone matrix.
# ROLE: Proves polarity, explicit verdict, threshold, provenance, and feature-weight behavior without human copy.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-HORIZON-TONE-SERVICE
# purpose: Test pure per-horizon tone assessment against accepted selected B2A anchors and explicit verdict maps.
# owns:
#   - apps/api/tests/test_horizon_tone_service.py
# inputs: Synthetic selected stories, verdict mappings, and test-local typed selection/canon copies.
# outputs: Assertions over tone boundary, contradiction, provenance, and determinism behavior.
# dependencies: pytest, B2B content testkit, B2A selection/tone schemas and service.
# side_effects: test-local monkeypatches only.
# emitted_logs: none.
# invariants:
#   - Russian labels never affect tone math.
#   - Missing verdicts do not become guessed neutral rows.
# failure_policy: test failures identify tone algorithm or canonical-weight regressions.
# END_MODULE_CONTRACT: M-TEST-HORIZON-TONE-SERVICE

# START_MODULE_MAP: M-TEST-HORIZON-TONE-SERVICE
# public_entrypoints:
#   - test_polarity_and_missing_verdict_boundaries
#   - test_explicit_mixed_and_material_opposition
#   - test_non_material_opposition_and_verdict_provenance
#   - test_mapping_order_unknown_input_and_label_independence
#   - test_feature_components_are_consumed_and_output_is_stable
#   - test_tone_provenance_mutations_reject
# semantic_blocks:
#   - HORIZON_TONE_DECISION_TESTS: polarity, thresholds, and opposing evidence.
#   - HORIZON_TONE_INTEGRITY_TESTS: mapping/provenance/label and feature mutation proof.
# owned_tests:
#   - apps/api/tests/test_horizon_tone_service.py
# END_MODULE_MAP: M-TEST-HORIZON-TONE-SERVICE

# START_BLOCK: HORIZON_TONE_DECISION_TESTS
from __future__ import annotations

from pathlib import Path

import app.services.horizon_tone_service as tone_module
import pytest
from pydantic import ValidationError

from app.schemas.horizon_selection import SelectedHorizonTriple
from app.schemas.horizon_tone import HorizonToneAssessment, HorizonToneResult
from app.services.horizon_content_canon_service import clear_horizon_content_canon_cache_for_tests, load_horizon_content_canons
from app.services.horizon_tone_service import HorizonToneService

from ._horizon_content_testkit import (
    build_selected_story,
    build_sphere_verdicts,
    copy_content_canon_dir,
    read_content_canon_yaml,
    write_content_canon_yaml,
)


def _selection_with(selection: SelectedHorizonTriple, index: int, **updates: object) -> SelectedHorizonTriple:
    data = selection.model_dump()
    data["items"][index].update(updates)
    return SelectedHorizonTriple.model_validate(data)


def _item(result, horizon: str):
    return next(item for item in result.items if item.horizon == horizon)


def test_polarity_and_missing_verdict_boundaries() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_polarity_and_missing_verdict_boundaries
    # purpose: Prove supportive/tense polarity crosses canonical threshold without supplied sphere verdicts.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on direct polarity score boundary regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_polarity_and_missing_verdict_boundaries
    selection, _, _ = build_selected_story("structure_boundaries_control")
    supportive = _selection_with(selection, 0, polarity="supportive")
    tense = _selection_with(selection, 0, polarity="tense")
    service = HorizonToneService()
    assert _item(service.assess(selection=supportive, sphere_verdicts={}), "long").tone == "supportive"
    assert _item(service.assess(selection=tense, sphere_verdicts={}), "long").tone == "tense"

    neutral = service.assess(selection=selection, sphere_verdicts={"work": "good"})
    assert _item(neutral, "long").tone == "neutral"


def test_explicit_mixed_and_material_opposition() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_explicit_mixed_and_material_opposition
    # purpose: Prove explicit mixed polarity and material opposing sphere evidence take precedence over net tone.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on mixed decision ordering regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_explicit_mixed_and_material_opposition
    selection, _, _ = build_selected_story("structure_boundaries_control")
    explicit = _selection_with(selection, 0, polarity="mixed")
    assert _item(HorizonToneService().assess(selection=explicit, sphere_verdicts={}), "long").tone == "mixed"

    supportive = _selection_with(selection, 0, polarity="supportive")
    opposing = _item(HorizonToneService().assess(selection=supportive, sphere_verdicts={"work": "avoid"}), "long")
    assert opposing.tone == "mixed"
    assert opposing.opposing_material_evidence is True

    tense = _selection_with(selection, 0, polarity="tense")
    opposite_good = _item(HorizonToneService().assess(selection=tense, sphere_verdicts={"work": "good"}), "long")
    assert opposite_good.tone == "mixed"
    assert opposite_good.opposing_material_evidence is True


def test_non_material_opposition_and_verdict_provenance() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_non_material_opposition_and_verdict_provenance
    # purpose: Prove below-threshold opposing components do not force mixed and only anchor spheres contribute.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on opposing threshold or provenance regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_non_material_opposition_and_verdict_provenance
    selection, _, _ = build_selected_story("structure_boundaries_control")
    data = selection.model_dump()
    data["items"][0]["polarity"] = "supportive"
    data["items"][0]["feature_scores"]["strength"] = 0.1
    data["items"][0]["feature_scores"]["contribution"] = 0.1
    data["items"][0]["feature_scores"]["convergence"] = 0.0
    data["items"][0]["impact_score"] = 0.1
    weak = SelectedHorizonTriple.model_validate(data)
    item = _item(
        HorizonToneService().assess(selection=weak, sphere_verdicts={"work": "caution", "shopping": "avoid"}), "long"
    )
    assert item.opposing_material_evidence is False
    assert item.tone == "neutral"
    assert item.sphere_keys == ("work",)


# END_BLOCK: HORIZON_TONE_DECISION_TESTS


# START_BLOCK: HORIZON_TONE_INTEGRITY_TESTS
def test_mapping_order_unknown_input_and_label_independence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_mapping_order_unknown_input_and_label_independence
    # purpose: Prove verdict mapping insertion order and Russian labels cannot affect pure tone output.
    # inputs: monkeypatch - test-local content loader replacement.
    # returns: none.
    # side_effects: monkeypatches tone module loader only.
    # emitted_logs: none.
    # error_behavior: assertion failure on input validation, mapping-order, or copy-coupling regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_mapping_order_unknown_input_and_label_independence
    selection, _, _ = build_selected_story("structure_boundaries_control")
    service = HorizonToneService()
    forward = service.assess(selection=selection, sphere_verdicts={"work": "good", "money": "caution"})
    reverse = service.assess(selection=selection, sphere_verdicts={"money": "caution", "work": "good"})
    assert forward.model_dump_json() == reverse.model_dump_json()
    with pytest.raises(ValueError, match="unknown sphere or verdict"):
        service.assess(selection=selection, sphere_verdicts={"unknown": "good"})
    with pytest.raises(ValueError, match="unknown sphere or verdict"):
        service.assess(selection=selection, sphere_verdicts={"work": "unknown"})

    directory = copy_content_canon_dir(tmp_path)
    language = read_content_canon_yaml(directory, "horizon_language.ru.v1.yml")
    language["tone_labels"] = {key: "COPY_SENTINEL" for key in language["tone_labels"]}
    write_content_canon_yaml(directory, "horizon_language.ru.v1.yml", language)
    clear_horizon_content_canon_cache_for_tests()
    changed_bundle = load_horizon_content_canons(directory)
    monkeypatch.setattr(tone_module, "load_horizon_content_canons", lambda: changed_bundle)
    assert (
        forward.model_dump_json()
        == service.assess(selection=selection, sphere_verdicts={"work": "good", "money": "caution"}).model_dump_json()
    )


def test_feature_components_are_consumed_and_output_is_stable() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_feature_components_are_consumed_and_output_is_stable
    # purpose: Mutation-prove strength/contribution/convergence influence activation confidence and output remains stable.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure if an accepted feature becomes dead configuration.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_feature_components_are_consumed_and_output_is_stable
    selection, _, _ = build_selected_story("structure_boundaries_control")
    baseline = _item(HorizonToneService().assess(selection=selection, sphere_verdicts=build_sphere_verdicts()), "long")
    data = selection.model_dump()
    data["items"][0]["feature_scores"]["strength"] = 0.0
    data["items"][0]["feature_scores"]["contribution"] = 0.0
    data["items"][0]["feature_scores"]["convergence"] = 0.0
    changed = SelectedHorizonTriple.model_validate(data)
    changed_item = _item(
        HorizonToneService().assess(selection=changed, sphere_verdicts=build_sphere_verdicts()), "long"
    )
    assert changed_item.activation_confidence < baseline.activation_confidence
    assert (
        HorizonToneService().assess(selection=selection, sphere_verdicts=build_sphere_verdicts()).model_dump_json()
        == HorizonToneService().assess(selection=selection, sphere_verdicts=build_sphere_verdicts()).model_dump_json()
    )


def _selection_for_long_score(*, polarity: str, strength: float, contribution: float, convergence: float, impact: float):
    data = build_selected_story("structure_boundaries_control")[0].model_dump()
    item = data["items"][0]
    item["polarity"] = polarity
    item["feature_scores"]["strength"] = strength
    item["feature_scores"]["contribution"] = contribution
    item["feature_scores"]["convergence"] = convergence
    item["impact_score"] = impact
    return SelectedHorizonTriple.model_validate(data)


def test_exact_tone_thresholds_and_minus_one_micro_boundaries() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_exact_tone_thresholds_and_minus_one_micro_boundaries
    # purpose: Prove supportive/tense threshold equality and one-micro boundary behavior are deterministic.
    # inputs: none.
    # returns: none.
    # side_effects: typed local selection construction only.
    # emitted_logs: none.
    # error_behavior: assertion failure on threshold comparison regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_exact_tone_thresholds_and_minus_one_micro_boundaries
    service = HorizonToneService()
    exact_supportive = _selection_for_long_score(
        polarity="supportive", strength=1.0, contribution=0.0, convergence=0.0, impact=0.2
    )
    below_supportive = _selection_for_long_score(
        polarity="supportive", strength=1.0, contribution=0.0, convergence=0.0, impact=0.199996
    )
    exact_tense = _selection_for_long_score(
        polarity="tense", strength=1.0, contribution=0.0, convergence=0.0, impact=0.2
    )
    above_tense = _selection_for_long_score(
        polarity="tense", strength=1.0, contribution=0.0, convergence=0.0, impact=0.199996
    )
    assert _item(service.assess(selection=exact_supportive, sphere_verdicts={}), "long").tone == "supportive"
    assert _item(service.assess(selection=below_supportive, sphere_verdicts={}), "long").tone == "neutral"
    assert _item(service.assess(selection=exact_tense, sphere_verdicts={}), "long").tone == "tense"
    assert _item(service.assess(selection=above_tense, sphere_verdicts={}), "long").tone == "neutral"


def test_missing_verdicts_are_omitted_from_denominator() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_missing_verdicts_are_omitted_from_denominator
    # purpose: Prove a missing anchor sphere verdict does not become an invented neutral denominator row.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on missing-verdict aggregation regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_missing_verdicts_are_omitted_from_denominator
    selection, _, _ = build_selected_story("structure_boundaries_control")
    long_item = _item(HorizonToneService().assess(selection=selection, sphere_verdicts={"work": "good"}), "long")
    assert long_item.sphere_keys == ("work",)
    assert long_item.sphere_component == 1.0


@pytest.mark.parametrize(
    ("field", "expected"),
    [("strength", 0.65), ("contribution", 0.75), ("convergence", 0.85), ("impact_score", 0.75)],
)
def test_each_tone_feature_independently_changes_confidence(field: str, expected: float) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_each_tone_feature_independently_changes_confidence
    # purpose: Mutation-prove each reviewed feature weight is live in activation confidence.
    # inputs: field - one selected feature; expected - exact confidence after zeroing it.
    # returns: none.
    # side_effects: typed local selection construction only.
    # emitted_logs: none.
    # error_behavior: assertion failure when a feature is dead configuration.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_each_tone_feature_independently_changes_confidence
    selection, _, _ = build_selected_story("structure_boundaries_control")
    data = selection.model_dump()
    item = data["items"][0]
    item["polarity"] = "neutral"
    item["feature_scores"]["strength"] = 1.0
    item["feature_scores"]["contribution"] = 1.0
    item["feature_scores"]["convergence"] = 1.0
    item["impact_score"] = 1.0
    if field == "impact_score":
        item[field] = 0.0
    else:
        item["feature_scores"][field] = 0.0
    result = _item(HorizonToneService().assess(selection=SelectedHorizonTriple.model_validate(data), sphere_verdicts={}), "long")
    assert result.activation_confidence == expected


def test_tone_schema_rejects_impossible_states() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_tone_schema_rejects_impossible_states
    # purpose: Prove frozen output models reject unrounded scores, blank provenance, duplicate anchors, and wrong order.
    # inputs: none.
    # returns: none.
    # side_effects: schema validation only.
    # emitted_logs: none.
    # error_behavior: assertion failure if an impossible output state is accepted.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_tone_schema_rejects_impossible_states
    selection, _, _ = build_selected_story("structure_boundaries_control")
    result = HorizonToneService().assess(selection=selection, sphere_verdicts=build_sphere_verdicts())
    bad_score = result.items[0].model_dump()
    bad_score["net_score"] = 0.1234567
    with pytest.raises(ValidationError):
        HorizonToneAssessment.model_validate(bad_score)
    blank_provenance = result.items[0].model_dump()
    blank_provenance["activation_ids"] = [""]
    with pytest.raises(ValidationError):
        HorizonToneAssessment.model_validate(blank_provenance)
    bad_result = result.model_dump()
    bad_result["items"][1]["horizon"] = "long"
    with pytest.raises(ValidationError):
        HorizonToneResult.model_validate(bad_result)


@pytest.mark.parametrize(
    ("case", "mutate"),
    [
        (
            "activation_component_exceeds_confidence",
            lambda data: data.update({"activation_confidence": 0.2, "activation_component": 0.3}),
        ),
        (
            "nonzero_sphere_component_without_keys",
            lambda data: data.update({"sphere_component": 1.0, "sphere_keys": []}),
        ),
        (
            "opposing_flag_same_sign_components",
            lambda data: data.update(
                {
                    "activation_confidence": 0.5,
                    "activation_component": 0.5,
                    "sphere_component": 0.5,
                    "sphere_keys": ["work"],
                    "opposing_material_evidence": True,
                    "tone": "mixed",
                }
            ),
        ),
        (
            "opposing_flag_without_mixed_tone",
            lambda data: data.update(
                {
                    "activation_confidence": 0.5,
                    "activation_component": 0.5,
                    "sphere_component": -0.5,
                    "sphere_keys": ["work"],
                    "opposing_material_evidence": True,
                    "tone": "supportive",
                }
            ),
        ),
        ("activation_id_over_160", lambda data: data.__setitem__("activation_ids", ["x" * 161])),
    ],
)
def test_tone_provenance_mutations_reject(case: str, mutate) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_tone_provenance_mutations_reject
    # purpose: Prove impossible activation/sphere/opposition provenance combinations fail independently.
    # inputs: case - descriptive provenance mutation; mutate - one output payload mutation.
    # returns: none.
    # side_effects: schema payload mutation only.
    # emitted_logs: none.
    # error_behavior: assertion failure if impossible tone provenance is accepted.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TONE-SERVICE.test_tone_provenance_mutations_reject
    selection, _, _ = build_selected_story("structure_boundaries_control")
    item = _item(HorizonToneService().assess(selection=selection, sphere_verdicts=build_sphere_verdicts()), "long")
    payload = item.model_dump()
    mutate(payload)
    with pytest.raises(ValidationError):
        HorizonToneAssessment.model_validate(payload)


# END_BLOCK: HORIZON_TONE_INTEGRITY_TESTS
