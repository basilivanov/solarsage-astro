# ############################################################################
# AI_HEADER: TEST_HORIZON_CONTENT_CANON_SERVICE — strict B2B1 three-canon loader coverage.
# ROLE: Proves caching, closed schema, cross-canon, and privacy-safe failure behavior for content canons.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-HORIZON-CONTENT-CANON-SERVICE
# purpose: Exercise default/explicit content canon loading and isolated schema/cross-canon rejection cases.
# owns:
#   - apps/api/tests/test_horizon_content_canon_service.py
# inputs: Real canon copies plus one-field temporary YAML mutations.
# outputs: Assertions over strict loader behavior without external runtime dependencies.
# dependencies: pytest/yaml, content canon loader/schema, canon service directory.
# side_effects: temporary test directory writes and loader-cache resets only.
# emitted_logs: none.
# invariants:
#   - Content canon errors are structural and do not reveal raw copy.
#   - Every accepted bundle has exact closed identity sets.
# failure_policy: test failures identify B2B1 canon validation regressions.
# END_MODULE_CONTRACT: M-TEST-HORIZON-CONTENT-CANON-SERVICE

# START_MODULE_MAP: M-TEST-HORIZON-CONTENT-CANON-SERVICE
# public_entrypoints:
#   - test_default_bundle_version_map_cache_and_cwd_independence
#   - test_explicit_directory_cache_isolation_and_reset
#   - test_missing_and_malformed_files_fail_closed
#   - test_language_extra_unknown_placeholder_and_tone_weight_fail_closed
#   - test_action_policy_and_coverage_fail_closed
#   - test_pattern_statement_and_normalized_predicate_fail_closed
# semantic_blocks:
#   - HORIZON_CONTENT_CANON_TEST_HELPERS: copied canon directory and mutation helpers.
#   - HORIZON_CONTENT_CANON_LOADER_TESTS: cache/default/error behaviors.
#   - HORIZON_CONTENT_CANON_STRICTNESS_TESTS: one-field schema and cross-canon mutations.
# owned_tests:
#   - apps/api/tests/test_horizon_content_canon_service.py
# END_MODULE_MAP: M-TEST-HORIZON-CONTENT-CANON-SERVICE

# START_BLOCK: HORIZON_CONTENT_CANON_TEST_HELPERS
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil

import pytest
import yaml

from app.services.canon_service import CANON_DIR, CanonValidationError
from app.services.horizon_content_canon_service import (
    clear_horizon_content_canon_cache_for_tests,
    get_horizon_content_canon_versions,
    load_horizon_content_canons,
)


def _copy_content_dir(tmp_path: Path) -> Path:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE._copy_content_dir
    # purpose: Copy the three committed B2B1 YAML files into one isolated temporary canon directory.
    # inputs: tmp_path - pytest-managed temporary root.
    # returns: isolated canon directory path.
    # side_effects: temporary filesystem writes only.
    # emitted_logs: none.
    # error_behavior: propagates filesystem errors.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE._copy_content_dir
    target = tmp_path / "canon"
    target.mkdir(parents=True)
    for name in (
        "horizon_language.ru.v1.yml",
        "horizon_actions.ru.v1.yml",
        "personal_patterns.ru.v1.yml",
    ):
        shutil.copy2(CANON_DIR / name, target / name)
    return target


def _read_yaml(directory: Path, name: str) -> dict[str, object]:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE._read_yaml
    # purpose: Read one copied YAML mapping for exactly one isolated mutation.
    # inputs: directory - temporary canon dir; name - file name.
    # returns: mutable mapping copy.
    # side_effects: temporary filesystem read only.
    # emitted_logs: none.
    # error_behavior: propagates parser errors.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE._read_yaml
    return deepcopy(yaml.safe_load((directory / name).read_text(encoding="utf-8")))


def _write_yaml(directory: Path, name: str, data: dict[str, object]) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE._write_yaml
    # purpose: Persist one synthetic canon mutation while retaining readable YAML key order.
    # inputs: directory - temporary canon dir; name - file name; data - mutated mapping.
    # returns: none.
    # side_effects: temporary filesystem write only.
    # emitted_logs: none.
    # error_behavior: propagates filesystem errors.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE._write_yaml
    (directory / name).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _assert_invalid(directory: Path) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE._assert_invalid
    # purpose: Assert the public explicit-directory loader rejects one isolated mutated bundle.
    # inputs: directory - temporary mutated canon directory.
    # returns: none.
    # side_effects: explicit cache reset only.
    # emitted_logs: none.
    # error_behavior: assertion failure when malformed content silently loads.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE._assert_invalid
    clear_horizon_content_canon_cache_for_tests()
    with pytest.raises(CanonValidationError):
        load_horizon_content_canons(directory)


# END_BLOCK: HORIZON_CONTENT_CANON_TEST_HELPERS


