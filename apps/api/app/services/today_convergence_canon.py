# ############################################################################
# AI_HEADER: MODULE_TODAY_CONVERGENCE_CANON — strict frozen W1 canon boundary.
# ROLE: Loads the production convergence canon and exposes typed fail-closed policy helpers.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-CANON
# purpose: Load the frozen Today Convergence and aspect canons without legacy or reference-analysis imports.
# owns:
#   - apps/api/app/services/today_convergence_canon.py
# inputs: Today convergence, product-spheres, aspect-rules, and versioned
#   narrow-theme YAML canons.
# outputs: immutable TodayConvergenceCanon/TonePolicyCanon/ProductSphereCanon,
#   strict canon artifact fingerprints, and pure resolver/significance/
#   eligibility helpers.
# dependencies: PyYAML and Python standard library only.
# side_effects: reads four YAML files; never writes or emits runtime logs.
# emitted_logs: none.
# invariants: frozen versions are exact; unknown mappings and normative values fail closed; no defaults/fallbacks.
# failure_policy: TodayConvergenceCanonError for missing, malformed, or unknown canon values.
# END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-CANON

# START_MODULE_MAP: M-TODAY-CONVERGENCE-CANON
# public_entrypoints:
#   - TodayConvergenceCanon
#   - BirthTimeCanon
#   - BirthTimeCapabilities
#   - BirthTimeOrbMargin
#   - TonePolicyCanon
#   - TodayConvergenceCanonError
#   - load_today_convergence_canon
#   - compute_today_convergence_canon_hash
#   - resolve_product_sphere
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
from hashlib import sha256
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
_PRODUCT_SPHERES_FILENAME = "product_spheres.v1.yml"
_ASPECT_FILENAME = "aspect_rules.v1.yml"
_THEME_FILENAME = "today_convergence_themes.v1.yml"
_RARE_TRANSIT_SOURCES = frozenset({"JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO"})


@dataclass(frozen=True)
class TonePolicyCanon:
    """Immutable owner-approved tone policy extracted from the frozen YAML."""

    status: str
    version: str
    layers: tuple[str, ...]
    unit_polarities: tuple[str, ...]
    neutral_maps_to: str
    role_weights: Mapping[str, float]
    independence: str
    min_side_weight: float
    mixed_margin: float
    day_tones: tuple[str, ...]
    fresh_predicate: tuple[str, ...]
    ongoing_roles_are_context: tuple[str, ...]
    fast_sources_detail_only: frozenset[str]
    high_confidence_strength: float
    min_independent_tense_units: int
    min_independent_supportive_units: int
    mixed_requires_fresh_support_and_tense: bool
    audit_fields: tuple[str, ...]


@dataclass(frozen=True)
class BirthTimeCapabilities:
    """Frozen calculation capabilities for one persisted birth-time mode."""

    houses: bool
    angles: bool
    lots: bool
    exact_timing: bool


@dataclass(frozen=True)
class BirthTimeOrbMargin:
    """Frozen birth-time uncertainty margin policy."""

    rule: str
    gap_hours: Mapping[str, int]
    formula: str


@dataclass(frozen=True)
class BirthTimeCanon:
    """Immutable extraction of the canonical birth-time section."""

    modes: tuple[str, ...]
    buckets_local: Mapping[str, tuple[int, int]]
    control_grid: Mapping[str, str]
    orb_margin: BirthTimeOrbMargin
    gate: str
    capabilities: Mapping[str, BirthTimeCapabilities]
    migration: Mapping[str, str]


@dataclass(frozen=True)
class ProductFacetCanon:
    """Immutable product facet used by the deterministic sphere resolver."""

    key: str
    label: str
    houses: tuple[int, ...]
    technical_spheres: tuple[str, ...]
    required_context: tuple[str, ...]
    modifiers: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True)
class ProductSphereCanon:
    """Immutable product sphere and its ordered facet definitions."""

    key: str
    title: str
    description: str
    facets: tuple[ProductFacetCanon, ...]


@dataclass(frozen=True)
class TodayConvergenceCanon:
    schema_version: str
    status: str
    formula_version: str
    canonical_spheres: tuple[str, ...]
    product_schema_version: str
    product_status: str
    product_spheres: Mapping[str, ProductSphereCanon]
    projection_priority: tuple[str, ...]
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
    theme_schema_version: str
    theme_status: str
    theme_formula_version: str
    theme_canonical_order: tuple[str, ...]
    technical_sphere_themes: Mapping[str, tuple[str, ...]]
    target_planet_themes: Mapping[str, tuple[str, ...]]
    tone_policy: TonePolicyCanon
    birth_time: BirthTimeCanon


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


