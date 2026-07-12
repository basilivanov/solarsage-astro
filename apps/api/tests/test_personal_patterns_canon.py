# ############################################################################
# AI_HEADER: TEST_PERSONAL_PATTERNS_CANON — isolated B2B1 personal-pattern canon regressions.
# ROLE: Proves deterministic catalog order, finite confidence, links, and natal predicate closure.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-PERSONAL-PATTERNS-CANON
# purpose: Exercise one-field pattern-canon mutations through the public strict bundle loader.
# owns:
#   - apps/api/tests/test_personal_patterns_canon.py
# inputs: Isolated temporary copies of the reviewed personal patterns canon.
# outputs: Assertions that invalid catalog/link/predicate mutations fail closed.
# dependencies: pytest, B2B1 canon testkit, strict content-canon loader.
# side_effects: temporary YAML writes and loader-cache resets only.
# emitted_logs: none.
# invariants:
#   - The twelve-rule v1 catalog order is deterministic.
#   - Every rule has finite linked predicates and one matching language statement.
# failure_policy: assertion failure identifies an accepted invalid pattern mutation.
# END_MODULE_CONTRACT: M-TEST-PERSONAL-PATTERNS-CANON

# START_MODULE_MAP: M-TEST-PERSONAL-PATTERNS-CANON
# public_entrypoints:
#   - test_personal_pattern_mutation_matrix_rejects
#   - test_personal_pattern_predicate_boundaries_reject
#   - test_known_sign_subset_remains_structurally_valid
#   - test_default_personal_pattern_catalog_matches_reviewed_golden_content
# semantic_blocks:
#   - PERSONAL_PATTERN_MUTATION_HELPERS: isolated loader rejection helper.
#   - PERSONAL_PATTERN_CLOSURE_TESTS: catalog/link/predicate regression coverage.
# owned_tests:
#   - apps/api/tests/test_personal_patterns_canon.py
# END_MODULE_MAP: M-TEST-PERSONAL-PATTERNS-CANON

# START_BLOCK: PERSONAL_PATTERN_MUTATION_HELPERS
from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from app.services.canon_service import CanonValidationError
from app.services.horizon_content_canon_service import (
    clear_horizon_content_canon_cache_for_tests,
    load_horizon_content_canons,
)

from ._horizon_content_testkit import (
    copy_content_canon_dir,
    read_content_canon_yaml,
    write_content_canon_yaml,
)

PatternMutation = Callable[[dict[str, object]], None]


def _reject_patterns(tmp_path: Path, mutate: PatternMutation) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-PATTERNS-CANON._reject_patterns
    # purpose: Apply one pattern mutation and prove the public loader rejects its bundle.
    # inputs: tmp_path - isolated pytest root; mutate - one-field patterns mapping mutation.
    # returns: none.
    # side_effects: temporary YAML write and loader-cache reset only.
    # emitted_logs: none.
    # error_behavior: assertion failure if the malformed canon loads.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-PATTERNS-CANON._reject_patterns
    directory = copy_content_canon_dir(tmp_path)
    patterns = read_content_canon_yaml(directory, "personal_patterns.ru.v1.yml")
    mutate(patterns)
    write_content_canon_yaml(directory, "personal_patterns.ru.v1.yml", patterns)
    clear_horizon_content_canon_cache_for_tests()
    with pytest.raises(CanonValidationError):
        load_horizon_content_canons(directory)


# END_BLOCK: PERSONAL_PATTERN_MUTATION_HELPERS


# START_BLOCK: PERSONAL_PATTERN_CLOSURE_TESTS
@pytest.mark.parametrize(
    ("case", "mutate"),
    [
        ("wrong_schema", lambda data: data.__setitem__("schema_version", "wrong")),
        ("extra_top_key", lambda data: data.__setitem__("extra", True)),
        ("base_confidence_below_min", lambda data: data["patterns"][0].__setitem__("base_confidence", 0.1)),
        ("empty_pattern_links_bundle", lambda data: data["patterns"][0].__setitem__("theme_keys", [])),
        ("empty_pattern_spheres", lambda data: data["patterns"][0].__setitem__("sphere_keys", [])),
        ("reordered_pattern_catalog", lambda data: data.__setitem__("patterns", list(reversed(data["patterns"])))),
        ("missing_order", lambda data: data["patterns"][0].pop("order")),
        ("duplicate_order", lambda data: data["patterns"][1].__setitem__("order", 1)),
        ("non_contiguous_order", lambda data: data["patterns"][1].__setitem__("order", 13)),
        ("zero_order", lambda data: data["patterns"][0].__setitem__("order", 0)),
        ("negative_order", lambda data: data["patterns"][0].__setitem__("order", -1)),
        ("missing_requirement", lambda data: data["patterns"][0].__setitem__("requirements", [])),
        ("unknown_statement", lambda data: data["patterns"][0].__setitem__("statement_key", "strength.unknown")),
        ("duplicate_predicate", lambda data: data["patterns"][1]["requirements"].append(dict(data["patterns"][1]["requirements"][0]))),
        ("extra_predicate_key", lambda data: data["patterns"][0]["requirements"][0].__setitem__("extra", True)),
    ],
)
def test_personal_pattern_mutation_matrix_rejects(tmp_path: Path, case: str, mutate: PatternMutation) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-PATTERNS-CANON.test_personal_pattern_mutation_matrix_rejects
    # purpose: Mutation-prove independently closed pattern catalog, link, confidence, and predicate fields.
    # inputs: tmp_path - isolated test root; case/mutate - descriptive one-field mutation.
    # returns: none.
    # side_effects: temporary YAML writes only.
    # emitted_logs: none.
    # error_behavior: assertion failure if case loads.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-PATTERNS-CANON.test_personal_pattern_mutation_matrix_rejects
    _reject_patterns(tmp_path / case, mutate)


