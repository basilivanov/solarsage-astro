# ############################################################################
# AI_HEADER: TEST_TODAY_HORIZONS_CONTRACT — additive Today V2 horizons contract tests.
# ROLE: Verifies pure public model validation for the B1 horizons block and its cross-evidence integrity rules.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-HORIZONS-CONTRACT
# purpose: Exercise TodayV2 horizon wire models and TodayV2Block cross-reference validation without services, DB, or network.
# owns:
#   - apps/api/tests/test_today_horizons_contract.py
# inputs: pure dict factories for TodayV2Block / TodayV2HorizonsBlock / ActivationEvidence.
# outputs: pytest assertions.
# dependencies: copy, pytest, pydantic, app.schemas.today.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - factories stay pure and deterministic.
#   - tests assert structural contract behavior only.
# failure_policy: pytest failure.
# END_MODULE_CONTRACT: M-TEST-TODAY-HORIZONS-CONTRACT

# START_MODULE_MAP: M-TEST-TODAY-HORIZONS-CONTRACT
# public_entrypoints:
#   - pytest tests
# semantic_blocks:
#   - FACTORIES: valid baseline payload builders.
#   - MODEL_VALIDATION: per-rule contract assertions.
# owned_tests:
#   - apps/api/tests/test_today_horizons_contract.py
# END_MODULE_MAP: M-TEST-TODAY-HORIZONS-CONTRACT

from __future__ import annotations

from copy import deepcopy
from typing import get_args

import pytest
from pydantic import ValidationError

from app.schemas.horizon_selection import HorizonSelectionReason
from app.schemas.today import (
    TodayPayload,
    TodayV2Block,
    TodayV2HorizonPipelineAuditBuilt,
    TodayV2UnavailableHorizonSelectionReason,
)
from app.schemas.today_horizons import TodayV2HorizonsBlock, TodayV2HorizonTiming


# START_BLOCK: FACTORIES
def build_activation_evidence() -> list[dict[str, object]]:
    return [
        {
            "id": "act-annual-profection",
            "kind": "period",
            "technique": "annual_profection",
            "technique_family": "profection",
            "target_type": "planet",
            "target_key": "PLUTO",
            "target_planet": "Pluto",
            "target_frame": "natal",
            "source_planet": None,
            "source_frame": None,
            "aspect": None,
            "orb": None,
            "strength": 0.6,
            "polarity": "mixed",
            "phase": "period",
            "active": True,
            "active_from": "2026-05-12",
            "active_until": "2027-05-11",
            "exact_at": None,
            "debug": {},
            "evidence": "annual-profection-evidence",
        },
        {
            "id": "act-firdar-major",
            "kind": "period",
            "technique": "firdar_major",
            "technique_family": "firdar",
            "target_type": "planet",
            "target_key": "PLUTO",
            "target_planet": "Pluto",
            "target_frame": "natal",
            "source_planet": None,
            "source_frame": None,
            "aspect": None,
            "orb": None,
            "strength": 0.5,
            "polarity": "neutral",
            "phase": "period",
            "active": True,
            "active_from": None,
            "active_until": None,
            "exact_at": None,
            "debug": {},
            "evidence": "firdar-major-evidence",
        },
        {
            "id": "act-pluto-trine-saturn",
            "kind": "aspect",
            "technique": "transit_to_natal",
            "technique_family": "transit",
            "target_type": "planet",
            "target_key": "SATURN",
            "target_planet": "Saturn",
            "target_frame": "natal",
            "source_planet": "Pluto",
            "source_frame": "transit",
            "aspect": "trine",
            "orb": 0.01,
            "strength": 0.8,
            "polarity": "supportive",
            "phase": "applying",
            "active": True,
            "active_from": "2026-07-03T00:00:00Z",
            "active_until": "2026-07-18T00:00:00Z",
            "exact_at": "2026-07-10T11:32:00Z",
            "debug": {},
            "evidence": "pluto-trine-saturn-evidence",
        },
        {
            "id": "act-neptune-opp-saturn",
            "kind": "aspect",
            "technique": "transit_to_natal",
            "technique_family": "transit",
            "target_type": "planet",
            "target_key": "SATURN",
            "target_planet": "Saturn",
            "target_frame": "natal",
            "source_planet": "Neptune",
            "source_frame": "transit",
            "aspect": "opposition",
            "orb": 0.29,
            "strength": 0.55,
            "polarity": "tense",
            "phase": "applying",
            "active": True,
            "active_from": None,
            "active_until": None,
            "exact_at": None,
            "debug": {},
            "evidence": "neptune-opp-saturn-evidence",
        },
        {
            "id": "act-moon-opp-pluto",
            "kind": "aspect",
            "technique": "transit_to_natal",
            "technique_family": "transit",
            "target_type": "planet",
            "target_key": "PLUTO",
            "target_planet": "Pluto",
            "target_frame": "natal",
            "source_planet": "Moon",
            "source_frame": "transit",
            "aspect": "opposition",
            "orb": 1.05,
            "strength": 0.72,
            "polarity": "tense",
            "phase": "separating",
            "active": True,
            "active_from": "2026-07-07T21:00:00Z",
            "active_until": "2026-07-09T21:00:00Z",
            "exact_at": "2026-07-08T05:00:00Z",
            "debug": {},
            "evidence": "moon-opp-pluto-evidence",
        },
    ]


def grounded_item(
    item_id: str,
    kind: str,
    text: str,
    *,
    activation_ids: list[str],
    natal_fact_ids: list[str] | None = None,
    profile_fact_ids: list[str] | None = None,
    sphere_keys: list[str] | None = None,
    conditional: bool = False,
) -> dict[str, object]:
    return {
        "id": item_id,
        "kind": kind,
        "text": text,
        "conditional": conditional,
        "provenance": {
            "activation_ids": activation_ids,
            "natal_fact_ids": natal_fact_ids or [],
            "profile_fact_ids": profile_fact_ids or [],
            "sphere_keys": sphere_keys or [],
        },
    }