def _canon_artifact_paths(canon_dir: Path | None) -> tuple[Path, Path, Path, Path]:
    directory = _DEFAULT_CANON_DIR if canon_dir is None else canon_dir
    if directory.is_file():
        today_path = directory
        directory = directory.parent
    else:
        today_path = directory / _TODAY_FILENAME
    return (
        today_path,
        directory / _PRODUCT_SPHERES_FILENAME,
        directory / _ASPECT_FILENAME,
        directory / _THEME_FILENAME,
    )


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


def _exact_int(value: Any, expected: int, reason: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value != expected:
        _fail(reason)
    return value


def _string_tuple(value: Any, reason: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        _fail(reason)
    result = tuple(_text(item, reason) for item in value)
    if not result or len(result) != len(set(result)):
        _fail(reason)
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


def _normalized_theme_token(value: Any, reason: str) -> str:
    token = _text(value, reason)
    normalized = token.lower()
    if token != normalized or any(not (char.isalnum() or char == "_") for char in token):
        _fail(reason)
    return normalized


def _normalized_registry_key(value: Any, reason: str, *, uppercase: bool) -> str:
    token = _text(value, reason)
    normalized = token.upper() if uppercase else token.lower()
    if token != normalized or any(not (char.isalnum() or char == "_") for char in token):
        _fail(reason)
    if normalized.startswith(("TRANSIT_", "NATAL_")):
        _fail(reason)
    return normalized


def _theme_mapping(value: Any, reason: str, *, uppercase_keys: bool) -> dict[str, tuple[str, ...]]:
    mapping = _require_mapping(value, reason)
    if not mapping:
        _fail(reason)
    result: dict[str, tuple[str, ...]] = {}
    for raw_key, raw_values in mapping.items():
        key = _normalized_registry_key(raw_key, reason, uppercase=uppercase_keys)
        if key in result:
            _fail(reason)
        values = _string_tuple(raw_values, reason)
        normalized_values = tuple(_normalized_theme_token(item, reason) for item in values)
        if len(normalized_values) != len(set(normalized_values)):
            _fail(reason)
        result[key] = normalized_values
    return result


def _normalized_token_tuple(
    value: Any,
    reason: str,
    *,
    uppercase: bool = False,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    """Read a strict unique token list used by product-sphere metadata."""

    if allow_empty:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            _fail(reason)
        values = tuple(_text(item, reason) for item in value)
        if len(values) != len(set(values)):
            _fail(reason)
    else:
        values = _string_tuple(value, reason)
    result = tuple(item.upper() if uppercase else item.lower() for item in values)
    if result != values and any(
        (item.upper() if uppercase else item.lower()) != item for item in values
    ):
        _fail(reason)
    if any(any(not (char.isalnum() or char == "_") for char in item) for item in result):
        _fail(reason)
    return result


def _product_spheres_canon(value: Any) -> tuple[
    str,
    str,
    tuple[str, ...],
    Mapping[str, ProductSphereCanon],
    tuple[str, ...],
]:
    """Validate and materialize the single product sphere/facet canon."""

    product = _require_mapping(value, "product_mapping")
    _require_keys(
        product,
        {
            "schema_version", "status", "description", "canonical_order",
            "allowed_technical_spheres", "allowed_context_keys", "allowed_planets",
            "migration_aliases", "resolver", "spheres",
        },
        "product_top_keys",
    )
    if product.get("schema_version") != "product_spheres.v1":
        _fail("product_schema_version")
    if product.get("status") != "frozen_w1":
        _fail("product_status")
    _text(product["description"], "product_description")

    canonical_order = _normalized_token_tuple(product["canonical_order"], "product_canonical_order")
    expected_order = (
        "work", "finance", "documents", "relationships", "sport", "communication",
        "health", "home_family", "travel", "creativity", "study", "friends_goals",
    )
    if canonical_order != expected_order:
        _fail("product_canonical_order")

    technical_keys = _normalized_token_tuple(
        product["allowed_technical_spheres"], "product_technical_keys"
    )
    if technical_keys != (
        "thinking_speech_learning", "work_status_achievement", "relationships_partnership",
        "money_security_resources", "body_energy_health", "home_family_roots",
        "inner_background_unconscious", "crisis_transformation_control",
        "meaning_expansion_vector",
    ):
        _fail("product_technical_keys")
    context_keys = set(_normalized_token_tuple(product["allowed_context_keys"], "product_context_keys"))
    if not context_keys:
        _fail("product_context_keys")
    planets = _normalized_token_tuple(product["allowed_planets"], "product_planets", uppercase=True)
    if planets != ("SUN", "MOON", "MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO"):
        _fail("product_planets")

    migration_aliases = _require_mapping(product["migration_aliases"], "product_migration_aliases")
    if dict(migration_aliases) != {"money": "finance", "shopping": "finance"}:
        _fail("product_migration_aliases")

    resolver = _require_mapping(product["resolver"], "product_resolver")
    _require_keys(
        resolver,
        {"rule", "priority", "output", "unknown", "planet_only_narrow_facets"},
        "product_resolver_keys",
    )
    priority = _normalized_token_tuple(resolver["priority"], "product_resolver_priority")
    if priority != ("house", "technical_spheres", "explicit_context", "planets_tiebreak"):
        _fail("product_resolver_priority")
    if resolver["rule"] != "one_group_to_one_sphere":
        _fail("product_resolver_rule")
    if resolver["output"] != ["sphere", "facet_or_null"]:
        _fail("product_resolver_output")
    if resolver["unknown"] != "unresolved":
        _fail("product_resolver_unknown")
    if resolver["planet_only_narrow_facets"] != "forbidden":
        _fail("product_resolver_planet_only")

    spheres_raw = _require_mapping(product["spheres"], "product_spheres")
    if set(spheres_raw) != set(canonical_order):
        _fail("product_spheres_order")
    sphere_values: dict[str, ProductSphereCanon] = {}
    global_facets: set[str] = set()
    for raw_sphere_key in canonical_order:
        raw_sphere = _require_mapping(spheres_raw.get(raw_sphere_key), "product_sphere_mapping")
        _require_keys(raw_sphere, {"key", "title", "description", "facets"}, "product_sphere_keys")
        sphere_key = _normalized_token_tuple([raw_sphere["key"]], "product_sphere_key")[0]
        if sphere_key != raw_sphere_key:
            _fail("product_sphere_key")
        title = _text(raw_sphere["title"], "product_sphere_title")
        description = _text(raw_sphere["description"], "product_sphere_description")
        facets_raw = raw_sphere["facets"]
        if not isinstance(facets_raw, Sequence) or isinstance(facets_raw, (str, bytes)) or not facets_raw:
            _fail("product_facets")
        facets: list[ProductFacetCanon] = []
        facet_keys: set[str] = set()
        for raw_facet in facets_raw:
            facet = _require_mapping(raw_facet, "product_facet_mapping")
            required_facet_keys = {"key", "label", "houses", "modifiers"}
            allowed_facet_keys = required_facet_keys | {"technical_spheres", "required_context"}
            if not required_facet_keys.issubset(facet) or set(facet) - allowed_facet_keys:
                _fail("product_facet_keys")
            facet_key = _normalized_token_tuple([facet["key"]], "product_facet_key")[0]
            if facet_key in facet_keys or facet_key in global_facets:
                _fail("product_facet_unique")
            facet_keys.add(facet_key)
            global_facets.add(facet_key)
            label = _text(facet["label"], "product_facet_label")
            raw_houses = facet["houses"]
            if not isinstance(raw_houses, Sequence) or isinstance(raw_houses, (str, bytes)) or not raw_houses:
                _fail("product_facet_houses")
            houses = tuple(raw_houses)
            if any(
                isinstance(house, bool) or not isinstance(house, int) or not 1 <= house <= 12
                for house in houses
            ) or len(houses) != len(set(houses)):
                _fail("product_facet_houses")
            facet_technical = _normalized_token_tuple(
                facet.get("technical_spheres", []), "product_facet_technical", allow_empty=True
            )
            if set(facet_technical) - set(technical_keys):
                _fail("product_facet_technical_reference")
            required_context = _normalized_token_tuple(
                facet.get("required_context", []), "product_facet_context", allow_empty=True
            )
            if set(required_context) - context_keys:
                _fail("product_facet_context_reference")
            modifiers = _require_mapping(facet["modifiers"], "product_facet_modifiers")
            _require_keys(modifiers, {"planets"}, "product_facet_modifiers_keys")
            modifier_planets = _normalized_token_tuple(modifiers["planets"], "product_facet_planets", uppercase=True)
            if set(modifier_planets) - set(planets):
                _fail("product_facet_planet_reference")
            facets.append(
                ProductFacetCanon(
                    key=facet_key,
                    label=label,
                    houses=houses,
                    technical_spheres=facet_technical,
                    required_context=required_context,
                    modifiers=MappingProxyType({"planets": modifier_planets}),
                )
            )
        sphere_values[sphere_key] = ProductSphereCanon(
            key=sphere_key,
            title=title,
            description=description,
            facets=tuple(facets),
        )
    return product["schema_version"], product["status"], canonical_order, MappingProxyType(sphere_values), priority


def _birth_time_canon(value: Any) -> BirthTimeCanon:
    birth_time = _require_mapping(value, "birth_time_mapping")
    missing_reasons = {
        "modes": "birth_time_modes",
        "buckets_local": "birth_time_bucket_ranges",
        "control_grid": "birth_time_control_grid",
        "orb_margin": "birth_time_orb_margin",
        "gate": "birth_time_gate",
        "capabilities": "birth_time_capabilities",
        "migration": "birth_time_migration",
    }
    for key, reason in missing_reasons.items():
        if key not in birth_time:
            _fail(reason)
    _require_keys(
        birth_time,
        {"modes", "buckets_local", "control_grid", "orb_margin", "gate", "capabilities", "migration"},
        "birth_time_keys",
    )

    raw_modes = birth_time["modes"]
    if not isinstance(raw_modes, Sequence) or isinstance(raw_modes, (str, bytes)):
        _fail("birth_time_modes")
    modes = tuple(raw_modes)
    if modes != ("exact", "bucket", "unknown") or any(not isinstance(mode, str) for mode in modes):
        _fail("birth_time_modes")

    bucket_mapping = _require_mapping(birth_time["buckets_local"], "birth_time_bucket_ranges")
    _require_keys(bucket_mapping, {"night", "morning", "day", "evening"}, "birth_time_bucket_ranges")
    bucket_ranges: dict[str, tuple[int, int]] = {}
    for name in ("night", "morning", "day", "evening"):
        raw_range = bucket_mapping[name]
        if not isinstance(raw_range, Sequence) or isinstance(raw_range, (str, bytes)) or len(raw_range) != 2:
            _fail("birth_time_bucket_ranges")
        start, end = raw_range
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
            or not 0 <= start < end <= 24
        ):
            _fail("birth_time_bucket_ranges")
        bucket_ranges[name] = (start, end)
    if bucket_ranges != {
        "night": (0, 6),
        "morning": (6, 12),
        "day": (12, 18),
        "evening": (18, 24),
    }:
        _fail("birth_time_bucket_ranges")
    ordered_ranges = tuple(bucket_ranges.values())
    if ordered_ranges[0][0] != 0 or ordered_ranges[-1][1] != 24 or any(
        left[1] != right[0] for left, right in zip(ordered_ranges, ordered_ranges[1:])
    ):
        _fail("birth_time_bucket_ranges")

    control_grid = _require_mapping(birth_time["control_grid"], "birth_time_control_grid")
    _require_keys(control_grid, {"bucket", "unknown"}, "birth_time_control_grid")
    if dict(control_grid) != {
        "bucket": "edges_plus_middle",
        "unknown": "every_4h_plus_2359",
    }:
        _fail("birth_time_control_grid")

    orb_margin = _require_mapping(birth_time["orb_margin"], "birth_time_orb_margin")
    _require_keys(orb_margin, {"rule", "gap_hours", "formula"}, "birth_time_orb_margin")
    if orb_margin["rule"] != "canonical_fixed":
        _fail("birth_time_orb_margin_rule")
    gap_hours = _require_mapping(orb_margin["gap_hours"], "birth_time_orb_margin_gap_hours")
    _require_keys(gap_hours, {"bucket", "unknown"}, "birth_time_orb_margin_gap_hours")
    if (
        isinstance(gap_hours["bucket"], bool)
        or isinstance(gap_hours["unknown"], bool)
        or not isinstance(gap_hours["bucket"], int)
        or not isinstance(gap_hours["unknown"], int)
        or dict(gap_hours) != {"bucket": 3, "unknown": 4}
    ):
        _fail("birth_time_orb_margin_gap_hours")
    if orb_margin["formula"] != "speed(target_deg_per_hour) * gap_hours / max_orb(source)":
        _fail("birth_time_orb_margin_formula")
    if birth_time["gate"] != "published_sparse_subset_of_robust_dense":
        _fail("birth_time_gate")

    capabilities_raw = _require_mapping(birth_time["capabilities"], "birth_time_capabilities")
    _require_keys(capabilities_raw, set(modes), "birth_time_capabilities")
    capability_values: dict[str, BirthTimeCapabilities] = {}
    expected_capabilities = {
        "exact": {"houses": True, "angles": True, "lots": True, "exact_timing": True},
        "bucket": {"houses": False, "angles": False, "lots": False, "exact_timing": False},
        "unknown": {"houses": False, "angles": False, "lots": False, "exact_timing": False},
    }
    for mode in modes:
        raw_capabilities = _require_mapping(capabilities_raw[mode], "birth_time_capability_keys")
        _require_keys(raw_capabilities, {"houses", "angles", "lots", "exact_timing"}, "birth_time_capability_keys")
        if any(not isinstance(raw_capabilities[key], bool) for key in raw_capabilities):
            _fail("birth_time_capability_value")
        if dict(raw_capabilities) != expected_capabilities[mode]:
            _fail("birth_time_capability_value")
        capability_values[mode] = BirthTimeCapabilities(**dict(raw_capabilities))

    migration = _require_mapping(birth_time["migration"], "birth_time_migration")
    _require_keys(migration, {"null_birth_time", "non_null"}, "birth_time_migration")
    if dict(migration) != {"null_birth_time": "unknown", "non_null": "exact"}:
        _fail("birth_time_migration")

    return BirthTimeCanon(
        modes=modes,
        buckets_local=MappingProxyType(bucket_ranges),
        control_grid=MappingProxyType(dict(control_grid)),
        orb_margin=BirthTimeOrbMargin(
            rule="canonical_fixed",
            gap_hours=MappingProxyType(dict(gap_hours)),
            formula=orb_margin["formula"],
        ),
        gate="published_sparse_subset_of_robust_dense",
        capabilities=MappingProxyType(capability_values),
        migration=MappingProxyType(dict(migration)),
    )


def load_today_convergence_canon(canon_dir: Path | None = None) -> TodayConvergenceCanon:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.load_today_convergence_canon
    # purpose: Load and validate the frozen convergence, product-spheres, aspect, and theme YAML canons.
    # inputs: canon_dir — directory containing all four normative YAML files; repository canon by default.
    # returns: immutable TodayConvergenceCanon.
    # side_effects: reads YAML files only.
    # emitted_logs: none.
    # error_behavior: raises TodayConvergenceCanonError on any missing/malformed/unknown value.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.load_today_convergence_canon
    today_path, product_path, aspect_path, theme_path = _canon_artifact_paths(canon_dir)
    today = _read_yaml(today_path, "today")
    product = _read_yaml(product_path, "product")
    aspect = _read_yaml(aspect_path, "aspect")
    theme = _read_yaml(theme_path, "theme")

    (
        product_schema_version,
        product_status,
        product_canonical_order,
        product_spheres,
        projection_priority,
    ) = _product_spheres_canon(product)

    _require_keys(
        theme,
        {"schema_version", "status", "formula_version", "canonical_order", "technical_sphere_themes", "target_planet_themes"},
        "theme_top_keys",
    )
    if theme.get("schema_version") != "today_convergence_themes.v1":
        _fail("theme_schema_version")
    if theme.get("status") != "frozen_w1":
        _fail("theme_status")
    if theme.get("formula_version") != "today-convergence-2":
        _fail("theme_formula_version")
    theme_canonical_order = tuple(
        _normalized_theme_token(value, "theme_order")
        for value in _string_tuple(theme["canonical_order"], "theme_order")
    )
    if len(theme_canonical_order) != len(set(theme_canonical_order)):
        _fail("theme_order")
    technical_sphere_themes = _theme_mapping(theme["technical_sphere_themes"], "theme_technical_keys", uppercase_keys=False)
    target_planet_themes = _theme_mapping(theme["target_planet_themes"], "theme_target_keys", uppercase_keys=True)
    known_themes = set(theme_canonical_order)
    if any(set(values) - known_themes for values in technical_sphere_themes.values()):
        _fail("theme_reference")
    if any(set(values) - known_themes for values in target_planet_themes.values()):
        _fail("theme_reference")

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

    tone_policy_raw = _require_mapping(today["tone_policy"], "tone_policy_mapping")
    _require_keys(
        tone_policy_raw,
        {
            "status", "version", "layers", "unit_polarity", "neutral_maps_to", "weights",
            "group_balance", "day_tone", "audit_fields",
        },
        "tone_policy_keys",
    )
    if tone_policy_raw["status"] != "frozen_w1":
        _fail("tone_policy_status")
    if tone_policy_raw["version"] != "tone-candidate-0.1":
        _fail("tone_policy_version")
    tone_layers = _string_tuple(tone_policy_raw["layers"], "tone_policy_layers")
    if tone_layers != ("unit_polarity", "group_polarity", "day_tone"):
        _fail("tone_policy_layers")
    unit_polarities = _string_tuple(tone_policy_raw["unit_polarity"], "tone_policy_unit_polarity")
    if unit_polarities != ("supportive", "tense", "mixed", "steady"):
        _fail("tone_policy_unit_polarity")
    if tone_policy_raw["neutral_maps_to"] != "steady":
        _fail("tone_policy_neutral_maps_to")

    weights_raw = _require_mapping(tone_policy_raw["weights"], "tone_policy_role_weights")
    _require_keys(
        weights_raw,
        {"anchor_today", "supporting_context", "background", "mixed_split"},
        "tone_policy_role_weights",
    )
    role_weights = {key: _bounded_number(weights_raw[key], "tone_policy_role_weights") for key in weights_raw}
    if role_weights != {
        "anchor_today": 1.0,
        "supporting_context": 0.5,
        "background": 0.0,
        "mixed_split": 0.5,
    }:
        _fail("tone_policy_role_weights")

    group_balance = _require_mapping(tone_policy_raw["group_balance"], "tone_policy_group_balance")
    _require_keys(group_balance, {"independence", "min_side_weight", "mixed_margin"}, "tone_policy_group_balance")
    if group_balance["independence"] != "distinct_driver":
        _fail("tone_policy_group_balance")
    min_side_weight = _bounded_number(group_balance["min_side_weight"], "tone_policy_group_balance")
    mixed_margin = _bounded_number(group_balance["mixed_margin"], "tone_policy_group_balance")
    if min_side_weight != 0.25 or mixed_margin != 0.25:
        _fail("tone_policy_group_balance")

    day_tone = _require_mapping(tone_policy_raw["day_tone"], "tone_policy_day_tone")
    _require_keys(
        day_tone,
        {
            "values", "fresh_predicate", "ongoing_roles_are_context", "fast_sources_detail_only",
            "high_confidence_strength", "min_independent_tense_units", "min_independent_supportive_units",
            "mixed_requires_fresh_support_and_tense",
        },
        "tone_policy_day_tone_keys",
    )
    day_tones = _string_tuple(day_tone["values"], "tone_policy_day_tones")
    if day_tones != ("supportive", "tense", "mixed", "steady"):
        _fail("tone_policy_day_tones")
    fresh_predicate = _string_tuple(day_tone["fresh_predicate"], "tone_policy_fresh_predicate")
    if fresh_predicate != ("temporal_role == anchor_today", "exact_at local_date == target_date"):
        _fail("tone_policy_fresh_predicate")
    ongoing_roles = _string_tuple(day_tone["ongoing_roles_are_context"], "tone_policy_ongoing_roles")
    if ongoing_roles != ("supporting", "background"):
        _fail("tone_policy_ongoing_roles")
    fast_sources_detail_only = frozenset(
        _normal_source(value) for value in _string_tuple(day_tone["fast_sources_detail_only"], "tone_policy_fast_sources")
    )
    if None in fast_sources_detail_only:
        _fail("tone_policy_fast_sources")
    high_confidence_strength = _bounded_number(
        day_tone["high_confidence_strength"], "tone_policy_high_confidence_strength"
    )
    if high_confidence_strength != 0.75:
        _fail("tone_policy_high_confidence_strength")
    min_independent_tense_units = _exact_int(
        day_tone["min_independent_tense_units"], 2, "tone_policy_tense_threshold"
    )
    min_independent_supportive_units = _exact_int(
        day_tone["min_independent_supportive_units"], 2, "tone_policy_supportive_threshold"
    )
    if not isinstance(day_tone["mixed_requires_fresh_support_and_tense"], bool):
        _fail("tone_policy_mixed_requirement")
    mixed_requires_fresh_support_and_tense = day_tone["mixed_requires_fresh_support_and_tense"]
    if mixed_requires_fresh_support_and_tense is not True:
        _fail("tone_policy_mixed_requirement")
    audit_fields = _string_tuple(tone_policy_raw["audit_fields"], "tone_policy_audit_fields")
    if audit_fields != (
        "unit_polarity_counts", "group_polarity_counts", "day_tone", "tone_scores",
        "tone_trigger_keys", "legacy_any_selected_tense",
    ):
        _fail("tone_policy_audit_fields")
    tone_policy = TonePolicyCanon(
        status="frozen_w1",
        version="tone-candidate-0.1",
        layers=tone_layers,
        unit_polarities=unit_polarities,
        neutral_maps_to="steady",
        role_weights=MappingProxyType(role_weights),
        independence="distinct_driver",
        min_side_weight=min_side_weight,
        mixed_margin=mixed_margin,
        day_tones=day_tones,
        fresh_predicate=fresh_predicate,
        ongoing_roles_are_context=ongoing_roles,
        fast_sources_detail_only=frozenset(fast_sources_detail_only),
        high_confidence_strength=high_confidence_strength,
        min_independent_tense_units=min_independent_tense_units,
        min_independent_supportive_units=min_independent_supportive_units,
        mixed_requires_fresh_support_and_tense=mixed_requires_fresh_support_and_tense,
        audit_fields=audit_fields,
    )
    birth_time_canon = _birth_time_canon(today["birth_time"])

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
    if tone_policy.fast_sources_detail_only != fast_sources:
        _fail("tone_policy_fast_sources")
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
        {"rule", "source", "one_group", "priority", "fail_unmapped", "canonical_order"},
        "sphere_projection_keys",
    )
    if sphere["rule"] != "one_group_to_one_sphere":
        _fail("sphere_projection_rule")
    if sphere["source"] != _PRODUCT_SPHERES_FILENAME:
        _fail("sphere_projection_source")
    if sphere["one_group"] != "one_sphere_one_facet_or_null":
        _fail("sphere_projection_one_group")
    sphere_priority = _normalized_token_tuple(sphere["priority"], "sphere_projection_priority")
    if sphere_priority != projection_priority:
        _fail("sphere_projection_priority")
    if sphere["fail_unmapped"] is not True:
        _fail("sphere_projection_unmapped")
    canonical_spheres = _string_tuple(sphere["canonical_order"], "canonical_order")
    if canonical_spheres != product_canonical_order:
        _fail("canonical_order")

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
        product_schema_version=product_schema_version,
        product_status=product_status,
        product_spheres=product_spheres,
        projection_priority=projection_priority,
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
        theme_schema_version=theme["schema_version"],
        theme_status=theme["status"],
        theme_formula_version=theme["formula_version"],
        theme_canonical_order=theme_canonical_order,
        technical_sphere_themes=MappingProxyType(technical_sphere_themes),
        target_planet_themes=MappingProxyType(target_planet_themes),
        tone_policy=tone_policy,
        birth_time=birth_time_canon,
    )


