# ############################################################################
# AI_HEADER: TEST_HORIZON_LANGUAGE_CANON — isolated B2B1 language-canon closure regressions.
# ROLE: Proves language copy, timing templates, policy, and threshold mutations fail closed.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-HORIZON-LANGUAGE-CANON
# purpose: Exercise one-field language canon mutations through the public strict bundle loader.
# owns:
#   - apps/api/tests/test_horizon_language_canon.py
# inputs: Isolated temporary copies of the reviewed language canon.
# outputs: Regression assertions that invalid language canons are rejected without raw copy leaks.
# dependencies: pytest, B2B1 canon testkit, strict content-canon loader.
# side_effects: temporary YAML writes and process-local loader cache resets only.
# emitted_logs: none.
# invariants:
#   - Timing keys/placeholders and user-facing copy are closed.
#   - Loaded policy, not Python Russian literals, controls conditional validation.
# failure_policy: assertion failure identifies an accepted invalid language mutation.
# END_MODULE_CONTRACT: M-TEST-HORIZON-LANGUAGE-CANON

# START_MODULE_MAP: M-TEST-HORIZON-LANGUAGE-CANON
# public_entrypoints:
#   - test_language_mutation_matrix_rejects
#   - test_language_closed_key_matrix_rejects
#   - test_loaded_policy_owns_conditional_prefix
# semantic_blocks:
#   - HORIZON_LANGUAGE_MUTATION_HELPERS: isolated loader rejection helper.
#   - HORIZON_LANGUAGE_CLOSURE_TESTS: language/policy/threshold mutation coverage.
# owned_tests:
#   - apps/api/tests/test_horizon_language_canon.py
# END_MODULE_MAP: M-TEST-HORIZON-LANGUAGE-CANON

# START_BLOCK: HORIZON_LANGUAGE_MUTATION_HELPERS
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

LanguageMutation = Callable[[dict[str, object]], None]


def _reject_language(tmp_path: Path, mutate: LanguageMutation) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-LANGUAGE-CANON._reject_language
    # purpose: Apply one language mutation and prove the public loader rejects its bundle.
    # inputs: tmp_path - isolated pytest root; mutate - one-field language mapping mutation.
    # returns: none.
    # side_effects: temporary YAML write and loader-cache reset only.
    # emitted_logs: none.
    # error_behavior: assertion failure if the malformed canon loads.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-LANGUAGE-CANON._reject_language
    directory = copy_content_canon_dir(tmp_path)
    language = read_content_canon_yaml(directory, "horizon_language.ru.v1.yml")
    mutate(language)
    write_content_canon_yaml(directory, "horizon_language.ru.v1.yml", language)
    clear_horizon_content_canon_cache_for_tests()
    with pytest.raises(CanonValidationError):
        load_horizon_content_canons(directory)


# END_BLOCK: HORIZON_LANGUAGE_MUTATION_HELPERS


# START_BLOCK: HORIZON_LANGUAGE_CLOSURE_TESTS
@pytest.mark.parametrize(
    ("case", "mutate"),
    [
        ("wrong_schema", lambda data: data.__setitem__("schema_version", "wrong")),
        ("wrong_version", lambda data: data.__setitem__("version", "v2")),
        ("wrong_locale", lambda data: data.__setitem__("locale", "en")),
        ("extra_timing_template", lambda data: data["timing_templates"].__setitem__("extra", "x")),
        ("missing_timing_template", lambda data: data["timing_templates"].pop("range")),
        ("timing_placeholder_extra", lambda data: data["timing_templates"].__setitem__("peak", "{exact_at} {active_until}")),
        ("timing_unbalanced_brace", lambda data: data["timing_templates"].__setitem__("peak", "{exact_at")),
        ("technique_unknown_placeholder", lambda data: data["techniques"]["annual_profection"].__setitem__("why_it_matters_template", "{raw}")),
        ("blank_horizon_copy", lambda data: data["horizons"]["long"].__setitem__("eyebrow", "  ")),
        ("blank_theme_copy", lambda data: data["themes"]["structure_boundaries_control"].__setitem__("headline", "\t")),
        ("blank_policy_fragment", lambda data: data["conditional_policy"]["forbidden_certainty_fragments"].__setitem__(0, " ")),
        ("infinite_tone_thresholds", lambda data: data["tone_rules"].__setitem__("supportive_min", float("inf"))),
        ("negative_mixed_threshold", lambda data: data["tone_rules"].__setitem__("mixed_opposing_min", -0.1)),
    ],
)
def test_language_mutation_matrix_rejects(tmp_path: Path, case: str, mutate: LanguageMutation) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-LANGUAGE-CANON.test_language_mutation_matrix_rejects
    # purpose: Mutation-prove independently closed language schema, copy, template, and tone fields.
    # inputs: tmp_path - isolated test root; case/mutate - descriptive one-field mutation.
    # returns: none.
    # side_effects: temporary YAML writes only.
    # emitted_logs: none.
    # error_behavior: assertion failure if case loads.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-LANGUAGE-CANON.test_language_mutation_matrix_rejects
    _reject_language(tmp_path / case, mutate)