@pytest.mark.parametrize(
    ("case", "mutate"),
    [
        ("unknown_planet", lambda data: data["patterns"][0]["requirements"][0].__setitem__("planet", "RAW")),
        ("unknown_sign", lambda data: data["patterns"][0]["requirements"][0].__setitem__("signs", ["RAW"])),
        ("house_outside_range", lambda data: data["patterns"][0]["requirements"][1].__setitem__("houses", [13])),
        ("unknown_aspect", lambda data: data["patterns"][1]["requirements"][0].__setitem__("aspect_types", ["RAW"])),
        ("zero_orb", lambda data: data["patterns"][1]["requirements"][0].__setitem__("max_orb", 0.0)),
        ("infinite_orb", lambda data: data["patterns"][1]["requirements"][0].__setitem__("max_orb", float("inf"))),
    ],
)
def test_personal_pattern_predicate_boundaries_reject(tmp_path: Path, case: str, mutate: PatternMutation) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-PATTERNS-CANON.test_personal_pattern_predicate_boundaries_reject
    # purpose: Prove every supported natal predicate family rejects its invalid known-value boundaries.
    # inputs: tmp_path - isolated test root; case/mutate - descriptive predicate mutation.
    # returns: none.
    # side_effects: temporary YAML writes only.
    # emitted_logs: none.
    # error_behavior: assertion failure if an invalid predicate loads.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-PATTERNS-CANON.test_personal_pattern_predicate_boundaries_reject
    _reject_patterns(tmp_path / case, mutate)


def test_known_sign_subset_remains_structurally_valid(tmp_path: Path) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-PATTERNS-CANON.test_known_sign_subset_remains_structurally_valid
    # purpose: Prove runtime validation does not duplicate exact reviewed predicate content from YAML.
    # inputs: tmp_path - isolated temporary canon root.
    # returns: none.
    # side_effects: temporary YAML write and loader-cache reset only.
    # emitted_logs: none.
    # error_behavior: assertion failure if a structurally valid known predicate subset is rejected.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-PATTERNS-CANON.test_known_sign_subset_remains_structurally_valid
    directory = copy_content_canon_dir(tmp_path)
    patterns = read_content_canon_yaml(directory, "personal_patterns.ru.v1.yml")
    patterns["patterns"][0]["requirements"][0]["signs"] = ["CAPRICORN"]
    write_content_canon_yaml(directory, "personal_patterns.ru.v1.yml", patterns)
    clear_horizon_content_canon_cache_for_tests()
    assert load_horizon_content_canons(directory).patterns.patterns[0].requirements[0].signs == ("CAPRICORN",)


