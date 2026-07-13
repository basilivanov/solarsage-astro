# ############################################################################
# AI_HEADER: TEST_HORIZON_CANON_SERVICE — fail-closed B2A horizon canon coverage.
# ROLE: Proves loader privacy, strict canon boundaries, normalized ranges, and version isolation.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-HORIZON-CANON-SERVICE
# purpose: Exercise every B2A horizon canon validation boundary through public loader and typed schema paths.
# owns:
#   - apps/api/tests/test_horizon_canon_service.py
# inputs: Temporary YAML mutations of the committed horizon selection canon.
# outputs: Deterministic pass/fail assertions with no external side effects beyond tmp files.
# dependencies: pytest/yaml/pydantic, B2A canon schema and loader services.
# side_effects: temporary test-file writes only.
# emitted_logs: none.
# invariants:
#   - malformed or impossible canon is rejected before selection runtime.
#   - error messages never expose raw secret test input.
# failure_policy: test failures identify missing fail-closed validation.
# END_MODULE_CONTRACT: M-TEST-HORIZON-CANON-SERVICE

# START_MODULE_MAP: M-TEST-HORIZON-CANON-SERVICE
# public_entrypoints:
#   - test_real_horizon_canon_validates
#   - test_default_cache_clear_and_explicit_path_behavior
#   - test_canon_loader_rejects_missing_malformed_extra_and_wrong_version
#   - test_normalized_ranges_and_priority_coverage_fail_closed
#   - test_canon_rejects_weights_duration_and_mapping_identity_failures
#   - test_canon_missing_isolated_negative_matrix
#   - test_error_privacy_and_separate_versions
# semantic_blocks:
#   - HORIZON_CANON_TEST_HELPERS: isolated YAML mutation helpers.
#   - HORIZON_CANON_LOADER_TESTS: loader/cache/version tests.
#   - HORIZON_CANON_STRICTNESS_TESTS: strict normalized and identity boundary tests.
# owned_tests:
#   - apps/api/tests/test_horizon_canon_service.py
# END_MODULE_MAP: M-TEST-HORIZON-CANON-SERVICE

# START_BLOCK: HORIZON_CANON_TEST_HELPERS
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.schemas.horizon_canon import StateRelevance
from app.services.canon_service import CANON_DIR, CanonValidationError, get_canon_versions
from app.services.horizon_canon_service import (
    clear_horizon_canon_cache_for_tests,
    get_horizon_canon_versions,
    load_horizon_selection_canon,
)

REAL_CANON_PATH = CANON_DIR / "horizon_selection.v1.yml"
REAL_CANON_DATA = yaml.safe_load(REAL_CANON_PATH.read_text(encoding="utf-8"))


def _canon_copy() -> dict[str, object]:
    return deepcopy(REAL_CANON_DATA)


def _write_yaml(path: Path, data: dict[str, object]) -> Path:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _assert_invalid(tmp_path: Path, data: dict[str, object]) -> None:
    path = _write_yaml(tmp_path / "invalid.yml", data)
    with pytest.raises(CanonValidationError):
        load_horizon_selection_canon(path)
# END_BLOCK: HORIZON_CANON_TEST_HELPERS


# START_BLOCK: HORIZON_CANON_LOADER_TESTS
def test_real_horizon_canon_validates() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CANON-SERVICE.test_real_horizon_canon_validates
    # purpose: Prove the committed v1 canon remains a valid typed closed model.
    # inputs: none.
    # returns: none.
    # side_effects: cache reset only.
    # emitted_logs: none.
    # error_behavior: assertion failure if committed canon is invalid.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CANON-SERVICE.test_real_horizon_canon_validates
    clear_horizon_canon_cache_for_tests()
    canon = load_horizon_selection_canon()
    assert canon.version == "v1"
    assert canon.schema_version == "horizon_selection.v1"


