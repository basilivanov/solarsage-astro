# ############################################################################
# AI_HEADER: TEST_HORIZON_SELECTION_ORDERING — deterministic B2A ordering and bounded-work proofs.
# ROLE: Proves pair and triple ordering, helper execution, inactive exclusion, and exact prebound diagnostics.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-HORIZON-SELECTION-ORDERING
# purpose: Test deterministic B2A ordering and bounded preselection behavior with synthetic testkit inputs.
# owns:
#   - apps/api/tests/test_horizon_selection_ordering.py
# inputs: Shared synthetic builders, selection canon, typed candidates, and the B2A selection service.
# outputs: Assertions over rounded overlap, tie-breaks, helper use, prebound priority, and diagnostics.
# dependencies: pytest, B2A testkit, horizon selection canon/schemas/service.
# side_effects: test-local monkeypatches only.
# emitted_logs: none.
# invariants:
#   - Pair scores round before threshold consumers compare them.
#   - Candidate/triple ties use the documented total ordering and stable lexical fallback.
#   - Exactly 256 active inputs are classified after canonical prebound ordering.
# failure_policy: test failures identify ordering, bounded-work, or mutation-adequacy regressions.
# END_MODULE_CONTRACT: M-TEST-HORIZON-SELECTION-ORDERING

# START_MODULE_MAP: M-TEST-HORIZON-SELECTION-ORDERING
# public_entrypoints:
#   - test_pair_overlap_rounds_before_threshold_comparison
#   - test_pair_overlap_component_matrix
#   - test_family_diversity_bonus_and_threshold_gate
#   - test_candidate_stable_tie_break_levels
#   - test_triple_stable_tie_break_levels_and_service_lex_winner
#   - test_production_triple_helpers_are_used
#   - test_inactive_evidence_is_ignored_and_deterministic
#   - test_input_prebound_exact_survivors_and_determinism
#   - test_exact_diagnostics_and_combinations
# semantic_blocks:
#   - PAIR_AND_SCORE_ORDERING_TESTS: rounded overlap components and pure stable ordering keys.
#   - SERVICE_ORDERING_AND_BOUND_TESTS: production helper use, inactive evidence, prebound, and diagnostics.
# owned_tests:
#   - apps/api/tests/test_horizon_selection_ordering.py
# END_MODULE_MAP: M-TEST-HORIZON-SELECTION-ORDERING

# START_BLOCK: PAIR_AND_SCORE_ORDERING_TESTS
from __future__ import annotations

import app.services.horizon_selection_service as selection_module
import pytest

from app.schemas.activation import ActivationEvidence
from app.schemas.horizon_canon import HorizonSelectionCanon
from app.schemas.horizon_selection import HorizonCandidate
from app.services.horizon_canon_service import load_horizon_selection_canon
from app.services.horizon_selection_service import (
    HorizonSelectionService,
    _family_diversity_score,
    _triple_sort_key,
    _triple_total_score,
)

from ._horizon_selection_testkit import (
    build_activation,
    build_candidate_from_anchor,
    build_control_selection,
    build_equal_score_triple_population,
    build_layer,
    build_scoring,
    build_story,
)