def compute_today_convergence_canon_hash(canon_dir: Path | None = None) -> str:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.compute_today_convergence_canon_hash
    # purpose: Fingerprint exact bytes of the four strictly validated W1 canon artifacts.
    # inputs: canon_dir — repository canon directory or a complete copied canon directory.
    # returns: lowercase SHA-256 hex digest with filename boundaries.
    # side_effects: reads the four canon files; does not cache or write.
    # emitted_logs: none.
    # error_behavior: raises TodayConvergenceCanonError before hashing malformed/missing canon.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.compute_today_convergence_canon_hash
    load_today_convergence_canon(canon_dir)
    digest = sha256()
    for path in _canon_artifact_paths(canon_dir):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
# END_BLOCK: CANON_LOADER


# START_BLOCK: CANON_POLICY
def _input_token_tuple(value: Sequence[str] | str | None) -> tuple[str, ...]:
    """Normalize tolerant resolver input without assigning unknown values."""

    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        values: Sequence[Any] = (value,)
    elif isinstance(value, Sequence):
        values = value
    else:
        return ()
    return tuple(str(item).strip().lower().replace("-", "_") for item in values if str(item).strip())


def _product_facet_candidates(canon: TodayConvergenceCanon) -> tuple[tuple[str, ProductFacetCanon], ...]:
    return tuple(
        (sphere_key, facet)
        for sphere_key in canon.canonical_spheres
        for facet in canon.product_spheres[sphere_key].facets
    )