def test_default_cache_clear_and_explicit_path_behavior(tmp_path: Path) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CANON-SERVICE.test_default_cache_clear_and_explicit_path_behavior
    # purpose: Prove default cache semantics and explicit resolved-path validation.
    # inputs: tmp_path - pytest temporary directory.
    # returns: none.
    # side_effects: cache reset and temporary YAML write.
    # emitted_logs: none.
    # error_behavior: assertion failure on incorrect cache boundaries.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CANON-SERVICE.test_default_cache_clear_and_explicit_path_behavior
    clear_horizon_canon_cache_for_tests()
    first = load_horizon_selection_canon()
    assert load_horizon_selection_canon() is first
    clear_horizon_canon_cache_for_tests()
    assert load_horizon_selection_canon() is not first
    explicit = _write_yaml(tmp_path / "explicit.yml", _canon_copy())
    assert load_horizon_selection_canon(explicit).version == "v1"


def test_canon_loader_rejects_missing_malformed_extra_and_wrong_version(tmp_path: Path) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CANON-SERVICE.test_canon_loader_rejects_missing_malformed_extra_and_wrong_version
    # purpose: Prove public loader rejects basic file and closed-schema errors.
    # inputs: tmp_path - pytest temporary directory.
    # returns: none.
    # side_effects: temporary test-file writes.
    # emitted_logs: none.
    # error_behavior: assertion failure if invalid loader input succeeds.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CANON-SERVICE.test_canon_loader_rejects_missing_malformed_extra_and_wrong_version
    with pytest.raises(CanonValidationError, match="missing canon file"):
        load_horizon_selection_canon(tmp_path / "missing.yml")
    malformed = tmp_path / "malformed.yml"
    malformed.write_text("schema_version: horizon_selection.v1\nversion: [\n", encoding="utf-8")
    with pytest.raises(CanonValidationError, match="malformed YAML"):
        load_horizon_selection_canon(malformed)
    extra = _canon_copy()
    extra["unexpected"] = True
    _assert_invalid(tmp_path, extra)
    wrong_version = _canon_copy()
    wrong_version["version"] = "v2"
    _assert_invalid(tmp_path, wrong_version)
# END_BLOCK: HORIZON_CANON_LOADER_TESTS


# START_BLOCK: HORIZON_CANON_STRICTNESS_TESTS
def test_normalized_ranges_and_priority_coverage_fail_closed(tmp_path: Path) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CANON-SERVICE.test_normalized_ranges_and_priority_coverage_fail_closed
    # purpose: Prove every downstream-normalized canon family rejects invalid unit/rule coverage values at load time.
    # inputs: tmp_path - pytest temporary directory.
    # returns: none.
    # side_effects: temporary canon writes.
    # emitted_logs: none.
    # error_behavior: assertion failure if any invalid canonical mutation validates.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CANON-SERVICE.test_normalized_ranges_and_priority_coverage_fail_closed
    invalid_values = (-0.001, 1.001, float("nan"), float("inf"))
    for value in invalid_values:
        for state in ("upcoming", "building", "active", "exact", "peaked", "fading", "background"):
            data = _canon_copy()
            data["timing"]["state_relevance"][state] = value
            _assert_invalid(tmp_path, data)
        for field in ("peaked_post_exact_fraction", "completeness_with_exact", "completeness_without_exact"):
            data = _canon_copy()
            data["timing"][field] = value
            _assert_invalid(tmp_path, data)
        for field in ("long", "medium", "fast"):
            data = _canon_copy()
            data["min_candidate_impact"][field] = value
            _assert_invalid(tmp_path, data)
        for field in ("long_medium", "medium_fast", "long_fast", "triple_mean"):
            data = _canon_copy()
            data["min_pair_overlap"][field] = value
            _assert_invalid(tmp_path, data)
        data = _canon_copy()
        data["technique_rules"]["annual_profection"]["priority_by_horizon"]["long"] = value
        _assert_invalid(tmp_path, data)

    missing_priority = _canon_copy()
    del missing_priority["technique_rules"]["transit_to_natal"]["priority_by_horizon"]["fast"]
    _assert_invalid(tmp_path, missing_priority)
    extra_priority = _canon_copy()
    extra_priority["technique_rules"]["annual_profection"]["priority_by_horizon"]["fast"] = 0.5
    _assert_invalid(tmp_path, extra_priority)
    reordered = _canon_copy()
    reordered["technique_rules"]["firdar_minor"]["allowed_horizons"] = ["medium", "long"]
    _assert_invalid(tmp_path, reordered)
    duplicate = _canon_copy()
    duplicate["technique_rules"]["firdar_minor"]["allowed_horizons"] = ["long", "long"]
    _assert_invalid(tmp_path, duplicate)


