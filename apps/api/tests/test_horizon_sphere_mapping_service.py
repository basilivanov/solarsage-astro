# ############################################################################
# AI_HEADER: TEST_HORIZON_SPHERE_MAPPING_SERVICE — B2A scoring identity and sphere mapping coverage.
# ROLE: Proves ordered activation-only mapping, canon reachability, privacy, and fail-fast score identities.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-HORIZON-SPHERE-MAPPING-SERVICE
# purpose: Exercise pure mapping from scoring V2 entries to B2A technical/product/theme spheres.
# owns:
#   - apps/api/tests/test_horizon_sphere_mapping_service.py
# inputs: Synthetic ScoringV2Result and SphereScoreV2 payloads.
# outputs: Deterministic mapping/invariant assertions without database or network access.
# dependencies: pytest, scoring schemas, B2A mapping service/canon loader.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - only matching activation contributions affect a mapping.
#   - redundant score identities must agree before ordering/summing.
# failure_policy: test failures identify mapping accuracy or invariant regressions.
# END_MODULE_CONTRACT: M-TEST-HORIZON-SPHERE-MAPPING-SERVICE

# START_MODULE_MAP: M-TEST-HORIZON-SPHERE-MAPPING-SERVICE
# public_entrypoints:
#   - test_mapping_orders_exact_linkage_and_themes
#   - test_mapping_reachability_and_empty_privacy
#   - test_mapping_fails_fast_for_scoring_identity_and_nonfinite_values
#   - test_mapping_lexicographic_tie_target_source_order_and_unrelated_isolation
# semantic_blocks:
#   - HORIZON_SPHERE_MAPPING_TEST_HELPERS: synthetic scoring builders.
#   - HORIZON_SPHERE_MAPPING_TESTS: mapping and invariant assertions.
# owned_tests:
#   - apps/api/tests/test_horizon_sphere_mapping_service.py
# END_MODULE_MAP: M-TEST-HORIZON-SPHERE-MAPPING-SERVICE

# START_BLOCK: HORIZON_SPHERE_MAPPING_TEST_HELPERS
from __future__ import annotations

import math

import pytest

from app.schemas.scoring_v2 import ScoringV2Result, SphereContribution, SphereScoreV2
from app.services.horizon_canon_service import load_horizon_selection_canon
from app.services.horizon_sphere_mapping_service import HorizonSphereMappingService


def _score(
    key: str,
    final_score: float,
    activation_id: str,
    amount: float,
    *,
    contribution_sphere: str | None = None,
) -> SphereScoreV2:
    return SphereScoreV2(
        key=key,
        title=key,
        base_score=0.0,
        activation_score=amount,
        convergence_bonus=0.0,
        raw_score=amount,
        final_score=final_score,
        contributions=[
            SphereContribution(
                sphere=contribution_sphere or key,
                source="activation",
                source_id=activation_id,
                amount=amount,
                evidence=f"linked {key}",
            ),
            SphereContribution(
                sphere=key,
                source="activation",
                source_id="other",
                amount=99.0,
                evidence="unrelated activation",
            ),
        ],
    )


def _scoring(sphere_scores: dict[str, SphereScoreV2]) -> ScoringV2Result:
    return ScoringV2Result(
        canon_versions={"spheres": "v1"},
        day_status="supportive",
        status_breakdown={},
        sphere_scores=sphere_scores,
        top_signals=[],
        top_activations=[],
    )
# END_BLOCK: HORIZON_SPHERE_MAPPING_TEST_HELPERS


# START_BLOCK: HORIZON_SPHERE_MAPPING_TESTS
def test_mapping_orders_exact_linkage_and_themes() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SPHERE-MAPPING-SERVICE.test_mapping_orders_exact_linkage_and_themes
    # purpose: Prove amount/final/key rank order, activation filtering, dedupe/truncation, and theme order.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on mapping ordering regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SPHERE-MAPPING-SERVICE.test_mapping_orders_exact_linkage_and_themes
    service = HorizonSphereMappingService()
    scoring = _scoring(
        {
            "money_security_resources": _score("money_security_resources", 0.60, "act-1", 2.0),
            "work_status_achievement": _score("work_status_achievement", 0.90, "act-1", 2.0),
            "thinking_speech_learning": _score("thinking_speech_learning", 0.20, "act-1", 1.0),
        }
    )
    mapping = service.map_activation("act-1", scoring, source_planet="Transit_Mercury", target_planet_or_key="Natal_Venus")
    assert mapping.technical_spheres == ["work_status_achievement", "money_security_resources", "thinking_speech_learning"]
    assert mapping.product_spheres == ["work", "decisions", "money"]
    assert mapping.theme_keys == [
        "structure_boundaries_control",
        "resources_security",
        "communication_learning_documents",
        "relationships_values_closeness",
    ]
    assert mapping.linked_abs_amount == 5.0
    assert mapping.best_technical_rank == 1


