#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: CONVERGENCE_CANON — analysis-side product sphere/facet resolver.
# ROLE: Loads the frozen product taxonomy and mirrors the production resolver
#       for replay projection without reintroducing factor fan-out.
# ############################################################################

# START_MODULE_CONTRACT: M-CONVERGENCE-CANON
# purpose: Load and validate the frozen product sphere/facet canon, then resolve
#   one physical group to one product sphere and optional facet for replay.
# owns:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/convergence_canon.py
# inputs: grace/canon/product_spheres.v1.yml and group-level house, technical,
#   context/theme, and optional planet evidence.
# outputs: immutable product canon constants and resolve_product_sphere().
# dependencies: PyYAML; repository product-spheres canon.
# side_effects: reads one repository YAML file at module import.
# emitted_logs: none.
# invariants:
#   - one input group resolves to one canonical sphere and one facet or null;
#   - a planet is a tie-break/modifier only, never a sphere origin;
#   - unknown input is unresolved; no legacy aliases are emitted;
#   - resolver precedence matches apps/api production resolver exactly.
# failure_policy: raises ValueError at import for malformed canon and returns
#   None for an invalid or unmapped resolver input.
# END_MODULE_CONTRACT: M-CONVERGENCE-CANON

# START_MODULE_MAP: M-CONVERGENCE-CANON
# public_entrypoints:
#   - CANONICAL_PRODUCT_KEYS
#   - PRODUCT_CANON
#   - VALID_FACET_KEYS
#   - resolve_product_sphere
#   - resolve_factor_projection
# semantic_blocks:
#   - CANON_LOAD: strict extraction of product sphere/facet metadata.
#   - RESOLVER: production-parity group-level projection.
# owned_tests:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_convergence_canon.py
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_sphere_mapping_delta.py
# END_MODULE_MAP: M-CONVERGENCE-CANON

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import yaml


# START_BLOCK: CANON_LOAD
REPO = Path(__file__).resolve().parents[4]
PRODUCT_CANON_PATH = REPO / "grace/canon/product_spheres.v1.yml"


@dataclass(frozen=True)
class ProductFacetCanon:
    """Immutable facet metadata used by the replay resolver."""

    key: str
    houses: tuple[int, ...]
    technical_spheres: tuple[str, ...]
    required_context: tuple[str, ...]
    modifier_planets: tuple[str, ...]


@dataclass(frozen=True)
class ProductSphereCanon:
    """Immutable ordered facets for one product sphere."""

    key: str
    facets: tuple[ProductFacetCanon, ...]


@dataclass(frozen=True)
class ProductCanon:
    """Minimal product canon required by the deterministic resolver."""

    schema_version: str
    status: str
    canonical_order: tuple[str, ...]
    product_spheres: Mapping[str, ProductSphereCanon]
    priority: tuple[str, ...]


def _fail(reason: str) -> None:
    raise ValueError(f"convergence_canon:{reason}")


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