def test_pair_overlap_rounds_before_threshold_comparison(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-ORDERING.test_pair_overlap_rounds_before_threshold_comparison
    # purpose: Prove floating component accumulation is rounded before canonical threshold consumers compare it.
    # inputs: monkeypatch - test-local replacement for the production canon loader.
    # returns: none.
    # side_effects: replaces the production canon loader for this test only.
    # emitted_logs: none.
    # error_behavior: assertion failure on pair-score rounding regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-ORDERING.test_pair_overlap_rounds_before_threshold_comparison
    canon_data = load_horizon_selection_canon().model_dump()
    canon_data["story_overlap_weights"] = {
        "same_target": 0.1000004,
        "shared_theme": 0.8999996,
        "shared_product_sphere": 0.0,
        "same_planet_or_house": 0.0,
        "shared_technical_sphere": 0.0,
    }
    canon_data["min_pair_overlap"]["long_medium"] = 0.1000003
    custom_canon = HorizonSelectionCanon.model_validate(canon_data)
    monkeypatch.setattr(selection_module, "load_horizon_selection_canon", lambda: custom_canon)

    anchor = build_control_selection().items[0]
    left = build_candidate_from_anchor(anchor)
    right = build_candidate_from_anchor(
        anchor,
        activation_id="rounded-right",
        updates={
            "target_key_normalized": left.target_key_normalized,
            "source_planet_normalized": "MARS",
            "target_planet_normalized": "VENUS",
            "technical_spheres": ["other_technical"],
            "product_spheres": ["money"],
            "theme_keys": ["other_theme"],
        },
    )

    pair_score = HorizonSelectionService()._pair_overlap(left, right)

    assert pair_score == 0.1
    assert pair_score < custom_canon.min_pair_overlap.long_medium


def test_pair_overlap_component_matrix() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-ORDERING.test_pair_overlap_component_matrix
    # purpose: Prove every canon pair-overlap component contributes exactly once and clamps at one.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on overlap component weighting regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-ORDERING.test_pair_overlap_component_matrix
    anchor = build_control_selection().items[0]
    left = build_candidate_from_anchor(anchor)
    service = HorizonSelectionService()
    weights = load_horizon_selection_canon().story_overlap_weights

    def _right(
        activation_id: str,
        **updates: object,
    ) -> HorizonCandidate:
        return build_candidate_from_anchor(
            anchor,
            activation_id=activation_id,
            updates={
                "target_key_normalized": "MARS",
                "source_planet_normalized": "VENUS",
                "target_planet_normalized": "VENUS",
                "technical_spheres": ["other_technical"],
                "product_spheres": ["money"],
                "theme_keys": ["other_theme"],
                **updates,
            },
        )

    component_cases = [
        (
            "same-target",
            {"target_key_normalized": left.target_key_normalized},
            weights.same_target,
        ),
        (
            "shared-theme",
            {"theme_keys": [left.theme_keys[0]]},
            weights.shared_theme,
        ),
        (
            "shared-product",
            {"product_spheres": [left.product_spheres[0]]},
            weights.shared_product_sphere,
        ),
        (
            "same-planet",
            {"source_planet_normalized": left.target_planet_normalized},
            weights.same_planet_or_house,
        ),
        (
            "shared-technical",
            {"technical_spheres": [left.technical_spheres[0]]},
            weights.shared_technical_sphere,
        ),
    ]
    for activation_id, updates, expected_score in component_cases:
        assert service._pair_overlap(left, _right(activation_id, **updates)) == expected_score

    all_component_updates = left.model_dump(exclude={"activation_id", "timing"})
    assert service._pair_overlap(left, _right("all-components", **all_component_updates)) == 1.0


def test_family_diversity_bonus_and_threshold_gate() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-ORDERING.test_family_diversity_bonus_and_threshold_gate
    # purpose: Prove family diversity has its canonical score bonus but cannot bypass coherence thresholds.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on family-score or pair-threshold ordering regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-ORDERING.test_family_diversity_bonus_and_threshold_gate
    assert _family_diversity_score(1) == 0.0
    assert _family_diversity_score(2) == 0.5
    assert _family_diversity_score(3) == 1.0
    assert (
        _triple_total_score(
            mean_impact=0.5,
            mean_overlap=0.5,
            family_diversity_score=0.0,
        )
        == 0.475
    )
    assert (
        _triple_total_score(
            mean_impact=0.5,
            mean_overlap=0.5,
            family_diversity_score=0.5,
        )
        == 0.5
    )
    assert (
        _triple_total_score(
            mean_impact=0.5,
            mean_overlap=0.5,
            family_diversity_score=1.0,
        )
        == 0.525
    )

    activations = [
        build_activation(id="long-isolated", target_key="SATURN", target_planet="SATURN"),
        build_activation(
            id="medium-isolated",
            technique="lunar_return",
            technique_family="lunar_return",
            target_key="MERCURY",
            target_planet="MERCURY",
            active_from="2026-07-01T00:00:00Z",
            exact_at="2026-07-12T12:00:00Z",
            active_until="2026-07-20T00:00:00Z",
        ),
        build_activation(
            id="fast-isolated",
            technique="transit_to_natal",
            technique_family="transit",
            source_planet="MOON",
            target_key="MARS",
            target_planet="MARS",
            active_from="2026-07-12T00:00:00Z",
            exact_at="2026-07-12T12:00:00Z",
            active_until="2026-07-12T23:00:00Z",
        ),
    ]
    result = HorizonSelectionService().select(
        activation_layer=build_layer(activations),
        scoring_result=build_scoring(
            activations,
            {
                "long-isolated": ("work_status_achievement", 2.0),
                "medium-isolated": ("thinking_speech_learning", 2.0),
                "fast-isolated": ("body_energy_health", 2.0),
            },
        ),
    )

    assert result.reason == "no_coherent_triple"
    assert result.diagnostics.combinations_evaluated == 1


def test_candidate_stable_tie_break_levels() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-ORDERING.test_candidate_stable_tie_break_levels
    # purpose: Prove candidate ordering follows impact, timing completeness, strength, priority, then id.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on candidate tie-break precedence regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-ORDERING.test_candidate_stable_tie_break_levels
    anchor = build_control_selection().items[0]

    def _candidate(
        activation_id: str,
        *,
        impact: float = 0.7,
        timing_completeness: float = 0.9,
        strength: float = 0.8,
        technique_priority: float = 0.8,
    ) -> HorizonCandidate:
        feature_scores = anchor.feature_scores.model_dump()
        feature_scores.update(
            {
                "timing_completeness": timing_completeness,
                "strength": strength,
                "technique_priority": technique_priority,
            }
        )
        return build_candidate_from_anchor(
            anchor,
            activation_id=activation_id,
            updates={
                "feature_scores": feature_scores,
                "impact_score": impact,
            },
        )

    assert _candidate("impact", impact=0.8).tie_break_key() < _candidate("timing").tie_break_key()
    assert _candidate("timing", timing_completeness=1.0).tie_break_key() < _candidate("strength").tie_break_key()
    assert _candidate("strength", strength=0.9).tie_break_key() < _candidate("priority").tie_break_key()
    assert _candidate("priority", technique_priority=0.9).tie_break_key() < _candidate("z-id").tie_break_key()
    assert _candidate("a-id").tie_break_key() < _candidate("z-id").tie_break_key()


def test_triple_stable_tie_break_levels_and_service_lex_winner() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-ORDERING.test_triple_stable_tie_break_levels_and_service_lex_winner
    # purpose: Prove triple ordering follows total, overlap, impact, families, then ids and reaches lexical winner in service.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on triple tie-break or lexical deterministic-selection regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-ORDERING.test_triple_stable_tie_break_levels_and_service_lex_winner
    def _key(
        *,
        total_score: float = 0.7,
        mean_overlap: float = 0.6,
        mean_impact: float = 0.5,
        unique_family_count: int = 2,
        activation_ids: tuple[str, str, str] = ("long-z", "medium-z", "fast-z"),
    ) -> tuple[float, float, float, int, tuple[str, str, str]]:
        return _triple_sort_key(
            total_score=total_score,
            mean_overlap=mean_overlap,
            mean_impact=mean_impact,
            unique_family_count=unique_family_count,
            activation_ids=activation_ids,
        )

    assert _key(total_score=0.8) < _key()
    assert _key(mean_overlap=0.7) < _key()
    assert _key(mean_impact=0.6) < _key()
    assert _key(unique_family_count=3) < _key()
    assert _key(activation_ids=("long-a", "medium-a", "fast-a")) < _key()

    activations, mapping = build_equal_score_triple_population()
    service = HorizonSelectionService()
    result = service.select(
        activation_layer=build_layer(activations),
        scoring_result=build_scoring(activations, mapping),
    )
    again = service.select(
        activation_layer=build_layer(list(reversed(activations))),
        scoring_result=build_scoring(list(reversed(activations)), mapping),
    )

    assert result.selection is not None
    assert tuple(item.activation_id for item in result.selection.items) == (
        "long-a",
        "medium-a",
        "fast-a",
    )
    assert result.model_dump_json() == again.model_dump_json()


# END_BLOCK: PAIR_AND_SCORE_ORDERING_TESTS


# START_BLOCK: SERVICE_ORDERING_AND_BOUND_TESTS
def test_production_triple_helpers_are_used(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-ORDERING.test_production_triple_helpers_are_used
    # purpose: Mutation-proof that production selection invokes family, total-score, and triple-sort helpers.
    # inputs: monkeypatch - test-local wrappers for production pure helper functions.
    # returns: none.
    # side_effects: replaces module-global helpers for the duration of this test.
    # emitted_logs: none.
    # error_behavior: assertion failure if selection inlines or bypasses a required ordering helper.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-ORDERING.test_production_triple_helpers_are_used
    family_calls: list[int] = []
    total_calls: list[tuple[float, float, float]] = []
    sort_calls: list[tuple[float, float, float, int, tuple[str, str, str]]] = []
    original_family = selection_module._family_diversity_score
    original_total = selection_module._triple_total_score
    original_sort = selection_module._triple_sort_key

    def _family_spy(unique_family_count: int) -> float:
        family_calls.append(unique_family_count)
        return original_family(unique_family_count)

    def _total_spy(
        *,
        mean_impact: float,
        mean_overlap: float,
        family_diversity_score: float,
    ) -> float:
        total_calls.append((mean_impact, mean_overlap, family_diversity_score))
        return original_total(
            mean_impact=mean_impact,
            mean_overlap=mean_overlap,
            family_diversity_score=family_diversity_score,
        )

    def _sort_spy(
        *,
        total_score: float,
        mean_overlap: float,
        mean_impact: float,
        unique_family_count: int,
        activation_ids: tuple[str, str, str],
    ) -> tuple[float, float, float, int, tuple[str, str, str]]:
        sort_calls.append(
            (
                total_score,
                mean_overlap,
                mean_impact,
                unique_family_count,
                activation_ids,
            )
        )
        return original_sort(
            total_score=total_score,
            mean_overlap=mean_overlap,
            mean_impact=mean_impact,
            unique_family_count=unique_family_count,
            activation_ids=activation_ids,
        )

    monkeypatch.setattr(selection_module, "_family_diversity_score", _family_spy)
    monkeypatch.setattr(selection_module, "_triple_total_score", _total_spy)
    monkeypatch.setattr(selection_module, "_triple_sort_key", _sort_spy)
    activations, mapping, _, _ = build_story("structure_boundaries_control")
    result = HorizonSelectionService().select(
        activation_layer=build_layer(activations),
        scoring_result=build_scoring(activations, mapping),
    )

    assert result.reason == "selected"
    assert family_calls
    assert total_calls
    assert sort_calls


def test_inactive_evidence_is_ignored_and_deterministic() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-ORDERING.test_inactive_evidence_is_ignored_and_deterministic
    # purpose: Prove inactive high-strength evidence cannot affect selection and input order stays deterministic.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure if inactive evidence is classified or input order leaks into output.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-ORDERING.test_inactive_evidence_is_ignored_and_deterministic
    activations, mapping, expected_ids, _ = build_story("structure_boundaries_control")
    inactive = build_activation(
        id="inactive-high-strength",
        technique="transit_to_natal",
        technique_family="transit",
        source_planet="MOON",
        target_key="JUPITER",
        target_planet="JUPITER",
        active=False,
        strength=1.0,
        active_from="2026-06-01T00:00:00Z",
        exact_at="2026-06-15T12:00:00Z",
        active_until="2026-07-01T00:00:00Z",
    )
    service = HorizonSelectionService()
    result = service.select(
        activation_layer=build_layer([inactive, *activations]),
        scoring_result=build_scoring([inactive, *activations], mapping),
    )
    again = service.select(
        activation_layer=build_layer([*reversed(activations), inactive]),
        scoring_result=build_scoring([*reversed(activations), inactive], mapping),
    )

    assert result.selection is not None
    assert tuple(item.activation_id for item in result.selection.items) == expected_ids
    assert result.diagnostics.input_count == len(activations) + 1
    assert result.diagnostics.active_count == len(activations)
    assert result.diagnostics.classified_count == len(activations)
    assert result.model_dump_json() == again.model_dump_json()


def test_input_prebound_exact_survivors_and_determinism(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-ORDERING.test_input_prebound_exact_survivors_and_determinism
    # purpose: Prove prebound retains exactly 256 active inputs using priority before lexical id fallback.
    # inputs: monkeypatch - test-local timing classifier capture wrapper.
    # returns: none.
    # side_effects: captures the actual production prebound classification order.
    # emitted_logs: none.
    # error_behavior: assertion failure if canonical priority or exact prebound limit regresses.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-ORDERING.test_input_prebound_exact_survivors_and_determinism
    stronger = [
        build_activation(
            id=f"strong-unknown-{index:03d}",
            technique="made_up",
            technique_family="unknown",
            strength=0.9,
        )
        for index in range(255)
    ]
    boundary = [
        build_activation(
            id="z-annual",
            technique="annual_profection",
            technique_family="profection",
            strength=0.5,
        ),
        build_activation(
            id="a-firdar",
            technique="firdar_major",
            technique_family="firdar",
            strength=0.5,
        ),
        build_activation(
            id="b-solar",
            technique="solar_return",
            technique_family="solar_return",
            strength=0.5,
        ),
        build_activation(
            id="a-monthly",
            technique="monthly_profection",
            technique_family="profection",
            strength=0.5,
        ),
    ]
    activations = [*stronger, *boundary]
    canonical = load_horizon_selection_canon()

    def _select_with_capture(
        ordered_activations: list[ActivationEvidence],
    ) -> tuple[object, list[str]]:
        service = HorizonSelectionService()
        original_classify = service._timing.classify
        classified_ids: list[str] = []

        def _classify_spy(
            evidence: ActivationEvidence,
            *,
            target_date: str,
            target_time: str,
            target_tz: str,
        ) -> object:
            classified_ids.append(evidence.id)
            return original_classify(
                evidence,
                target_date=target_date,
                target_time=target_time,
                target_tz=target_tz,
            )

        monkeypatch.setattr(service._timing, "classify", _classify_spy)
        result = service.select(
            activation_layer=build_layer(ordered_activations),
            scoring_result=build_scoring(ordered_activations, {}),
        )
        return result, classified_ids

    result, classified_ids = _select_with_capture(activations)
    reversed_result, reversed_classified_ids = _select_with_capture(list(reversed(activations)))

    assert min(boundary, key=lambda evidence: (-evidence.strength, evidence.id)).id == "a-firdar"
    assert (
        sorted(
            boundary,
            key=lambda evidence: (
                -evidence.strength,
                -max(canonical.technique_rules[evidence.technique].priority_by_horizon.values()),
                evidence.id,
            ),
        )[0].id
        == "z-annual"
    )
    assert len(classified_ids) == 256
    assert classified_ids[-1] == "z-annual"
    assert set(classified_ids) == {item.id for item in stronger} | {"z-annual"}
    assert classified_ids == reversed_classified_ids
    assert result.model_dump_json() == reversed_result.model_dump_json()
    assert result.diagnostics.active_count == 259
    assert result.diagnostics.classified_count == 256
    assert result.diagnostics.input_truncated is True


def test_exact_diagnostics_and_combinations() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-ORDERING.test_exact_diagnostics_and_combinations
    # purpose: Prove exact per-horizon counts and all eight bounded equal-score triple combinations are reported.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on diagnostics accounting or bounded combinations regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-ORDERING.test_exact_diagnostics_and_combinations
    activations, mapping = build_equal_score_triple_population()
    result = HorizonSelectionService().select(
        activation_layer=build_layer(activations),
        scoring_result=build_scoring(activations, mapping),
    )

    assert result.reason == "selected"
    assert result.diagnostics.model_dump() == {
        "input_count": 6,
        "active_count": 6,
        "classified_count": 6,
        "candidate_count": 6,
        "per_horizon_pre_bound_counts": {"long": 2, "medium": 2, "fast": 2},
        "per_horizon_post_bound_counts": {"long": 2, "medium": 2, "fast": 2},
        "excluded_counts_by_reason": {},
        "combinations_evaluated": 8,
        "input_truncated": False,
    }


# END_BLOCK: SERVICE_ORDERING_AND_BOUND_TESTS
