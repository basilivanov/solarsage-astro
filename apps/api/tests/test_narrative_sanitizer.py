# ############################################################################
# AI_HEADER: TEST_NARRATIVE_SANITIZER — machine-token leak guard coverage.
# ROLE: Verifies that public narrative text fails closed on known provider
#       signal-name artifacts and the sphere/facet contract.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-NARRATIVE-SANITIZER
# purpose: Exercise the deterministic narrative sanitizer independently from
#   either provider orchestration path.
# owns:
#   - apps/api/tests/test_narrative_sanitizer.py
# inputs: safe, provider-leaked, and sphere/facet-bound text samples.
# outputs: sanitizer boolean and safe-text assertions.
# dependencies: app.services.narrative_sanitizer, pytest.
# side_effects: none.
# emitted_logs: none.
# invariants: forbidden text is never returned as publishable text.
# failure_policy: pytest failure on an accepted machine token.
# END_MODULE_CONTRACT: M-TEST-NARRATIVE-SANITIZER

# START_MODULE_MAP: M-TEST-NARRATIVE-SANITIZER
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - FORBIDDEN_TOKENS: machine-token and sanitizer boundary assertions.
#   - GROUNDING: sphere/facet ownership, lot-name masking, polarity negation windows,
#     and the romantic-conversations null regression.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-NARRATIVE-SANITIZER

from __future__ import annotations

import pytest

from app.services.narrative_sanitizer import (
    has_forbidden_narrative_tokens,
    has_narrative_grounding_violation,
    sanitize_narrative_text,
)


@pytest.mark.parametrize(
    "text",
    [
        "Transit_Mars создаёт напряжение.",
        "Transit_ нельзя показывать.",
        "Natal_Moon поддерживает привычный ритм.",
        "Сигнал Planet нельзя показывать пользователю.",
        "Связка M, Mars не является человеческим описанием.",
        "Natal, Planet, Moon — служебный список.",
    ],
)
def test_machine_driver_artifacts_are_rejected(text: str) -> None:
    assert has_forbidden_narrative_tokens(text) is True
    assert sanitize_narrative_text(text) is None


def test_safe_russian_text_is_trimmed_and_kept() -> None:
    assert sanitize_narrative_text("  Выбери один понятный шаг.  ") == "Выбери один понятный шаг."


def test_grounding_accepts_a_valid_claim_for_its_sphere_and_polarity() -> None:
    assert has_narrative_grounding_violation(
        "Меркурий в гармонии с твоим Ураном помогает точнее проверять документы.",
        allowed_spheres={"documents"},
        polarity="supportive",
    ) is False


def test_grounding_rejects_an_unrelated_sphere() -> None:
    assert has_narrative_grounding_violation(
        "Встречи в сфере отношений могут стать более напряжёнными.",
        allowed_spheres={"documents"},
        polarity="supportive",
    ) is True


def test_grounding_rejects_an_explicit_polarity_antonym() -> None:
    assert has_narrative_grounding_violation(
        "В сфере документов всё легко складывается.",
        allowed_spheres={"documents"},
        polarity="tense",
    ) is True


def test_grounding_rejects_a_foreign_sphere_without_related_allowance() -> None:
    assert has_narrative_grounding_violation(
        "Коммуникация и обучение помогают проверить документы.",
        allowed_spheres={"documents"},
        polarity="supportive",
    ) is True


def test_personal_money_rejects_credit_and_tax_language() -> None:
    assert has_narrative_grounding_violation(
        "Кредит и налог требуют отдельного внимания.",
        allowed_spheres={"finance"},
        allowed_facets={"personal_money"},
        polarity="tense",
    ) is True


def test_financial_obligations_does_not_generalize_tension_to_finance() -> None:
    assert has_narrative_grounding_violation(
        "Во всех финансах сегодня напряжение.",
        allowed_spheres={"finance"},
        allowed_facets={"financial_obligations"},
        polarity="tense",
    ) is True


def test_nullable_finance_facet_rejects_purchase_and_debt_language() -> None:
    assert has_narrative_grounding_violation(
        "Покупка и долг требуют точного расчёта.",
        allowed_spheres={"finance"},
        polarity="mixed",
    ) is True


def test_health_claim_rejects_diagnosis() -> None:
    assert has_narrative_grounding_violation(
        "Диагноз нельзя выводить из этого сигнала.",
        allowed_spheres={"health"},
        allowed_facets={"general_condition"},
        polarity="mixed",
    ) is True


