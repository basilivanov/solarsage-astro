# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_HORARY_NARRATIVE_BOUNDARY — horary structured narrative.
# ROLE: Proves the new horary boundary: the LLM writes ONLY five narrative
#       strings through provider-enforced Structured Outputs (strict
#       json_schema + require_parameters, Horary-only); the backend assembles
#       the public 8 blocks with engine-owned verdict/confidence/testimonies/
#       timing verbatim; invalid narrative after two attempts keeps the honest
#       HoraryGenerationError -> failed/refund path.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-HORARY-NARRATIVE-BOUNDARY
# purpose: Directed tests for the horary narrative/assembly contract
#   (release E2E 29895867779 root cause).
# owns:
#   - apps/api/tests/test_horary_narrative_boundary.py
# inputs: mocked transports/providers; no real network.
# outputs: request-body, attempt-count, block-order, engine-ownership and
#   log-shape assertions.
# dependencies: app.services.llm_service, app.schemas.horary_analysis.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Structured Outputs requested ONLY on the horary path.
#   - Engine fields are never LLM-substituted.
#   - unclear timing never exposes the internal hint.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-HORARY-NARRATIVE-BOUNDARY

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.horary_analysis import EvidenceItem, HoraryAnalysis, TimingInfo
from app.services.llm_service import (
    _HORARY_NARRATIVE_JSON_SCHEMA,
    HoraryGenerationError,
    LLMService,
)

VALID_NARRATIVE = {
    "lead": "Ответ скорее положительный, потому что карта показывает больше поддерживающих факторов, чем ослабляющих указаний.",
    "significator_paragraph": "Сигнификаторы пользователя и вопроса описывают ситуацию без явных противоречий и позволяют рассматривать развитие как рабочее и реалистичное.",
    "change_paragraph": "Исход может измениться, если появятся новые сдерживающие факторы или если участники начнут действовать менее последовательно, чем сейчас.",
    "advice_callout": "Действуй спокойно и не форсируй процесс: лучше закрепить уже имеющиеся преимущества, проверить детали и дать ситуации раскрыться естественным образом.",
    "final_summary": "Итог указывает на благоприятное развитие при сохранении текущего курса, особенно если не создавать лишнего давления и не торопить события.",
}

EXPECTED_ORDER = [
    "verdict_card", "lead", "paragraph", "testimonies",
    "paragraph", "timing", "callout", "paragraph",
]


def _analysis(**timing_kwargs) -> HoraryAnalysis:
    timing = timing_kwargs.pop("timing", None) or TimingInfo(
        status="known", time_range="1 неделя", text="Срок виден по карте.", basis="орб 1.0°"
    )
    return HoraryAnalysis(
        verdict="yes",
        confidence_score=70,
        confidence_label="medium",
        confidence_explanation="Карта согласована и не содержит критичных противоречий по теме.",
        involved_planets=["Venus", "Moon"],
        testimonies_for=[
            EvidenceItem(
                type="main_aspect",
                title="Гармоничный аспект",
                explanation="Поддержка темы вопроса сильным аспектом.",
                weight=0.5,
                planets_involved=["Venus", "Jupiter"],
                aspect_type="trine",
                orb=1.2,
            )
        ],
        testimonies_against=[
            EvidenceItem(
                type="chart_weakness",
                title="Слабый дом",
                explanation="Тема попадает в слабый дом карты.",
                weight=-0.2,
                planets_involved=["Moon"],
                aspect_type=None,
                orb=None,
            )
        ],
        neutral_factors=[],
        timing=timing,
        calculation_warnings=[],
    )


@pytest.fixture
def svc(monkeypatch):
    monkeypatch.setattr(LLMService, "__init__", lambda self: None)
    return LLMService()


# -- narrative validation + attempt contract ----------------------------------