def build_horizons_block() -> dict[str, object]:
    long_timing = {
        "active_from": "2026-05-12",
        "exact_at": None,
        "active_until": "2027-05-11",
        "precision": "date",
        "state": "background",
        "range_label": "12 мая 2026 — 11 мая 2027",
        "peak_label": None,
        "state_label": "Фон уже действует",
        "timezone": "Europe/Moscow",
    }
    medium_timing = {
        "active_from": "2026-07-03T00:00:00Z",
        "exact_at": "2026-07-10T11:32:00Z",
        "active_until": "2026-07-18T00:00:00Z",
        "precision": "instant",
        "state": "building",
        "range_label": "3–18 июля",
        "peak_label": "Точный пик — 10 июля, 14:32 по Москве",
        "state_label": "Набирает силу",
        "timezone": "Europe/Moscow",
    }
    fast_timing = {
        "active_from": "2026-07-07T21:00:00Z",
        "exact_at": "2026-07-08T05:00:00Z",
        "active_until": "2026-07-09T21:00:00Z",
        "precision": "instant",
        "state": "peaked",
        "range_label": "8–10 июля по Москве",
        "peak_label": "Пик был 8 июля в 08:00",
        "state_label": "Пик уже пройден",
        "timezone": "Europe/Moscow",
    }
    return {
        "schema_version": "today-horizons.v1",
        "guidance_mode": "deterministic",
        "intro": {
            "eyebrow": "Личная логика периода",
            "headline": "Опору сейчас лучше перестраивать без резких движений",
            "body": "Долгий цикл меняет отношение к ответственности и контролю, ближайшие недели дают окно для одного практического изменения, а сегодняшний эмоциональный пик показывает, где не стоит торопиться.",
            "theme_key": "structure_boundaries_control",
            "activation_ids": [
                "act-annual-profection",
                "act-firdar-major",
                "act-pluto-trine-saturn",
                "act-neptune-opp-saturn",
                "act-moon-opp-pluto",
            ],
        },
        "items": [
            {
                "id": "hz-long",
                "horizon": "long",
                "tone": "mixed",
                "eyebrow": "Долгий цикл · что перестраивать",
                "title": "Пересобрать опору, границы и отношение к контролю",
                "summary": "Главная тема года связана с тем, как вы распределяете ответственность и что считаете надёжной опорой.",
                "plain_explanation": "Это не про резкий разрыв, а про длинную перестройку правил, на которые вы опираетесь каждый день.",
                "timing": long_timing,
                "likely_spheres": ["work", "decisions", "money"],
                "manifestations": [
                    {
                        "id": "mf-long-role",
                        "title": "Новая рамка для роли и обязанностей",
                        "body": "Можно заметить, что привычный объём контроля больше не даёт прежней устойчивости и требует новой структуры.",
                        "condition": "Если сейчас вы обсуждаете новую роль или объём ответственности…",
                        "sphere_keys": ["work", "decisions"],
                        "provenance": {
                            "activation_ids": ["act-annual-profection"],
                            "natal_fact_ids": ["natal.pluto_control_pattern"],
                            "profile_fact_ids": [],
                            "sphere_keys": ["work", "decisions"],
                        },
                    },
                    {
                        "id": "mf-long-money",
                        "title": "Опора в деньгах и ресурсах",
                        "body": "Фон года помогает увидеть, какие финансовые решения держатся на реальной опоре, а какие — только на привычке всё контролировать.",
                        "condition": None,
                        "sphere_keys": ["money"],
                        "provenance": {
                            "activation_ids": ["act-firdar-major"],
                            "natal_fact_ids": [],
                            "profile_fact_ids": ["profile.scope_finance_mode"],
                            "sphere_keys": ["money"],
                        },
                    },
                ],
                "strength": grounded_item(
                    "gi-long-strength",
                    "strength",
                    "У вас уже есть способность удерживать долгий курс и не рушить всё из-за краткого напряжения.",
                    activation_ids=["act-annual-profection"],
                    natal_fact_ids=["natal.saturn_resilience_strength"],
                    sphere_keys=["work"],
                ),
                "risk": grounded_item(
                    "gi-long-risk",
                    "risk",
                    "Привычка держать под контролем каждую деталь может мешать заметить, где системе нужна новая форма.",
                    activation_ids=["act-firdar-major"],
                    natal_fact_ids=["natal.pluto_control_pattern"],
                    sphere_keys=["decisions"],
                ),
                "actions": {
                    "heading": "Что стоит перестраивать",
                    "valid_until": "2027-05-11",
                    "valid_until_label": "Эта рамка актуальна до 11 мая 2027",
                    "do": [
                        grounded_item(
                            "gi-long-do-1",
                            "action",
                            "Выберите один устойчивый процесс, который можно упростить без потери качества.",
                            activation_ids=["act-annual-profection"],
                            sphere_keys=["work"],
                        ),
                        grounded_item(
                            "gi-long-do-2",
                            "action",
                            "Назовите одну границу ответственности, которую пора оформить словами и правилами.",
                            activation_ids=["act-firdar-major"],
                            sphere_keys=["decisions"],
                        ),
                    ],
                    "avoid": [
                        grounded_item(
                            "gi-long-avoid-1",
                            "avoid",
                            "Не превращайте усталость от контроля в ультиматум себе или другим.",
                            activation_ids=["act-firdar-major"],
                            sphere_keys=["work"],
                        )
                    ],
                },
                "technique_explanations": [
                    {
                        "technique": "annual_profection",
                        "label": "Профекция",
                        "what_it_is": "Профекция — символический годовой цикл, который показывает, какая тема сейчас получает больше веса во всём вашем году.",
                        "why_it_matters_now": "С 12 мая 2026 по 11 мая 2027 этот цикл делает тему контроля, границ и опоры системной, а не случайной.",
                        "timing": long_timing,
                        "activation_ids": ["act-annual-profection"],
                    },
                    {
                        "technique": "firdar_major",
                        "label": "Фирдар",
                        "what_it_is": "Фирдар — длинная последовательность периодов, которая показывает, какие темы остаются на переднем плане дольше обычного.",
                        "why_it_matters_now": "Этот длинный период поддерживает ту же задачу: перестраивать опору постепенно и без резких жестов.",
                        "timing": None,
                        "activation_ids": ["act-firdar-major"],
                    },
                ],
                "activation_ids": ["act-annual-profection", "act-firdar-major"],
            },
            {
                "id": "hz-medium",
                "horizon": "medium",
                "tone": "mixed",
                "eyebrow": "Текущий период · что попробовать",
                "title": "Проверить одну новую границу до 18 июля",
                "summary": "Ближайшие недели подходят для одного точного эксперимента с правилами, деньгами или объёмом обязательств.",
                "plain_explanation": "Сейчас полезнее менять один элемент системы и смотреть на результат, чем пытаться перестроить всё сразу.",
                "timing": medium_timing,
                "likely_spheres": ["work", "money", "decisions"],
                "manifestations": [
                    {
                        "id": "mf-medium-terms",
                        "title": "Проверка условий и обязанностей",
                        "body": "Подходит окно, чтобы уточнить одно правило, дедлайн или границу ответственности и посмотреть, как меняется нагрузка.",
                        "condition": None,
                        "sphere_keys": ["work", "decisions"],
                        "provenance": {
                            "activation_ids": ["act-pluto-trine-saturn"],
                            "natal_fact_ids": ["natal.saturn_resilience_strength"],
                            "profile_fact_ids": [],
                            "sphere_keys": ["work", "decisions"],
                        },
                    },
                    {
                        "id": "mf-medium-budget",
                        "title": "Осторожность в решениях о ресурсе",
                        "body": "Одновременно важно перепроверять ожидания и условия, чтобы желание стабильности не увело в неясное решение.",
                        "condition": None,
                        "sphere_keys": ["money"],
                        "provenance": {
                            "activation_ids": ["act-neptune-opp-saturn"],
                            "natal_fact_ids": [],
                            "profile_fact_ids": ["profile.scope_finance_mode"],
                            "sphere_keys": ["money"],
                        },
                    },
                ],
                "strength": grounded_item(
                    "gi-medium-strength",
                    "strength",
                    "Умение действовать по шагам помогает вам проверять новую рамку без лишней драмы.",
                    activation_ids=["act-pluto-trine-saturn"],
                    natal_fact_ids=["natal.saturn_resilience_strength"],
                    sphere_keys=["work"],
                ),
                "risk": grounded_item(
                    "gi-medium-risk",
                    "risk",
                    "Желание быстрее вернуть контроль может подтолкнуть к решению, которое выглядит ясным только из-за напряжения.",
                    activation_ids=["act-neptune-opp-saturn"],
                    natal_fact_ids=["natal.neptune_uncertainty_risk"],
                    sphere_keys=["money"],
                ),
                "actions": {
                    "heading": "Что можно попробовать до 18 июля",
                    "valid_until": "2026-07-18T00:00:00Z",
                    "valid_until_label": "Этот эксперимент актуален до 18 июля",
                    "do": [
                        grounded_item(
                            "gi-medium-do-1",
                            "action",
                            "Разделите свои обязательства и привычные лишние задачи в одном рабочем контуре.",
                            activation_ids=["act-pluto-trine-saturn"],
                            sphere_keys=["work"],
                        ),
                        grounded_item(
                            "gi-medium-do-2",
                            "action",
                            "Обсудите одно конкретное условие только если есть спокойный контекст для разговора.",
                            activation_ids=["act-neptune-opp-saturn"],
                            sphere_keys=["decisions"],
                            conditional=True,
                        ),
                    ],
                    "avoid": [
                        grounded_item(
                            "gi-medium-avoid-1",
                            "avoid",
                            "Не принимайте резкое решение только ради ощущения немедленного контроля.",
                            activation_ids=["act-neptune-opp-saturn"],
                            sphere_keys=["money"],
                        )
                    ],
                },
                "technique_explanations": [
                    {
                        "technique": "transit_to_natal",
                        "label": "Транзит к натальной опоре",
                        "what_it_is": "Такой расчёт показывает, как текущие движения неба временно усиливают уже существующую личную тему.",
                        "why_it_matters_now": "С 3 по 18 июля окно подходит для одного проверяемого изменения: оно поддержано реальной устойчивостью, но требует трезвой сверки ожиданий.",
                        "timing": medium_timing,
                        "activation_ids": ["act-pluto-trine-saturn", "act-neptune-opp-saturn"],
                    }
                ],
                "activation_ids": ["act-pluto-trine-saturn", "act-neptune-opp-saturn"],
            },
            {
                "id": "hz-fast",
                "horizon": "fast",
                "tone": "tense",
                "eyebrow": "Быстрый триггер · что сделать сегодня",
                "title": "Сначала назвать реакцию, потом отвечать",
                "summary": "Сегодняшний пик показывает, где импульс может оказаться сильнее самого повода.",
                "plain_explanation": "Сейчас полезнее сделать короткую паузу, чем отвечать из автоматической защиты.",
                "timing": fast_timing,
                "likely_spheres": ["decisions", "relationships", "health"],
                "manifestations": [
                    {
                        "id": "mf-fast-trigger",
                        "title": "Точка мгновенной реакции",
                        "body": "Короткий пик помогает заметить момент, где сначала поднимается реакция, а уже потом появляется желание отвечать или решать.",
                        "condition": None,
                        "sphere_keys": ["decisions", "relationships"],
                        "provenance": {
                            "activation_ids": ["act-moon-opp-pluto"],
                            "natal_fact_ids": ["natal.pluto_control_pattern"],
                            "profile_fact_ids": [],
                            "sphere_keys": ["decisions", "relationships"],
                        },
                    }
                ],
                "strength": None,
                "risk": grounded_item(
                    "gi-fast-risk",
                    "risk",
                    "На пике проще ответить из напряжения, чем из того, что вы действительно хотите сказать или сделать.",
                    activation_ids=["act-moon-opp-pluto"],
                    natal_fact_ids=["natal.moon_reactivity_risk"],
                    sphere_keys=["decisions"],
                ),
                "actions": {
                    "heading": "Что сделать сегодня",
                    "valid_until": "2026-07-09T21:00:00Z",
                    "valid_until_label": "Этот шаг полезен до конца короткого окна",
                    "do": [
                        grounded_item(
                            "gi-fast-do-1",
                            "action",
                            "Назовите свою реакцию про себя и только потом решайте, нужно ли отвечать сразу.",
                            activation_ids=["act-moon-opp-pluto"],
                            sphere_keys=["decisions"],
                            conditional=True,
                        )
                    ],
                    "avoid": [
                        grounded_item(
                            "gi-fast-avoid-1",
                            "avoid",
                            "Не принимайте окончательный тон разговора на первом импульсе.",
                            activation_ids=["act-moon-opp-pluto"],
                            sphere_keys=["relationships"],
                        )
                    ],
                },
                "technique_explanations": [
                    {
                        "technique": "transit_to_natal",
                        "label": "Короткий эмоциональный триггер",
                        "what_it_is": "Это короткое окно показывает, где текущая реакция особенно быстро цепляет уже знакомую личную тему.",
                        "why_it_matters_now": "С 8 по 10 июля по Москве короткий пик уже прошёл, поэтому сегодня полезнее заметить реакцию и уменьшить скорость ответа.",
                        "timing": fast_timing,
                        "activation_ids": ["act-moon-opp-pluto"],
                    }
                ],
                "activation_ids": ["act-moon-opp-pluto"],
            },
        ],
        "warnings": [],
    }


