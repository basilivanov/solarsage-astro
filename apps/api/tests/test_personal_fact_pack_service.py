# ############################################################################
# AI_HEADER: TEST_PERSONAL_FACT_PACK_SERVICE — deterministic B2B1 personal fact-pack coverage.
# ROLE: Proves exact selected provenance, finite natal matching, omission boundaries, privacy, and stable serialization.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-PERSONAL-FACT-PACK-SERVICE
# purpose: Test B2B1 sphere/strength/risk fact extraction using only synthetic selected stories and natal contexts.
# owns:
#   - apps/api/tests/test_personal_fact_pack_service.py
# inputs: Synthetic B2A selected stories, scoring contributions, and finite natal chart values.
# outputs: Assertions over ordered fact records, omissions, privacy, and integrity failures.
# dependencies: pytest/pydantic, B2B content testkit, personal fact schema/service.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Weak or unlinked natal matches emit no strength/risk claim.
#   - Raw evidence/debug/profile/natal values never reach serialized facts or errors.
# failure_policy: test failures identify B2B1 fact grounding or privacy regressions.
# END_MODULE_CONTRACT: M-TEST-PERSONAL-FACT-PACK-SERVICE

# START_MODULE_MAP: M-TEST-PERSONAL-FACT-PACK-SERVICE
# public_entrypoints:
#   - test_three_golden_fact_packs_are_distinct_and_grounded
#   - test_unlinked_or_weak_patterns_are_omitted
#   - test_aspect_boundaries_and_reverse_order_are_deterministic
#   - test_selected_scoring_and_activation_integrity_fail_closed
#   - test_fact_pack_privacy_stable_ids_and_schema_invariants
#   - test_fact_pack_rejects_missing_selected_sphere_group
#   - test_fact_pack_rejects_empty_and_only_personal_records
#   - test_fact_pack_activation_ids_strip_and_enforce_160_character_limit
# semantic_blocks:
#   - FACT_PACK_GOLDEN_AND_MATCH_TESTS: golden rule matching and omission boundaries.
#   - FACT_PACK_INTEGRITY_AND_PRIVACY_TESTS: selected/scoring checks, privacy, and frozen model proof.
# owned_tests:
#   - apps/api/tests/test_personal_fact_pack_service.py
# END_MODULE_MAP: M-TEST-PERSONAL-FACT-PACK-SERVICE

# START_BLOCK: FACT_PACK_GOLDEN_AND_MATCH_TESTS
from __future__ import annotations

from math import nan

import pytest
from pydantic import ValidationError

from app.schemas.natal import NatalChartAspect, NatalChartPlanet
from app.schemas.personal_fact_pack import PersonalFact, PersonalFactPack
from app.services.personal_fact_pack_service import PersonalFactPackService

from ._horizon_content_testkit import (
    build_communication_natal,
    build_fact_pack,
    build_natal_context,
    build_relationship_natal,
    build_selected_story,
    build_structure_natal,
)


def _statement_keys(pack: PersonalFactPack) -> set[str]:
    return {fact.statement_key for fact in pack.facts if fact.kind != "sphere"}


def test_three_golden_fact_packs_are_distinct_and_grounded() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_three_golden_fact_packs_are_distinct_and_grounded
    # purpose: Prove reviewed structure/communication/relationship charts emit materially distinct selected facts.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on golden matching or selected sphere provenance regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_three_golden_fact_packs_are_distinct_and_grounded
    structure = build_fact_pack("structure_boundaries_control", build_structure_natal())
    communication = build_fact_pack("communication_learning_documents", build_communication_natal())
    relationships = build_fact_pack("relationships_values_closeness", build_relationship_natal())

    assert {
        "strength.structure.steady_responsibility",
        "risk.structure.control_under_pressure",
    } <= _statement_keys(structure)
    assert _statement_keys(communication) == {"strength.communication.structured_thinking"}
    assert {
        "strength.relationships.tactful_clarity",
        "risk.relationships.defensive_strictness",
    } <= _statement_keys(relationships)
    assert len({structure.model_dump_json(), communication.model_dump_json(), relationships.model_dump_json()}) == 3
    assert all(fact.kind == "sphere" for fact in structure.facts[:6])
    assert all(set(fact.activation_ids) <= set(structure.selected_activation_ids) for fact in structure.facts)


