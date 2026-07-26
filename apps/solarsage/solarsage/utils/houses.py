# ############################################################################
# AI_HEADER: MODULE_SIDECAR_HOUSES
# ROLE: House lookup utility for planet longitudes given house cusps.
# DEPENDENCIES: None (pure math/astrology utility)
# GRACE_ANCHORS: [HOUSE_FINDER]
# ############################################################################

# START_MODULE_CONTRACT: M-SIDECAR-HOUSES
# purpose: Determine astrological house (1..12) for a given longitude and 12 house cusps.
# owns:
#   - apps/solarsage/solarsage/utils/houses.py
# inputs:
#   - longitude: float (0..360)
#   - cusps: list[float] (12 house cusp longitudes in order 1..12)
# outputs:
#   - house number: int (1..12) or None if cusps invalid
# invariants:
#   - Half-open interval [cusp, next): planet exactly on cusp belongs to starting house
#   - Supports 360->0 degree wrap-around
#   - Returns strictly 1..12 or None (never fabricates 1 for invalid cusps)
# END_MODULE_CONTRACT: M-SIDECAR-HOUSES

# START_MODULE_MAP: M-SIDECAR-HOUSES
# public_entrypoints:
#   - find_house
# semantic_blocks:
#   - HOUSE_FINDER: find_house function implementation
# owned_tests:
#   - apps/solarsage/tests/test_houses.py
# END_MODULE_MAP: M-SIDECAR-HOUSES

from __future__ import annotations


# START_BLOCK: HOUSE_FINDER
def find_house(longitude: float, cusps: list[float]) -> int | None:
    # START_FUNCTION_CONTRACT: M-SIDECAR-HOUSES.find_house
    # purpose: Map longitude to house number 1..12 using 12 cusps.
    # inputs: longitude (float), cusps (list[float])
    # returns: int (1..12) or None
    # side_effects: none
    # emitted_logs: none
    # error_behavior: returns None on invalid inputs
    # END_FUNCTION_CONTRACT: M-SIDECAR-HOUSES.find_house
    if not cusps or len(cusps) != 12:
        return None

    lon = longitude % 360.0

    for i in range(12):
        cusp_current = cusps[i] % 360.0
        cusp_next = cusps[(i + 1) % 12] % 360.0
        house_num = i + 1

        if cusp_current <= cusp_next:
            if cusp_current <= lon < cusp_next:
                return house_num
        else:
            # Wrap-around case (e.g. cusp_current = 350.0, cusp_next = 20.0)
            if lon >= cusp_current or lon < cusp_next:
                return house_num

    return None
# END_BLOCK: HOUSE_FINDER
