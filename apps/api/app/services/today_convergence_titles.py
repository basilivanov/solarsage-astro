# ############################################################################
# AI_HEADER: MODULE_TODAY_CONVERGENCE_TITLES — human titles for deterministic event units.
# ROLE: Adapts normalized snapshot units to the existing localized title builder
#       and returns null when a truthful public title cannot be established.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-TITLES
# purpose: Build safe localized titles for Today convergence drilldown events.
# owns:
#   - apps/api/app/services/today_convergence_titles.py
# inputs: normalized factor-unit mappings from a published snapshot.
# outputs: localized title string or None.
# dependencies: focus_title_builder and narrative_sanitizer.
# side_effects: none; pure calculation.
# emitted_logs: none.
# invariants: raw prefixes and machine identifiers never leave this boundary.
# failure_policy: unknown or incomplete drivers return None.
# END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-TITLES

# START_MODULE_MAP: M-TODAY-CONVERGENCE-TITLES
# public_entrypoints:
#   - build_today_convergence_event_title
# semantic_blocks:
#   - DRIVER_ELIGIBILITY: identify a real normalized planet/aspect/structural driver.
#   - TITLE_PROJECTION: localize and sanitize the deterministic title.
# owned_tests:
#   - apps/api/tests/test_today_convergence_titles.py
# END_MODULE_MAP: M-TODAY-CONVERGENCE-TITLES

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.services.focus_title_builder import (
    ANGLE_LABELS_RU,
    LOT_LABELS_RU,
    PLANET_NOMINATIVE_RU,
    build_event_title,
    check_public_title_eligibility,
)
from app.services.narrative_sanitizer import sanitize_narrative_text
from app.services.astro_utils import strip_prefix


_STRUCTURAL_TARGET_TYPES = frozenset({"house", "angle", "lot"})
_SLOW_TECHNIQUES = frozenset({
    "firdar",
    "profection",
    "return",
    "solar_return",
    "lunar_return",
})


def _normalized_key(value: object) -> str:
    return strip_prefix(str(value).strip()).upper() if value is not None else ""


# START_BLOCK: DRIVER_ELIGIBILITY
def _has_honest_driver(unit: Mapping[str, Any]) -> bool:
    source = _normalized_key(unit.get("source_key"))
    target = _normalized_key(unit.get("target_key"))
    target_type = str(unit.get("target_type") or "").casefold()
    aspect = str(unit.get("aspect_type") or "").strip()
    technique = str(
        unit.get("technique")
        or unit.get("technique_family")
        or unit.get("technique_horizon")
        or ""
    ).casefold()

    source_is_planet = source in PLANET_NOMINATIVE_RU
    target_is_named = (
        target in PLANET_NOMINATIVE_RU
        or target in ANGLE_LABELS_RU
        or target in LOT_LABELS_RU
    )
    structural_target = target_type in _STRUCTURAL_TARGET_TYPES and bool(
        target or unit.get("house") is not None
    )

    if aspect:
        return source_is_planet and (target_is_named or structural_target)
    if technique in _SLOW_TECHNIQUES:
        return source_is_planet or target_is_named
    return source_is_planet or target_is_named or structural_target
# END_BLOCK: DRIVER_ELIGIBILITY


# START_BLOCK: TITLE_PROJECTION
def build_today_convergence_event_title(unit: Mapping[str, Any]) -> str | None:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-TITLES.build_today_convergence_event_title
    # purpose: Build one localized title from a normalized factor unit.
    # inputs: unit — snapshot factor unit with normalized source/target/aspect fields.
    # returns: safe human title, or None when the driver is not honest to describe.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: malformed/non-mapping input returns None.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-TITLES.build_today_convergence_event_title
    if not isinstance(unit, Mapping) or not _has_honest_driver(unit):
        return None

    factor = dict(unit)
    # CanonicalUnit stores the family in technique_horizon; the title builder
    # accepts the older technique/technique_family names as well.
    factor.setdefault("technique", factor.get("technique_horizon"))
    factor.setdefault("technique_family", factor.get("technique_horizon"))
    human_title, _technical_title = build_event_title(factor)
    clean_title = sanitize_narrative_text(human_title)
    if clean_title is None or check_public_title_eligibility(clean_title) is not None:
        return None
    if clean_title.casefold() in {"планета", "планета планета", "жребий"}:
        return None
    return clean_title
# END_BLOCK: TITLE_PROJECTION


__all__ = ["build_today_convergence_event_title"]