def build_today_v2_block() -> dict[str, object]:
    return {
        "activation_summary": {
            "headline": "Контроль и перестройка сходятся в одну тему.",
            "top_activated_targets": [],
        },
        "activation_evidence": build_activation_evidence(),
        "score_breakdown": {},
        "why_today": [],
        "audit": {
            "payload_version": "today.v2",
            "calculation_version": "calc-v1",
            "scoring_version": "scoring-v1",
            "available": True,
            "canon_versions": {},
        },
        "horizons": build_horizons_block(),
    }


def build_complete_today_payload(
    *,
    payload_version: str,
    frontend_payload_version: int,
    audit_payload_version: str,
    include_pipeline_audit: bool,
) -> dict[str, object]:
    v2 = build_today_v2_block()
    audit = v2["audit"]  # type: ignore[assignment]
    audit["payload_version"] = audit_payload_version
    if include_pipeline_audit:
        audit["horizon_pipeline"] = {
            "status": "built",
            "reason": "selected",
            "selected_count": 3,
        }
    return {
        "meta": {
            "schema_version": "today/v1",
            "contract_version": 3,
            "calculation_version": "ss-calc-1.2.0",
            "normalization_version": 1,
            "scoring_version": "ss-scoring-2.0",
            "prompt_version": 2,
            "content_version": 10,
            "generated_at": "2026-07-12T12:00:00Z",
            "payload_version": payload_version,
            "frontend_payload_version": frontend_payload_version,
        },
        "date": "2026-07-12",
        "title": "Сегодня",
        "headline": "Структурный тест",
        "access": {"state": "full", "reason": "active_subscription"},
        "day_status": "steady",
        "day_summary": {"status_label": "Ровный день", "status_line": "Структурный тест", "facts": []},
        "concrete_advice": {
            "rows": [],
            "counts": {"good": 0, "caution": 0, "avoid": 0, "neutral": 0},
        },
        "top_flags": [],
        "reading": {"paragraphs": ["Структурный тест"]},
        "why_this_happens": {"sections": []},
        "week_strip": [],
        "microcopy": [],
        "v2": v2,
    }
