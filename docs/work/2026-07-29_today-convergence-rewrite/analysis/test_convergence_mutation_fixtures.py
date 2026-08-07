# ############################################################################
# AI_HEADER: TEST_CONVERGENCE_MUTATION_FIXTURES — isolated W1 C1 regressions.
# ROLE: Turns mutation fixtures 1–5 and sphere-cap invariants into executable tests.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-CONVERGENCE-MUTATION-FIXTURES
# purpose: Prove that duplicates, fast noise, non-rare pairs, transitive bridges,
#   background rows, and sphere fan-out cannot inflate a W1 hero result.
# owns:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_convergence_mutation_fixtures.py
# inputs: small synthetic factor dictionaries matching classify_day_v2 input.
# outputs: pytest assertions for C1 classification and per-group projection.
# dependencies: ablation_harness classify_day_v2.
# side_effects: ablation_harness reads committed canon and local diagnostic dump at import.
# emitted_logs: none.
# invariants: one physical driver is one evidence unit and one group exposes one
#   resolver-backed sphere plus an optional facet.
# failure_policy: any classification drift fails the W1 freeze gate.
# END_MODULE_CONTRACT: M-TEST-CONVERGENCE-MUTATION-FIXTURES

# START_MODULE_MAP: M-TEST-CONVERGENCE-MUTATION-FIXTURES
# public_entrypoints: none
# semantic_blocks:
#   - FACTOR_FIXTURE: minimal canonical factor builder.
#   - MUTATION_TESTS: executable fixtures 1–5 plus background/orb/fan-out gates.
# owned_tests:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_convergence_mutation_fixtures.py
# END_MODULE_MAP: M-TEST-CONVERGENCE-MUTATION-FIXTURES

from __future__ import annotations

from typing import Any

from ablation_harness import classify_day_v2


# START_BLOCK: FACTOR_FIXTURE
def _factor(
    semantic_key: str,
    source: str,
    target: str,
    *,
    role: str = "supporting",
    target_type: str = "natal_planet",
    aspect: str | None = "trine",
    orb: float | None = 1.0,
    strength: float = 0.9,
    technique: str = "transit_to_natal",
    family: str = "transit",
    themes: tuple[str, ...] = (),
    spheres: tuple[str, ...] = ("work",),
    technical_spheres: tuple[str, ...] = ("work_status_achievement",),
    house: int = 6,
    polarity: str = "supportive",
) -> dict[str, Any]:
    return {
        "semantic_key": semantic_key,
        "factor_id": f"factor:{semantic_key}",
        "source": "activation",
        "temporal_role": role,
        "technique": technique,
        "technique_family": family,
        "source_planet": source,
        "aspect_type": aspect,
        "orb": orb,
        "strength": strength,
        "polarity": polarity,
        "target_type": target_type,
        "target_key": target,
        "theme_keys": list(themes),
        "technical_spheres": list(technical_spheres),
        "house": house,
        "spheres": list(spheres),
        "exact_at": "2026-07-30T12:00:00+03:00" if role == "anchor_today" else None,
    }


def _classify(factors: list[dict[str, Any]]) -> dict[str, Any]:
    return classify_day_v2(factors, 0.55, 0.5, rule="B")


def _hero_keys(result: dict[str, Any]) -> set[str]:
    return {
        str(group["hero_anchor"]["semantic_key"])
        for group in result["hero_groups"]
    }
# END_BLOCK: FACTOR_FIXTURE


# START_BLOCK: MUTATION_TESTS
def test_fixture_1_two_ordinary_lunar_aspects_on_one_target_are_not_hero() -> None:
    result = _classify(
        [
            _factor("moon:trine:sun", "MOON", "SUN", role="anchor_today"),
            _factor("moon:sextile:sun", "MOON", "SUN", role="anchor_today", aspect="sextile"),
        ]
    )
    assert result["state"] == "single_impulse"
    assert result["hero_groups"] == []


def test_fixture_2_duplicate_producers_do_not_create_an_independent_unit() -> None:
    rare = _factor("saturn:trine:sun", "SATURN", "SUN", role="anchor_today")
    first = _factor("jupiter:sextile:sun", "JUPITER", "SUN", aspect="sextile")
    duplicate = {**first, "factor_id": "factor:producer-two"}
    result = _classify([rare, first, duplicate])

    assert result["state"] == "hero"
    assert result["hero_groups"][0]["n_independent"] == 2
    assert len(result["selected_public_units"]) == 2


def test_fixture_3_factor_just_outside_canonical_orb_is_noise() -> None:
    result = _classify(
        [_factor("jupiter:edge:sun", "JUPITER", "SUN", role="anchor_today", orb=3.51)]
    )
    assert result["state"] == "quiet"
    assert result["n_significant"] == 0


def test_fixture_4_independent_pair_is_hero_only_with_rare_anchor() -> None:
    ordinary = _classify(
        [
            _factor("sun:trine:mars", "SUN", "MARS", role="anchor_today"),
            _factor("mars:sextile:mars", "MARS", "MARS", aspect="sextile"),
        ]
    )
    rare = _classify(
        [
            _factor("saturn:trine:mars", "SATURN", "MARS", role="anchor_today"),
            _factor("sun:sextile:mars", "SUN", "MARS", aspect="sextile"),
        ]
    )

    assert ordinary["state"] == "convergence"
    assert ordinary["hero_groups"] == []
    assert rare["state"] == "hero"
    assert _hero_keys(rare) == {"saturn:trine:mars"}


def test_fixture_5_transitive_bridge_does_not_join_c_to_anchor_a() -> None:
    anchor_a = _factor(
        "saturn:a", "SATURN", "TARGET_A", role="anchor_today", themes=("alpha",)
    )
    bridge_b = _factor(
        "jupiter:b", "JUPITER", "TARGET_B", themes=("alpha", "beta")
    )
    unrelated_c = _factor(
        "pluto:c", "PLUTO", "TARGET_C", themes=("beta",)
    )
    result = _classify([anchor_a, bridge_b, unrelated_c])

    member_keys = {
        member["semantic_key"]
        for group in result["groups"]
        for member in group["members"]
    }
    assert member_keys == {"saturn:a", "jupiter:b"}
    assert "pluto:c" not in member_keys


def test_background_cannot_confirm_a_rare_anchor() -> None:
    result = _classify(
        [
            _factor("saturn:anchor", "SATURN", "SUN", role="anchor_today"),
            _factor("jupiter:background", "JUPITER", "SUN", role="background"),
        ]
    )
    assert result["state"] == "single_impulse"
    assert result["groups"] == []


def test_group_projection_caps_each_group_not_the_whole_day() -> None:
    result = _classify(
        [
            _factor(
                "saturn:wide",
                "SATURN",
                "SUN",
                role="anchor_today",
                spheres=("work", "money", "documents", "decisions"),
            ),
            _factor(
                "jupiter:wide",
                "JUPITER",
                "SUN",
                spheres=("money", "relationships", "travel", "study"),
            ),
        ]
    )
    assert result["groups"]
    assert all(len(group["spheres"]) == 1 for group in result["groups"])
    assert all("facet" in group for group in result["groups"])
# END_BLOCK: MUTATION_TESTS
