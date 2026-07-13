# ############################################################################
# AI_HEADER: TEST_HORIZON_ACTIONS_CANON — isolated B2B1 safety-matrix canon regressions.
# ROLE: Proves action metadata, loaded safety compatibility, coverage, and raw YAML explicitness.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-HORIZON-ACTIONS-CANON
# purpose: Exercise one-field action-canon mutations through the public strict bundle loader.
# owns:
#   - apps/api/tests/test_horizon_actions_canon.py
# inputs: Isolated temporary copies of the reviewed actions canon.
# outputs: Assertions over template closure, safety availability, and complete explicit YAML metadata.
# dependencies: pytest, B2B1 canon testkit, strict content-canon loader.
# side_effects: temporary YAML writes and loader-cache resets only.
# emitted_logs: none.
# invariants:
#   - 86 unique templates cover every theme/horizon/tone/verdict combination.
#   - Actions use only validated safety compatibility; anchors and merge keys do not exist.
# failure_policy: assertion failure identifies an accepted unsafe action mutation.
# END_MODULE_CONTRACT: M-TEST-HORIZON-ACTIONS-CANON

# START_MODULE_MAP: M-TEST-HORIZON-ACTIONS-CANON
# public_entrypoints:
#   - test_action_mutation_matrix_rejects
#   - test_action_templates_are_explicit_unique_and_cover_safety_matrix
# semantic_blocks:
#   - HORIZON_ACTION_MUTATION_HELPERS: isolated loader rejection helper.
#   - HORIZON_ACTION_SAFETY_TESTS: template metadata and coverage regression tests.
# owned_tests:
#   - apps/api/tests/test_horizon_actions_canon.py
# END_MODULE_MAP: M-TEST-HORIZON-ACTIONS-CANON

# START_BLOCK: HORIZON_ACTION_MUTATION_HELPERS
from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from app.schemas.horizon_content_canon_types import TONES, VERDICTS
from app.services.canon_service import CANON_DIR, CanonValidationError
from app.services.horizon_content_canon_service import (
    clear_horizon_content_canon_cache_for_tests,
    load_horizon_content_canons,
)

from ._horizon_content_testkit import (
    copy_content_canon_dir,
    read_content_canon_yaml,
    write_content_canon_yaml,
)

ActionMutation = Callable[[dict[str, object]], None]


def _reject_actions(tmp_path: Path, mutate: ActionMutation) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-ACTIONS-CANON._reject_actions
    # purpose: Apply one actions mutation and prove the public loader rejects its bundle.
    # inputs: tmp_path - isolated pytest root; mutate - one-field actions mapping mutation.
    # returns: none.
    # side_effects: temporary YAML write and loader-cache reset only.
    # emitted_logs: none.
    # error_behavior: assertion failure if the malformed canon loads.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-ACTIONS-CANON._reject_actions
    directory = copy_content_canon_dir(tmp_path)
    actions = read_content_canon_yaml(directory, "horizon_actions.ru.v1.yml")
    mutate(actions)
    write_content_canon_yaml(directory, "horizon_actions.ru.v1.yml", actions)
    clear_horizon_content_canon_cache_for_tests()
    with pytest.raises(CanonValidationError):
        load_horizon_content_canons(directory)


# END_BLOCK: HORIZON_ACTION_MUTATION_HELPERS


# START_BLOCK: HORIZON_ACTION_SAFETY_TESTS
@pytest.mark.parametrize(
    ("case", "mutate"),
    [
        ("wrong_schema", lambda data: data.__setitem__("schema_version", "wrong")),
        ("extra_top_key", lambda data: data.__setitem__("extra", True)),
        ("extra_template_key", lambda data: data["themes"]["structure_boundaries_control"]["long"]["do"][0].__setitem__("extra", True)),
        ("empty_template_tones", lambda data: data["themes"]["structure_boundaries_control"]["long"]["do"][0].__setitem__("tones", [])),
        ("empty_compatible_verdicts", lambda data: data["safety_classes"]["reflection"].__setitem__("compatible_verdicts", [])),
        ("action_unknown_placeholder", lambda data: data["themes"]["structure_boundaries_control"]["long"]["do"][0].__setitem__("text", "{unknown}")),
        ("avoid_intent_inside_do", lambda data: data["themes"]["structure_boundaries_control"]["long"]["do"][0].__setitem__("intent", "avoid_assumption")),
        ("positive_intent_inside_avoid", lambda data: data["themes"]["structure_boundaries_control"]["long"]["avoid"][0].__setitem__("intent", "reflect")),
        ("unordered_compatible_verdicts", lambda data: data["safety_classes"]["reflection"].__setitem__("compatible_verdicts", ["avoid", "good"])),
        ("conditional_prefix", lambda data: data["themes"]["structure_boundaries_control"]["medium"]["do"][0].__setitem__("text", "Без условия")),
        ("duplicate_normalized_text", lambda data: data["themes"]["structure_boundaries_control"]["long"]["avoid"][0].__setitem__("text", data["themes"]["structure_boundaries_control"]["long"]["do"][0]["text"])),
    ],
)
def test_action_mutation_matrix_rejects(tmp_path: Path, case: str, mutate: ActionMutation) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-ACTIONS-CANON.test_action_mutation_matrix_rejects
    # purpose: Mutation-prove independently closed action template and safety-class fields.
    # inputs: tmp_path - isolated test root; case/mutate - descriptive one-field mutation.
    # returns: none.
    # side_effects: temporary YAML writes only.
    # emitted_logs: none.
    # error_behavior: assertion failure if case loads.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-ACTIONS-CANON.test_action_mutation_matrix_rejects
    _reject_actions(tmp_path / case, mutate)