# END_BLOCK: FACTORIES


# START_BLOCK: MODEL_VALIDATION
def test_complete_valid_snake_input_validates() -> None:
    model = TodayV2Block.model_validate(build_today_v2_block())
    assert model.horizons is not None
    assert [item.horizon for item in model.horizons.items] == ["long", "medium", "fast"]


def test_camel_dump_round_trips() -> None:
    model = TodayV2Block.model_validate(build_today_v2_block())
    dumped = model.model_dump(by_alias=True)
    assert "activationSummary" in dumped
    assert "activationEvidence" in dumped
    assert "horizons" in dumped
    assert "schemaVersion" in dumped["horizons"]
    assert TodayV2Block.model_validate(dumped).model_dump() == model.model_dump()


@pytest.mark.parametrize("value", [{"drop_horizons": True}, {"horizons": None}])
def test_horizons_omitted_or_null_accepted_in_today_v2_block(value: dict[str, object]) -> None:
    payload = build_today_v2_block()
    if value.get("drop_horizons"):
        payload.pop("horizons")
    else:
        payload.update(value)
    model = TodayV2Block.model_validate(payload)
    assert model.horizons is None


def test_horizon_pipeline_audit_union_rejects_invalid_local_combo() -> None:
    payload = build_today_v2_block()
    payload["audit"]["horizon_pipeline"] = {  # type: ignore[index]
        "status": "built",
        "reason": "missing_fast",
        "selected_count": 0,
    }
    with pytest.raises(ValidationError):
        TodayV2Block.model_validate(payload)


def test_horizon_pipeline_audit_built_requires_horizons() -> None:
    payload = build_today_v2_block()
    payload["audit"]["horizon_pipeline"] = {  # type: ignore[index]
        "status": "built",
        "reason": "selected",
        "selected_count": 3,
    }
    payload["horizons"] = None
    with pytest.raises(ValidationError, match="built horizon pipeline requires horizons"):
        TodayV2Block.model_validate(payload)


def test_horizon_pipeline_audit_unavailable_requires_null_horizons() -> None:
    payload = build_today_v2_block()
    payload["audit"]["horizon_pipeline"] = {  # type: ignore[index]
        "status": "unavailable",
        "reason": "missing_fast",
        "selected_count": 0,
    }
    with pytest.raises(ValidationError, match="unavailable horizon pipeline requires null horizons"):
        TodayV2Block.model_validate(payload)


def test_current_today_payload_requires_pipeline_audit() -> None:
    payload = build_complete_today_payload(
        payload_version="today.v2.1",
        frontend_payload_version=3,
        audit_payload_version="today.v2.1",
        include_pipeline_audit=False,
    )
    with pytest.raises(ValidationError, match="current V2 identity requires horizon pipeline audit"):
        TodayPayload.model_validate(payload)


@pytest.mark.parametrize(
    ("payload_version", "frontend_payload_version"),
    [("today.v2.1", 2), ("today.v2", 3)],
)
def test_current_today_payload_rejects_mismatched_identity_pair(
    payload_version: str,
    frontend_payload_version: int,
) -> None:
    payload = build_complete_today_payload(
        payload_version=payload_version,
        frontend_payload_version=frontend_payload_version,
        audit_payload_version=payload_version,
        include_pipeline_audit=True,
    )
    with pytest.raises(ValidationError, match="exact payload/frontend version pair"):
        TodayPayload.model_validate(payload)


