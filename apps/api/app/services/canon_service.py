# ############################################################################
# AI_HEADER: MODULE_CANON_SERVICE — canon YAML loading, validation, versioning.
# ROLE: Load and validate all grace/canon/*.yml files at production startup.
#       Provides typed canon data and version strings.
# ############################################################################

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[4]

CANON_DIR = _REPO_ROOT / "grace" / "canon"

CANON_FILES = [
    "spheres.v1.yml",
    "dignities.v1.yml",
    "aspect_rules.v1.yml",
    "activation_rules.v1.yml",
    "scoring_v2.v1.yml",
]

OPTIONAL_INTERNAL_CANON_FILES = [
    "horizon_selection.v1.yml",
    "horizon_language.ru.v1.yml",
    "horizon_actions.ru.v1.yml",
    "personal_patterns.ru.v1.yml",
]

CANON_VERSIONS: dict[str, str] = {
    "spheres": "v1",
    "dignities": "v1",
    "aspect_rules": "v1",
    "activation_rules": "v1",
    "scoring_v2": "v1",
}


REQUIRED_TOP_KEYS: dict[str, list[str]] = {
    "spheres.v1.yml": ["schema_version", "spheres"],
    "dignities.v1.yml": ["schema_version"],
    "aspect_rules.v1.yml": ["schema_version", "aspect_weights", "aspect_threshold"],
    "activation_rules.v1.yml": ["schema_version", "technique_families"],
    "scoring_v2.v1.yml": ["schema_version"],
}

FAMILY_TECHNIQUE_KEYS = [
    "transit_to_natal", "transit_to_angle", "transit_to_lot", "transit_planet_in_house",
    "annual_profection", "monthly_profection",
    "firdar_major", "firdar_minor",
    "solar_return", "lunar_return",
    "secondary_progression", "solar_arc",
    "eclipse_window",
]


class CanonValidationError(Exception):
    """Raised when canon file validation fails."""


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def validate_canon_bundle(canon_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load and validate all canon files. Raise CanonValidationError on failure.

    Returns dict mapping filename stem to loaded data, e.g. {"spheres": {...}}.
    """
    cd = canon_dir or CANON_DIR
    bundle: dict[str, dict[str, Any]] = {}

    for filename in CANON_FILES:
        path = cd / filename
        if not path.exists():
            raise CanonValidationError(f"Missing canon file: {path}")

        data = _load_yaml(path)
        bundle[filename] = data

        # Check schema_version exists
        if "schema_version" not in data:
            raise CanonValidationError(f"{filename}: missing 'schema_version'")

        # Check required top-level keys
        required = REQUIRED_TOP_KEYS.get(filename, [])
        for key in required:
            if key not in data:
                raise CanonValidationError(f"{filename}: missing required key '{key}'")

    # Activation rules specific validation
    act_file = "activation_rules.v1.yml"
    activate_data = bundle[act_file]
    families = activate_data.get("technique_families", {})
    if not families:
        raise CanonValidationError(f"{act_file}: 'technique_families' is empty")

    known_techniques = set(FAMILY_TECHNIQUE_KEYS)
    for family_name, family_data in families.items():
        members = family_data.get("members", [])
        for member in members:
            if member not in known_techniques:
                raise CanonValidationError(
                    f"{act_file}: technique '{member}' in family '{family_name}' is not a known technique"
                )

    from app.services.horizon_canon_service import load_horizon_selection_canon
    from app.services.horizon_content_canon_service import load_horizon_content_canons

    load_horizon_selection_canon((cd / "horizon_selection.v1.yml").resolve())
    load_horizon_content_canons(cd.resolve())

    return bundle


def load_canon_bundle(canon_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load canon bundle without raising on missing files.
    Returns empty dict for missing files but logs warnings.
    Used by production startup path.
    """
    import sys
    cd = canon_dir or CANON_DIR
    bundle: dict[str, dict[str, Any]] = {}

    for filename in CANON_FILES:
        path = cd / filename
        if not path.exists():
            print(f"WARNING: Canon file not found: {path}", file=sys.stderr)
            continue
        try:
            data = _load_yaml(path)
            bundle[filename] = data
        except Exception as exc:
            print(f"ERROR: Failed to load canon file {filename}: {exc}", file=sys.stderr)

    for filename in OPTIONAL_INTERNAL_CANON_FILES:
        path = cd / filename
        if not path.exists():
            continue
        try:
            bundle[filename] = _load_yaml(path)
        except Exception as exc:
            print(f"ERROR: Failed to load canon file {filename}: {exc}", file=sys.stderr)

    return bundle


def get_canon_versions() -> dict[str, str]:
    """Return the current canon version map."""
    return dict(CANON_VERSIONS)