def test_unlinked_or_weak_patterns_are_omitted() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_unlinked_or_weak_patterns_are_omitted
    # purpose: Prove chart-only, missing-AND, wrong-aspect, and thematically unlinked patterns do not create claims.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure if an unsupported strength/risk fact is emitted.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_unlinked_or_weak_patterns_are_omitted
    missing_house = build_natal_context(
        planets=[NatalChartPlanet(name="SATURN", sign="AQUARIUS", degree=0.0, house=2, retrograde=False, longitude=0.0)]
    )
    assert _statement_keys(build_fact_pack("structure_boundaries_control", missing_house)) == set()

    wrong_aspect = build_natal_context(
        planets=[
            NatalChartPlanet(name="MERCURY", sign="GEMINI", degree=0.0, house=3, retrograde=False, longitude=0.0),
            NatalChartPlanet(name="SATURN", sign="ARIES", degree=0.0, house=2, retrograde=False, longitude=0.0),
        ],
        aspects=[NatalChartAspect(planet_a="MERCURY", planet_b="SATURN", aspect_type="CONJUNCTION", orb=1.0)],
    )
    assert _statement_keys(build_fact_pack("communication_learning_documents", wrong_aspect)) == set()

    unlinked = build_fact_pack("relationships_values_closeness", build_structure_natal())
    assert "risk.structure.control_under_pressure" not in _statement_keys(unlinked)


def test_aspect_boundaries_and_reverse_order_are_deterministic() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_aspect_boundaries_and_reverse_order_are_deterministic
    # purpose: Prove inclusive max-orb confidence, above-bound omission, and reverse aspect ordering stability.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on deterministic finite aspect matching regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_aspect_boundaries_and_reverse_order_are_deterministic
    exact = build_natal_context(
        aspects=[NatalChartAspect(planet_a="MERCURY", planet_b="SATURN", aspect_type="TRINE", orb=4.0)]
    )
    exact_pack = build_fact_pack("communication_learning_documents", exact)
    assert "strength.communication.structured_thinking" not in _statement_keys(exact_pack)

    threshold = build_natal_context(
        aspects=[
            NatalChartAspect(
                planet_a="MERCURY",
                planet_b="SATURN",
                aspect_type="TRINE",
                orb=2.2857142857142856,
            )
        ]
    )
    threshold_pack = build_fact_pack("communication_learning_documents", threshold)
    matched = next(
        fact for fact in threshold_pack.facts if fact.statement_key == "strength.communication.structured_thinking"
    )
    assert matched.confidence == 0.72

    above = build_natal_context(
        aspects=[NatalChartAspect(planet_a="MERCURY", planet_b="SATURN", aspect_type="TRINE", orb=4.000001)]
    )
    assert _statement_keys(build_fact_pack("communication_learning_documents", above)) == set()

    forward = build_fact_pack("communication_learning_documents", build_communication_natal())
    reverse = build_fact_pack(
        "communication_learning_documents",
        build_natal_context(
            aspects=[NatalChartAspect(planet_a="SATURN", planet_b="MERCURY", aspect_type="TRINE", orb=1.5)]
        ),
    )
    assert forward.model_dump_json() == reverse.model_dump_json()


# END_BLOCK: FACT_PACK_GOLDEN_AND_MATCH_TESTS


