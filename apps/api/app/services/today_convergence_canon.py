# ############################################################################
# AI_HEADER: MODULE_TODAY_CONVERGENCE_CANON — strict frozen W1 canon boundary.
# ROLE: Loads the production convergence canon and exposes typed fail-closed policy helpers.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-CANON
# purpose: Load the frozen Today Convergence and aspect canons without legacy or reference-analysis imports.
# owns:
#   - apps/api/app/services/today_convergence_canon.py
# inputs: grace/canon/today_convergence.v1.yml and grace/canon/aspect_rules.v1.yml.
# outputs: immutable TodayConvergenceCanon and pure mapping/significance/eligibility helpers.
# dependencies: PyYAML and Python standard library only.
# side_effects: reads two YAML files; never writes or emits runtime logs.
# emitted_logs: none.
# invariants: frozen versions are exact; unknown mappings and normative values fail closed; no defaults/fallbacks.
# failure_policy: TodayConvergenceCanonError for missing, malformed, or unknown canon values.
# END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-CANON

# START_MODULE_MAP: M-TODAY-CONVERGENCE-CANON
# public_entrypoints:
#   - TodayConvergenceCanon
#   - TodayConvergenceCanonError
#   - load_today_convergence_canon
#   - map_factor_to_product_spheres
#   - aspect_weight
#   - source_max_orb
#   - event_class_significance
#   - is_fast_source
#   - is_rare_source
#   - hero_confirmation_policy
# semantic_blocks:
#   - CANON_LOADER: strict YAML loading and immutable typed extraction.
#   - CANON_POLICY: fail-closed sphere, threshold, source, event-class, and eligibility helpers.
# owned_tests:
#   - apps/api/tests/test_today_convergence_canon.py
# END_MODULE_MAP: M-TODAY-CONVERGENCE-CANON

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import yaml


# START_BLOCK: CANON_LOADER
class TodayConvergenceCanonError(ValueError):
    """Raised when frozen W1 canon cannot be loaded without ambiguity."""


_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_CANON_DIR = _REPO_ROOT / "grace" / "canon"
_TODAY_FILENAME = "today_convergence.v1.yml"
_ASPECT_FILENAME = "aspect_rules.v1.yml"
_RARE_TRANSIT_SOURCES = frozenset({"JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO"})


@dataclass(frozen=True)
class TodayConvergenceCanon:
    schema_version: str
    status: str
    formula_version: str
    canonical_spheres: tuple[str, ...]
    technical_to_product: Mapping[str, tuple[str, ...]]
    technical_alias_to_product: Mapping[str, tuple[str, ...]]
    planet_to_product: Mapping[str, tuple[str, ...]]
    max_planet_spheres: int
    aspect_weights: Mapping[str, float]
    orb_profile: Mapping[str, float]
    aspect_weight_min: float
    orb_ratio_max: float
    event_classes: Mapping[str, bool]
    fast_sources: frozenset[str]
    fast_policy: Mapping[str, bool]
    slow_sources: frozenset[str]
    rare_transit_sources: frozenset[str]
    slow_policy: Mapping[str, bool]
    rare_anchor_event_classes: frozenset[str]
    rare_anchor_excluded: frozenset[str]
    driver_rules: Mapping[str, str]
    hero_target_types: frozenset[str]


def _fail(reason: str) -> None:
    raise TodayConvergenceCanonError(f"today_convergence_canon:{reason}")


def _read_yaml(path: Path, label: str) -> Mapping[str, Any]:
    if not path.exists() or not path.is_file():
        _fail(f"{label}_missing:{path}")
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - parser-specific detail
        raise TodayConvergenceCanonError(f"today_convergence_canon:{label}_yaml") from exc
    if not isinstance(value, Mapping):
        _fail(f"{label}_mapping")
    return value