def test_previous_today_payload_pair_without_pipeline_audit_remains_compatible() -> None:
    payload = build_complete_today_payload(
        payload_version="today.v2",
        frontend_payload_version=2,
        audit_payload_version="today.v2",
        include_pipeline_audit=False,
    )
    parsed = TodayPayload.model_validate(payload)
    assert parsed.meta.payload_version == "today.v2"
    assert parsed.meta.frontend_payload_version == 2
    assert parsed.v2 is not None
    assert parsed.v2.audit.horizon_pipeline is None


def test_current_today_payload_pair_with_matching_audit_is_valid() -> None:
    payload = build_complete_today_payload(
        payload_version="today.v2.1",
        frontend_payload_version=3,
        audit_payload_version="today.v2.1",
        include_pipeline_audit=True,
    )
    parsed = TodayPayload.model_validate(payload)
    assert parsed.v2 is not None
    assert parsed.v2.audit.payload_version == parsed.meta.payload_version
    assert parsed.v2.audit.horizon_pipeline is not None
    assert parsed.v2.audit.horizon_pipeline.status == "built"


def test_current_today_payload_rejects_audit_payload_version_mismatch() -> None:
    payload = build_complete_today_payload(
        payload_version="today.v2.1",
        frontend_payload_version=3,
        audit_payload_version="today.v2",
        include_pipeline_audit=True,
    )
    with pytest.raises(ValidationError, match="audit payload version must match meta"):
        TodayPayload.model_validate(payload)


def test_v1_today_payload_with_null_v2_remains_compatible() -> None:
    payload = build_complete_today_payload(
        payload_version="today.v2",
        frontend_payload_version=2,
        audit_payload_version="today.v2",
        include_pipeline_audit=False,
    )
    payload["meta"]["payload_version"] = "today.v1"  # type: ignore[index]
    payload["meta"]["frontend_payload_version"] = 1  # type: ignore[index]
    payload["v2"] = None
    assert TodayPayload.model_validate(payload).v2 is None


def test_public_horizon_reason_union_matches_internal_selector_reasons() -> None:
    public_unavailable = set(get_args(TodayV2UnavailableHorizonSelectionReason))
    internal_unavailable = set(get_args(HorizonSelectionReason)) - {"selected"}
    built_reasons = set(get_args(TodayV2HorizonPipelineAuditBuilt.model_fields["reason"].annotation))
    assert public_unavailable == internal_unavailable
    assert built_reasons == {"selected"}


def test_exact_item_order_accepted() -> None:
    model = TodayV2HorizonsBlock.model_validate(build_horizons_block())
    assert [item.horizon for item in model.items] == ["long", "medium", "fast"]


def test_wrong_order_rejected() -> None:
    payload = build_horizons_block()
    payload["items"][0], payload["items"][1] = payload["items"][1], payload["items"][0]  # type: ignore[index]
    with pytest.raises(ValidationError, match="horizons-must-be-long-medium-fast"):
        TodayV2HorizonsBlock.model_validate(payload)


@pytest.mark.parametrize("new_length", [2, 4])
def test_fewer_or_more_than_three_items_rejected(new_length: int) -> None:
    payload = build_horizons_block()
    items = payload["items"]  # type: ignore[assignment]
    if new_length == 2:
        payload["items"] = items[:2]
    else:
        payload["items"] = [*items, deepcopy(items[-1])]  # type: ignore[index]
    with pytest.raises(ValidationError):
        TodayV2HorizonsBlock.model_validate(payload)


def test_duplicate_horizon_grounded_and_manifestation_ids_rejected() -> None:
    payload = build_horizons_block()
    payload["items"][1]["id"] = "hz-long"  # type: ignore[index]
    with pytest.raises(ValidationError, match="duplicate:hz-long"):
        TodayV2HorizonsBlock.model_validate(payload)

    payload = build_horizons_block()
    payload["items"][1]["strength"]["id"] = "gi-long-strength"  # type: ignore[index]
    with pytest.raises(ValidationError, match="duplicate-grounded-id"):
        TodayV2HorizonsBlock.model_validate(payload)

    payload = build_horizons_block()
    payload["items"][1]["manifestations"][0]["id"] = "mf-long-role"  # type: ignore[index]
    with pytest.raises(ValidationError, match="duplicate-manifestation-id"):
        TodayV2HorizonsBlock.model_validate(payload)


def test_duplicate_normalized_action_text_across_horizons_rejected() -> None:
    payload = build_horizons_block()
    payload["items"][1]["actions"]["do"][0]["text"] = "Выберите один устойчивый процесс, который можно упростить без потери качества!!!"  # type: ignore[index]
    with pytest.raises(ValidationError, match="duplicate-normalized-action-text"):
        TodayV2HorizonsBlock.model_validate(payload)


def test_empty_provenance_rejected() -> None:
    payload = build_horizons_block()
    payload["items"][0]["strength"]["provenance"] = {  # type: ignore[index]
        "activation_ids": [],
        "natal_fact_ids": [],
        "profile_fact_ids": [],
        "sphere_keys": [],
    }
    with pytest.raises(ValidationError, match="at-least-one-source-list-required"):
        TodayV2HorizonsBlock.model_validate(payload)


def test_dangling_horizon_activation_rejected() -> None:
    payload = build_today_v2_block()
    payload["horizons"]["items"][0]["activation_ids"].append("act-missing")  # type: ignore[index]
    with pytest.raises(ValidationError, match="unknown-activation-id"):
        TodayV2Block.model_validate(payload)


def test_dangling_nested_provenance_activation_rejected() -> None:
    payload = build_today_v2_block()
    payload["horizons"]["items"][0]["manifestations"][0]["provenance"]["activation_ids"] = ["act-missing"]  # type: ignore[index]
    payload["horizons"]["items"][0]["activation_ids"].append("act-missing")  # type: ignore[index]
    with pytest.raises(ValidationError, match="unknown-activation-id"):
        TodayV2Block.model_validate(payload)


