# ############################################################################
# AI_HEADER: MODULE_HORIZON_CANON_SERVICE — typed B2A horizon canon loader.
# ROLE: Resolve, load, cache, and typed-validate the dedicated horizon-selection canon file.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-CANON-SERVICE
# purpose: Load grace/canon/horizon_selection.v1.yml from repo-relative path and validate it strictly.
# owns:
#   - apps/api/app/services/horizon_canon_service.py
# inputs: Optional explicit canon file path.
# outputs: HorizonSelectionCanon instance and separate horizon canon version identity.
# dependencies: functools/pathlib/yaml stdlib, pydantic, app.schemas.horizon_canon, app.services.canon_service.CanonValidationError.
# side_effects: filesystem reads only.
# emitted_logs: none.
# invariants:
#   - default repo file uses a dedicated lru_cache(maxsize=1).
#   - explicit paths are resolved from the provided path, never cwd-dependent.
#   - errors contain path plus structural field, never raw YAML body.
# failure_policy: raises CanonValidationError on missing, malformed, or invalid canon.
# END_MODULE_CONTRACT: M-HORIZON-CANON-SERVICE

# START_MODULE_MAP: M-HORIZON-CANON-SERVICE
# public_entrypoints:
#   - load_horizon_selection_canon
#   - get_horizon_canon_versions
#   - clear_horizon_canon_cache_for_tests
# semantic_blocks:
#   - HORIZON_CANON_LOADING: repo resolution, typed validation, and cache helpers.
# owned_tests:
#   - apps/api/tests/test_horizon_canon_service.py
# END_MODULE_MAP: M-HORIZON-CANON-SERVICE

# START_BLOCK: HORIZON_CANON_LOADING
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from app.schemas.horizon_canon import HorizonSelectionCanon
from app.services.canon_service import CanonValidationError

_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_HORIZON_CANON_PATH = _REPO_ROOT / "grace" / "canon" / "horizon_selection.v1.yml"


def _format_validation_error(path: Path, exc: ValidationError) -> CanonValidationError:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SERVICE._format_validation_error
    # purpose: Convert Pydantic validation failures into compact structural canon errors.
    # inputs: path - canon path; exc - Pydantic validation error.
    # returns: CanonValidationError ready to raise.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SERVICE._format_validation_error
    first = exc.errors()[0]
    loc = ".".join(str(part) for part in first.get("loc", ())) or "<root>"
    message = first.get("msg", "invalid canon")
    if loc.startswith("transit_speed_eligibility"):
        message = "unknown speed group"
    elif loc.startswith("technical_sphere_themes") or loc.startswith("target_planet_themes"):
        message = "invalid theme id"
    return CanonValidationError(f"{path}: {loc}: {message}")


def _read_and_validate(path: Path) -> HorizonSelectionCanon:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SERVICE._read_and_validate
    # purpose: Read YAML from disk and validate it against the typed horizon canon schema.
    # inputs: path - resolved canon file path.
    # returns: validated HorizonSelectionCanon.
    # side_effects: filesystem read only.
    # emitted_logs: none.
    # error_behavior: raises CanonValidationError on missing, malformed, or invalid content.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SERVICE._read_and_validate
    if not path.exists():
        raise CanonValidationError(f"{path}: missing canon file")
    try:
        with path.open("r", encoding="utf-8") as handle:
            raw: Any = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        raise CanonValidationError(f"{path}: malformed YAML") from exc
    except OSError as exc:
        raise CanonValidationError(f"{path}: unreadable canon file") from exc
    try:
        return HorizonSelectionCanon.model_validate(raw)
    except ValidationError as exc:
        raise _format_validation_error(path, exc) from exc


@lru_cache(maxsize=1)
def _load_default_horizon_selection_canon() -> HorizonSelectionCanon:
    return _read_and_validate(DEFAULT_HORIZON_CANON_PATH)


@lru_cache(maxsize=32)
def _load_explicit_horizon_selection_canon(path_str: str) -> HorizonSelectionCanon:
    return _read_and_validate(Path(path_str))


def load_horizon_selection_canon(path: Path | None = None) -> HorizonSelectionCanon:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SERVICE.load_horizon_selection_canon
    # purpose: Public typed loader for the dedicated horizon selection canon.
    # inputs: path - optional explicit file path.
    # returns: validated HorizonSelectionCanon instance.
    # side_effects: filesystem reads and in-memory cache population.
    # emitted_logs: none.
    # error_behavior: raises CanonValidationError on any load/validation failure.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SERVICE.load_horizon_selection_canon
    if path is None:
        return _load_default_horizon_selection_canon()
    return _load_explicit_horizon_selection_canon(str(path.resolve()))


def get_horizon_canon_versions() -> dict[str, str]:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SERVICE.get_horizon_canon_versions
    # purpose: Expose the separate B2A horizon-canon version identity without touching core cache identity.
    # inputs: none.
    # returns: mapping of dedicated horizon canon names to versions.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SERVICE.get_horizon_canon_versions
    canon = load_horizon_selection_canon()
    return {"horizon_selection": canon.version}


def clear_horizon_canon_cache_for_tests() -> None:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SERVICE.clear_horizon_canon_cache_for_tests
    # purpose: Clear default and explicit-path caches to isolate tests.
    # inputs: none.
    # returns: none.
    # side_effects: resets process-local lru caches.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CANON-SERVICE.clear_horizon_canon_cache_for_tests
    _load_default_horizon_selection_canon.cache_clear()
    _load_explicit_horizon_selection_canon.cache_clear()
# END_BLOCK: HORIZON_CANON_LOADING


__all__ = [
    "load_horizon_selection_canon",
    "get_horizon_canon_versions",
    "clear_horizon_canon_cache_for_tests",
]