def test_mapping_reachability_and_empty_privacy() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SPHERE-MAPPING-SERVICE.test_mapping_reachability_and_empty_privacy
    # purpose: Prove all canon technical/product keys are reachable and no-link serialization leaks no raw prose/debug.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on canon reachability or privacy regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SPHERE-MAPPING-SERVICE.test_mapping_reachability_and_empty_privacy
    service = HorizonSphereMappingService()
    canon = load_horizon_selection_canon()
    product_union: set[str] = set()
    for technical_key in canon.technical_to_product_spheres:
        mapping = service.map_activation(
            technical_key,
            _scoring({technical_key: _score(technical_key, 1.0, technical_key, 1.0)}),
            source_planet="Moon",
            target_planet_or_key="Pluto",
        )
        assert mapping.technical_spheres == [technical_key]
        product_union.update(mapping.product_spheres)
    assert len(canon.technical_to_product_spheres) == 9
    assert product_union == {
        "work", "money", "documents", "relationships", "sport", "communication",
        "health", "decisions", "travel", "creativity", "study", "shopping",
    }
    empty = service.map_activation(
        "absent",
        ScoringV2Result(
            canon_versions={"spheres": "v1"}, day_status="supportive", status_breakdown={},
            sphere_scores={}, top_signals=[], top_activations=[], debug={"raw": "SECRET_MAPPING_DEBUG"},
        ),
        source_planet="Moon",
        target_planet_or_key="Pluto",
    )
    dumped = empty.model_dump_json()
    assert empty.technical_spheres == []
    assert "evidence" not in dumped and "debug" not in dumped and "SECRET_MAPPING_DEBUG" not in dumped


def test_mapping_lexicographic_tie_target_source_order_and_unrelated_isolation() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SPHERE-MAPPING-SERVICE.test_mapping_lexicographic_tie_target_source_order_and_unrelated_isolation
    # purpose: Prove final lex tie ordering, visible technical-target-source theme order, and source-id isolation.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on ranking/theme order or unrelated-contribution isolation regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SPHERE-MAPPING-SERVICE.test_mapping_lexicographic_tie_target_source_order_and_unrelated_isolation
    service = HorizonSphereMappingService()
    lex_scoring = _scoring(
        {
            "home_family_roots": _score("home_family_roots", 0.75, "lex", 2.0),
            "body_energy_health": _score("body_energy_health", 0.75, "lex", 2.0),
        }
    )
    lex_mapping = service.map_activation("lex", lex_scoring, source_planet=None, target_planet_or_key=None)
    assert lex_mapping.technical_spheres == ["body_energy_health", "home_family_roots"]

    ordered = service.map_activation(
        "ordered",
        _scoring({"home_family_roots": _score("home_family_roots", 1.0, "ordered", 1.0)}),
        source_planet="SUN",
        target_planet_or_key="URANUS",
    )
    assert ordered.theme_keys == ["home_belonging", "change_innovation", "creativity_visibility"]

    baseline_score = _score("work_status_achievement", 1.0, "selected", 2.0)
    unrelated_nonfinite = SphereContribution(
        sphere="work_status_achievement",
        source="activation",
        source_id="other",
        amount=math.nan,
        evidence="unrelated nonfinite evidence",
    )
    isolated_score = baseline_score.model_copy(
        update={"contributions": [*baseline_score.contributions, unrelated_nonfinite]}
    )
    baseline = service.map_activation(
        "selected",
        _scoring({"work_status_achievement": baseline_score}),
        source_planet=None,
        target_planet_or_key=None,
    )
    isolated = service.map_activation(
        "selected",
        _scoring({"work_status_achievement": isolated_score}),
        source_planet=None,
        target_planet_or_key=None,
    )
    assert isolated == baseline


@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf])
def test_mapping_fails_fast_for_scoring_identity_and_nonfinite_values(bad_value: float) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SPHERE-MAPPING-SERVICE.test_mapping_fails_fast_for_scoring_identity_and_nonfinite_values
    # purpose: Prove redundant sphere identity and all ordering/summing numeric inputs fail fast.
    # inputs: bad_value - nan or infinity numeric mutation.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure if programming invariants are silently mapped.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SPHERE-MAPPING-SERVICE.test_mapping_fails_fast_for_scoring_identity_and_nonfinite_values
    service = HorizonSphereMappingService()
    score_key_mismatch = _score("work_status_achievement", 1.0, "act", 1.0).model_copy(update={"key": "money_security_resources"})
    with pytest.raises(AssertionError, match="outer score identity"):
        service.map_activation("act", _scoring({"work_status_achievement": score_key_mismatch}), source_planet=None, target_planet_or_key=None)
    contribution_mismatch = _score("work_status_achievement", 1.0, "act", 1.0, contribution_sphere="money_security_resources")
    with pytest.raises(AssertionError, match="contribution sphere"):
        service.map_activation("act", _scoring({"work_status_achievement": contribution_mismatch}), source_planet=None, target_planet_or_key=None)
    nonfinite_final = _score("work_status_achievement", bad_value, "act", 1.0)
    with pytest.raises(AssertionError, match="final score"):
        service.map_activation("act", _scoring({"work_status_achievement": nonfinite_final}), source_planet=None, target_planet_or_key=None)
    nonfinite_amount = _score("work_status_achievement", 1.0, "act", bad_value)
    with pytest.raises(AssertionError, match="amount"):
        service.map_activation("act", _scoring({"work_status_achievement": nonfinite_amount}), source_planet=None, target_planet_or_key=None)
# END_BLOCK: HORIZON_SPHERE_MAPPING_TESTS