def test_intro_activation_outside_item_union_rejected() -> None:
    payload = build_horizons_block()
    payload["intro"]["activation_ids"].append("act-not-in-items")  # type: ignore[index]
    with pytest.raises(ValidationError, match="intro-ids-outside-item-union"):
        TodayV2HorizonsBlock.model_validate(payload)


def test_technique_mismatch_and_reference_rules_rejected() -> None:
    payload = build_today_v2_block()
    payload["horizons"]["items"][0]["technique_explanations"][0]["technique"] = "solar_return"  # type: ignore[index]
    with pytest.raises(ValidationError, match="technique-mismatch-with-evidence"):
        TodayV2Block.model_validate(payload)

    payload = build_today_v2_block()
    payload["horizons"]["items"][0]["technique_explanations"][0]["activation_ids"] = ["act-moon-opp-pluto"]  # type: ignore[index]
    with pytest.raises(ValidationError, match="technique-activation-id-outside-horizon"):
        TodayV2Block.model_validate(payload)


def test_invalid_product_sphere_rejected() -> None:
    payload = build_horizons_block()
    payload["items"][0]["likely_spheres"] = ["unknown-sphere"]  # type: ignore[index]
    with pytest.raises(ValidationError):
        TodayV2HorizonsBlock.model_validate(payload)


def test_manifestation_spheres_outside_likely_spheres_rejected() -> None:
    payload = build_horizons_block()
    payload["items"][0]["manifestations"][0]["sphere_keys"] = ["shopping"]  # type: ignore[index]
    with pytest.raises(ValidationError, match="manifestation-spheres-outside-likely-spheres"):
        TodayV2HorizonsBlock.model_validate(payload)


def test_manifestation_provenance_spheres_outside_likely_spheres_rejected() -> None:
    payload = build_horizons_block()
    payload["items"][0]["manifestations"][0]["provenance"]["sphere_keys"] = ["shopping"]  # type: ignore[index]
    with pytest.raises(ValidationError, match="provenance-spheres-outside-likely-spheres"):
        TodayV2HorizonsBlock.model_validate(payload)


def test_strength_provenance_spheres_outside_likely_spheres_rejected() -> None:
    payload = build_horizons_block()
    payload["items"][0]["strength"]["provenance"]["sphere_keys"] = ["shopping"]  # type: ignore[index]
    with pytest.raises(ValidationError, match=r"todayV2Horizon\.strength\.provenance.*provenance-spheres-outside-likely-spheres.*id=gi-long-strength"):
        TodayV2HorizonsBlock.model_validate(payload)


def test_risk_provenance_spheres_outside_likely_spheres_rejected() -> None:
    payload = build_horizons_block()
    payload["items"][0]["risk"]["provenance"]["sphere_keys"] = ["shopping"]  # type: ignore[index]
    with pytest.raises(ValidationError, match=r"todayV2Horizon\.risk\.provenance.*provenance-spheres-outside-likely-spheres.*id=gi-long-risk"):
        TodayV2HorizonsBlock.model_validate(payload)


def test_do_action_provenance_spheres_outside_likely_spheres_rejected() -> None:
    payload = build_horizons_block()
    payload["items"][0]["actions"]["do"][0]["provenance"]["sphere_keys"] = ["shopping"]  # type: ignore[index]
    with pytest.raises(ValidationError, match=r"todayV2Horizon\.actions\.do\[gi-long-do-1\]\.provenance.*provenance-spheres-outside-likely-spheres.*id=gi-long-do-1"):
        TodayV2HorizonsBlock.model_validate(payload)


def test_avoid_action_provenance_spheres_outside_likely_spheres_rejected() -> None:
    payload = build_horizons_block()
    payload["items"][0]["actions"]["avoid"][0]["provenance"]["sphere_keys"] = ["shopping"]  # type: ignore[index]
    with pytest.raises(ValidationError, match=r"todayV2Horizon\.actions\.avoid\[gi-long-avoid-1\]\.provenance.*provenance-spheres-outside-likely-spheres.*id=gi-long-avoid-1"):
        TodayV2HorizonsBlock.model_validate(payload)


def test_date_precision_format_order_and_exact_boundaries() -> None:
    valid = TodayV2HorizonTiming.model_validate(
        {
            "active_from": "2026-05-12",
            "active_until": "2026-05-20",
            "exact_at": "2026-05-16",
            "precision": "date",
            "state": "active",
            "range_label": "12–20 мая",
            "peak_label": "Пик — 16 мая",
            "state_label": "В процессе",
            "timezone": "Europe/Moscow",
        }
    )
    assert valid.exact_at == "2026-05-16"

    with pytest.raises(ValidationError, match="expected-date-precision"):
        TodayV2HorizonTiming.model_validate(
            {
                "active_from": "2026-05-12T00:00:00Z",
                "active_until": "2026-05-20",
                "precision": "date",
                "state": "background",
                "range_label": "12–20 мая",
                "state_label": "Фон",
                "timezone": "Europe/Moscow",
            }
        )

    with pytest.raises(ValidationError, match="active-from-after-active-until"):
        TodayV2HorizonTiming.model_validate(
            {
                "active_from": "2026-05-21",
                "active_until": "2026-05-20",
                "precision": "date",
                "state": "background",
                "range_label": "21–20 мая",
                "state_label": "Фон",
                "timezone": "Europe/Moscow",
            }
        )

    with pytest.raises(ValidationError, match="exact-at-outside-range"):
        TodayV2HorizonTiming.model_validate(
            {
                "active_from": "2026-05-12",
                "active_until": "2026-05-20",
                "exact_at": "2026-05-21",
                "precision": "date",
                "state": "active",
                "range_label": "12–20 мая",
                "peak_label": "Пик",
                "state_label": "В процессе",
                "timezone": "Europe/Moscow",
            }
        )


def test_instant_requires_timezone_and_handles_offsets_deterministically() -> None:
    timing = TodayV2HorizonTiming.model_validate(
        {
            "active_from": "2026-07-03T03:00:00+03:00",
            "active_until": "2026-07-18T03:00:00+03:00",
            "exact_at": "2026-07-10T14:32:00+03:00",
            "precision": "instant",
            "state": "building",
            "range_label": "3–18 июля",
            "peak_label": "Пик",
            "state_label": "Набирает силу",
            "timezone": "Europe/Moscow",
        }
    )
    assert timing.exact_at == "2026-07-10T14:32:00+03:00"

    with pytest.raises(ValidationError, match="expected-instant-precision"):
        TodayV2HorizonTiming.model_validate(
            {
                "active_from": "2026-07-03T00:00:00",
                "active_until": "2026-07-18T00:00:00Z",
                "precision": "instant",
                "state": "building",
                "range_label": "3–18 июля",
                "state_label": "Набирает силу",
                "timezone": "Europe/Moscow",
            }
        )