@pytest.mark.asyncio
async def test_valid_narrative_builds_exact_eight_block_order(svc):
    async def fake_gen(prompt, max_tokens, json_schema=None):
        return json.dumps(VALID_NARRATIVE, ensure_ascii=False)

    with patch.object(svc, "_generate_text", fake_gen):
        out = await svc.generate_horary_answer(question_text="Q", category=None, analysis=_analysis())

    blocks = out["blocks"]
    assert [b["type"] for b in blocks] == EXPECTED_ORDER


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [
    "not json",  # parse
    json.dumps(["lead"]),  # type (top-level list)
    json.dumps({"lead": "x" * 80}),  # missing fields
    json.dumps({**VALID_NARRATIVE, "lead": ["не", "строка"]}),  # non-string field
    json.dumps({**VALID_NARRATIVE, "lead": "коротко"}),  # quality (too short)
    json.dumps({**VALID_NARRATIVE, "extra_field": "лишнее поле для проверки"}),  # extra key
])
async def test_bad_narrative_exactly_two_attempts_then_error(svc, bad):
    calls = []

    async def fake_gen(prompt, max_tokens, json_schema=None):
        calls.append(prompt)
        return bad

    with patch.object(svc, "_generate_text", fake_gen):
        with pytest.raises(HoraryGenerationError):
            await svc.generate_horary_answer(question_text="Q", category=None, analysis=_analysis())
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_provider_refusal_and_exception_are_safe(svc):
    # refusal/empty content -> "empty" reject path
    async def empty_gen(prompt, max_tokens, json_schema=None):
        return ""

    with patch.object(svc, "_generate_text", empty_gen):
        with pytest.raises(HoraryGenerationError):
            await svc.generate_horary_answer(question_text="Q", category=None, analysis=_analysis())

    # transport exception -> "provider" reject path, never propagates raw
    async def boom_gen(prompt, max_tokens, json_schema=None):
        raise RuntimeError("provider raw internal detail")

    with patch.object(svc, "_generate_text", boom_gen):
        with pytest.raises(HoraryGenerationError) as excinfo:
            await svc.generate_horary_answer(question_text="Q", category=None, analysis=_analysis())
    assert "raw internal detail" not in str(excinfo.value)


@pytest.mark.asyncio
async def test_rejection_logs_have_no_raw_response(svc):
    secret = "секретный текст ответа модели"
    bad = json.dumps({**VALID_NARRATIVE, "lead": secret[:30]})
    logs = []

    async def fake_gen(prompt, max_tokens, json_schema=None):
        return bad

    with patch.object(svc, "_generate_text", fake_gen), \
         patch("app.services.llm_service.log_event", side_effect=lambda *a, **k: logs.append((a, k))):
        with pytest.raises(HoraryGenerationError):
            await svc.generate_horary_answer(question_text="Q", category=None, analysis=_analysis())

    assert len(logs) == 2  # exactly two rejected attempts logged
    for args, kwargs in logs:
        assert args[0] == "llm.response_rejected"
        assert kwargs["payload"] == {"reason": "schema_invalid"}
        assert secret not in str(kwargs["msg"])


# -- engine ownership ----------------------------------------------------------

@pytest.mark.asyncio
async def test_engine_fields_come_from_analysis_regardless_of_narrative(svc):
    # Mechanical ownership proof ONLY: engine-owned fields are taken verbatim
    # from the analysis even when the narrative mentions other numbers. This
    # does NOT bless semantically contradictory user-visible narrative — the
    # prompt-level guard ("Не переопределяй вердикт...") discourages it, and
    # no general semantic claim framework exists (deliberately).
    creative = dict(VALID_NARRATIVE)
    creative["lead"] = (
        "Вердикт абсолютно точно НЕТ и уверенность девяносто девять процентов, "
        "а срок ровно семь дней, потому что я так решил — вопрос закрыт."
    )
    async def fake_gen(prompt, max_tokens, json_schema=None):
        return json.dumps(creative, ensure_ascii=False)

    analysis = _analysis()
    with patch.object(svc, "_generate_text", fake_gen):
        out = await svc.generate_horary_answer(question_text="Q", category=None, analysis=analysis)

    verdict_card = out["blocks"][0]
    assert verdict_card["verdict"] == analysis.verdict
    assert verdict_card["confidence"] == analysis.confidence_score / 100.0
    assert verdict_card["confidenceLabel"] == analysis.confidence_label
    assert verdict_card["confidenceExplanation"] == analysis.confidence_explanation

    testimonies = out["blocks"][3]
    assert testimonies["prosLabel"] == "Свидетельства «за»"
    assert testimonies["consLabel"] == "Свидетельства «против»"
    assert testimonies["neutralLabel"] == "Нейтральные факторы"
    assert testimonies["pros"][0] == {
        "title": "Гармоничный аспект",
        "explanation": "Поддержка темы вопроса сильным аспектом.",
        "weight": 0.5,
        "planets": ["Venus", "Jupiter"],
        "aspectType": "trine",
        "orb": 1.2,
    }
    assert testimonies["cons"][0]["weight"] == -0.2
    assert testimonies["cons"][0]["orb"] is None

    timing = out["blocks"][5]
    assert timing["status"] == "known"
    assert timing["timeRange"] == "1 неделя"
    # timing text is honestly augmented with the computed basis
    assert "Основание: орб 1.0°." in timing["text"]


@pytest.mark.asyncio
async def test_unclear_timing_never_exposes_internal_hint(svc):
    analysis = _analysis(
        timing=TimingInfo(
            status="unclear",
            time_range="weeks-months",  # internal category hint
            text="Срок по карте не выражен достаточно ясно.",
            basis="типовая оценка по категории вопроса (низкая уверенность)",
        )
    )
    async def fake_gen(prompt, max_tokens, json_schema=None):
        return json.dumps(VALID_NARRATIVE, ensure_ascii=False)

    with patch.object(svc, "_generate_text", fake_gen):
        out = await svc.generate_horary_answer(question_text="Q", category=None, analysis=analysis)

    timing = out["blocks"][5]
    assert timing["status"] == "unclear"
    assert timing["timeRange"] is None
    assert "weeks-months" not in json.dumps(out["blocks"], ensure_ascii=False)