# START_BLOCK: FACT_PACK_INTEGRITY_AND_PRIVACY_TESTS
def test_selected_scoring_and_activation_integrity_fail_closed() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_selected_scoring_and_activation_integrity_fail_closed
    # purpose: Prove selected facts require active matching evidence and activation-linked non-zero scoring contributions.
    # inputs: none.
    # returns: none.
    # side_effects: test-local mutable synthetic model copies only.
    # emitted_logs: none.
    # error_behavior: assertion failure if invalid selected/scoring state becomes an empty fact pack.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_selected_scoring_and_activation_integrity_fail_closed
    selection, layer, scoring = build_selected_story("structure_boundaries_control")
    empty_scores = scoring.model_copy(deep=True)
    for score in empty_scores.sphere_scores.values():
        score.contributions = []
    with pytest.raises(ValueError, match="selected-anchor-without-scoring-contribution"):
        PersonalFactPackService().build(
            selection=selection,
            activation_layer=layer,
            scoring_result=empty_scores,
            natal_context=build_structure_natal(),
        )

    inactive_layer = layer.model_copy(deep=True)
    inactive_layer.activations[0].active = False
    with pytest.raises(ValueError, match="selected-anchor-inactive"):
        PersonalFactPackService().build(
            selection=selection,
            activation_layer=inactive_layer,
            scoring_result=scoring,
            natal_context=build_structure_natal(),
        )

    mismatched_layer = layer.model_copy(deep=True)
    mismatched_layer.activations[0].target_key = "MARS"
    with pytest.raises(ValueError, match="selected-anchor-integrity"):
        PersonalFactPackService().build(
            selection=selection,
            activation_layer=mismatched_layer,
            scoring_result=scoring,
            natal_context=build_structure_natal(),
        )

    duplicate_layer = layer.model_copy(deep=True)
    duplicate_layer.activations.append(duplicate_layer.activations[0].model_copy())
    with pytest.raises(ValueError, match="duplicate ids"):
        PersonalFactPackService().build(
            selection=selection,
            activation_layer=duplicate_layer,
            scoring_result=scoring,
            natal_context=build_structure_natal(),
        )

    invalid_orb = build_natal_context(
        aspects=[NatalChartAspect(planet_a="SATURN", planet_b="PLUTO", aspect_type="SQUARE", orb=nan)]
    )
    with pytest.raises(ValueError, match="invalid orb"):
        PersonalFactPackService().build(
            selection=selection,
            activation_layer=layer,
            scoring_result=scoring,
            natal_context=invalid_orb,
        )


def test_fact_pack_privacy_stable_ids_and_schema_invariants() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_fact_pack_privacy_stable_ids_and_schema_invariants
    # purpose: Prove fact serialization stays opaque under sentinel/debug changes and rejects impossible internal states.
    # inputs: none.
    # returns: none.
    # side_effects: test-local synthetic activation/scoring debug mutations only.
    # emitted_logs: none.
    # error_behavior: assertion failure on privacy, determinism, stable-id, or model validation regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_fact_pack_privacy_stable_ids_and_schema_invariants
    selection, layer, scoring = build_selected_story("structure_boundaries_control")
    layer.activations[0].evidence = "RAW_ACTIVATION_EVIDENCE_SENTINEL"
    layer.activations[0].debug = {"private": "RAW_ACTIVATION_DEBUG_SENTINEL"}
    scoring.debug = {"private": "RAW_SCORING_DEBUG_SENTINEL"}
    pack = PersonalFactPackService().build(
        selection=selection,
        activation_layer=layer,
        scoring_result=scoring,
        natal_context=build_structure_natal(),
    )
    dumped = pack.model_dump_json()
    assert all(
        sentinel not in dumped
        for sentinel in (
            "RAW_ACTIVATION_EVIDENCE_SENTINEL",
            "RAW_ACTIVATION_DEBUG_SENTINEL",
            "RAW_SCORING_DEBUG_SENTINEL",
            "AQUARIUS",
            "HOUSE_10_SENTINEL",
            "OPPOSITION",
            "ORB_1_05_SENTINEL",
        )
    )
    assert all(fact.id.startswith("pf:v1:") for fact in pack.facts)
    assert (
        pack.model_dump_json()
        == PersonalFactPackService()
        .build(
            selection=selection,
            activation_layer=layer,
            scoring_result=scoring,
            natal_context=build_structure_natal(),
        )
        .model_dump_json()
    )
    with pytest.raises(ValidationError):
        PersonalFact.model_validate({**pack.facts[0].model_dump(), "confidence": 0.1234567})
    with pytest.raises(ValidationError):
        PersonalFactPack.model_validate({**pack.model_dump(), "selected_activation_ids": ["x", "x", "z"]})