@pytest.mark.parametrize(
    ("text", "spheres", "facets"),
    [
        ("Финансы помогают внимательнее распределить личные средства.", {"finance"}, {"personal_money"}),
        ("Дом и семья поддерживают спокойную бытовую опору.", {"home_family"}, {None}),
        ("Планы помогают удержать долгосрочное направление.", {"friends_goals"}, {"long_term_goals"}),
    ],
)
def test_valid_new_spheres_and_facets_are_accepted(
    text: str,
    spheres: set[str],
    facets: set[str | None],
) -> None:
    normalized_facets = {facet for facet in facets if facet is not None}
    assert has_narrative_grounding_violation(
        text,
        allowed_spheres=spheres,
        allowed_facets=normalized_facets,
        polarity="supportive",
    ) is False


def test_foreign_facet_is_rejected_even_inside_the_same_sphere() -> None:
    assert has_narrative_grounding_violation(
        "Покупка требует отдельной проверки.",
        allowed_spheres={"finance"},
        allowed_facets={"personal_money"},
        polarity="mixed",
    ) is True


@pytest.mark.parametrize(
    ("spheres", "facets"),
    [({"money"}, set()), ({"finance"}, {"unknown_facet"})],
)
def test_unknown_sphere_or_facet_fails_closed(
    spheres: set[str],
    facets: set[str],
) -> None:
    assert has_narrative_grounding_violation(
        "Спокойный общий фокус.",
        allowed_spheres=spheres,
        allowed_facets=facets,
        polarity="mixed",
    ) is True


def test_s15_price_pattern_does_not_swallow_assessment_wording() -> None:
    # S15: «оценка/оценить» is not a purchases facet mention; «цена» still is.
    assert has_narrative_grounding_violation(
        "В финансовой сфере возможна активность, связанная с оценкой приоритетов.",
        allowed_spheres={"finance"},
        allowed_facets={"personal_money"},
        polarity="mixed",
    ) is False
    assert has_narrative_grounding_violation(
        "Цена покупки сегодня удачная.",
        allowed_spheres={"finance"},
        allowed_facets={"personal_money"},
        polarity="mixed",
    ) is True


def test_s15_romance_adjective_counts_as_facet_wording() -> None:
    # S15: «романтические отношения» is romance-facet wording, not sphere-broad.
    assert has_narrative_grounding_violation(
        "Романтические отношения могут испытывать напряжение из-за конфликтов.",
        allowed_spheres={"relationships"},
        allowed_facets={"romance"},
        polarity="tense",
    ) is False


def test_s17_named_marriage_lot_is_not_partnership_facet_language() -> None:
    assert has_narrative_grounding_violation(
        "Меркурий в гармонии с твоим жребием Брака: сегодня ощущается поддержка и легкость в симпатии и свиданиях.",
        allowed_spheres={"relationships"},
        allowed_facets={"romance"},
        polarity="supportive",
    ) is False


def test_s17_lot_name_mask_does_not_hide_a_second_bare_marriage_word() -> None:
    assert has_narrative_grounding_violation(
        "Жребий Брака активен: брак сегодня выгоден.",
        allowed_spheres={"relationships"},
        allowed_facets={"romance"},
        polarity="supportive",
    ) is True


def test_s17_mitigated_supportive_antonym_is_accepted() -> None:
    assert has_narrative_grounding_violation(
        "День помогает снизить напряжение в тренировках.",
        allowed_spheres={"sport"},
        allowed_facets={"training_routine"},
        polarity="supportive",
    ) is False


def test_s17_bare_supportive_antonym_is_still_rejected() -> None:
    assert has_narrative_grounding_violation(
        "Сегодня напряжение в тренировках.",
        allowed_spheres={"sport"},
        allowed_facets={"training_routine"},
        polarity="supportive",
    ) is True


def test_s17_negated_tense_antonym_is_accepted_but_bare_one_is_rejected() -> None:
    assert has_narrative_grounding_violation(
        "Утром будет не легко, к вечеру отпустит.",
        allowed_spheres={"health"},
        allowed_facets={"general_condition"},
        polarity="tense",
    ) is False
    assert has_narrative_grounding_violation(
        "День лёгкий и спокойный.",
        allowed_spheres={"health"},
        allowed_facets={"general_condition"},
        polarity="tense",
    ) is True


def test_s17_romantic_conversations_remain_a_null_regression() -> None:
    # The romance claim must remain rejected because «разговорах» belongs to
    # the foreign everyday_contacts facet.
    assert has_narrative_grounding_violation(
        "Сегодня ощущается напряжение в романтических разговорах.",
        allowed_spheres={"relationships"},
        allowed_facets={"romance"},
        polarity="tense",
    ) is True