def test_action_templates_are_explicit_unique_and_cover_safety_matrix() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-ACTIONS-CANON.test_action_templates_are_explicit_unique_and_cover_safety_matrix
    # purpose: Prove the reviewed action file has explicit metadata and all 480 safety combinations available.
    # inputs: none.
    # returns: none.
    # side_effects: loader-cache use only.
    # emitted_logs: none.
    # error_behavior: assertion failure on anchors, duplicate templates, or a coverage deficit.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-ACTIONS-CANON.test_action_templates_are_explicit_unique_and_cover_safety_matrix
    raw = (CANON_DIR / "horizon_actions.ru.v1.yml").read_text(encoding="utf-8")
    assert "<<:" not in raw
    assert "&" not in raw
    assert "*" not in raw
    bundle = load_horizon_content_canons()
    templates = [
        template
        for matrix in bundle.actions.themes.values()
        for horizon in ("long", "medium", "fast")
        for bucket in ("do", "avoid")
        for template in getattr(getattr(matrix, horizon), bucket)
    ]
    assert len(templates) == len({template.id for template in templates}) == 86
    assert len({" ".join(template.text.split()).casefold() for template in templates}) == 86
    assert all(
        tuple(template.model_dump()) == ("id", "text", "intent", "safety_class", "conditional", "tones", "sphere_keys")
        for template in templates
    )
    minimums = {"long": (1, 1), "medium": (2, 1), "fast": (1, 1)}
    combinations = 0
    for matrix in bundle.actions.themes.values():
        for horizon, (need_do, need_avoid) in minimums.items():
            lists = getattr(matrix, horizon)
            for tone in TONES:
                for verdict in VERDICTS:
                    combinations += 1
                    def eligible(template):
                        # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-ACTIONS-CANON.eligible
                        # purpose: Check template compatibility for the current tone/verdict proof row.
                        # inputs: template - action template from the current horizon bucket.
                        # returns: True when the template supports the current tone/verdict pair.
                        # side_effects: none.
                        # emitted_logs: none.
                        # error_behavior: propagates missing safety-class lookup errors.
                        # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-ACTIONS-CANON.eligible
                        return tone in template.tones and verdict in bundle.actions.safety_classes[
                            template.safety_class
                        ].compatible_verdicts

                    assert sum(eligible(template) for template in lists.do) >= need_do
                    assert sum(eligible(template) for template in lists.avoid) >= need_avoid
    assert combinations == 480


def test_reviewed_safe_fallback_copy_is_exact() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-ACTIONS-CANON.test_reviewed_safe_fallback_copy_is_exact
    # purpose: Lock the thirteen architect-reviewed all-verdict reflection fallbacks to their exact approved copy.
    # inputs: none.
    # returns: none.
    # side_effects: loader-cache use only.
    # emitted_logs: none.
    # error_behavior: assertion failure on fallback wording, intent, or metadata drift.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-ACTIONS-CANON.test_reviewed_safe_fallback_copy_is_exact
    expected = {
        "structure.medium.fallback_working_signs": "Составьте короткий список признаков, по которым поймёте, что правило или граница действительно работает.",
        "communication.medium.fallback_fact_question_draft": "Запишите отдельно факт, вопрос и формулировку, которую пока не стоит отправлять.",
        "relationships.medium.fallback_known_unknown_boundary": "Запишите, какой факт вы знаете, чего пока не знаете и какую границу хотите прояснить.",
        "resources.medium.fallback_constraint_check": "Сверьте решение с одним заранее выбранным ограничением: сроком, суммой или запасом.",
        "energy.medium.fallback_load_marker": "Зафиксируйте текущий объём нагрузки и один признак, по которому заметите лишнюю интенсивность.",
        "home.medium.fallback_rule_cost": "Запишите одно бытовое правило, которое сейчас создаёт больше напряжения, чем пользы.",
        "home.medium.fallback_fact_not_generalization": "Отделите конкретное неудобство от общего вывода о доме или близких.",
        "clarity.medium.fallback_open_question": "Назовите один вопрос, который можно оставить открытым до появления новых фактов.",
        "direction.medium.fallback_pro_con_unknown": "Запишите один аргумент за, один против и один факт, которого пока не хватает.",
        "creativity.medium.fallback_one_element": "Запишите один элемент результата, который уже можно оценить отдельно от общего впечатления.",
        "change.medium.fallback_problem_first": "Сформулируйте, какую проблему должно решить изменение, прежде чем выбирать новый способ.",
        "creativity.fast.fallback_feedback_fact": "Запишите одну конкретную деталь обратной связи и отложите общую оценку результата.",
        "change.fast.fallback_record_small_change": "Запишите самое маленькое изменение, которое можно проверить позже без разрушения текущей системы.",
    }
    bundle = load_horizon_content_canons()
    actual = {
        template.id: template
        for matrix in bundle.actions.themes.values()
        for horizon in ("long", "medium", "fast")
        for bucket in ("do", "avoid")
        for template in getattr(getattr(matrix, horizon), bucket)
        if ".fallback_" in template.id
    }
    assert {template_id: template.text for template_id, template in actual.items()} == expected
    assert all(
        template.safety_class == "reflection"
        and template.conditional is False
        and template.tones == TONES
        for template in actual.values()
    )


# END_BLOCK: HORIZON_ACTION_SAFETY_TESTS
