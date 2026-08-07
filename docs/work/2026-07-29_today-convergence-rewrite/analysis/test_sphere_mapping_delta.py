# ############################################################################
# AI_HEADER: TEST_SPHERE_MAPPING_DELTA — group-level projection attestation.
# ROLE: Proves the replay classifier keeps physical identity while product
#       attribution moves to the production sphere/facet resolver.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-SPHERE-MAPPING-DELTA
# purpose: Exercise resolver-backed group projection in the analysis classifier
#   and prove that one physical group is never cloned into secondary spheres.
# owns:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_sphere_mapping_delta.py
# inputs: small canonical factor fixtures with technical sphere and house data.
# outputs: pytest assertions for state/hero/tone stability and one-sphere output.
# dependencies: convergence_canon; ablation_harness; tone_policy_candidate.
# side_effects: ablation_harness reads the frozen aspect/convergence canons.
# emitted_logs: none.
# invariants: product projection cannot alter physical group membership, hero
#   identity, or day tone; every resolved group has one sphere and one facet/null.
# failure_policy: any projection fan-out or physical drift fails the replay gate.
# END_MODULE_CONTRACT: M-TEST-SPHERE-MAPPING-DELTA

# START_MODULE_MAP: M-TEST-SPHERE-MAPPING-DELTA
# public_entrypoints: none
# semantic_blocks:
#   - FACTOR_FIXTURE: canonical physical units carrying resolver inputs.
#   - DELTA_GATES: physical invariance and no-fan-out assertions.
# owned_tests:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_sphere_mapping_delta.py
# END_MODULE_MAP: M-TEST-SPHERE-MAPPING-DELTA

from __future__ import annotations

from typing import Any

from ablation_harness import classify_day_v2
from convergence_canon import resolve_product_sphere
from tone_policy_candidate import compute_tone_policy


# START_BLOCK: FACTOR_FIXTURE
def _factor(
    semantic_key: str,
    source: str,
    *,
    target: str = "SUN",
    role: str,
    polarity: str,
    technical: tuple[str, ...],
    house: int,
    themes: tuple[str, ...] = (),
) -> dict[str, Any]:
    projection = resolve_product_sphere(
        house=house,
        technical_spheres=technical,
        theme_keys=themes,
    )
    assert projection is not None
    sphere, facet = projection
    return {
        "semantic_key": semantic_key,
        "factor_id": f"factor:{semantic_key}",
        "source": "activation",
        "temporal_role": role,
        "technique": "transit_to_natal",
        "technique_family": "transit",
        "source_planet": source,
        "aspect_type": "trine",
        "orb": 1.0,
        "strength": 0.9,
        "polarity": polarity,
        "target_type": "natal_planet",
        "target_key": target,
        "theme_keys": list(themes),
        "technical_spheres": list(technical),
        "house": house,
        "spheres": [sphere],
        "facet": facet,
        "exact_at": "2026-07-30T12:00:00+03:00" if role == "anchor_today" else None,
    }
# END_BLOCK: FACTOR_FIXTURE


# START_BLOCK: DELTA_GATES
def test_group_projection_preserves_state_hero_and_tone() -> None:
    factors = [
        _factor(
            "saturn:trine:sun",
            "SATURN",
            role="anchor_today",
            polarity="tense",
            technical=("work_status_achievement",),
            house=6,
        ),
        _factor(
            "jupiter:trine:sun",
            "JUPITER",
            role="supporting",
            polarity="supportive",
            technical=("work_status_achievement",),
            house=6,
        ),
    ]
    result = classify_day_v2(factors, 0.55, 0.5, rule="B")
    tone = compute_tone_policy(result, target_date="2026-07-30")

    assert result["state"] == "hero"
    assert [group["hero_anchor"]["semantic_key"] for group in result["hero_groups"]] == [
        "saturn:trine:sun"
    ]
    assert tone["day_tone"] == "tense"
    assert len(result["groups"]) == 1
    assert result["groups"][0]["spheres"] == ("work",)
    assert result["groups"][0]["facet"] == "daily_work"


def test_group_projection_does_not_clone_one_physical_group() -> None:
    result = classify_day_v2(
        [
            _factor(
                "saturn:wide",
                "SATURN",
                role="anchor_today",
                polarity="tense",
                technical=("work_status_achievement", "money_security_resources"),
                house=8,
            ),
            _factor(
                "jupiter:wide",
                "JUPITER",
                role="supporting",
                polarity="supportive",
                technical=("work_status_achievement", "money_security_resources"),
                house=8,
            ),
        ],
        0.55,
        0.5,
        rule="B",
    )

    assert len(result["groups"]) == 1
    assert result["groups"][0]["spheres"] == ("finance",)
    assert result["groups"][0]["facet"] == "shared_money"
    assert all(len(group["spheres"]) == 1 for group in result["groups"])


def test_unresolved_group_stays_physical_but_is_not_published() -> None:
    factors = [
        {
            "semantic_key": "mars:square:uranus",
            "factor_id": "factor:mars:square:uranus",
            "source": "activation",
            "temporal_role": "anchor_today",
            "technique": "transit_to_natal",
            "technique_family": "transit",
            "source_planet": "MARS",
            "aspect_type": "square",
            "orb": 1.0,
            "strength": 0.9,
            "polarity": "tense",
            "target_type": "natal_planet",
            "target_key": "URANUS",
            "theme_keys": [],
            "technical_spheres": [],
            "house": None,
            "spheres": [],
            "facet": None,
            "exact_at": "2026-07-30T12:00:00+03:00",
        },
        {
            "semantic_key": "uranus:square:uranus",
            "factor_id": "factor:uranus:square:uranus",
            "source": "activation",
            "temporal_role": "supporting",
            "technique": "transit_to_natal",
            "technique_family": "transit",
            "source_planet": "URANUS",
            "aspect_type": "square",
            "orb": 1.0,
            "strength": 0.9,
            "polarity": "tense",
            "target_type": "natal_planet",
            "target_key": "URANUS",
            "theme_keys": [],
            "technical_spheres": [],
            "house": None,
            "spheres": [],
            "facet": None,
            "exact_at": None,
        },
    ]

    result = classify_day_v2(factors, 0.55, 0.5, rule="B")

    assert len(result["sig_units"]) == 2
    assert len(result["groups"]) == 1
    assert {
        member["semantic_key"] for member in result["groups"][0]["members"]
    } == {"mars:square:uranus", "uranus:square:uranus"}
    assert result["groups"][0]["spheres"] == ()
    assert result["published_groups"] == []
    assert result["selected_public_units"] == []
    assert result["group_without_sphere_count"] == 1
# END_BLOCK: DELTA_GATES
