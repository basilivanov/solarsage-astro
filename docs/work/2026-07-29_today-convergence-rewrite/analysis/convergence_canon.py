#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: CONVERGENCE_CANON — strict W1 mapping loader for replay/reference code.
# ROLE: Makes the new convergence sphere mapping independent from legacy Today UI/API maps.
# ############################################################################

# START_MODULE_CONTRACT: M-CONVERGENCE-CANON
# purpose: Load and validate the W1 Today-convergence sphere registry, then map
#   technical themes and physical factor keys to product spheres fail-closed.
# owns:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/convergence_canon.py
# inputs: grace/canon/today_convergence.v1.yml and factor technical/source/target keys.
# outputs: immutable mapping constants and map_product_spheres tuples.
# dependencies: PyYAML; repository Today-convergence canon.
# side_effects: reads one repository YAML file at module import.
# emitted_logs: none.
# invariants:
#   - unknown factors never fall back to work;
#   - every returned sphere belongs to canonical_order;
#   - one planet maps to at most two product spheres;
#   - this module never imports a legacy Today frontend/API mapping.
# failure_policy: raises ValueError at import for malformed canon and returns an
#   empty tuple for an unmapped factor so the caller can exclude it explicitly.
# END_MODULE_CONTRACT: M-CONVERGENCE-CANON

# START_MODULE_MAP: M-CONVERGENCE-CANON
# public_entrypoints:
#   - CANONICAL_PRODUCT_KEYS
#   - PLANET_TO_PRODUCT_MAP
#   - TECH_SPHERE_TO_PRODUCT_MAP
#   - map_product_spheres
# semantic_blocks:
#   - CANON_LOAD: strict extraction and validation of sphere mappings.
#   - FACTOR_MAPPING: fail-closed factor-to-product projection.
# owned_tests:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_convergence_canon.py
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_sphere_mapping_delta.py
# END_MODULE_MAP: M-CONVERGENCE-CANON

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml


# START_BLOCK: CANON_LOAD
REPO = Path(__file__).resolve().parents[4]
CANON_PATH = REPO / "grace/canon/today_convergence.v1.yml"


def _tuple_mapping(raw: Any, *, label: str) -> dict[str, tuple[str, ...]]:
    if not isinstance(raw, Mapping):
        raise ValueError(f"{label} must be a mapping")
    result: dict[str, tuple[str, ...]] = {}
    for raw_key, raw_values in raw.items():
        key = str(raw_key).strip()
        if not key or not isinstance(raw_values, Sequence) or isinstance(raw_values, str):
            raise ValueError(f"invalid {label} entry: {raw_key!r}")
        values = tuple(str(value).strip() for value in raw_values)
        if not values or any(not value for value in values):
            raise ValueError(f"empty {label} entry: {raw_key!r}")
        result[key] = values
    return result


_RAW_CANON = yaml.safe_load(CANON_PATH.read_text(encoding="utf-8"))
if not isinstance(_RAW_CANON, Mapping):
    raise ValueError("today convergence canon must be a mapping")
_SPHERE_CANON = _RAW_CANON.get("sphere_projection")
if not isinstance(_SPHERE_CANON, Mapping):
    raise ValueError("sphere_projection must be a mapping")

CANONICAL_PRODUCT_KEYS = tuple(
    str(value).strip() for value in _SPHERE_CANON.get("canonical_order", ())
)
if not CANONICAL_PRODUCT_KEYS or len(set(CANONICAL_PRODUCT_KEYS)) != len(
    CANONICAL_PRODUCT_KEYS
):
    raise ValueError("canonical_order must contain unique product spheres")
_VALID_SPHERES = frozenset(CANONICAL_PRODUCT_KEYS)

PLANET_TO_PRODUCT_MAP = {
    key.upper(): values
    for key, values in _tuple_mapping(
        _SPHERE_CANON.get("planet_to_product"), label="planet_to_product"
    ).items()
}
_TECHNICAL = _tuple_mapping(
    _SPHERE_CANON.get("technical_to_product"), label="technical_to_product"
)
_TECHNICAL_ALIASES = _tuple_mapping(
    _SPHERE_CANON.get("technical_alias_to_product"),
    label="technical_alias_to_product",
)
TECH_SPHERE_TO_PRODUCT_MAP = {
    **{key.lower(): values for key, values in _TECHNICAL.items()},
    **{key.lower(): values for key, values in _TECHNICAL_ALIASES.items()},
}

_MAX_PLANET_SPHERES = int(
    (_SPHERE_CANON.get("planet_sphere_limits") or {}).get(
        "max_spheres_per_planet", 0
    )
)
if _MAX_PLANET_SPHERES <= 0:
    raise ValueError("max_spheres_per_planet must be positive")
for mapping_name, mapping in (
    ("planet_to_product", PLANET_TO_PRODUCT_MAP),
    ("technical_to_product", TECH_SPHERE_TO_PRODUCT_MAP),
):
    for key, values in mapping.items():
        unknown = set(values) - _VALID_SPHERES
        if unknown:
            raise ValueError(f"{mapping_name}.{key} has unknown spheres: {sorted(unknown)}")
for planet, values in PLANET_TO_PRODUCT_MAP.items():
    if len(values) > _MAX_PLANET_SPHERES:
        raise ValueError(
            f"planet_to_product.{planet} exceeds {_MAX_PLANET_SPHERES} spheres"
        )
# END_BLOCK: CANON_LOAD


# START_BLOCK: FACTOR_MAPPING
def _clean_factor_key(value: str | None) -> str:
    key = str(value or "").strip().upper()
    for prefix in ("TRANSIT_", "NATAL_"):
        if key.startswith(prefix):
            key = key[len(prefix) :]
    return key


def map_product_spheres(
    technical_spheres: Sequence[str] | None,
    source_key: str | None,
    target_key: str | None,
) -> tuple[str, ...]:
    # START_FUNCTION_CONTRACT: F-M-CONVERGENCE-CANON.map_product_spheres
    # purpose: Project one physical factor through the frozen W1 sphere registry.
    # inputs: technical theme keys plus optional physical source and target keys.
    # returns: de-duplicated product spheres in canonical order; empty if unmapped.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: unknown keys are ignored fail-closed; malformed canon fails at import.
    # END_FUNCTION_CONTRACT: F-M-CONVERGENCE-CANON.map_product_spheres
    mapped: set[str] = set()
    for technical in technical_spheres or ():
        mapped.update(TECH_SPHERE_TO_PRODUCT_MAP.get(str(technical).lower(), ()))
    for raw_key in (source_key, target_key):
        mapped.update(PLANET_TO_PRODUCT_MAP.get(_clean_factor_key(raw_key), ()))
    return tuple(key for key in CANONICAL_PRODUCT_KEYS if key in mapped)
# END_BLOCK: FACTOR_MAPPING
