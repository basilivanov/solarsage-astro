# ############################################################################
# AI_HEADER: HORIZON_CONTENT_CANON_SERVICE — strict cached B2B1 content-canon loader.
# ROLE: Resolves, reads, validates, and version-exposes the three internal content canon files.
# ############################################################################

# START_MODULE_CONTRACT: M-HORIZON-CONTENT-CANON-SERVICE
# purpose: Load the language/actions/personal-pattern canon bundle from a repo-relative or explicit directory.
# owns:
#   - apps/api/app/services/horizon_content_canon_service.py
# inputs: Optional canon directory path.
# outputs: HorizonContentCanonBundle and a separate B2B1 version map.
# dependencies: functools/pathlib/yaml/pydantic, content canon schema, CanonValidationError.
# side_effects: filesystem reads and process-local LRU cache population only.
# emitted_logs: none.
# invariants:
#   - Default loading is repo-relative and never depends on cwd.
#   - Missing, malformed, unreadable, and structurally invalid files fail closed.
# failure_policy: raises CanonValidationError without raw YAML values or prose.
# END_MODULE_CONTRACT: M-HORIZON-CONTENT-CANON-SERVICE

# START_MODULE_MAP: M-HORIZON-CONTENT-CANON-SERVICE
# public_entrypoints:
#   - load_horizon_content_canons
#   - get_horizon_content_canon_versions
#   - clear_horizon_content_canon_cache_for_tests
# semantic_blocks:
#   - HORIZON_CONTENT_CANON_LOADING: deterministic directory resolution, validation, and cache control.
# owned_tests:
#   - apps/api/tests/test_horizon_content_canon_service.py
# END_MODULE_MAP: M-HORIZON-CONTENT-CANON-SERVICE

# START_BLOCK: HORIZON_CONTENT_CANON_LOADING
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from app.schemas.horizon_content_canon import (
    HorizonActionsCanon,
    HorizonContentCanonBundle,
    HorizonLanguageCanon,
    PersonalPatternsCanon,
)
from app.services.canon_service import CanonValidationError

_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CONTENT_CANON_DIR = _REPO_ROOT / "grace" / "canon"
CONTENT_CANON_FILES = {
    "language": "horizon_language.ru.v1.yml",
    "actions": "horizon_actions.ru.v1.yml",
    "patterns": "personal_patterns.ru.v1.yml",
}


def _read_yaml(path: Path) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SERVICE._read_yaml
    # purpose: Read one content canon YAML file and classify filesystem/parser failures.
    # inputs: path - resolved content canon file path.
    # returns: parsed mapping.
    # side_effects: filesystem read only.
    # emitted_logs: none.
    # error_behavior: raises CanonValidationError on missing, unreadable, malformed, or non-mapping YAML.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SERVICE._read_yaml
    if not path.exists():
        raise CanonValidationError(f"{path}: missing canon file")
    try:
        with path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise CanonValidationError(f"{path}: malformed YAML") from exc
    except OSError as exc:
        raise CanonValidationError(f"{path}: unreadable canon file") from exc
    if not isinstance(raw, dict):
        raise CanonValidationError(f"{path}: expected mapping")
    return raw


def _validation_error(path: Path, exc: ValidationError) -> CanonValidationError:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SERVICE._validation_error
    # purpose: Convert Pydantic errors into compact structural content-canon errors.
    # inputs: path - canon file or bundle marker; exc - Pydantic validation error.
    # returns: CanonValidationError.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SERVICE._validation_error
    first = exc.errors()[0]
    location = ".".join(str(part) for part in first.get("loc", ())) or "<root>"
    return CanonValidationError(f"{path}: {location}: invalid content canon")