@pytest.mark.parametrize(
    ("case", "mutate"),
    [
        ("extra_horizon", lambda data: data["horizons"].__setitem__("other", {})),
        ("missing_tone", lambda data: data["tone_labels"].pop("mixed")),
        ("extra_state", lambda data: data["timing_state_labels"].__setitem__("other", "x")),
        ("missing_technique", lambda data: data["techniques"].pop("solar_return")),
        ("extra_theme", lambda data: data["themes"].__setitem__("other", {})),
        ("missing_sphere", lambda data: data["product_spheres"].pop("work")),
    ],
)
def test_language_closed_key_matrix_rejects(tmp_path: Path, case: str, mutate: LanguageMutation) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-LANGUAGE-CANON.test_language_closed_key_matrix_rejects
    # purpose: Prove all closed language key domains reject missing or unknown members.
    # inputs: tmp_path - isolated test root; case/mutate - one key-domain mutation.
    # returns: none.
    # side_effects: temporary YAML writes only.
    # emitted_logs: none.
    # error_behavior: assertion failure if a closed key mutation loads.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-LANGUAGE-CANON.test_language_closed_key_matrix_rejects
    _reject_language(tmp_path / case, mutate)


def test_loaded_policy_owns_conditional_prefix(tmp_path: Path) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-LANGUAGE-CANON.test_loaded_policy_owns_conditional_prefix
    # purpose: Prove a reviewed local policy replacement works without a Python hardcoded Russian prefix.
    # inputs: tmp_path - isolated test root.
    # returns: none.
    # side_effects: temporary YAML writes and loader-cache reset only.
    # emitted_logs: none.
    # error_behavior: assertion failure if validation ignores the loaded policy.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-LANGUAGE-CANON.test_loaded_policy_owns_conditional_prefix
    directory = copy_content_canon_dir(tmp_path)
    language = read_content_canon_yaml(directory, "horizon_language.ru.v1.yml")
    actions = read_content_canon_yaml(directory, "horizon_actions.ru.v1.yml")
    language["conditional_policy"]["required_prefixes"] = ["При условии "]
    for sphere in language["product_spheres"].values():
        sphere["manifestation_body"] = sphere["manifestation_body"].replace("Если ", "При условии ", 1)
    for matrix in actions["themes"].values():
        for horizon in ("long", "medium", "fast"):
            for bucket in ("do", "avoid"):
                for template in matrix[horizon][bucket]:
                    if template["conditional"]:
                        template["text"] = template["text"].replace("Если ", "При условии ", 1)
    write_content_canon_yaml(directory, "horizon_language.ru.v1.yml", language)
    write_content_canon_yaml(directory, "horizon_actions.ru.v1.yml", actions)
    clear_horizon_content_canon_cache_for_tests()
    assert load_horizon_content_canons(directory).language.conditional_policy.required_prefixes == ("При условии ",)


# END_BLOCK: HORIZON_LANGUAGE_CLOSURE_TESTS
