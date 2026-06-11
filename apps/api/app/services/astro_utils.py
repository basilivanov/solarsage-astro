# ############################################################################
# AI_HEADER: MODULE_ASTRO_UTILS
# ROLE: Shared astrological utilities — house finding, name normalization.
# DEPENDENCIES: typing
# GRACE_ANCHORS: [FIND_HOUSE, STRIP_PREFIX]
# ############################################################################

# START_MODULE_CONTRACT: M-ASTRO-UTILS
# purpose: Shared utility functions for house finding and planet name normalization.
# owns:
#   - apps/api/app/services/astro_utils.py
# inputs:
#   - longitude: float
#   - houses: list of dicts
#   - name: str | None
# outputs:
#   - int | None (house number)
#   - str (stripped planet name)
# dependencies:
#   - none (pure functions)
# side_effects:
#   - none (pure functions)
# invariants:
#   - find_house handles wraparound correctly
#   - strip_prefix removes Transit_/Natal_ prefix
# failure_policy:
#   - returns None if houses list is empty
#   - returns "" if name is None
# END_MODULE_CONTRACT: M-ASTRO-UTILS

# START_MODULE_MAP: M-ASTRO-UTILS
# public_entrypoints:
#   - find_house
#   - strip_prefix
# semantic_blocks:
#   - FIND_HOUSE: find which house a longitude falls into
#   - STRIP_PREFIX: strip Transit_/Natal_ prefix from planet name
# END_MODULE_MAP: M-ASTRO-UTILS

from typing import Any


def find_house(longitude: float, houses: list[dict[str, Any]]) -> int | None:
    """Find which natal house a longitude falls into.

    Houses may be in any order — sorts by cusp ascending before lookup.
    Handles wrap-around (e.g., house spanning 350°→10°).

    Returns None if houses list is empty, otherwise always returns a house number.
    """
    if not houses:
        return None

    sorted_houses = sorted(houses, key=lambda h: float(h.get("cusp", 0)))

    for i, h in enumerate(sorted_houses):
        next_h = sorted_houses[(i + 1) % len(sorted_houses)]
        cusp = float(h.get("cusp", 0))
        next_cusp = float(next_h.get("cusp", 0))

        if next_cusp > cusp:
            if cusp <= longitude < next_cusp:
                return int(h["number"])
        else:  # wraparound: e.g., house starts at 350°, ends at 10°
            if longitude >= cusp or longitude < next_cusp:
                return int(h["number"])

    # Fallback: should not reach here, but return first house
    return int(sorted_houses[0]["number"])


def strip_prefix(name: str | None) -> str:
    """Strip Transit_/Natal_ prefix from planet name."""
    if not name:
        return ""
    for prefix in ("Transit_", "Natal_"):
        if name.startswith(prefix):
            return name[len(prefix):]
    return name