# START_BLOCK: HORIZON_CONTENT_CANON_LOADER_TESTS
def test_default_bundle_version_map_cache_and_cwd_independence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE.test_default_bundle_version_map_cache_and_cwd_independence
    # purpose: Prove repo-relative default loading, exact versions, and identity caching.
    # inputs: monkeypatch - cwd isolation; tmp_path - empty alternate cwd.
    # returns: none.
    # side_effects: cache reset and temporary cwd change only.
    # emitted_logs: none.
    # error_behavior: assertion failure on cache/version/cwd regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE.test_default_bundle_version_map_cache_and_cwd_independence
    clear_horizon_content_canon_cache_for_tests()
    first = load_horizon_content_canons()
    monkeypatch.chdir(tmp_path)
    second = load_horizon_content_canons()
    assert first is second
    assert get_horizon_content_canon_versions() == {
        "horizon_language_ru": "v1",
        "horizon_actions_ru": "v1",
        "personal_patterns_ru": "v1",
    }


def test_explicit_directory_cache_isolation_and_reset(tmp_path: Path) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE.test_explicit_directory_cache_isolation_and_reset
    # purpose: Prove explicit resolved directories cache separately and clear resets object identity.
    # inputs: tmp_path - temporary canon roots.
    # returns: none.
    # side_effects: temporary filesystem writes and cache reset.
    # emitted_logs: none.
    # error_behavior: assertion failure on cache key isolation regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE.test_explicit_directory_cache_isolation_and_reset
    first_dir = _copy_content_dir(tmp_path / "one")
    second_dir = _copy_content_dir(tmp_path / "two")
    clear_horizon_content_canon_cache_for_tests()
    first = load_horizon_content_canons(first_dir)
    assert first is load_horizon_content_canons(first_dir)
    assert first is not load_horizon_content_canons(second_dir)
    clear_horizon_content_canon_cache_for_tests()
    assert first is not load_horizon_content_canons(first_dir)


def test_missing_and_malformed_files_fail_closed(tmp_path: Path) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE.test_missing_and_malformed_files_fail_closed
    # purpose: Prove each mandatory content file has no fallback and malformed YAML hides raw payloads.
    # inputs: tmp_path - temporary canon copy roots.
    # returns: none.
    # side_effects: temporary filesystem mutations and cache reset.
    # emitted_logs: none.
    # error_behavior: assertion failure when a failure mode is accepted or leaks copy.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE.test_missing_and_malformed_files_fail_closed
    for name in (
        "horizon_language.ru.v1.yml",
        "horizon_actions.ru.v1.yml",
        "personal_patterns.ru.v1.yml",
    ):
        directory = _copy_content_dir(tmp_path / name)
        (directory / name).unlink()
        clear_horizon_content_canon_cache_for_tests()
        with pytest.raises(CanonValidationError, match="missing canon file"):
            load_horizon_content_canons(directory)
    directory = _copy_content_dir(tmp_path / "malformed")
    (directory / "horizon_language.ru.v1.yml").write_text("raw_copy_secret: [", encoding="utf-8")
    clear_horizon_content_canon_cache_for_tests()
    with pytest.raises(CanonValidationError) as error:
        load_horizon_content_canons(directory)
    assert "raw_copy_secret" not in str(error.value)


# END_BLOCK: HORIZON_CONTENT_CANON_LOADER_TESTS


# START_BLOCK: HORIZON_CONTENT_CANON_STRICTNESS_TESTS
def test_language_extra_unknown_placeholder_and_tone_weight_fail_closed(tmp_path: Path) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE.test_language_extra_unknown_placeholder_and_tone_weight_fail_closed
    # purpose: Prove independent language schema, placeholder, and numeric rule mutations fail closed.
    # inputs: tmp_path - temporary canon roots.
    # returns: none.
    # side_effects: temporary YAML mutations only.
    # emitted_logs: none.
    # error_behavior: assertion failure if a closed language invariant is weakened.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE.test_language_extra_unknown_placeholder_and_tone_weight_fail_closed
    directory = _copy_content_dir(tmp_path / "extra")
    language = _read_yaml(directory, "horizon_language.ru.v1.yml")
    language["unknown_top_level"] = True
    _write_yaml(directory, "horizon_language.ru.v1.yml", language)
    _assert_invalid(directory)

    directory = _copy_content_dir(tmp_path / "placeholder")
    language = _read_yaml(directory, "horizon_language.ru.v1.yml")
    language["techniques"]["annual_profection"]["why_it_matters_template"] = "{unknown_placeholder}"
    _write_yaml(directory, "horizon_language.ru.v1.yml", language)
    _assert_invalid(directory)

    directory = _copy_content_dir(tmp_path / "weights")
    language = _read_yaml(directory, "horizon_language.ru.v1.yml")
    language["tone_rules"]["feature_weights"]["strength"] = 0.36
    _write_yaml(directory, "horizon_language.ru.v1.yml", language)
    _assert_invalid(directory)