def test_canon_rejects_weights_duration_and_mapping_identity_failures(tmp_path: Path) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CANON-SERVICE.test_canon_rejects_weights_duration_and_mapping_identity_failures
    # purpose: Prove convex, duration, speed, product, and theme mapping invariants fail at the canon boundary.
    # inputs: tmp_path - pytest temporary directory.
    # returns: none.
    # side_effects: temporary canon writes.
    # emitted_logs: none.
    # error_behavior: assertion failure if a malformed canon validates.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CANON-SERVICE.test_canon_rejects_weights_duration_and_mapping_identity_failures
    mutations: list[tuple[list[str], object]] = [
        (["impact_weights", "strength"], 0.29),
        (["story_overlap_weights", "same_target"], 0.36),
        (["triple_score_weights", "mean_overlap"], 0.31),
        (["duration_bands", "medium", "eligible_min_days"], 241),
        (["limits", "max_anchor_combinations"], 1000),
        (["transit_speed_eligibility", "long"], ["slow", "slow"]),
        (["planet_speed_groups", "fast"], []),
        (["planet_speed_groups", "fast"], ["Transit_MOON"]),
        (["technical_to_product_spheres", "thinking_speech_learning"], []),
        (["technical_sphere_themes", "thinking_speech_learning"], []),
        (["target_planet_themes", "SATURN"], []),
    ]
    for path, value in mutations:
        data = _canon_copy()
        target = data
        for part in path[:-1]:
            target = target[part]
        target[path[-1]] = value
        _assert_invalid(tmp_path, data)
    unknown_technique = _canon_copy()
    unknown_technique["technique_rules"]["invented"] = unknown_technique["technique_rules"]["annual_profection"]
    _assert_invalid(tmp_path, unknown_technique)
    missing_sphere = _canon_copy()
    del missing_sphere["technical_to_product_spheres"]["body_energy_health"]
    _assert_invalid(tmp_path, missing_sphere)
    duplicate_product = _canon_copy()
    duplicate_product["technical_to_product_spheres"]["thinking_speech_learning"] = ["communication", "communication"]
    _assert_invalid(tmp_path, duplicate_product)
    unknown_product = _canon_copy()
    unknown_product["technical_to_product_spheres"]["thinking_speech_learning"] = ["imaginary"]
    _assert_invalid(tmp_path, unknown_product)
    bad_target_key = _canon_copy()
    bad_target_key["target_planet_themes"]["Transit_MOON"] = ["energy_body_pacing"]
    _assert_invalid(tmp_path, bad_target_key)


