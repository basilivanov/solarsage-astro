# ############################################################################
# AI_HEADER: TEST_HORIZON_SELECTION_SERVICE — coherent B2A selector result behavior.
# ROLE: Proves goldens, honest fallbacks, selected-anchor completeness, and strict internal result contracts.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-HORIZON-SELECTION-SERVICE
# purpose: Test public-result-oriented B2A selection behavior using deterministic synthetic testkit inputs.
# owns:
#   - apps/api/tests/test_horizon_selection_service.py
# inputs: Synthetic activations and scoring results from _horizon_selection_testkit.
# outputs: Assertions over deterministic selected results, fallback reasons, privacy, and typed strict schemas.
# dependencies: pytest/pydantic, B2A testkit, horizon selection schemas and service.
# side_effects: test-local monkeypatches only.
# emitted_logs: none.
# invariants:
#   - No raw evidence/debug/PII reaches selected internal result serialization.
#   - Selector returns honest null reasons rather than a forced incoherent triple.
# failure_policy: test failures identify B2A result-contract regressions.
# END_MODULE_CONTRACT: M-TEST-HORIZON-SELECTION-SERVICE

# START_MODULE_MAP: M-TEST-HORIZON-SELECTION-SERVICE
# public_entrypoints:
#   - test_selection_goldens_are_coherent_and_byte_deterministic
#   - test_coherence_beats_raw_strength_and_honesty_fallbacks
#   - test_unknown_technique_source_speed_low_impact_and_bounds_diagnostics
#   - test_selected_anchor_preserves_candidate_data_for_b2b
#   - test_selection_exclusions_and_exact_honesty_fallbacks
#   - test_internal_models_fail_closed_and_hide_input
# semantic_blocks:
#   - CORE_SELECTION_RESULT_TESTS: goldens, honest fallbacks, exclusions, and anchor completeness.
#   - CORE_SELECTION_SCHEMA_TESTS: strict internal model and privacy assertions.
# owned_tests:
#   - apps/api/tests/test_horizon_selection_service.py
# END_MODULE_MAP: M-TEST-HORIZON-SELECTION-SERVICE

# START_BLOCK: CORE_SELECTION_RESULT_TESTS
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.horizon_selection import (
    HorizonCandidate,
    HorizonSelectionDiagnostics,
    HorizonSelectionResult,
    HorizonSphereMapping,
    HorizonTimingAssessment,
    SelectedHorizonAnchor,
    SelectedHorizonTriple,
)
from app.services.horizon_selection_service import HorizonSelectionService

from ._horizon_selection_testkit import build_activation, build_layer, build_scoring, build_story