@pytest.mark.parametrize(
    ("item_index", "timing_field", "replacement"),
    [
        (0, "active_from", "2026-01-02"),
        (1, "exact_at", "2026-07-12T12:00:01Z"),
        (2, "active_until", "2026-07-13T00:00:00Z"),
    ],
)
def test_selected_anchor_timing_fields_independently_fail_closed(
    item_index: int,
    timing_field: str,
    replacement: str,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_selected_anchor_timing_fields_independently_fail_closed
    # purpose: Prove each selected timing identity field remains anchored to its activation evidence.
    # inputs: item_index/timing_field/replacement - one selected timing mutation.
    # returns: none.
    # side_effects: test-local selection reconstruction only.
    # emitted_logs: none.
    # error_behavior: assertion failure if timing drift emits facts.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_selected_anchor_timing_fields_independently_fail_closed
    selection, layer, scoring = build_selected_story("structure_boundaries_control")
    selection_data = selection.model_dump()
    selection_data["items"][item_index]["timing"][timing_field] = replacement
    with pytest.raises(ValueError, match="selected-anchor-integrity"):
        PersonalFactPackService().build(
            selection=selection.model_validate(selection_data),
            activation_layer=layer,
            scoring_result=scoring,
            natal_context=build_structure_natal(),
        )


@pytest.mark.parametrize("case", ["score_key", "contribution_sphere", "zero_amount", "base_only", "convergence_only", "other_activation"])
def test_selected_scoring_contribution_identity_boundaries_fail_closed(case: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_selected_scoring_contribution_identity_boundaries_fail_closed
    # purpose: Prove selected sphere facts require a finite non-zero contribution from the exact selected anchor.
    # inputs: case - one contribution identity/grounding mutation.
    # returns: none.
    # side_effects: test-local scoring mutation only.
    # emitted_logs: none.
    # error_behavior: assertion failure if an ungrounded sphere fact is emitted.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_selected_scoring_contribution_identity_boundaries_fail_closed
    selection, layer, scoring = build_selected_story("structure_boundaries_control")
    mutated = scoring.model_copy(deep=True)
    anchor = selection.items[0]
    score = mutated.sphere_scores[anchor.technical_spheres[0]]
    contribution = score.contributions[0]
    if case == "score_key":
        score.key = "other"
    elif case == "contribution_sphere":
        contribution.sphere = "other"
    elif case == "zero_amount":
        contribution.amount = 0.0
    elif case == "base_only":
        contribution.source = "base_signal"
    elif case == "convergence_only":
        contribution.source = "convergence"
    else:
        contribution.source_id = "unrelated-activation"
    with pytest.raises(ValueError):
        PersonalFactPackService().build(
            selection=selection,
            activation_layer=layer,
            scoring_result=mutated,
            natal_context=build_structure_natal(),
        )


def test_nonfinite_contribution_and_negative_natal_orb_are_private_failures() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_nonfinite_contribution_and_negative_natal_orb_are_private_failures
    # purpose: Prove non-finite used scoring and negative natal orbs fail without raw sentinel leakage.
    # inputs: none.
    # returns: none.
    # side_effects: test-local scoring/natal mutations only.
    # emitted_logs: none.
    # error_behavior: assertion failure if unsafe values or raw sentinels surface.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_nonfinite_contribution_and_negative_natal_orb_are_private_failures
    selection, layer, scoring = build_selected_story("structure_boundaries_control")
    layer.activations[0].evidence = "RAW_EVIDENCE_SENTINEL"
    broken = scoring.model_copy(deep=True)
    broken.sphere_scores[selection.items[0].technical_spheres[0]].contributions[0].amount = nan
    with pytest.raises(ValueError) as contribution_error:
        PersonalFactPackService().build(
            selection=selection,
            activation_layer=layer,
            scoring_result=broken,
            natal_context=build_structure_natal(),
        )
    assert "RAW_EVIDENCE_SENTINEL" not in str(contribution_error.value)
    negative_orb = build_natal_context(
        aspects=[NatalChartAspect(planet_a="SATURN", planet_b="PLUTO", aspect_type="SQUARE", orb=-0.1)]
    )
    with pytest.raises(ValueError, match="invalid orb"):
        PersonalFactPackService().build(
            selection=selection,
            activation_layer=layer,
            scoring_result=scoring,
            natal_context=negative_orb,
        )


def test_natal_aspect_selection_uses_smallest_orb_independent_of_input_order() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_natal_aspect_selection_uses_smallest_orb_independent_of_input_order
    # purpose: Prove matching aspect traversal chooses the smallest orb and ignores irrelevant valid aspects.
    # inputs: none.
    # returns: none.
    # side_effects: synthetic natal construction only.
    # emitted_logs: none.
    # error_behavior: assertion failure on input-order-dependent fact serialization.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_natal_aspect_selection_uses_smallest_orb_independent_of_input_order
    small = NatalChartAspect(planet_a="MERCURY", planet_b="SATURN", aspect_type="TRINE", orb=1.0)
    large = NatalChartAspect(planet_a="SATURN", planet_b="MERCURY", aspect_type="SEXTILE", orb=3.0)
    irrelevant = NatalChartAspect(planet_a="SUN", planet_b="MOON", aspect_type="TRINE", orb=1.0)
    first = build_fact_pack("communication_learning_documents", build_natal_context(aspects=[large, irrelevant, small]))
    second = build_fact_pack("communication_learning_documents", build_natal_context(aspects=[small, irrelevant, large]))
    assert first.model_dump_json() == second.model_dump_json()
    strength = next(fact for fact in first.facts if fact.kind == "strength")
    assert strength.confidence == 0.7875


def test_fact_pack_schema_rejects_blank_selected_and_fact_activation_ids() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_fact_pack_schema_rejects_blank_selected_and_fact_activation_ids
    # purpose: Mutation-prove opaque activation references cannot be blank at pack or fact level.
    # inputs: none.
    # returns: none.
    # side_effects: schema validation only.
    # emitted_logs: none.
    # error_behavior: assertion failure if blank provenance is accepted.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_fact_pack_schema_rejects_blank_selected_and_fact_activation_ids
    pack = build_fact_pack("structure_boundaries_control", build_structure_natal())
    with pytest.raises(ValidationError):
        PersonalFactPack.model_validate({**pack.model_dump(), "selected_activation_ids": [" ", "middle", "fast"]})
    first_fact = pack.facts[0].model_dump()
    first_fact["activation_ids"] = [" "]
    with pytest.raises(ValidationError):
        PersonalFact.model_validate(first_fact)


def test_missing_selected_activation_and_pack_order_alignment_fail_closed() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_missing_selected_activation_and_pack_order_alignment_fail_closed
    # purpose: Prove missing selected evidence fails and schema enforces deterministic horizon/id/source alignment.
    # inputs: none.
    # returns: none.
    # side_effects: test-local activation and schema payload mutations only.
    # emitted_logs: none.
    # error_behavior: assertion failure if missing evidence or misaligned facts are accepted.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_missing_selected_activation_and_pack_order_alignment_fail_closed
    selection, layer, scoring = build_selected_story("structure_boundaries_control")
    missing = layer.model_copy(deep=True)
    missing.activations = [activation for activation in missing.activations if activation.id != selection.items[0].activation_id]
    with pytest.raises(ValueError, match="selected-anchor-missing"):
        PersonalFactPackService().build(
            selection=selection,
            activation_layer=missing,
            scoring_result=scoring,
            natal_context=build_structure_natal(),
        )
    pack = build_fact_pack("structure_boundaries_control", build_structure_natal())
    sphere_horizons = [fact.horizon_ids[0] for fact in pack.facts if fact.kind == "sphere"]
    assert sphere_horizons == sorted(sphere_horizons, key=("long", "medium", "fast").index)
    personal = next(fact for fact in pack.facts if fact.kind == "strength")
    invalid_fact = personal.model_dump()
    invalid_fact["activation_ids"] = list(reversed(invalid_fact["activation_ids"]))
    with pytest.raises(ValidationError):
        PersonalFactPack.model_validate(
            {**pack.model_dump(), "facts": [fact.model_dump() if fact.id != personal.id else invalid_fact for fact in pack.facts]}
        )


@pytest.mark.parametrize("missing_horizon", ["long", "medium", "fast"])
def test_fact_pack_rejects_missing_selected_sphere_group(missing_horizon: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_fact_pack_rejects_missing_selected_sphere_group
    # purpose: Prove every selected long/medium/fast anchor retains at least one sphere provenance fact.
    # inputs: missing_horizon - one selected horizon whose sphere facts are removed.
    # returns: none.
    # side_effects: schema payload mutation only.
    # emitted_logs: none.
    # error_behavior: assertion failure if an incomplete selected pack is accepted.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_fact_pack_rejects_missing_selected_sphere_group
    pack = build_fact_pack("structure_boundaries_control", build_structure_natal())
    facts = [
        fact.model_dump()
        for fact in pack.facts
        if not (fact.kind == "sphere" and fact.horizon_ids[0] == missing_horizon)
    ]
    with pytest.raises(ValidationError):
        PersonalFactPack.model_validate({**pack.model_dump(), "facts": facts})


def test_fact_pack_rejects_empty_and_only_personal_records() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_fact_pack_rejects_empty_and_only_personal_records
    # purpose: Prove a selected triple cannot serialize an empty or sphere-provenance-free fact pack.
    # inputs: none.
    # returns: none.
    # side_effects: schema payload mutation only.
    # emitted_logs: none.
    # error_behavior: assertion failure if an incomplete selected pack is accepted.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_fact_pack_rejects_empty_and_only_personal_records
    pack = build_fact_pack("structure_boundaries_control", build_structure_natal())
    with pytest.raises(ValidationError):
        PersonalFactPack.model_validate({**pack.model_dump(), "facts": []})
    personal_only = [fact.model_dump() for fact in pack.facts if fact.kind != "sphere"]
    with pytest.raises(ValidationError):
        PersonalFactPack.model_validate({**pack.model_dump(), "facts": personal_only})


def test_fact_pack_activation_ids_strip_and_enforce_160_character_limit() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_fact_pack_activation_ids_strip_and_enforce_160_character_limit
    # purpose: Prove activation provenance preserves arbitrary characters while requiring trimmed 1..160-character ids.
    # inputs: none.
    # returns: none.
    # side_effects: schema payload mutation only.
    # emitted_logs: none.
    # error_behavior: assertion failure if overlong ids load or valid aligned 160-character ids fail.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-FACT-PACK-SERVICE.test_fact_pack_activation_ids_strip_and_enforce_160_character_limit
    pack = build_fact_pack("structure_boundaries_control", build_structure_natal())
    with pytest.raises(ValidationError):
        PersonalFactPack.model_validate(
            {**pack.model_dump(), "selected_activation_ids": ["x" * 161, "medium", "fast"]}
        )
    fact_data = pack.facts[0].model_dump()
    fact_data["activation_ids"] = ["x" * 161]
    with pytest.raises(ValidationError):
        PersonalFact.model_validate(fact_data)
    replacements = dict(zip(pack.selected_activation_ids, ("a" * 160, "b" * 160, "c" * 160), strict=True))
    payload = pack.model_dump()
    payload["selected_activation_ids"] = list(replacements.values())
    for fact in payload["facts"]:
        fact["activation_ids"] = [replacements[activation_id] for activation_id in fact["activation_ids"]]
    validated = PersonalFactPack.model_validate(payload)
    assert validated.selected_activation_ids == ("a" * 160, "b" * 160, "c" * 160)


# END_BLOCK: FACT_PACK_INTEGRITY_AND_PRIVACY_TESTS