def test_canon_missing_isolated_negative_matrix(tmp_path: Path) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CANON-SERVICE.test_canon_missing_isolated_negative_matrix
    # purpose: Prove each previously unisolated B2A canon invariant rejects its own precise mutation.
    # inputs: tmp_path - pytest temporary directory.
    # returns: none.
    # side_effects: temporary YAML writes only.
    # emitted_logs: none.
    # error_behavior: assertion failure if a stated fail-closed canon rule accepts malformed data.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CANON-SERVICE.test_canon_missing_isolated_negative_matrix
    cases: list[tuple[str, dict[str, object]]] = []

    unknown_horizon = _canon_copy()
    unknown_horizon["technique_rules"]["annual_profection"]["allowed_horizons"] = ["long", "warp"]
    cases.append(("unknown_horizon", unknown_horizon))

    unknown_speed = _canon_copy()
    unknown_speed["transit_speed_eligibility"]["long"] = ["warp"]
    cases.append(("unknown_speed_group", unknown_speed))

    overlapping_planet = _canon_copy()
    overlapping_planet["planet_speed_groups"]["medium"].append("MOON")
    cases.append(("normalized_planet_in_two_groups", overlapping_planet))

    duplicate_planet = _canon_copy()
    duplicate_planet["planet_speed_groups"]["fast"].append("MOON")
    cases.append(("duplicate_planet_in_group", duplicate_planet))

    missing_technical_theme = _canon_copy()
    del missing_technical_theme["technical_sphere_themes"]["body_energy_health"]
    cases.append(("missing_technical_theme_key", missing_technical_theme))

    duplicate_technical_theme = _canon_copy()
    duplicate_technical_theme["technical_sphere_themes"]["body_energy_health"] = [
        "energy_body_pacing", "energy_body_pacing",
    ]
    cases.append(("duplicate_technical_theme", duplicate_technical_theme))

    duplicate_target_theme = _canon_copy()
    duplicate_target_theme["target_planet_themes"]["SATURN"] = [
        "structure_boundaries_control", "structure_boundaries_control",
    ]
    cases.append(("duplicate_target_theme", duplicate_target_theme))

    invalid_theme = _canon_copy()
    invalid_theme["technical_sphere_themes"]["body_energy_health"] = ["BadTheme"]
    cases.append(("invalid_theme_pattern", invalid_theme))

    missing_product_union = _canon_copy()
    missing_product_union["technical_to_product_spheres"]["money_security_resources"] = ["money", "documents"]
    cases.append(("missing_product_with_all_technical_keys", missing_product_union))

    for group_name, field_name in (
        ("impact_weights", "strength"),
        ("story_overlap_weights", "same_target"),
        ("triple_score_weights", "mean_impact"),
    ):
        for value_name, value in (("nan", float("nan")), ("inf", float("inf"))):
            nonfinite = _canon_copy()
            nonfinite[group_name][field_name] = value
            cases.append((f"{group_name}_{value_name}", nonfinite))

    assert len(cases) == 15
    for case_name, data in cases[:9]:
        path = _write_yaml(tmp_path / f"{case_name}.yml", data)
        with pytest.raises(CanonValidationError):
            load_horizon_selection_canon(path)
    for case_name, data in cases[9:]:
        path = _write_yaml(tmp_path / f"{case_name}.yml", data)
        with pytest.raises(CanonValidationError, match="finite"):
            load_horizon_selection_canon(path)


def test_error_privacy_and_separate_versions() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CANON-SERVICE.test_error_privacy_and_separate_versions
    # purpose: Prove Pydantic hides raw invalid input and B2A version identity leaves core versions unchanged.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure if privacy or version isolation regresses.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-CANON-SERVICE.test_error_privacy_and_separate_versions
    marker = "SECRET_HORIZON_CANON_MARKER"
    with pytest.raises(ValidationError) as captured:
        StateRelevance.model_validate(
            {
                "upcoming": marker,
                "building": 0.1,
                "active": 0.1,
                "exact": 0.1,
                "peaked": 0.1,
                "fading": 0.1,
                "background": 0.1,
            }
        )
    assert marker not in str(captured.value)
    assert get_canon_versions() == {
        "spheres": "v1",
        "dignities": "v1",
        "aspect_rules": "v1",
        "activation_rules": "v1",
        "scoring_v2": "v1",
        "horizon_selection": "v1",
        "horizon_language_ru": "v1",
        "horizon_actions_ru": "v1",
        "personal_patterns_ru": "v1",
    }
    assert get_horizon_canon_versions() == {"horizon_selection": "v1"}
# END_BLOCK: HORIZON_CANON_STRICTNESS_TESTS