@pytest.mark.parametrize(
    ("story", "expected_theme"),
    [
        ("structure_boundaries_control", "structure_boundaries_control"),
        ("communication_learning_documents", "communication_learning_documents"),
        ("relationships_values_closeness", "relationships_values_closeness"),
    ],
)
def test_selection_goldens_are_coherent_and_byte_deterministic(
    story: str,
    expected_theme: str,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-SERVICE.test_selection_goldens_are_coherent_and_byte_deterministic
    # purpose: Prove three coherent story themes win deterministically over stronger unrelated alternatives.
    # inputs: story - synthetic golden id; expected_theme - expected stable theme key.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on golden, determinism, or privacy regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-SERVICE.test_selection_goldens_are_coherent_and_byte_deterministic
    activations, mapping, expected_ids, _ = build_story(story)
    service = HorizonSelectionService()
    result = service.select(
        activation_layer=build_layer(activations),
        scoring_result=build_scoring(activations, mapping),
    )
    again = service.select(
        activation_layer=build_layer(activations),
        scoring_result=build_scoring(activations, mapping),
    )
    assert result.reason == "selected"
    assert result.selection is not None
    assert tuple(item.activation_id for item in result.selection.items) == expected_ids
    assert expected_theme in result.selection.shared_theme_keys
    assert result.model_dump_json() == again.model_dump_json()
    dumped = result.model_dump_json()
    assert all(value not in dumped for value in ("evidence", "debug", "Moscow", "Alice"))


def test_coherence_beats_raw_strength_and_honesty_fallbacks() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-SERVICE.test_coherence_beats_raw_strength_and_honesty_fallbacks
    # purpose: Prove coherent controls win and exact missing/no-coherent fallback reasons remain honest.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure if selector forces a weak unrelated triple.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-SERVICE.test_coherence_beats_raw_strength_and_honesty_fallbacks
    activations, mapping, expected_ids, _ = build_story("structure_boundaries_control")
    service = HorizonSelectionService()
    result = service.select(
        activation_layer=build_layer(activations),
        scoring_result=build_scoring(activations, mapping),
    )
    assert result.selection is not None
    assert tuple(item.activation_id for item in result.selection.items) == expected_ids

    missing_medium = service.select(
        activation_layer=build_layer([activations[0], activations[2]]),
        scoring_result=build_scoring(
            [activations[0], activations[2]],
            {key: value for key, value in mapping.items() if key in {activations[0].id, activations[2].id}},
        ),
    )
    assert missing_medium.reason == "missing_medium"

    unrelated = [
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
    no_triple = service.select(
        activation_layer=build_layer(unrelated),
        scoring_result=build_scoring(
            unrelated,
            {
                activations[0].id: mapping[activations[0].id],
                "medium-unrelated": ("meaning_expansion_vector", 3.0),
                "fast-unrelated": ("relationships_partnership", 3.0),
            },
        ),
    )
    assert no_triple.reason == "no_coherent_triple"


def test_unknown_technique_source_speed_low_impact_and_bounds_diagnostics() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-SERVICE.test_unknown_technique_source_speed_low_impact_and_bounds_diagnostics
    # purpose: Prove prebound count/diagnostic invariants under a large mixed-quality activation population.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on B2A bounds or diagnostics accounting regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-SERVICE.test_unknown_technique_source_speed_low_impact_and_bounds_diagnostics
    base = build_activation(id="long-base")
    bulk = [
        build_activation(
            id=f"bulk-{index:03d}",
            technique="transit_to_natal",
            technique_family="transit",
            source_planet="MOON",
            target_key="PLUTO",
            target_planet="PLUTO",
            strength=0.7 + index / 1000.0,
            active_from="2026-07-12T00:00:00Z",
            exact_at="2026-07-12T12:00:00Z",
            active_until="2026-07-12T23:00:00Z",
        )
        for index in range(259)
    ]
    activations = [
        base,
        *bulk,
        build_activation(
            id="unknown-technique",
            technique="made_up",
            technique_family="x",
            source_planet=None,
            target_planet="SATURN",
        ),
        build_activation(
            id="unknown-speed",
            technique="transit_to_natal",
            technique_family="transit",
            source_planet="CERES",
            target_key="SATURN",
            target_planet="SATURN",
            active_from="2026-03-01T00:00:00Z",
            exact_at="2026-07-12T12:00:00Z",
            active_until="2026-09-30T00:00:00Z",
        ),
        build_activation(
            id="low-impact",
            technique="transit_to_natal",
            technique_family="transit",
            source_planet="MOON",
            target_key="SATURN",
            target_planet="SATURN",
            strength=0.0,
            active_from="2026-07-12T00:00:00Z",
            exact_at="2026-07-12T12:00:00Z",
            active_until="2026-07-12T23:00:00Z",
        ),
    ]
    mapping = {
        activation.id: ("work_status_achievement", 2.0)
        if activation.id == "long-base"
        else ("crisis_transformation_control", 1.0)
        for activation in activations
    }
    mapping["low-impact"] = ("body_energy_health", 0.01)
    result = HorizonSelectionService().select(
        activation_layer=build_layer(activations),
        scoring_result=build_scoring(activations, mapping),
    )
    assert result.diagnostics.active_count == len(activations)
    assert result.diagnostics.classified_count == 256
    assert result.diagnostics.input_truncated is True
    assert result.diagnostics.combinations_evaluated <= 1728
    assert result.diagnostics.candidate_count == sum(result.diagnostics.per_horizon_pre_bound_counts.values())
    assert all(
        result.diagnostics.per_horizon_post_bound_counts[horizon]
        <= result.diagnostics.per_horizon_pre_bound_counts[horizon]
        and result.diagnostics.per_horizon_post_bound_counts[horizon] <= 12
        for horizon in ("long", "medium", "fast")
    )


def test_selected_anchor_preserves_candidate_data_for_b2b(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-SERVICE.test_selected_anchor_preserves_candidate_data_for_b2b
    # purpose: Prove anchors copy selected candidate timing/features/convergence without human payloads.
    # inputs: monkeypatch - test-local anchor conversion wrapper.
    # returns: none.
    # side_effects: records candidates passed into anchor conversion.
    # emitted_logs: none.
    # error_behavior: assertion failure when B2B-required internal data is lost or altered.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-SERVICE.test_selected_anchor_preserves_candidate_data_for_b2b
    activations, mapping, _, _ = build_story("structure_boundaries_control")
    service = HorizonSelectionService()
    captured: dict[tuple[str, str], HorizonCandidate] = {}
    original = service._to_anchor

    def capture(candidate: HorizonCandidate) -> SelectedHorizonAnchor:
        # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-SERVICE.test_selected_anchor_preserves_candidate_data_for_b2b.capture
        # purpose: Capture candidate facts passed to the production selected-anchor conversion.
        # inputs: candidate - selected candidate.
        # returns: original selected anchor.
        # side_effects: updates test-local capture mapping.
        # emitted_logs: none.
        # error_behavior: delegates production conversion behavior.
        # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-SERVICE.test_selected_anchor_preserves_candidate_data_for_b2b.capture
        captured[(candidate.activation_id, candidate.horizon)] = candidate
        return original(candidate)

    monkeypatch.setattr(service, "_to_anchor", capture)
    result = service.select(
        activation_layer=build_layer(activations),
        scoring_result=build_scoring(activations, mapping),
    )
    assert result.reason == "selected"
    assert result.selection is not None
    for anchor in result.selection.items:
        candidate = captured[(anchor.activation_id, anchor.horizon)]
        assert anchor.timing.model_dump_json() == candidate.timing.model_dump_json()
        assert anchor.feature_scores == candidate.feature_scores
        assert anchor.target_family_convergence_count == candidate.target_family_convergence_count
        assert anchor.impact_score == candidate.impact_score
        assert anchor.timing.active_from is not None
        assert anchor.timing.active_until is not None
        assert anchor.timing.duration_days is not None
    dumped = result.model_dump_json()
    assert all(value not in dumped for value in ("evidence", "debug", "Moscow", "Alice"))


def test_selection_exclusions_and_exact_honesty_fallbacks() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-SERVICE.test_selection_exclusions_and_exact_honesty_fallbacks
    # purpose: Prove isolated exclusions are counted at their stage and null fallback reasons are exact.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on exclusion accounting or fallback-reason regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-SERVICE.test_selection_exclusions_and_exact_honesty_fallbacks
    service = HorizonSelectionService()
    activations, mapping, _, _ = build_story("structure_boundaries_control")
    cases = [
        (
            build_activation(
                id="unknown-technique", technique="made_up", technique_family="unknown", target_planet="SATURN"
            ),
            {"unknown-technique": ("work_status_achievement", 1.0)},
            "unknown_technique",
        ),
        (
            build_activation(
                id="unknown-speed",
                technique="transit_to_natal",
                technique_family="transit",
                source_planet="CERES",
                target_planet="SATURN",
                active_from="2026-03-01T00:00:00Z",
                exact_at="2026-07-12T12:00:00Z",
                active_until="2026-09-30T00:00:00Z",
            ),
            {"unknown-speed": ("work_status_achievement", 1.0)},
            "unknown_source_speed",
        ),
        (
            build_activation(
                id="no-product", technique="annual_profection", technique_family="profection", target_planet="SATURN"
            ),
            {},
            "no_product_sphere",
        ),
        (
            build_activation(
                id="low-impact",
                technique="annual_profection",
                technique_family="profection",
                strength=0.0,
                target_planet="SATURN",
            ),
            {"low-impact": ("body_energy_health", 0.0)},
            "below_impact_threshold",
        ),
    ]
    for activation, case_mapping, reason in cases:
        result = service.select(
            activation_layer=build_layer([activation]),
            scoring_result=build_scoring([activation], case_mapping),
        )
        assert result.diagnostics.excluded_counts_by_reason == {reason: 1}
        assert result.diagnostics.candidate_count == 0
        assert result.reason == "missing_long"

    assert (
        service.select(
            activation_layer=build_layer(activations, target_time="99:00"),
            scoring_result=build_scoring(activations, mapping),
        ).reason
        == "invalid_target_clock"
    )
    assert (
        service.select(
            activation_layer=build_layer([activations[2]]),
            scoring_result=build_scoring([activations[2]], {"fast-structure": mapping["fast-structure"]}),
        ).reason
        == "missing_long"
    )
    assert (
        service.select(
            activation_layer=build_layer([activations[0], activations[2]]),
            scoring_result=build_scoring(
                [activations[0], activations[2]], {key: mapping[key] for key in ("long-structure", "fast-structure")}
            ),
        ).reason
        == "missing_medium"
    )
    assert (
        service.select(
            activation_layer=build_layer(activations[:2]),
            scoring_result=build_scoring(
                activations[:2], {key: mapping[key] for key in ("long-structure", "medium-structure")}
            ),
        ).reason
        == "missing_fast"
    )

    duplicate_slow = build_activation(
        id="one-slow",
        technique="transit_to_natal",
        technique_family="transit",
        source_planet="PLUTO",
        target_key="SATURN",
        target_planet="SATURN",
        active_from="2026-01-14T00:00:00Z",
        exact_at="2026-07-12T12:00:00Z",
        active_until="2026-07-13T00:00:00Z",
    )
    distinct_fast = build_activation(
        id="distinct-fast",
        technique="transit_to_natal",
        technique_family="transit",
        source_planet="MOON",
        target_key="SATURN",
        target_planet="SATURN",
        active_from="2026-07-12T00:00:00Z",
        exact_at="2026-07-12T12:00:00Z",
        active_until="2026-07-12T23:00:00Z",
    )
    duplicate_result = service.select(
        activation_layer=build_layer([duplicate_slow, distinct_fast]),
        scoring_result=build_scoring(
            [duplicate_slow, distinct_fast],
            {"one-slow": ("work_status_achievement", 2.0), "distinct-fast": ("work_status_achievement", 2.0)},
        ),
    )
    assert duplicate_result.reason == "no_coherent_triple"
    assert duplicate_result.diagnostics.combinations_evaluated == 1


# END_BLOCK: CORE_SELECTION_RESULT_TESTS


# START_BLOCK: CORE_SELECTION_SCHEMA_TESTS
def test_internal_models_fail_closed_and_hide_input() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-SERVICE.test_internal_models_fail_closed_and_hide_input
    # purpose: Prove impossible timing/mapping/candidate/triple/diagnostic/result states are unconstructable and private.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure if strict internal model or privacy validation regresses.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-SERVICE.test_internal_models_fail_closed_and_hide_input
    activations, mapping, _, _ = build_story("structure_boundaries_control")
    result = HorizonSelectionService().select(
        activation_layer=build_layer(activations),
        scoring_result=build_scoring(activations, mapping),
    )
    assert result.selection is not None
    anchor = result.selection.items[0]
    timing_data = anchor.timing.model_dump()
    with pytest.raises(ValidationError) as timing_error:
        HorizonTimingAssessment.model_validate(
            {**timing_data, "duration_seconds": None, "target_local": "SECRET_INTERNAL_MARKER"}
        )
    assert "SECRET_INTERNAL_MARKER" not in str(timing_error.value)
    with pytest.raises(ValidationError):
        HorizonTimingAssessment.model_validate({**timing_data, "eligible_horizons": ["medium", "long"]})
    with pytest.raises(ValidationError):
        HorizonTimingAssessment.model_validate({**timing_data, "preferred_horizons": ["medium"]})
    with pytest.raises(ValidationError):
        HorizonTimingAssessment.model_validate({**timing_data, "active_from": None})
    with pytest.raises(ValidationError):
        HorizonSphereMapping.model_validate({"linked_abs_amount": 1.0})
    candidate_data = anchor.model_dump()
    with pytest.raises(ValidationError):
        HorizonCandidate.model_validate({**candidate_data, "activation_id": "other"})
    with pytest.raises(ValidationError):
        HorizonCandidate.model_validate({**candidate_data, "impact_score": 0.1234567})
    with pytest.raises(ValidationError):
        SelectedHorizonAnchor.model_validate({**anchor.model_dump(), "theme_keys": ["duplicate", "duplicate"]})
    triple_data = result.selection.model_dump()
    with pytest.raises(ValidationError):
        SelectedHorizonTriple.model_validate({**triple_data, "items": list(reversed(triple_data["items"]))})
    with pytest.raises(ValidationError):
        SelectedHorizonTriple.model_validate({**triple_data, "pair_overlap_scores": {"long_medium": 0.2}})
    with pytest.raises(ValidationError):
        SelectedHorizonTriple.model_validate({**triple_data, "total_score": 0.1234567})
    with pytest.raises(ValidationError):
        SelectedHorizonTriple.model_validate({**triple_data, "unique_family_count": 1})
    diagnostics_data = result.diagnostics.model_dump()
    with pytest.raises(ValidationError):
        HorizonSelectionDiagnostics.model_validate({**diagnostics_data, "candidate_count": 999})
    with pytest.raises(ValidationError):
        HorizonSelectionDiagnostics.model_validate({**diagnostics_data, "combinations_evaluated": 1729})
    with pytest.raises(ValidationError):
        HorizonSelectionResult.model_validate({**result.model_dump(), "warnings": ["not_typed"]})


# END_BLOCK: CORE_SELECTION_SCHEMA_TESTS