def test_action_policy_and_coverage_fail_closed(tmp_path: Path) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE.test_action_policy_and_coverage_fail_closed
    # purpose: Prove forbidden intent/copy and required medium coverage mutations fail independently.
    # inputs: tmp_path - temporary canon roots.
    # returns: none.
    # side_effects: temporary YAML mutations only.
    # emitted_logs: none.
    # error_behavior: assertion failure if action policy/coverage is silently accepted.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE.test_action_policy_and_coverage_fail_closed
    directory = _copy_content_dir(tmp_path / "intent")
    actions = _read_yaml(directory, "horizon_actions.ru.v1.yml")
    actions["themes"]["structure_boundaries_control"]["long"]["do"][0]["intent"] = "escalate"
    _write_yaml(directory, "horizon_actions.ru.v1.yml", actions)
    _assert_invalid(directory)

    directory = _copy_content_dir(tmp_path / "copy")
    actions = _read_yaml(directory, "horizon_actions.ru.v1.yml")
    actions["themes"]["structure_boundaries_control"]["long"]["do"][0]["text"] = "Это точно случится."
    _write_yaml(directory, "horizon_actions.ru.v1.yml", actions)
    _assert_invalid(directory)

    directory = _copy_content_dir(tmp_path / "coverage")
    actions = _read_yaml(directory, "horizon_actions.ru.v1.yml")
    actions["themes"]["structure_boundaries_control"]["medium"]["do"].pop()
    actions["themes"]["structure_boundaries_control"]["medium"]["do"].pop()
    _write_yaml(directory, "horizon_actions.ru.v1.yml", actions)
    _assert_invalid(directory)


def test_pattern_statement_and_normalized_predicate_fail_closed(tmp_path: Path) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE.test_pattern_statement_and_normalized_predicate_fail_closed
    # purpose: Prove cross-canon statement and canonicalized duplicate aspect predicate rules fail closed.
    # inputs: tmp_path - temporary canon roots.
    # returns: none.
    # side_effects: temporary YAML mutations only.
    # emitted_logs: none.
    # error_behavior: assertion failure if pattern cross-references or normalized duplicates are accepted.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE.test_pattern_statement_and_normalized_predicate_fail_closed
    directory = _copy_content_dir(tmp_path / "statement")
    patterns = _read_yaml(directory, "personal_patterns.ru.v1.yml")
    patterns["patterns"][0]["statement_key"] = "strength.unknown.statement"
    _write_yaml(directory, "personal_patterns.ru.v1.yml", patterns)
    _assert_invalid(directory)


def test_unreadable_non_mapping_and_validation_errors_hide_raw_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE.test_unreadable_non_mapping_and_validation_errors_hide_raw_copy
    # purpose: Prove unreadable/non-mapping/validation failures are structural and never expose review-copy sentinels.
    # inputs: monkeypatch - isolated Path.open failure; tmp_path - temporary canon roots.
    # returns: none.
    # side_effects: temporary YAML mutations, cache reset, and Path.open monkeypatch only.
    # emitted_logs: none.
    # error_behavior: assertion failure on fallback, raw-copy leakage, or accepted non-mapping YAML.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CONTENT-CANON-SERVICE.test_unreadable_non_mapping_and_validation_errors_hide_raw_copy
    directory = _copy_content_dir(tmp_path / "unreadable")
    original_open = Path.open

    def _unreadable(path: Path, *args: object, **kwargs: object):
        if path.name == "horizon_language.ru.v1.yml":
            raise OSError("RAW_UNREADABLE_SENTINEL")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", _unreadable)
    clear_horizon_content_canon_cache_for_tests()
    with pytest.raises(CanonValidationError) as unreadable_error:
        load_horizon_content_canons(directory)
    assert "RAW_UNREADABLE_SENTINEL" not in str(unreadable_error.value)
    monkeypatch.undo()

    directory = _copy_content_dir(tmp_path / "non-mapping")
    (directory / "horizon_language.ru.v1.yml").write_text("- RAW_NON_MAPPING_SENTINEL", encoding="utf-8")
    _assert_invalid(directory)

    directory = _copy_content_dir(tmp_path / "validation")
    language = _read_yaml(directory, "horizon_language.ru.v1.yml")
    language["themes"]["structure_boundaries_control"]["headline"] = "RAW_VALIDATION_COPY_SENTINEL"
    language["themes"]["structure_boundaries_control"]["intro_body"] = " "
    _write_yaml(directory, "horizon_language.ru.v1.yml", language)
    clear_horizon_content_canon_cache_for_tests()
    with pytest.raises(CanonValidationError) as validation_error:
        load_horizon_content_canons(directory)
    assert "RAW_VALIDATION_COPY_SENTINEL" not in str(validation_error.value)

    directory = _copy_content_dir(tmp_path / "duplicate")
    patterns = _read_yaml(directory, "personal_patterns.ru.v1.yml")
    patterns["patterns"][1]["requirements"].append(
        {
            "type": "aspect",
            "point_a": "SATURN",
            "point_b": "MERCURY",
            "aspect_types": ["SEXTILE", "TRINE"],
            "max_orb": 4.0,
        }
    )
    _write_yaml(directory, "personal_patterns.ru.v1.yml", patterns)
    _assert_invalid(directory)


# END_BLOCK: HORIZON_CONTENT_CANON_STRICTNESS_TESTS
