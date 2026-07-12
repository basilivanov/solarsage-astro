# ############################################################################
# AI_HEADER: HORIZON_CONTENT_CANON_TYPES — shared closed types and structural helpers for B2B1 canons.
# ROLE: Keeps copy-agnostic aliases and validation mechanics separate from content-canon models.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-CONTENT-CANON-TYPES
# purpose: Provide re-exportable closed aliases, structural constants, and safe validation helpers.
# owns:
#   - apps/api/app/schemas/horizon_content_canon_types.py
# inputs: Parsed machine identifiers and numeric canon values.
# outputs: Frozen base model, literals, canonical orders, regexes, and structural validators.
# dependencies: math/re/typing stdlib, pydantic, B2A schema constants.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Helpers never own Russian copy policy.
#   - Closed aliases and canonical orders remain deterministic.
# failure_policy: raises ValueError for invalid structural values.
# END_MODULE_CONTRACT: M-HORIZON-CONTENT-CANON-TYPES

# START_MODULE_MAP: M-HORIZON-CONTENT-CANON-TYPES
# public_entrypoints:
#   - HorizonContentCanonModel
#   - HorizonThemeKey
#   - PersonalFactKind
# semantic_blocks:
#   - HORIZON_CONTENT_CLOSED_TYPES: literals and orders.
#   - HORIZON_CONTENT_STRUCTURAL_HELPERS: copy-agnostic checks.
# owned_tests:
#   - apps/api/tests/test_horizon_language_canon.py
#   - apps/api/tests/test_horizon_actions_canon.py
#   - apps/api/tests/test_personal_patterns_canon.py
# END_MODULE_MAP: M-HORIZON-CONTENT-CANON-TYPES

# START_BLOCK: HORIZON_CONTENT_CLOSED_TYPES
from __future__ import annotations

import math
import re
from typing import Iterable, Literal, get_args

from pydantic import BaseModel, ConfigDict

from app.schemas.horizon_canon import HORIZON_IDS, KNOWN_TECHNIQUES, PUBLIC_PRODUCT_SPHERES
from app.schemas.today_horizons import (
    TodayV2HorizonTone,
    TodayV2ProductSphereKey,
    TodayV2TimingState,
)

THEME_KEYS = tuple(
    "communication_learning_documents structure_boundaries_control relationships_values_closeness resources_security "
    "energy_body_pacing home_belonging inner_clarity_recovery direction_growth_meaning creativity_visibility "
    "change_innovation".split()
)
HorizonThemeKey = Literal[*THEME_KEYS]
PersonalFactKind = Literal["strength", "risk", "profile", "natal", "sphere"]
ClaimSafetyClass = Literal[
    "reflection",
    "reversible_experiment",
    "low_stakes_communication",
    "pacing",
    "guardrail",
]
PositiveActionIntent = Literal[
    "reflect",
    "plan",
    "clarify",
    "small_experiment",
    "communicate_boundary",
    "reduce_load",
    "create_draft",
    "record_observation",
]
AvoidActionIntent = Literal[
    "postpone_major_decision",
    "avoid_escalation",
    "avoid_overcommitment",
    "avoid_all_at_once",
    "avoid_assumption",
    "avoid_extra_intensity",
]
ActionIntent = PositiveActionIntent | AvoidActionIntent
ForbiddenPolicyIntent = Literal[
    "immediate_major_decision",
    "increase_commitment",
    "escalate",
    "replace_everything",
    "increase_intensity",
]
HorizonSphereVerdict = Literal["good", "neutral", "caution", "avoid"]
PRODUCT_SPHERE_ORDER: tuple[TodayV2ProductSphereKey, ...] = get_args(TodayV2ProductSphereKey)
TIMING_STATES: tuple[TodayV2TimingState, ...] = get_args(TodayV2TimingState)
HORIZON_SELECTION_TECHNIQUES: frozenset[str] = KNOWN_TECHNIQUES - {"primary_direction"}
TONES: tuple[TodayV2HorizonTone, ...] = ("supportive", "neutral", "tense", "mixed")
VERDICTS: tuple[HorizonSphereVerdict, ...] = ("good", "neutral", "caution", "avoid")
PLANET_ORDER: tuple[str, ...] = tuple("SUN MOON MERCURY VENUS MARS JUPITER SATURN URANUS NEPTUNE PLUTO".split())
SIGN_KEYS: frozenset[str] = frozenset(
    "ARIES TAURUS GEMINI CANCER LEO VIRGO LIBRA SCORPIO SAGITTARIUS CAPRICORN AQUARIUS PISCES".split()
)
ASPECT_TYPES: frozenset[str] = frozenset({"CONJUNCTION", "SEXTILE", "SQUARE", "TRINE", "OPPOSITION"})
PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")
BRACE_RE = re.compile(r"[{}]")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")
STATEMENT_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
ALLOWED_PLACEHOLDERS: frozenset[str] = frozenset(
    "active_from active_until exact_at range_label peak_label state_label theme_label sphere_label target_label source_label".split()
)


class HorizonContentCanonModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


# END_BLOCK: HORIZON_CONTENT_CLOSED_TYPES


# START_BLOCK: HORIZON_CONTENT_STRUCTURAL_HELPERS
def _ensure_exact_keys(actual: set[str], expected: set[str], path: str) -> None:
    if actual != expected:
        raise ValueError(f"{path}: expected exact closed key set")


def _ensure_unique_non_blank(values: tuple[str, ...] | list[str], path: str) -> None:
    if any(not value.strip() for value in values) or len(values) != len(set(values)):
        raise ValueError(f"{path}: expected unique non-blank values")


def _ensure_finite(value: float, path: str, lower: float, upper: float) -> None:
    if not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError(f"{path}: expected finite value in canonical range")


def _normalize_copy(value: str) -> str:
    return " ".join(value.split()).casefold()


def _validate_copy(value: str, path: str) -> None:
    if not value.strip():
        raise ValueError(f"{path}: expected non-blank copy")


def _template_placeholders(value: str, path: str) -> tuple[str, ...]:
    placeholders = tuple(PLACEHOLDER_RE.findall(value))
    if BRACE_RE.search(PLACEHOLDER_RE.sub("", value)):
        raise ValueError(f"{path}: invalid template braces")
    return placeholders


def _contains_forbidden_copy(values: Iterable[str], fragments: Iterable[str]) -> bool:
    normalized_fragments = tuple(_normalize_copy(fragment) for fragment in fragments)
    return any(
        re.search(rf"(?<!\w){re.escape(fragment)}(?!\w)", _normalize_copy(value))
        for value in values
        for fragment in normalized_fragments
    )


def _canonical_pair(point_a: str, point_b: str) -> tuple[str, str]:
    if point_a not in PLANET_ORDER or point_b not in PLANET_ORDER or point_a == point_b:
        raise ValueError("predicate: expected two distinct known planets")
    return tuple(sorted((point_a, point_b), key=PLANET_ORDER.index))


__all__ = [
    "ALLOWED_PLACEHOLDERS",
    "ASPECT_TYPES",
    "ActionIntent",
    "AvoidActionIntent",
    "BRACE_RE",
    "ClaimSafetyClass",
    "ForbiddenPolicyIntent",
    "HORIZON_SELECTION_TECHNIQUES",
    "HorizonContentCanonModel",
    "HorizonSphereVerdict",
    "HorizonThemeKey",
    "ID_RE",
    "PLANET_ORDER",
    "PLACEHOLDER_RE",
    "PRODUCT_SPHERE_ORDER",
    "PersonalFactKind",
    "PositiveActionIntent",
    "SIGN_KEYS",
    "STATEMENT_KEY_RE",
    "THEME_KEYS",
    "TIMING_STATES",
    "TONES",
    "VERDICTS",
    "_canonical_pair",
    "_contains_forbidden_copy",
    "_ensure_exact_keys",
    "_ensure_finite",
    "_ensure_unique_non_blank",
    "_normalize_copy",
    "_template_placeholders",
    "_validate_copy",
]
# END_BLOCK: HORIZON_CONTENT_STRUCTURAL_HELPERS
