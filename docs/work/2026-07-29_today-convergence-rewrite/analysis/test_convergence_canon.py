# ############################################################################
# AI_HEADER: TEST_CONVERGENCE_CANON — W1 sphere-registry contract tests.
# ROLE: Proves strict canon loading, bounded planet maps, and fail-closed projection.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-CONVERGENCE-CANON
# purpose: Validate the new convergence sphere registry without importing legacy Today maps.
# owns:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_convergence_canon.py
# inputs: committed Today-convergence canon and small synthetic factor keys.
# outputs: pytest assertions over mapping completeness, ordering, and failure behavior.
# dependencies: convergence_canon.
# side_effects: reads the committed canon through convergence_canon.
# emitted_logs: none.
# invariants: unmapped input never becomes work and every planet map has at most two spheres.
# failure_policy: any mapping or ordering drift fails the W1 gate.
# END_MODULE_CONTRACT: M-TEST-CONVERGENCE-CANON

# START_MODULE_MAP: M-TEST-CONVERGENCE-CANON
# public_entrypoints: none
# semantic_blocks:
#   - CANON_MAPPING: registry constraints and representative projections.
# owned_tests:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_convergence_canon.py
# END_MODULE_MAP: M-TEST-CONVERGENCE-CANON

from __future__ import annotations

from convergence_canon import (
    CANONICAL_PRODUCT_KEYS,
    PLANET_TO_PRODUCT_MAP,
    map_product_spheres,
)


# START_BLOCK: CANON_MAPPING
def test_planet_mapping_is_complete_bounded_and_decisions_is_not_catch_all() -> None:
    assert set(PLANET_TO_PRODUCT_MAP) == {
        "SUN",
        "MOON",
        "MERCURY",
        "VENUS",
        "MARS",
        "JUPITER",
        "SATURN",
        "URANUS",
        "NEPTUNE",
        "PLUTO",
    }
    assert all(1 <= len(spheres) <= 2 for spheres in PLANET_TO_PRODUCT_MAP.values())
    assert {
        planet for planet, spheres in PLANET_TO_PRODUCT_MAP.items() if "decisions" in spheres
    } == {"SATURN", "PLUTO"}


def test_mapping_uses_canonical_order_and_explicit_technical_themes() -> None:
    mapped = map_product_spheres(
        ["thinking_speech_learning", "money_security_resources"],
        "Transit_VENUS",
        "Natal_MERCURY",
    )
    assert mapped == tuple(key for key in CANONICAL_PRODUCT_KEYS if key in set(mapped))
    assert {"money", "documents", "relationships", "communication", "study", "shopping"} <= set(mapped)


def test_unmapped_factor_is_excluded_instead_of_falling_back_to_work() -> None:
    assert map_product_spheres(["unknown_theme"], "SOLAR", "UNKNOWN") == ()
# END_BLOCK: CANON_MAPPING