def _planet_values(source_key: str | None, target_key: str | None) -> frozenset[str]:
    return frozenset(
        key
        for key in (_normal_source(source_key), _normal_source(target_key))
        if key is not None
    )


def resolve_product_sphere(
    canon: TodayConvergenceCanon,
    house: int | None = None,
    technical_spheres: Sequence[str] | None = None,
    context_keys: Sequence[str] | None = None,
    theme_keys: Sequence[str] | None = None,
    context_theme_keys: Sequence[str] | None = None,
    source_key: str | None = None,
    target_key: str | None = None,
    *,
    context: Sequence[str] | None = None,
    source_planet: str | None = None,
    target_planet: str | None = None,
) -> tuple[str, str | None] | None:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.resolve_product_sphere
    # purpose: Resolve one physical group to one product sphere and optional facet.
    # inputs: canon; optional house (or one mapping with these fields),
    #   technical spheres, normalized context/theme keys, and source/target planets.
    # returns: (sphere, facet) or (sphere, None) when the sphere is known; None
    #   for an unknown/unmapped group.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: invalid/unknown input remains unresolved; no work
    #   fallback and no planet-only narrow facet are allowed.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.resolve_product_sphere
    if isinstance(house, Mapping):
        payload = house
        house = payload.get("house")
        technical_spheres = payload.get("technical_spheres", technical_spheres)
        context_keys = payload.get("context_keys", context_keys)
        theme_keys = payload.get("theme_keys", theme_keys)
        context_theme_keys = payload.get("context_theme_keys", context_theme_keys)
        source_key = payload.get("source_key", source_key)
        target_key = payload.get("target_key", target_key)
        source_planet = payload.get("source_planet", source_planet)
        target_planet = payload.get("target_planet", target_planet)

    house_value = None
    if house is not None:
        if isinstance(house, bool) or not isinstance(house, int) or not 1 <= house <= 12:
            return None
        house_value = house

    technical_values = frozenset(_input_token_tuple(technical_spheres))
    context_values = set(_input_token_tuple(context_keys))
    context_values.update(_input_token_tuple(theme_keys))
    context_values.update(_input_token_tuple(context_theme_keys))
    context_values.update(_input_token_tuple(context))
    effective_source = source_key if source_key is not None else source_planet
    effective_target = target_key if target_key is not None else target_planet
    planets = _planet_values(effective_source, effective_target)
    candidates = _product_facet_candidates(canon)

    if house_value is not None:
        base = [item for item in candidates if house_value in item[1].houses]
        if not base:
            return None
        technical_base = [item for item in base if set(item[1].technical_spheres) & technical_values]
        if technical_base:
            base = technical_base
    elif technical_values:
        base = [item for item in candidates if set(item[1].technical_spheres) & technical_values]
        if not base and context_values:
            base = [item for item in candidates if set(item[1].required_context) & context_values]
    elif context_values:
        base = [item for item in candidates if set(item[1].required_context) & context_values]
    else:
        # A planet is only a modifier/tie-break, never an origin of a product
        # sphere or a narrow facet.
        return None

    if not base:
        return None

    eligible = [
        item for item in base
        if not item[1].required_context or set(item[1].required_context) & context_values
    ]
    if not eligible:
        # The physical/technical evidence still identifies a sphere, but not a
        # context-specific facet. This is the explicit nullable-facet outcome.
        planet_sphere_matches = [
            item for item in base
            if set(item[1].modifiers["planets"]) & planets
            and (
                house_value is None
                or len(item[1].houses) == 1
                or item[1].houses[0] == house_value
            )
        ]
        if planet_sphere_matches:
            return planet_sphere_matches[0][0], None
        return base[0][0], None

    contextual = [item for item in eligible if set(item[1].required_context) & context_values]
    # S15/F3: no cross-sphere planet override here — master §5 makes planets a
    # tie-break only inside the candidates already chosen by house/context.
    selected = contextual or eligible
    if len(selected) > 1 and planets:
        planet_matches = [
            item for item in selected
            if set(item[1].modifiers["planets"]) & planets
        ]
        if planet_matches:
            selected = planet_matches

    sphere_key, facet = selected[0]
    return sphere_key, facet.key


