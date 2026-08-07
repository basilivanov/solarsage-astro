# ############################################################################
# AI_HEADER: TEST_CONVERGENCE_CANON — analysis/production resolver parity.
# ROLE: Proves the replay projection uses the frozen sphere/facet taxonomy and
#       has the same precedence and fail-closed behavior as production.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-CONVERGENCE-CANON
# purpose: Validate the analysis product resolver against the production S2
#   resolver on representative group inputs.
# owns:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_convergence_canon.py
# inputs: frozen product canon and parity fixture payloads.
# outputs: pytest assertions over sphere/facet parity and fail-closed rules.
# dependencies: convergence_canon; apps/api production resolver.
# side_effects: reads the committed product canon through both loaders.
# emitted_logs: none.
# invariants: one input produces one sphere/facet-or-null result; planets alone
#   never create a product sphere; no legacy key is emitted.
# failure_policy: any analysis/production resolver drift fails the replay gate.
# END_MODULE_CONTRACT: M-TEST-CONVERGENCE-CANON

# START_MODULE_MAP: M-TEST-CONVERGENCE-CANON
# public_entrypoints: none
# semantic_blocks:
#   - PARITY_FIXTURES: representative group-level resolver inputs.
#   - RESOLVER_GATES: parity, nullable facet, and fail-closed assertions.
# owned_tests:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_convergence_canon.py
# END_MODULE_MAP: M-TEST-CONVERGENCE-CANON

from __future__ import annotations

import pytest

from app.services.today_convergence_canon import (
    load_today_convergence_canon,
    resolve_product_sphere as production_resolve_product_sphere,
)
from convergence_canon import (
    CANONICAL_PRODUCT_KEYS,
    VALID_FACET_KEYS,
    resolve_product_sphere,
)


# START_BLOCK: PARITY_FIXTURES
PRODUCTION_CANON = load_today_convergence_canon()

# These are group-shaped inputs, not per-factor fan-out cases. They cover the
# resolver priority, nullable facet branch, aliases accepted by the API, and
# unmapped/invalid fail-closed outcomes.
PARITY_FIXTURES: tuple[dict[str, object], ...] = (
    {"house": 2},
    {"house": 8},
    {"house": 8, "context_keys": ["obligation"]},
    {"house": 3, "context_keys": ["travel"]},
    {"house": 9, "context_keys": ["study"]},
    {"technical_spheres": ["meaning_expansion_vector", "thinking_speech_learning"]},
    {
        "house": 9,
        "technical_spheres": ["meaning_expansion_vector"],
        "context_keys": ["travel"],
        "source_key": "Transit_Uranus",
    },
    {"source_key": "Uranus"},
    {"house": 9, "source_key": "Uranus"},
    {"technical_spheres": ["unknown_factor"]},
    {"house": 0},
    {
        "house": 3,
        "technical_spheres": ["thinking-speech-learning"],
        "context": ["communication"],
        "source_planet": "Transit_Mercury",
    },
    {
        "technical_spheres": ["meaning_expansion_vector"],
        "context_theme_keys": ["higher-education"],
        "target_planet": "Natal_Jupiter",
    },
)
# END_BLOCK: PARITY_FIXTURES


# START_BLOCK: RESOLVER_GATES
@pytest.mark.parametrize("payload", PARITY_FIXTURES)
def test_analysis_resolver_matches_production(payload: dict[str, object]) -> None:
    expected = production_resolve_product_sphere(PRODUCTION_CANON, **payload)
    assert resolve_product_sphere(**payload) == expected


def test_product_canon_has_only_current_spheres_and_facets() -> None:
    assert CANONICAL_PRODUCT_KEYS == (
        "work",
        "finance",
        "documents",
        "relationships",
        "sport",
        "communication",
        "health",
        "home_family",
        "travel",
        "creativity",
        "study",
        "friends_goals",
    )
    assert not {"decisions", "shopping"} & set(CANONICAL_PRODUCT_KEYS)
    assert VALID_FACET_KEYS
    assert all("_" in facet or facet.isalpha() for facet in VALID_FACET_KEYS)


def test_planet_only_input_cannot_create_sphere_or_narrow_facet() -> None:
    assert resolve_product_sphere(source_key="Transit_Uranus") is None
    assert resolve_product_sphere(target_key="Natal_SUN") is None


def test_group_can_resolve_sphere_with_nullable_facet() -> None:
    assert resolve_product_sphere(house=9, source_key="Transit_Uranus") == ("travel", None)


def test_mapping_payload_matches_production_mapping_payload() -> None:
    payload = {
        "house": 8,
        "technical_spheres": ["money_security_resources"],
        "context": ["obligation"],
        "source_planet": "Transit_SATURN",
    }
    assert resolve_product_sphere(payload) == production_resolve_product_sphere(
        PRODUCTION_CANON, payload
    )


def test_invalid_house_is_unresolved_without_fallback() -> None:
    assert resolve_product_sphere(house=True) is None
    assert resolve_product_sphere(house=13, technical_spheres=["body_energy_health"]) is None
# END_BLOCK: RESOLVER_GATES