def test_exact_state_without_exact_at_rejected() -> None:
    with pytest.raises(ValidationError, match="exact-state-requires-exact-at"):
        TodayV2HorizonTiming.model_validate(
            {
                "active_from": "2026-07-03T00:00:00Z",
                "active_until": "2026-07-18T00:00:00Z",
                "precision": "instant",
                "state": "exact",
                "range_label": "3–18 июля",
                "state_label": "Пик",
                "timezone": "Europe/Moscow",
            }
        )


def test_exact_at_without_peak_label_rejected() -> None:
    with pytest.raises(ValidationError, match="exact-at-requires-peak-label"):
        TodayV2HorizonTiming.model_validate(
            {
                "active_from": "2026-07-03T00:00:00Z",
                "active_until": "2026-07-18T00:00:00Z",
                "exact_at": "2026-07-10T11:32:00Z",
                "precision": "instant",
                "state": "building",
                "range_label": "3–18 июля",
                "state_label": "Пик",
                "timezone": "Europe/Moscow",
            }
        )


def test_null_exact_with_non_null_peak_label_rejected() -> None:
    with pytest.raises(ValidationError, match="peak-label-requires-exact-at"):
        TodayV2HorizonTiming.model_validate(
            {
                "active_from": "2026-07-03T00:00:00Z",
                "active_until": "2026-07-18T00:00:00Z",
                "exact_at": None,
                "precision": "instant",
                "state": "building",
                "range_label": "3–18 июля",
                "peak_label": "Пик",
                "state_label": "Набирает силу",
                "timezone": "Europe/Moscow",
            }
        )


def test_medium_and_fast_without_peak_rejected() -> None:
    for index in [1, 2]:
        payload = build_horizons_block()
        payload["items"][index]["timing"]["exact_at"] = None  # type: ignore[index]
        payload["items"][index]["timing"]["peak_label"] = None  # type: ignore[index]
        with pytest.raises(ValidationError, match="medium-fast-requires-peak"):
            TodayV2HorizonsBlock.model_validate(payload)


def test_action_kind_and_count_rules_per_horizon() -> None:
    payload = build_horizons_block()
    payload["items"][0]["actions"]["do"][0]["kind"] = "avoid"  # type: ignore[index]
    with pytest.raises(ValidationError, match="kind-mismatch:avoid"):
        TodayV2HorizonsBlock.model_validate(payload)

    payload = build_horizons_block()
    payload["items"][2]["actions"]["do"].append(deepcopy(payload["items"][2]["actions"]["do"][0]))  # type: ignore[index]
    payload["items"][2]["actions"]["do"][1]["id"] = "gi-fast-do-2"  # type: ignore[index]
    payload["items"][2]["actions"]["do"][1]["text"] = "Сделайте один короткий шаг после паузы, а не вместо неё."  # type: ignore[index]
    with pytest.raises(ValidationError, match="count-out-of-range"):
        TodayV2HorizonsBlock.model_validate(payload)


def test_valid_until_mismatch_rejected() -> None:
    payload = build_horizons_block()
    payload["items"][1]["actions"]["valid_until"] = "2026-07-17T00:00:00Z"  # type: ignore[index]
    with pytest.raises(ValidationError, match="must-match-horizon-active-until"):
        TodayV2HorizonsBlock.model_validate(payload)


def test_timing_aggregate_min_max_accepted() -> None:
    model = TodayV2Block.model_validate(build_today_v2_block())
    assert model.horizons is not None
    medium = model.horizons.items[1]
    assert medium.timing.active_from == "2026-07-03T00:00:00Z"
    assert medium.timing.active_until == "2026-07-18T00:00:00Z"


def test_timing_aggregate_mismatch_rejected() -> None:
    payload = build_today_v2_block()
    payload["horizons"]["items"][1]["timing"]["active_from"] = "2026-07-04T00:00:00Z"  # type: ignore[index]
    with pytest.raises(ValidationError, match="aggregate-min-mismatch"):
        TodayV2Block.model_validate(payload)


def test_referenced_untimed_evidence_allowed_alongside_timed_evidence() -> None:
    payload = build_today_v2_block()
    payload["horizons"]["items"][1]["activation_ids"] = ["act-pluto-trine-saturn", "act-neptune-opp-saturn"]  # type: ignore[index]
    model = TodayV2Block.model_validate(payload)
    assert model.horizons is not None
    assert model.horizons.items[1].activation_ids == ["act-pluto-trine-saturn", "act-neptune-opp-saturn"]


def test_untimed_only_technique_explanation_with_timing_rejected() -> None:
    payload = build_today_v2_block()
    payload["horizons"]["items"][0]["technique_explanations"] = [
        {
            "technique": "firdar_major",
            "label": "Фирдар",
            "what_it_is": "Фирдар — длинная последовательность периодов, которая показывает, какие темы остаются на переднем плане дольше обычного.",
            "why_it_matters_now": "Этот длинный период поддерживает ту же задачу: перестраивать опору постепенно и без резких жестов.",
            "timing": payload["horizons"]["items"][0]["timing"],
            "activation_ids": ["act-firdar-major"],
        }
    ]  # type: ignore[index]
    with pytest.raises(ValidationError, match=r"technique-timing-without-timed-evidence.*id=firdar_major"):
        TodayV2Block.model_validate(payload)


def test_untimed_only_technique_explanation_with_null_timing_accepted() -> None:
    payload = build_today_v2_block()
    payload["horizons"]["items"][0]["technique_explanations"] = [
        {
            "technique": "firdar_major",
            "label": "Фирдар",
            "what_it_is": "Фирдар — длинная последовательность периодов, которая показывает, какие темы остаются на переднем плане дольше обычного.",
            "why_it_matters_now": "Этот длинный период поддерживает ту же задачу: перестраивать опору постепенно и без резких жестов.",
            "timing": None,
            "activation_ids": ["act-firdar-major"],
        }
    ]  # type: ignore[index]
    model = TodayV2Block.model_validate(payload)
    assert model.horizons is not None
    assert model.horizons.items[0].technique_explanations[0].timing is None