def map_factor_to_theme_keys(
    canon: TodayConvergenceCanon,
    technical_spheres: Sequence[str] | None = None,
    source_key: str | None = None,
    target_key: str | None = None,
) -> tuple[str, ...]:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.map_factor_to_theme_keys
    # purpose: Project physical and technical factors through the versioned narrow-theme registry.
    # inputs: canon plus optional technical, source, and target keys.
    # returns: de-duplicated theme keys in registry canonical order; unknown input returns ().
    # side_effects: none; registry is already materialized in canon.
    # emitted_logs: none.
    # error_behavior: unknown values remain unmapped without fallback themes or product spheres.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-CANON.map_factor_to_theme_keys
    mapped: set[str] = set()
    if technical_spheres is None or isinstance(technical_spheres, (str, bytes)) or not isinstance(technical_spheres, Sequence):
        technical_values: Sequence[str] = ()
    else:
        technical_values = technical_spheres
    for value in technical_values:
        mapped.update(canon.technical_sphere_themes.get(str(value).strip().lower(), ()))
    for value in (source_key, target_key):
        key = _normal_source(value)
        if key is not None:
            mapped.update(canon.target_planet_themes.get(key, ()))
    return tuple(theme for theme in canon.theme_canonical_order if theme in mapped)


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
    "BirthTimeCanon",
    "BirthTimeCapabilities",
    "BirthTimeOrbMargin",
    "TodayConvergenceCanon",
    "TodayConvergenceCanonError",
    "TonePolicyCanon",
    "ProductFacetCanon",
    "ProductSphereCanon",
    "load_today_convergence_canon",
    "compute_today_convergence_canon_hash",
    "resolve_product_sphere",
    "map_factor_to_theme_keys",
    "aspect_weight",
    "source_max_orb",
    "event_class_significance",
    "is_fast_source",
    "is_rare_source",
    "hero_confirmation_policy",
]
# END_BLOCK: CANON_POLICY