def _require_mapping(value: Any, reason: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(reason)
    return value


def _require_keys(value: Mapping[str, Any], keys: set[str], reason: str) -> None:
    if set(value) != keys:
        _fail(reason)


def _text(value: Any, reason: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(reason)
    return value.strip()


def _finite_number(value: Any, reason: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        _fail(reason)
    return float(value)


def _bounded_number(value: Any, reason: str) -> float:
    number = _finite_number(value, reason)
    if not 0.0 <= number <= 1.0:
        _fail(reason)
    return number


def _string_tuple(value: Any, reason: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        _fail(reason)
    result = tuple(_text(item, reason) for item in value)
    if not result or len(result) != len(set(result)):
        _fail(reason)
    return result


def _mapping_of_strings(value: Any, reason: str) -> dict[str, tuple[str, ...]]:
    mapping = _require_mapping(value, reason)
    result: dict[str, tuple[str, ...]] = {}
    for raw_key, raw_values in mapping.items():
        key = _text(raw_key, reason)
        result[key] = _string_tuple(raw_values, reason)
    return result


def _normal_source(value: str | None) -> str | None:
    if value is None:
        return None
    key = str(value).strip().upper()
    for prefix in ("TRANSIT_", "NATAL_"):
        if key.startswith(prefix):
            key = key[len(prefix):]
    return key or None


def _normal_key(value: str | None) -> str | None:
    if value is None:
        return None
    key = str(value).strip().upper()
    for prefix in ("TRANSIT_", "NATAL_"):
        if key.startswith(prefix):
            key = key[len(prefix):]
    return key or None


def _normal_event_class(value: str | None) -> str | None:
    if value is None:
        return None
    value = str(value).strip().lower()
    return value or None


def _normal_technique_family(value: str | None) -> str | None:
    if value is None:
        return None
    value = str(value).strip().lower()
    return value or None


def load_today_convergence_canon(canon_dir: Path | None = None) -> TodayConvergenceCanon:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.load_today_convergence_canon
    # purpose: Load and validate the frozen Today Convergence and aspect YAML pair.
    # inputs: canon_dir — directory containing both normative YAML files; repository canon by default.
    # returns: immutable TodayConvergenceCanon.
    # side_effects: reads YAML files only.
    # emitted_logs: none.
    # error_behavior: raises TodayConvergenceCanonError on any missing/malformed/unknown value.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.load_today_convergence_canon
    directory = canon_dir or _DEFAULT_CANON_DIR
    if directory.is_file():
        today_path = directory
        directory = directory.parent
    else:
        today_path = directory / _TODAY_FILENAME
    aspect_path = directory / _ASPECT_FILENAME
    today = _read_yaml(today_path, "today")
    aspect = _read_yaml(aspect_path, "aspect")

    _require_keys(
        today,
        {
            "schema_version", "status", "description", "formula_version", "significance",
            "eligibility", "rare_anchor_eligible", "rare_anchor_excluded", "independence",
            "background", "grouping", "hero_rule", "sphere_projection", "states",
            "content_states", "evidence_levels", "day_tone", "canonical_event", "inputs",
            "birth_time", "measured", "owner_decisions", "tone_policy",
        },
        "today_top_keys",
    )
    if today.get("schema_version") != "today_convergence.v1":
        _fail("schema_version")
    if today.get("status") != "frozen_w1":
        _fail("status")
    if today.get("formula_version") != "today-convergence-2":
        _fail("formula_version")

    canonical_event = _require_mapping(today["canonical_event"], "canonical_event")
    _require_keys(
        canonical_event,
        {"identity", "producer_precedence", "strip_prefixes", "daydelta_contract"},
        "canonical_event_keys",
    )
    if canonical_event["identity"] != "versioned_hash(normalized_physical_fields + event_window)":
        _fail("canonical_event_identity")
    if canonical_event["producer_precedence"] != ["activation", "day_signal"]:
        _fail("canonical_event_precedence")
    if canonical_event["strip_prefixes"] != ["Transit_", "Natal_"]:
        _fail("canonical_event_prefixes")
    if canonical_event["daydelta_contract"] != "semantic_keys":
        _fail("canonical_event_daydelta")

    background = _require_mapping(today["background"], "background")
    _require_keys(background, {"in_groups"}, "background_keys")
    if background["in_groups"] is not False:
        _fail("background_in_groups")

    significance = _require_mapping(today["significance"], "significance_mapping")
    _require_keys(significance, {"aspect_weight_min", "orb_ratio_max", "event_class"}, "significance_keys")
    aspect_weight_min = _bounded_number(significance["aspect_weight_min"], "aspect_weight_min")
    orb_ratio_max = _bounded_number(significance["orb_ratio_max"], "orb_ratio_max")
    event_classes_raw = _require_mapping(significance["event_class"], "event_class_mapping")
    event_classes: dict[str, bool] = {}
    for raw_key, raw_value in event_classes_raw.items():
        key = _normal_event_class(_text(raw_key, "event_class_key"))
        value = _require_mapping(raw_value, "event_class_rule")
        _require_keys(value, {"significant"}, "event_class_rule_keys")
        if not isinstance(value["significant"], bool):
            _fail("event_class_significance")
        assert key is not None
        event_classes[key] = value["significant"]

    eligibility = _require_mapping(today["eligibility"], "eligibility_mapping")
    _require_keys(eligibility, {"fast_sources", "fast", "slow"}, "eligibility_keys")
    fast_sources = frozenset(_normal_source(value) for value in _string_tuple(eligibility["fast_sources"], "fast_sources"))
    if None in fast_sources:
        _fail("fast_sources")
    fast_policy_raw = _require_mapping(eligibility["fast"], "fast_policy")
    slow_policy_raw = _require_mapping(eligibility["slow"], "slow_policy")
    _require_keys(fast_policy_raw, {"impulse", "evidence", "rare_anchor", "hero_confirmation"}, "fast_policy_keys")
    _require_keys(slow_policy_raw, {"impulse", "evidence", "rare_anchor", "hero_confirmation"}, "slow_policy_keys")
    for policy in (fast_policy_raw, slow_policy_raw):
        if any(not isinstance(policy[key], bool) for key in policy):
            _fail("eligibility_boolean")
    if dict(fast_policy_raw) != {
        "impulse": True,
        "evidence": True,
        "rare_anchor": False,
        "hero_confirmation": False,
    }:
        _fail("fast_policy_truth_table")
    if dict(slow_policy_raw) != {
        "impulse": True,
        "evidence": True,
        "rare_anchor": True,
        "hero_confirmation": True,
    }:
        _fail("slow_policy_truth_table")

    rare_anchor_event_classes = frozenset(
        _normal_event_class(value) for value in _string_tuple(today["rare_anchor_eligible"], "rare_anchor_eligible")
    )
    rare_anchor_excluded = frozenset(
        _normal_event_class(value) for value in _string_tuple(today["rare_anchor_excluded"], "rare_anchor_excluded")
    )
    if None in rare_anchor_event_classes or None in rare_anchor_excluded:
        _fail("rare_anchor_class")

    independence = _require_mapping(today["independence"], "independence_mapping")
    _require_keys(independence, {"rule", "driver_key", "note"}, "independence_keys")
    if independence["rule"] != "distinct_driver":
        _fail("independence_rule")
    driver_rules_raw = _require_mapping(independence["driver_key"], "driver_key_mapping")
    _require_keys(driver_rules_raw, {"transit", "timelord"}, "driver_key_keys")
    driver_rules = {key: _text(driver_rules_raw[key], "driver_key_value") for key in driver_rules_raw}
    if driver_rules["transit"] != "source_planet":
        _fail("driver_transit")
    if driver_rules["timelord"] != "technique_family":
        _fail("driver_timelord")

    grouping = _require_mapping(today["grouping"], "grouping_mapping")
    _require_keys(grouping, {"rule", "link", "hero_target_types"}, "grouping_keys")
    if grouping["rule"] != "direct_star":
        _fail("grouping_rule")
    if grouping["link"] != ["shared_target_key", "theme_intersection"]:
        _fail("grouping_link")
    hero_target_types = frozenset(_string_tuple(grouping["hero_target_types"], "hero_target_types"))

    sphere = _require_mapping(today["sphere_projection"], "sphere_projection_mapping")
    _require_keys(
        sphere,
        {"rule", "primary", "secondary_max", "fail_unmapped", "canonical_order", "technical_to_product",
         "technical_alias_to_product", "planet_to_product", "planet_sphere_limits"},
        "sphere_projection_keys",
    )
    if sphere["rule"] != "group_to_spheres":
        _fail("sphere_projection_rule")
    if sphere["primary"] != "majority_anchor_tiebreak":
        _fail("sphere_projection_primary")
    if not isinstance(sphere["secondary_max"], int) or isinstance(sphere["secondary_max"], bool) or sphere["secondary_max"] != 1:
        _fail("sphere_projection_secondary")
    if sphere["fail_unmapped"] is not True:
        _fail("sphere_projection_unmapped")
    canonical_spheres = _string_tuple(sphere["canonical_order"], "canonical_order")
    valid_spheres = frozenset(canonical_spheres)
    technical_to_product = _mapping_of_strings(sphere["technical_to_product"], "technical_to_product")
    technical_alias_to_product = _mapping_of_strings(sphere["technical_alias_to_product"], "technical_alias_to_product")
    planet_to_product = {
        _normal_source(key): values
        for key, values in _mapping_of_strings(sphere["planet_to_product"], "planet_to_product").items()
    }
    if None in planet_to_product:
        _fail("planet_key")
    for mapping in (technical_to_product, technical_alias_to_product, planet_to_product):
        if any(set(values) - valid_spheres for values in mapping.values()):
            _fail("sphere")
    limits = _require_mapping(sphere["planet_sphere_limits"], "planet_sphere_limits")
    _require_keys(limits, {"max_spheres_per_planet", "decisions"}, "planet_sphere_limits_keys")
    max_planet_spheres = limits["max_spheres_per_planet"]
    if not isinstance(max_planet_spheres, int) or max_planet_spheres <= 0:
        _fail("max_planet_spheres")
    if any(len(values) > max_planet_spheres for values in planet_to_product.values()):
        _fail("planet_sphere_limit")

    _require_keys(
        aspect,
        {"schema_version", "description", "orb_profile_default", "aspect_weights", "benefic_softening",
         "aspect_threshold", "convergence_curve", "technique_families", "dominance_cap",
         "planet_velocity_class", "velocity_factor"},
        "aspect_top_keys",
    )
    if aspect.get("schema_version") != "aspect_rules.v1":
        _fail("aspect_schema_version")
    aspect_threshold = _require_mapping(aspect["aspect_threshold"], "aspect_threshold")
    _require_keys(aspect_threshold, {"major", "minor", "description"}, "aspect_threshold_keys")
    _bounded_number(aspect_threshold["major"], "aspect_threshold")
    _bounded_number(aspect_threshold["minor"], "aspect_threshold")
    aspect_weights_raw = _require_mapping(aspect["aspect_weights"], "aspect_weights")
    aspect_weights = {
        _text(key, "aspect_key").upper(): _bounded_number(value, "aspect_weight")
        for key, value in aspect_weights_raw.items()
    }
    orb_raw = _require_mapping(aspect["orb_profile_default"], "orb_profile")
    orb_profile = {
        _normal_source(_text(key, "orb_source")): _finite_number(value, "orb_value")
        for key, value in orb_raw.items()
    }
    if not orb_profile:
        _fail("orb_profile")
    if None in orb_profile or any(value <= 0 for value in orb_profile.values()):
        _fail("orb_value")
    if not _RARE_TRANSIT_SOURCES.issubset(orb_profile):
        _fail("rare_transit_sources")
    velocity = _require_mapping(aspect["planet_velocity_class"], "velocity_class")
    _require_keys(velocity, {"description", "fast", "medium", "slow"}, "velocity_class_keys")
    slow_sources = frozenset(_normal_source(value) for value in _string_tuple(velocity["slow"], "slow_sources"))
    if None in slow_sources:
        _fail("slow_sources")

    return TodayConvergenceCanon(
        schema_version="today_convergence.v1",
        status="frozen_w1",
        formula_version="today-convergence-2",
        canonical_spheres=canonical_spheres,
        technical_to_product=MappingProxyType({key.lower(): value for key, value in technical_to_product.items()}),
        technical_alias_to_product=MappingProxyType({key.lower(): value for key, value in technical_alias_to_product.items()}),
        planet_to_product=MappingProxyType({key: value for key, value in planet_to_product.items()}),
        max_planet_spheres=max_planet_spheres,
        aspect_weights=MappingProxyType(aspect_weights),
        orb_profile=MappingProxyType(orb_profile),
        aspect_weight_min=aspect_weight_min,
        orb_ratio_max=orb_ratio_max,
        event_classes=MappingProxyType(event_classes),
        fast_sources=frozenset(value for value in fast_sources if value is not None),
        fast_policy=MappingProxyType(dict(fast_policy_raw)),
        slow_sources=frozenset(value for value in slow_sources if value is not None),
        rare_transit_sources=_RARE_TRANSIT_SOURCES,
        slow_policy=MappingProxyType(dict(slow_policy_raw)),
        rare_anchor_event_classes=frozenset(value for value in rare_anchor_event_classes if value is not None),
        rare_anchor_excluded=frozenset(value for value in rare_anchor_excluded if value is not None),
        driver_rules=MappingProxyType(driver_rules),
        hero_target_types=hero_target_types,
    )
# END_BLOCK: CANON_LOADER


# START_BLOCK: CANON_POLICY
def map_factor_to_product_spheres(
    canon: TodayConvergenceCanon,
    technical_spheres: Sequence[str] | None = None,
    source_key: str | None = None,
    target_key: str | None = None,
) -> tuple[str, ...]:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.map_factor_to_product_spheres
    # purpose: Map one physical/technical factor through frozen sphere maps without fallback.
    # inputs: canon plus optional technical, source, and target keys.
    # returns: canonical-order product spheres; empty tuple for unknown/unmapped factors.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: unknown keys are ignored and remain unmapped.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.map_factor_to_product_spheres
    mapped: set[str] = set()
    if technical_spheres is None or isinstance(technical_spheres, (str, bytes)) or not isinstance(technical_spheres, Sequence):
        technical_values: Sequence[str] = ()
    else:
        technical_values = technical_spheres
    for value in technical_values:
        key = str(value).strip().lower()
        mapped.update(canon.technical_to_product.get(key, ()))
        mapped.update(canon.technical_alias_to_product.get(key, ()))
    for value in (source_key, target_key):
        key = _normal_source(value)
        if key is not None:
            mapped.update(canon.planet_to_product.get(key, ()))
    return tuple(sphere for sphere in canon.canonical_spheres if sphere in mapped)


def aspect_weight(canon: TodayConvergenceCanon, aspect_type: str | None) -> float | None:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.aspect_weight
    # purpose: Return an explicit frozen aspect weight.
    # inputs: canon and case-insensitive aspect key.
    # returns: known weight or None for unknown aspect.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: unknown aspect returns None.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.aspect_weight
    if aspect_type is None:
        return None
    value = canon.aspect_weights.get(str(aspect_type).strip().upper())
    return value if value is not None and 0.0 <= value <= 1.0 and isfinite(value) else None


def source_max_orb(canon: TodayConvergenceCanon, source_key: str | None) -> float | None:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.source_max_orb
    # purpose: Return the explicit source max-orb from aspect_rules canon.
    # inputs: canon and source key with optional Transit_/Natal_ prefix.
    # returns: explicit max-orb or None; never a fallback.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: unknown source returns None.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.source_max_orb
    key = _normal_source(source_key)
    value = canon.orb_profile.get(key) if key is not None else None
    return value if value is not None and value > 0.0 and isfinite(value) else None


def event_class_significance(canon: TodayConvergenceCanon, event_class: str | None) -> bool | None:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.event_class_significance
    # purpose: Resolve non-aspect event-class significance without auto-pass.
    # inputs: canon and event class.
    # returns: True/False for explicit canon rules, None for unknown classes.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: unknown class returns None.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.event_class_significance
    key = _normal_event_class(event_class)
    return canon.event_classes.get(key) if key is not None else None


def is_fast_source(canon: TodayConvergenceCanon, source_key: str | None) -> bool:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.is_fast_source
    # purpose: Check frozen fast-source policy.
    # inputs: canon and source key.
    # returns: True only for explicit fast sources.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: unknown source returns False.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.is_fast_source
    key = _normal_source(source_key)
    return key in canon.fast_sources if key is not None else False


def is_rare_source(
    canon: TodayConvergenceCanon,
    source_key: str | None,
    *,
    technique_family: str | None = None,
    event_class: str | None = None,
    aspect_type: str | None = None,
) -> bool:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.is_rare_source
    # purpose: Resolve rare-anchor eligibility only after explicit significance is known.
    # inputs: canon, source, technique family, optional event class/aspect.
    # returns: True only for canon-significant rare source/class combinations.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: unknown event classes/aspects return False.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.is_rare_source
    event_key = _normal_event_class(event_class)
    if event_key is not None:
        if event_class_significance(canon, event_key) is not True:
            return False
        if event_key in canon.rare_anchor_excluded:
            return False
        if event_key in canon.rare_anchor_event_classes:
            return True
    family = _normal_technique_family(technique_family)
    source = _normal_source(source_key)
    if family == "transit" and source in canon.rare_transit_sources and aspect_weight(canon, aspect_type) is not None:
        return True
    return False


def hero_confirmation_policy(
    canon: TodayConvergenceCanon,
    source_key: str | None,
    *,
    technique_family: str | None = None,
    event_class: str | None = None,
) -> bool:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.hero_confirmation_policy
    # purpose: Resolve the frozen hero-confirmation policy without making structural unknowns eligible.
    # inputs: canon, source, technique family, and optional event class.
    # returns: True for explicit fast/slow/time-lord confirmation policy.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: unknown structural/event classes return False.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.hero_confirmation_policy
    event_key = _normal_event_class(event_class)
    if event_key is not None and event_class_significance(canon, event_key) is not True:
        return False
    if is_fast_source(canon, source_key):
        return bool(canon.fast_policy["hero_confirmation"])
    family = _normal_technique_family(technique_family)
    if family in {"firdar", "profection", "timelord"}:
        return True
    source = _normal_source(source_key)
    if source in canon.slow_sources:
        return bool(canon.slow_policy["hero_confirmation"])
    if source in canon.rare_transit_sources:
        return True
    return source in {"SUN", "MARS"}


__all__ = [
    "TodayConvergenceCanon",
    "TodayConvergenceCanonError",
    "load_today_convergence_canon",
    "map_factor_to_product_spheres",
    "aspect_weight",
    "source_max_orb",
    "event_class_significance",
    "is_fast_source",
    "is_rare_source",
    "hero_confirmation_policy",
]
# END_BLOCK: CANON_POLICY