def test_default_personal_pattern_catalog_matches_reviewed_golden_content() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-PATTERNS-CANON.test_default_personal_pattern_catalog_matches_reviewed_golden_content
    # purpose: Keep exact reviewed v1 rule content test-owned while runtime stays structural and self-describing.
    # inputs: none.
    # returns: none.
    # side_effects: default canon loader-cache use only.
    # emitted_logs: none.
    # error_behavior: assertion failure on reviewed YAML content drift.
    # END_FUNCTION_CONTRACT: F-M-TEST-PERSONAL-PATTERNS-CANON.test_default_personal_pattern_catalog_matches_reviewed_golden_content
    def _signature(predicate: object) -> tuple[object, ...]:
        kind = getattr(predicate, "type")
        if kind == "planet_in_sign":
            return kind, getattr(predicate, "planet"), tuple(sorted(getattr(predicate, "signs")))
        if kind == "planet_in_house":
            return kind, getattr(predicate, "planet"), tuple(sorted(getattr(predicate, "houses")))
        return (
            kind,
            getattr(predicate, "point_a"),
            getattr(predicate, "point_b"),
            tuple(sorted(getattr(predicate, "aspect_types"))),
            getattr(predicate, "max_orb"),
        )

    actual = tuple(
        (
            rule.order,
            rule.id,
            rule.kind,
            rule.statement_key,
            rule.theme_keys,
            rule.sphere_keys,
            rule.base_confidence,
            rule.min_confidence,
            tuple(_signature(predicate) for predicate in rule.requirements),
        )
        for rule in load_horizon_content_canons().patterns.patterns
    )
    expected = (
        (1, "saturn_angular_dignified_structure", "strength", "strength.structure.steady_responsibility", ("structure_boundaries_control", "resources_security"), ("work", "money", "documents", "decisions"), 0.86, 0.80, (("planet_in_sign", "SATURN", ("AQUARIUS", "CAPRICORN", "LIBRA")), ("planet_in_house", "SATURN", (1, 4, 7, 10)))),
        (2, "mercury_saturn_soft_structured_thinking", "strength", "strength.communication.structured_thinking", ("communication_learning_documents", "structure_boundaries_control"), ("work", "documents", "communication", "decisions", "study"), 0.84, 0.72, (("aspect", "MERCURY", "SATURN", ("SEXTILE", "TRINE"), 4.0),)),
        (3, "mars_saturn_soft_measured_effort", "strength", "strength.energy.measured_effort", ("structure_boundaries_control", "energy_body_pacing"), ("work", "sport", "health", "decisions"), 0.82, 0.70, (("aspect", "MARS", "SATURN", ("SEXTILE", "TRINE"), 4.0),)),
        (4, "mercury_venus_soft_tactful_clarity", "strength", "strength.relationships.tactful_clarity", ("communication_learning_documents", "relationships_values_closeness"), ("relationships", "communication", "documents"), 0.82, 0.70, (("aspect", "MERCURY", "VENUS", ("SEXTILE", "TRINE"), 4.0),)),
        (5, "sun_jupiter_soft_broad_view", "strength", "strength.direction.broad_view", ("direction_growth_meaning", "creativity_visibility"), ("work", "decisions", "travel", "creativity", "study"), 0.82, 0.70, (("aspect", "SUN", "JUPITER", ("SEXTILE", "TRINE"), 4.0),)),
        (6, "moon_mercury_soft_name_reaction", "strength", "strength.inner_clarity.name_reaction", ("communication_learning_documents", "inner_clarity_recovery"), ("health", "communication", "decisions", "creativity"), 0.80, 0.68, (("aspect", "MOON", "MERCURY", ("SEXTILE", "TRINE"), 4.0),)),
        (7, "saturn_pluto_hard_control_under_pressure", "risk", "risk.structure.control_under_pressure", ("structure_boundaries_control", "resources_security"), ("work", "money", "documents", "decisions"), 0.88, 0.76, (("aspect", "SATURN", "PLUTO", ("OPPOSITION", "SQUARE"), 4.0),)),
        (8, "mercury_saturn_hard_overchecking", "risk", "risk.communication.overchecking", ("communication_learning_documents", "structure_boundaries_control"), ("work", "documents", "communication", "decisions", "study"), 0.84, 0.72, (("aspect", "MERCURY", "SATURN", ("OPPOSITION", "SQUARE"), 4.0),)),
        (9, "mars_saturn_hard_increase_pressure", "risk", "risk.energy.increase_pressure", ("structure_boundaries_control", "energy_body_pacing"), ("work", "sport", "health", "decisions"), 0.86, 0.74, (("aspect", "MARS", "SATURN", ("OPPOSITION", "SQUARE"), 4.0),)),
        (10, "venus_saturn_hard_defensive_strictness", "risk", "risk.relationships.defensive_strictness", ("relationships_values_closeness", "resources_security"), ("money", "relationships", "communication", "decisions"), 0.84, 0.72, (("aspect", "VENUS", "SATURN", ("OPPOSITION", "SQUARE"), 4.0),)),
        (11, "moon_pluto_hard_intensity_before_clarity", "risk", "risk.inner_clarity.intensity_before_clarity", ("relationships_values_closeness", "structure_boundaries_control", "inner_clarity_recovery"), ("relationships", "health", "communication", "decisions", "creativity"), 0.88, 0.76, (("aspect", "MOON", "PLUTO", ("OPPOSITION", "SQUARE"), 3.0),)),
        (12, "sun_uranus_hard_all_at_once", "risk", "risk.change.all_at_once", ("direction_growth_meaning", "creativity_visibility", "change_innovation"), ("work", "documents", "decisions", "creativity"), 0.84, 0.72, (("aspect", "SUN", "URANUS", ("OPPOSITION", "SQUARE"), 4.0),)),
    )
    assert actual == expected


# END_BLOCK: PERSONAL_PATTERN_CLOSURE_TESTS
