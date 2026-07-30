# ############################################################################
# AI_HEADER: TEST_SPHERE_MAPPING_DELTA — replay-v3 to W1 mapping attestation.
# ROLE: Proves the mapping revision changes attribution only, not classification or tone.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-SPHERE-MAPPING-DELTA
# purpose: Compare the frozen replay-v3 mapping domain with the new W1 canon and
#   prove representative C1/dayTone invariance under the attribution change.
# owns:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_sphere_mapping_delta.py
# inputs: committed W1 canon plus literal replay-v3 mapping values used only as a test oracle.
# outputs: pytest assertions for mapping-domain equality, semantic parity, and group caps.
# dependencies: convergence_canon; ablation_harness; tone_policy_candidate.
# side_effects: ablation_harness reads committed canon and local diagnostic dump at import.
# emitted_logs: none.
# invariants:
#   - old and new mappings recognize the same planet/technical key domain;
#   - state, hero identity, and dayTone do not depend on revised sphere labels;
#   - only primary/secondary sphere attribution may change.
# failure_policy: any eligibility-domain or semantic drift fails W1 freeze.
# END_MODULE_CONTRACT: M-TEST-SPHERE-MAPPING-DELTA

# START_MODULE_MAP: M-TEST-SPHERE-MAPPING-DELTA
# public_entrypoints: none
# semantic_blocks:
#   - REPLAY_V3_ORACLE: frozen pre-change mapping values, test-only.
#   - DELTA_GATES: domain and classification parity assertions.
# owned_tests:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_sphere_mapping_delta.py
# END_MODULE_MAP: M-TEST-SPHERE-MAPPING-DELTA

from __future__ import annotations

from typing import Any

from ablation_harness import classify_day_v2
from convergence_canon import (
    CANONICAL_PRODUCT_KEYS,
    PLANET_TO_PRODUCT_MAP,
    TECH_SPHERE_TO_PRODUCT_MAP,
    map_product_spheres,
)
from tone_policy_candidate import compute_tone_policy


# START_BLOCK: REPLAY_V3_ORACLE
REPLAY_V3_PLANET_MAP: dict[str, tuple[str, ...]] = {
    "SUN": ("work", "decisions"),
    "MARS": ("work", "sport", "decisions"),
    "VENUS": ("money", "relationships", "shopping"),
    "MERCURY": ("documents", "communication", "study"),
    "JUPITER": ("work", "money", "decisions"),
    "SATURN": ("work", "decisions", "documents"),
    "MOON": ("relationships", "health"),
    "URANUS": ("decisions", "travel"),
    "NEPTUNE": ("creativity", "health"),
    "PLUTO": ("decisions", "work"),
}
REPLAY_V3_TECH_MAP: dict[str, tuple[str, ...]] = {
    "work_status_achievement": ("work",),
    "career": ("work",),
    "career_social_status": ("work",),
    "public_image": ("work",),
    "technology_innovation": ("work",),
    "finance_money": ("money",),
    "money_security_resources": ("money",),
    "legal_affairs": ("documents",),
    "partnerships_contracts": ("documents",),
    "relationships_partnership": ("relationships",),
    "relationships": ("relationships",),
    "home_family_roots": ("relationships",),
    "home_family": ("relationships",),
    "inheritance": ("relationships",),
    "body_energy_health": ("sport",),
    "daily_routine": ("sport",),
    "service_routine": ("sport",),
    "communication_learning": ("communication",),
    "thinking_speech_learning": ("communication",),
    "friendship_social": ("communication",),
    "spirituality_inner_growth": ("health",),
    "inner_background_unconscious": ("health",),
    "healing": ("health",),
    "hidden_matters": ("health",),
    "career_ambition": ("decisions",),
    "crisis_transformation": ("decisions",),
    "crisis_transformation_control": ("decisions",),
    "philosophy": ("decisions",),
    "travel_adventure": ("travel",),
}


def _legacy_spheres(
    technical: tuple[str, ...], source: str, target: str
) -> tuple[str, ...]:
    mapped: set[str] = set()
    for key in technical:
        mapped.update(REPLAY_V3_TECH_MAP.get(key.lower(), ()))
    for raw in (source, target):
        key = raw.upper().removeprefix("TRANSIT_").removeprefix("NATAL_")
        mapped.update(REPLAY_V3_PLANET_MAP.get(key, ()))
    return tuple(key for key in CANONICAL_PRODUCT_KEYS if key in mapped)


def _factor(
    semantic_key: str,
    source: str,
    *,
    role: str,
    polarity: str,
    technical: tuple[str, ...],
    new_mapping: bool,
) -> dict[str, Any]:
    target = "SUN"
    spheres = (
        map_product_spheres(technical, source, target)
        if new_mapping
        else _legacy_spheres(technical, source, target)
    )
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
        "theme_keys": [],
        "spheres": list(spheres),
        "exact_at": "2026-07-30T12:00:00+03:00" if role == "anchor_today" else None,
    }
# END_BLOCK: REPLAY_V3_ORACLE


# START_BLOCK: DELTA_GATES
def test_mapping_recognition_domain_is_identical_to_replay_v3() -> None:
    assert set(PLANET_TO_PRODUCT_MAP) == set(REPLAY_V3_PLANET_MAP)
    assert set(TECH_SPHERE_TO_PRODUCT_MAP) == set(REPLAY_V3_TECH_MAP)
    assert all(PLANET_TO_PRODUCT_MAP.values())
    assert all(TECH_SPHERE_TO_PRODUCT_MAP.values())


def test_mapping_delta_changes_only_attribution_not_state_hero_or_tone() -> None:
    specifications = (
        ("saturn:trine:sun", "SATURN", "anchor_today", "tense", ("work_status_achievement",)),
        ("jupiter:trine:sun", "JUPITER", "supporting", "supportive", ("money_security_resources",)),
        ("neptune:trine:sun", "NEPTUNE", "supporting", "tense", ("inner_background_unconscious",)),
    )
    old_factors = [
        _factor(key, source, role=role, polarity=polarity, technical=technical, new_mapping=False)
        for key, source, role, polarity, technical in specifications
    ]
    new_factors = [
        _factor(key, source, role=role, polarity=polarity, technical=technical, new_mapping=True)
        for key, source, role, polarity, technical in specifications
    ]
    old_result = classify_day_v2(old_factors, 0.55, 0.5, rule="B")
    new_result = classify_day_v2(new_factors, 0.55, 0.5, rule="B")
    old_tone = compute_tone_policy(old_result, target_date="2026-07-30")
    new_tone = compute_tone_policy(new_result, target_date="2026-07-30")

    signature = lambda result: (
        result["state"],
        tuple(sorted(group["hero_anchor"]["semantic_key"] for group in result["hero_groups"])),
    )
    assert signature(old_result) == signature(new_result)
    assert old_tone["day_tone"] == new_tone["day_tone"]
    assert [group["spheres"] for group in old_result["groups"]] != [
        group["spheres"] for group in new_result["groups"]
    ]
    assert all(len(group["spheres"]) <= 2 for group in new_result["groups"])
# END_BLOCK: DELTA_GATES