def _token_tuple(
    value: Any,
    reason: str,
    *,
    uppercase: bool = False,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        _fail(reason)
    if not value and not allow_empty:
        _fail(reason)
    values = tuple(_text(item, reason) for item in value)
    if len(values) != len(set(values)):
        _fail(reason)
    normalized = tuple(item.upper() if uppercase else item.lower() for item in values)
    if any(
        normalized_item != original
        for original, normalized_item in zip(values, normalized, strict=True)
    ):
        _fail(reason)
    if any(
        any(not (character.isalnum() or character == "_") for character in item)
        for item in normalized
    ):
        _fail(reason)
    return normalized


def _load_product_canon() -> ProductCanon:
    try:
        raw = yaml.safe_load(PRODUCT_CANON_PATH.read_text(encoding="utf-8"))
    except OSError as exc:  # pragma: no cover - repository packaging failure
        raise ValueError(f"convergence_canon:product_missing:{PRODUCT_CANON_PATH}") from exc
    product = _require_mapping(raw, "product_mapping")
    _require_keys(
        product,
        {
            "schema_version",
            "status",
            "description",
            "canonical_order",
            "allowed_technical_spheres",
            "allowed_context_keys",
            "allowed_planets",
            "migration_aliases",
            "resolver",
            "spheres",
        },
        "product_top_keys",
    )
    if product.get("schema_version") != "product_spheres.v1":
        _fail("product_schema_version")
    if product.get("status") != "frozen_w1":
        _fail("product_status")
    _text(product["description"], "product_description")

    canonical_order = _token_tuple(product["canonical_order"], "product_canonical_order")
    expected_order = (
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
    if canonical_order != expected_order:
        _fail("product_canonical_order")

    technical_keys = _token_tuple(
        product["allowed_technical_spheres"], "product_technical_keys"
    )
    context_keys = set(_token_tuple(product["allowed_context_keys"], "product_context_keys"))
    planets = _token_tuple(product["allowed_planets"], "product_planets", uppercase=True)
    aliases = _require_mapping(product["migration_aliases"], "product_migration_aliases")
    if dict(aliases) != {"money": "finance", "shopping": "finance"}:
        _fail("product_migration_aliases")

    resolver = _require_mapping(product["resolver"], "product_resolver")
    _require_keys(
        resolver,
        {"rule", "priority", "output", "unknown", "planet_only_narrow_facets"},
        "product_resolver_keys",
    )
    priority = _token_tuple(resolver["priority"], "product_resolver_priority")
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
    for sphere_key in canonical_order:
        raw_sphere = _require_mapping(spheres_raw.get(sphere_key), "product_sphere_mapping")
        _require_keys(raw_sphere, {"key", "title", "description", "facets"}, "product_sphere_keys")
        if _token_tuple([raw_sphere["key"]], "product_sphere_key")[0] != sphere_key:
            _fail("product_sphere_key")
        _text(raw_sphere["title"], "product_sphere_title")
        _text(raw_sphere["description"], "product_sphere_description")
        facets_raw = raw_sphere["facets"]
        if not isinstance(facets_raw, Sequence) or isinstance(facets_raw, (str, bytes)) or not facets_raw:
            _fail("product_facets")
        facets: list[ProductFacetCanon] = []
        local_facets: set[str] = set()
        for raw_facet in facets_raw:
            facet = _require_mapping(raw_facet, "product_facet_mapping")
            required = {"key", "label", "houses", "modifiers"}
            allowed = required | {"technical_spheres", "required_context"}
            if not required.issubset(facet) or set(facet) - allowed:
                _fail("product_facet_keys")
            facet_key = _token_tuple([facet["key"]], "product_facet_key")[0]
            if facet_key in local_facets or facet_key in global_facets:
                _fail("product_facet_unique")
            local_facets.add(facet_key)
            global_facets.add(facet_key)
            _text(facet["label"], "product_facet_label")
            raw_houses = facet["houses"]
            if not isinstance(raw_houses, Sequence) or isinstance(raw_houses, (str, bytes)) or not raw_houses:
                _fail("product_facet_houses")
            houses = tuple(raw_houses)
            if any(
                isinstance(house, bool) or not isinstance(house, int) or not 1 <= house <= 12
                for house in houses
            ) or len(houses) != len(set(houses)):
                _fail("product_facet_houses")
            facet_technical = _token_tuple(
                facet.get("technical_spheres", []),
                "product_facet_technical",
                allow_empty=True,
            )
            if set(facet_technical) - set(technical_keys):
                _fail("product_facet_technical_reference")
            required_context = _token_tuple(
                facet.get("required_context", []),
                "product_facet_context",
                allow_empty=True,
            )
            if set(required_context) - context_keys:
                _fail("product_facet_context_reference")
            modifiers = _require_mapping(facet["modifiers"], "product_facet_modifiers")
            _require_keys(modifiers, {"planets"}, "product_facet_modifiers_keys")
            modifier_planets = _token_tuple(
                modifiers["planets"],
                "product_facet_planets",
                uppercase=True,
            )
            if set(modifier_planets) - set(planets):
                _fail("product_facet_planet_reference")
            facets.append(
                ProductFacetCanon(
                    key=facet_key,
                    houses=houses,
                    technical_spheres=facet_technical,
                    required_context=required_context,
                    modifier_planets=modifier_planets,
                )
            )
        sphere_values[sphere_key] = ProductSphereCanon(sphere_key, tuple(facets))

    return ProductCanon(
        schema_version=str(product["schema_version"]),
        status=str(product["status"]),
        canonical_order=canonical_order,
        product_spheres=MappingProxyType(sphere_values),
        priority=priority,
    )


PRODUCT_CANON = _load_product_canon()
CANONICAL_PRODUCT_KEYS = PRODUCT_CANON.canonical_order
VALID_FACET_KEYS = frozenset(
    facet.key
    for sphere in PRODUCT_CANON.product_spheres.values()
    for facet in sphere.facets
)
# END_BLOCK: CANON_LOAD


# START_BLOCK: RESOLVER
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
    return tuple(
        str(item).strip().lower().replace("-", "_")
        for item in values
        if str(item).strip()
    )


def _normal_source(value: str | None) -> str | None:
    if value is None:
        return None
    key = str(value).strip().upper()
    for prefix in ("TRANSIT_", "NATAL_"):
        if key.startswith(prefix):
            key = key[len(prefix):]
    return key or None


def _planet_values(source_key: str | None, target_key: str | None) -> frozenset[str]:
    return frozenset(
        key
        for key in (_normal_source(source_key), _normal_source(target_key))
        if key is not None
    )


def _product_facet_candidates() -> tuple[tuple[str, ProductFacetCanon], ...]:
    return tuple(
        (sphere_key, facet)
        for sphere_key in PRODUCT_CANON.canonical_order
        for facet in PRODUCT_CANON.product_spheres[sphere_key].facets
    )


def resolve_product_sphere(
    house: int | Mapping[str, Any] | None = None,
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
    # START_FUNCTION_CONTRACT: F-M-CONVERGENCE-CANON.resolve_product_sphere
    # purpose: Resolve one analysis physical group to one product sphere and
    #   optional facet using the production S2 precedence rules.
    # inputs: optional house, technical spheres, explicit context/theme keys,
    #   and source/target planets; a mapping payload is also accepted.
    # returns: (sphere, facet) or (sphere, None); None when unresolved.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: invalid/unknown input remains unresolved; no fallback.
    # END_FUNCTION_CONTRACT: F-M-CONVERGENCE-CANON.resolve_product_sphere
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
    candidates = _product_facet_candidates()

    if house_value is not None:
        base = [item for item in candidates if house_value in item[1].houses]
        if not base:
            return None
        technical_base = [
            item for item in base if set(item[1].technical_spheres) & technical_values
        ]
        if technical_base:
            base = technical_base
    elif technical_values:
        base = [
            item for item in candidates if set(item[1].technical_spheres) & technical_values
        ]
        if not base and context_values:
            base = [
                item for item in candidates if set(item[1].required_context) & context_values
            ]
    elif context_values:
        base = [
            item for item in candidates if set(item[1].required_context) & context_values
        ]
    else:
        # A planet is only a modifier/tie-break, never an origin of a product
        # sphere or a narrow facet.
        return None

    if not base:
        return None

    eligible = [
        item
        for item in base
        if not item[1].required_context
        or set(item[1].required_context) & context_values
    ]
    if not eligible:
        # Physical/technical evidence identifies a sphere, but no contextual
        # facet is justified. This is the explicit nullable-facet outcome.
        planet_sphere_matches = [
            item
            for item in base
            if set(item[1].modifier_planets) & planets
            and (
                house_value is None
                or len(item[1].houses) == 1
                or item[1].houses[0] == house_value
            )
        ]
        if planet_sphere_matches:
            return planet_sphere_matches[0][0], None
        return base[0][0], None

    contextual = [
        item for item in eligible if set(item[1].required_context) & context_values
    ]
    if not contextual and planets:
        eligible_spheres = {item[0] for item in eligible}
        planet_sphere_matches = [
            item
            for item in base
            if item[0] not in eligible_spheres
            and set(item[1].modifier_planets) & planets
            and (
                house_value is None
                or len(item[1].houses) == 1
                or item[1].houses[0] == house_value
            )
        ]
        if planet_sphere_matches:
            return planet_sphere_matches[0][0], None
    selected = contextual or eligible
    if len(selected) > 1 and planets:
        planet_matches = [
            item for item in selected if set(item[1].modifier_planets) & planets
        ]
        if planet_matches:
            selected = planet_matches

    sphere_key, facet = selected[0]
    return sphere_key, facet.key


def resolve_factor_projection(
    *,
    house: int | None = None,
    technical_spheres: Sequence[str] | None = None,
    theme_keys: Sequence[str] | None = None,
    source_key: str | None = None,
    target_key: str | None = None,
) -> tuple[str, str | None] | None:
    # START_FUNCTION_CONTRACT: F-M-CONVERGENCE-CANON.resolve_factor_projection
    # purpose: Apply the same resolver to one replay factor while preserving
    #   the group-level API used by production grouping.
    # inputs: one factor's house, technical, theme, and planet fields.
    # returns: one sphere/facet pair or None; this helper never fans out.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: delegates fail-closed behavior to resolve_product_sphere.
    # END_FUNCTION_CONTRACT: F-M-CONVERGENCE-CANON.resolve_factor_projection
    return resolve_product_sphere(
        house=house,
        technical_spheres=technical_spheres,
        theme_keys=theme_keys,
        source_key=source_key,
        target_key=target_key,
    )
# END_BLOCK: RESOLVER


__all__ = [
    "CANONICAL_PRODUCT_KEYS",
    "PRODUCT_CANON",
    "ProductCanon",
    "ProductFacetCanon",
    "ProductSphereCanon",
    "VALID_FACET_KEYS",
    "resolve_factor_projection",
    "resolve_product_sphere",
]
