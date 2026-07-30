# ############################################################################
# AI_HEADER: TEST_TONE_POLICY_CANDIDATE — polarity-layer policy fixtures.
# ROLE: Verifies fast-source, context, mixed, and independent-tone rules.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TONE-POLICY-CANDIDATE
# purpose: Prove candidate unit/group/day tone behavior with small deterministic fixtures.
# owns:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_tone_policy_candidate.py
# inputs: synthetic classifier-result dictionaries.
# outputs: pytest assertions.
# dependencies: pytest; tone_policy_candidate.
# side_effects: none.
# emitted_logs: none.
# invariants: one fast factor never creates a general day tone.
# failure_policy: any policy regression fails the W1 candidate gate.
# END_MODULE_CONTRACT: M-TEST-TONE-POLICY-CANDIDATE

# START_MODULE_MAP: M-TEST-TONE-POLICY-CANDIDATE
# public_entrypoints: none
# semantic_blocks:
#   - FIXTURES: minimal factor/result builders.
#   - TESTS: unit, group, and day tone behavior.
# owned_tests:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_tone_policy_candidate.py
# END_MODULE_MAP: M-TEST-TONE-POLICY-CANDIDATE

from __future__ import annotations

from typing import Any

from tone_policy_candidate import compute_tone_policy, group_polarity


# START_BLOCK: FIXTURES
def _unit(
    source: str,
    polarity: str,
    *,
    role: str = "anchor_today",
    strength: float = 0.8,
    technique_family: str = "transit",
) -> dict[str, Any]:
    return {
        "semantic_key": f"{source}:{polarity}:{role}",
        "source_planet": source,
        "technique_family": technique_family,
        "temporal_role": role,
        "strength": strength,
        "polarity": polarity,
        "spheres": ["work"],
    }


def _result(units: list[dict[str, Any]], *, hero: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    group = {"members": units, "hero": bool(hero), "anchor": units[0] if units else {}}
    return {
        "sig_units": units,
        "selected_public_units": units,
        "groups": [group] if units else [],
        "hero_groups": [{**group, "hero_anchor": hero[0]} for _ in [0]] if hero else [],
    }
# END_BLOCK: FIXTURES


# START_BLOCK: TESTS
def test_single_fast_tense_unit_is_steady() -> None:
    result = compute_tone_policy(_result([_unit("MOON", "tense")]))
    assert result["day_tone"] == "steady"
    assert result["legacy_any_selected_tense"] is True


def test_long_running_tense_context_does_not_override_fresh_support() -> None:
    result = compute_tone_policy(
        _result(
            [
                _unit("NEPTUNE", "tense", role="supporting", strength=0.9),
                _unit("JUPITER", "supportive", role="anchor_today", strength=0.8),
            ]
        )
    )
    # The ongoing tense transit is context; one fresh supportive unit alone
    # is not enough for a global tone claim.
    assert result["day_tone"] == "steady"
    assert result["tone_scores"]["context_tense_units"] == 1


def test_two_independent_fresh_tense_units_create_tense() -> None:
    result = compute_tone_policy(
        _result([_unit("SATURN", "tense"), _unit("PLUTO", "tense")])
    )
    assert result["day_tone"] == "tense"
    assert result["tone_scores"]["fresh_tense_units"] == 2


def test_fresh_support_and_tension_are_mixed() -> None:
    result = compute_tone_policy(
        _result([_unit("SATURN", "tense"), _unit("JUPITER", "supportive")])
    )
    assert result["day_tone"] == "mixed"


def test_high_confidence_tense_hero_can_create_tense_alone() -> None:
    anchor = _unit("SATURN", "tense", strength=0.9)
    result = compute_tone_policy(_result([anchor], hero=[anchor]))
    assert result["day_tone"] == "tense"
    assert result["tone_scores"]["high_confidence_tense_anchor"] is True


def test_group_balance_is_independent_and_mixed() -> None:
    balance = group_polarity(
        [
            _unit("SATURN", "tense", strength=0.8),
            _unit("SATURN", "tense", strength=0.7),  # duplicate driver, ignored
            _unit("JUPITER", "supportive", strength=0.8),
        ]
    )
    assert balance["independent_units"] == 2
    assert balance["polarity"] == "mixed"
# END_BLOCK: TESTS