def _load_bundle(canon_dir: Path) -> HorizonContentCanonBundle:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SERVICE._load_bundle
    # purpose: Parse all three files and validate their individual plus cross-canon contracts.
    # inputs: canon_dir - resolved directory holding the three B2B1 files.
    # returns: validated HorizonContentCanonBundle.
    # side_effects: filesystem reads only.
    # emitted_logs: none.
    # error_behavior: raises CanonValidationError on any file or bundle validation failure.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SERVICE._load_bundle
    paths = {name: canon_dir / filename for name, filename in CONTENT_CANON_FILES.items()}
    try:
        language = HorizonLanguageCanon.model_validate(_read_yaml(paths["language"]))
    except ValidationError as exc:
        raise _validation_error(paths["language"], exc) from exc
    try:
        actions = HorizonActionsCanon.model_validate(_read_yaml(paths["actions"]))
    except ValidationError as exc:
        raise _validation_error(paths["actions"], exc) from exc
    try:
        patterns = PersonalPatternsCanon.model_validate(_read_yaml(paths["patterns"]))
    except ValidationError as exc:
        raise _validation_error(paths["patterns"], exc) from exc
    try:
        return HorizonContentCanonBundle(language=language, actions=actions, patterns=patterns)
    except ValidationError as exc:
        raise _validation_error(canon_dir, exc) from exc


@lru_cache(maxsize=1)
def _load_default_content_canons() -> HorizonContentCanonBundle:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SERVICE._load_default_content_canons
    # purpose: Cache the repo-default B2B1 content canon bundle.
    # inputs: none.
    # returns: validated default bundle.
    # side_effects: filesystem reads on cold cache only.
    # emitted_logs: none.
    # error_behavior: propagates CanonValidationError.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SERVICE._load_default_content_canons
    return _load_bundle(DEFAULT_CONTENT_CANON_DIR)


@lru_cache(maxsize=32)
def _load_explicit_content_canons(directory: str) -> HorizonContentCanonBundle:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SERVICE._load_explicit_content_canons
    # purpose: Cache a bundle isolated by its resolved explicit directory string.
    # inputs: directory - resolved explicit directory path string.
    # returns: validated explicit bundle.
    # side_effects: filesystem reads on cold cache only.
    # emitted_logs: none.
    # error_behavior: propagates CanonValidationError.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SERVICE._load_explicit_content_canons
    return _load_bundle(Path(directory))


def load_horizon_content_canons(canon_dir: Path | None = None) -> HorizonContentCanonBundle:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SERVICE.load_horizon_content_canons
    # purpose: Public strict loader for all B2B1 content canon files.
    # inputs: canon_dir - optional explicit directory containing the complete canon bundle.
    # returns: cached validated HorizonContentCanonBundle.
    # side_effects: filesystem reads and cache population only.
    # emitted_logs: none.
    # error_behavior: raises CanonValidationError on missing, malformed, unreadable, or invalid canon.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SERVICE.load_horizon_content_canons
    if canon_dir is None:
        return _load_default_content_canons()
    return _load_explicit_content_canons(str(canon_dir.resolve()))


def get_horizon_content_canon_versions() -> dict[str, str]:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SERVICE.get_horizon_content_canon_versions
    # purpose: Expose B2B1's internal canon identities without changing core cache/audit versions.
    # inputs: none.
    # returns: exact three-key B2B1 version map.
    # side_effects: loads default canon bundle if uncached.
    # emitted_logs: none.
    # error_behavior: propagates CanonValidationError from default loading.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SERVICE.get_horizon_content_canon_versions
    bundle = load_horizon_content_canons()
    return {
        "horizon_language_ru": bundle.language.version,
        "horizon_actions_ru": bundle.actions.version,
        "personal_patterns_ru": bundle.patterns.version,
    }


def clear_horizon_content_canon_cache_for_tests() -> None:
    # START_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SERVICE.clear_horizon_content_canon_cache_for_tests
    # purpose: Clear default and explicit content-canon caches for isolated test mutations.
    # inputs: none.
    # returns: none.
    # side_effects: clears process-local LRU caches.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-HORIZON-CONTENT-CANON-SERVICE.clear_horizon_content_canon_cache_for_tests
    _load_default_content_canons.cache_clear()
    _load_explicit_content_canons.cache_clear()


# END_BLOCK: HORIZON_CONTENT_CANON_LOADING


__all__ = [
    "clear_horizon_content_canon_cache_for_tests",
    "get_horizon_content_canon_versions",
    "load_horizon_content_canons",
]