def test_mixed_technique_explanation_with_timed_evidence_remains_valid() -> None:
    payload = build_today_v2_block()
    model = TodayV2Block.model_validate(payload)
    assert model.horizons is not None
    explanation = model.horizons.items[1].technique_explanations[0]
    assert explanation.timing is not None
    assert explanation.activation_ids == ["act-pluto-trine-saturn", "act-neptune-opp-saturn"]


def test_only_untimed_referenced_evidence_rejected() -> None:
    payload = build_today_v2_block()
    payload["horizons"]["items"][0]["activation_ids"] = ["act-firdar-major"]  # type: ignore[index]
    payload["horizons"]["items"][0]["timing"]["active_from"] = "2026-05-12"  # type: ignore[index]
    payload["horizons"]["items"][0]["timing"]["active_until"] = "2027-05-11"  # type: ignore[index]
    payload["horizons"]["items"][0]["strength"]["provenance"]["activation_ids"] = ["act-firdar-major"]  # type: ignore[index]
    payload["horizons"]["items"][0]["risk"]["provenance"]["activation_ids"] = ["act-firdar-major"]  # type: ignore[index]
    payload["horizons"]["items"][0]["manifestations"][0]["provenance"]["activation_ids"] = ["act-firdar-major"]  # type: ignore[index]
    payload["horizons"]["items"][0]["manifestations"][1]["provenance"]["activation_ids"] = ["act-firdar-major"]  # type: ignore[index]
    payload["horizons"]["items"][0]["actions"]["do"][0]["provenance"]["activation_ids"] = ["act-firdar-major"]  # type: ignore[index]
    payload["horizons"]["items"][0]["actions"]["do"][1]["provenance"]["activation_ids"] = ["act-firdar-major"]  # type: ignore[index]
    payload["horizons"]["items"][0]["actions"]["avoid"][0]["provenance"]["activation_ids"] = ["act-firdar-major"]  # type: ignore[index]
    payload["horizons"]["items"][0]["technique_explanations"] = [
        {
            "technique": "firdar_major",
            "label": "Фирдар",
            "what_it_is": "Фирдар — длинная последовательность периодов, которая показывает, какие темы остаются на переднем плане дольше обычного.",
            "why_it_matters_now": "Этот длинный период поддерживает ту же задачу: перестраивать опору постепенно и без резких жестов.",
            "timing": None,
            "activation_ids": ["act-firdar-major"],
        }
    ]  # type: ignore[index]
    payload["horizons"]["intro"]["activation_ids"] = [
        "act-firdar-major",
        "act-pluto-trine-saturn",
        "act-neptune-opp-saturn",
        "act-moon-opp-pluto",
    ]  # type: ignore[index]
    with pytest.raises(ValidationError, match="only-untimed-evidence"):
        TodayV2Block.model_validate(payload)


@pytest.mark.parametrize(
    "bad_id",
    [
        "has space",
        "bad@id",
        "bad/id",
    ],
)
def test_opaque_fact_id_format_rejects_spaces_at_and_slash(bad_id: str) -> None:
    payload = build_horizons_block()
    payload["items"][0]["strength"]["provenance"]["natal_fact_ids"] = [bad_id]  # type: ignore[index]
    with pytest.raises(ValidationError):
        TodayV2HorizonsBlock.model_validate(payload)


def test_warnings_uniqueness_and_non_empty() -> None:
    payload = build_horizons_block()
    payload["warnings"] = ["dup", "dup"]
    with pytest.raises(ValidationError) as exc_info:
        TodayV2HorizonsBlock.model_validate(payload)
    message = str(exc_info.value)
    assert "duplicate-warning" in message
    assert "todayV2HorizonsBlock.warnings[1]" in message

    payload = build_horizons_block()
    payload["warnings"] = ["   "]
    with pytest.raises(ValidationError, match="blank-after-strip"):
        TodayV2HorizonsBlock.model_validate(payload)


def test_duplicate_action_validation_errors_hide_short_human_text() -> None:
    payload = build_horizons_block()
    sentinel = "Секрет"
    payload["items"][1]["actions"]["do"][0]["text"] = sentinel  # type: ignore[index]
    payload["items"][2]["actions"]["do"][0]["text"] = sentinel + "!!!"  # type: ignore[index]
    with pytest.raises(ValidationError) as exc_info:
        TodayV2HorizonsBlock.model_validate(payload)
    message = str(exc_info.value)
    assert "duplicate-normalized-action-text" in message
    assert "todayV2HorizonsBlock.items" in message
    assert sentinel not in message


def test_duplicate_warning_validation_errors_hide_short_human_text() -> None:
    payload = build_horizons_block()
    payload["warnings"] = ["Секретная фраза", "Секретная фраза"]
    with pytest.raises(ValidationError) as exc_info:
        TodayV2HorizonsBlock.model_validate(payload)
    message = str(exc_info.value)
    assert "duplicate-warning" in message
    assert "todayV2HorizonsBlock.warnings[1]" in message
    assert "Секретная фраза" not in message


def test_invalid_opaque_fact_input_hidden_from_validation_errors() -> None:
    payload = build_horizons_block()
    payload["items"][0]["strength"]["provenance"]["natal_fact_ids"] = ["bad secret/id"]  # type: ignore[index]
    with pytest.raises(ValidationError) as exc_info:
        TodayV2HorizonsBlock.model_validate(payload)
    message = str(exc_info.value)
    assert "natal_fact_ids" in message
    assert "bad secret/id" not in message


def test_fast_why_it_matters_now_matches_product_timezone_day_semantics() -> None:
    model = TodayV2Block.model_validate(build_today_v2_block())
    assert model.horizons is not None
    fast = model.horizons.items[2]
    assert fast.timing.range_label == "8–10 июля по Москве"
    assert fast.technique_explanations[0].why_it_matters_now.startswith("С 8 по 10 июля по Москве")
# END_BLOCK: MODEL_VALIDATION