@pytest.mark.asyncio
async def test_timing_basis_not_duplicated_when_already_in_text(svc):
    analysis = _analysis(
        timing=TimingInfo(
            status="known", time_range="несколько дней",
            text="Срок близкий: орб 1.0°.", basis="орб 1.0°",
        )
    )
    async def fake_gen(prompt, max_tokens, json_schema=None):
        return json.dumps(VALID_NARRATIVE, ensure_ascii=False)

    with patch.object(svc, "_generate_text", fake_gen):
        out = await svc.generate_horary_answer(question_text="Q", category=None, analysis=analysis)
    timing = out["blocks"][5]
    assert timing["text"].count("орб 1.0°") == 1


# -- Structured Outputs request proof ------------------------------------------

def _openrouter_capture(response_content: str):
    mock_resp = MagicMock()
    mock_resp.json = MagicMock(return_value={
        "choices": [{"message": {"content": response_content}}]
    })
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    return mock_client


@pytest.mark.asyncio
async def test_horary_request_body_has_strict_json_schema(svc, monkeypatch):
    monkeypatch.setattr("app.services.llm_service.settings.openrouter_api_key", "test-key")
    mock_client = _openrouter_capture(json.dumps(VALID_NARRATIVE, ensure_ascii=False))

    with patch("app.services.llm_service.httpx.AsyncClient") as mock_class:
        mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_class.return_value.__aexit__ = AsyncMock(return_value=None)
        await svc.generate_horary_answer(question_text="Q", category=None, analysis=_analysis())

    body = mock_client.post.call_args.kwargs["json"]
    assert body["response_format"] == {
        "type": "json_schema",
        "json_schema": _HORARY_NARRATIVE_JSON_SCHEMA,
    }
    assert body["provider"] == {"require_parameters": True}
    schema = _HORARY_NARRATIVE_JSON_SCHEMA
    assert schema["strict"] is True
    props = schema["schema"]["properties"]
    assert sorted(props.keys()) == [
        "advice_callout", "change_paragraph", "final_summary", "lead", "significator_paragraph",
    ]
    assert schema["schema"]["required"] == [
        "lead", "significator_paragraph", "change_paragraph", "advice_callout", "final_summary",
    ]
    assert schema["schema"]["additionalProperties"] is False


@pytest.mark.asyncio
async def test_ordinary_call_request_body_unchanged(svc, monkeypatch):
    monkeypatch.setattr("app.services.llm_service.settings.openrouter_api_key", "test-key")
    mock_client = _openrouter_capture("Заголовок дня")

    with patch("app.services.llm_service.httpx.AsyncClient") as mock_class:
        mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_class.return_value.__aexit__ = AsyncMock(return_value=None)
        out = await svc.generate_headline("steady", [])

    assert out == "Заголовок дня"
    body = mock_client.post.call_args.kwargs["json"]
    assert "response_format" not in body
    assert "provider" not in body


# -- single-source floor drift proofs ------------------------------------------

def test_schema_patterns_derive_from_single_floor_map():
    from app.services.llm_service import (
        _HORARY_NARRATIVE_FIELDS,
        _HORARY_NARRATIVE_JSON_SCHEMA,
        _HORARY_NARRATIVE_MIN_LENGTH,
    )

    props = _HORARY_NARRATIVE_JSON_SCHEMA["schema"]["properties"]
    for field in _HORARY_NARRATIVE_FIELDS:
        floor = _HORARY_NARRATIVE_MIN_LENGTH[field]
        assert props[field]["pattern"] == rf"^[\s\S]{{{floor},}}$"
        assert f"Минимум {floor} символов" in props[field]["description"]


@pytest.mark.asyncio
async def test_prompt_states_length_requirements_and_no_override_guard(svc):
    from app.services.llm_service import _HORARY_NARRATIVE_MIN_LENGTH

    captured = {}

    async def fake_gen(prompt, max_tokens, json_schema=None):
        captured["prompt"] = prompt
        return json.dumps(VALID_NARRATIVE, ensure_ascii=False)

    with patch.object(svc, "_generate_text", fake_gen):
        await svc.generate_horary_answer(question_text="Q", category=None, analysis=_analysis())

    prompt = captured["prompt"]
    for field, floor in _HORARY_NARRATIVE_MIN_LENGTH.items():
        assert f"{field} — не короче {floor} символов" in prompt
    assert "Не переопределяй и не пересчитывай вердикт" in prompt
