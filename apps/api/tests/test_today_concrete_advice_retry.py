# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_TODAY_CONCRETE_ADVICE_RETRY — retry/degraded proofs.
# ROLE: Proves the concrete-advice bounded-retry and degraded-cache contracts:
#       exactly one advice-only retry on unacceptable first attempts, atomic
#       application, 12-row honest fallback without ValueError, endpoint 200,
#       and no payload-cache write on degraded batches.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-TODAY-CONCRETE-ADVICE-RETRY
# purpose: Directed regression tests for the concrete advice retry/fallback/
#   cacheability contract (release E2E 29890349759 root cause).
# owns:
#   - apps/api/tests/test_today_concrete_advice_retry.py
# inputs: mocked LLMService batch methods, endpoint harness mocks.
# outputs: call-count, row-content, log-shape and cache-call assertions.
# dependencies: conftest fixtures (async_client, make_initdata, db_session).
# side_effects: none (all externals mocked).
# emitted_logs: none.
# invariants:
#   - Planet interpretations are never re-run by an advice retry.
#   - Degraded batches never raise and never reach the payload cache.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-TODAY-CONCRETE-ADVICE-RETRY

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import settings
from app.schemas.today import DayChart, DayChartTransitPlanet
from app.services.today_interpretation_service import (
    CONCRETE_ADVICE_FALLBACK_TEXT,
    TodayInterpretationService,
)

CANONICAL_12_KEYS = [
    "work", "money", "documents", "relationships", "sport", "communication",
    "health", "decisions", "travel", "creativity", "study", "shopping",
]

VALID_TEXTS = {k: f"Спокойный день для дела номер {i}." for i, k in enumerate(CANONICAL_12_KEYS)}

BUILD_KWARGS = dict(
    target_date=date(2026, 7, 5),
    day_status="supportive",
    scoring_result={"day_status": "supportive", "sphere_scores": {}},
    signals=[],
    semantic_layer=None,
    planet_influences=[],
    sphere_scores=[],
    important_items=[],
)


def _day_chart() -> DayChart:
    return DayChart(
        source="solarsage",
        houses=[],
        transit_planets=[
            DayChartTransitPlanet(name="Sun", longitude=150.0, sign="Virgo", house=1),
        ],
        aspects=[],
    )


async def _build_with_mocks(advice_side_effect, planet_return=None):
    service = TodayInterpretationService()
    with patch("app.services.llm_service.LLMService.generate_concrete_advice", new_callable=AsyncMock) as mock_advice, \
         patch("app.services.llm_service.LLMService.generate_planet_interpretations", new_callable=AsyncMock) as mock_planets, \
         patch("app.core.config.settings.openrouter_api_key", "test-key"):
        mock_advice.side_effect = advice_side_effect
        mock_planets.return_value = planet_return or {"Sun": "Солнце помогает делам."}
        result = await service.build(day_chart=_day_chart(), **BUILD_KWARGS)
    return result, mock_advice, mock_planets


# -- call-count contract ------------------------------------------------------

@pytest.mark.asyncio
async def test_valid_first_attempt_single_advice_call():
    (concrete_advice, _, _), mock_advice, mock_planets = await _build_with_mocks([VALID_TEXTS])
    assert mock_advice.call_count == 1  # valid first: no retry
    assert mock_planets.call_count == 1  # planet batch untouched by advice logic
    for row in concrete_advice.rows:
        assert row.text == VALID_TEXTS[row.key]


@pytest.mark.asyncio
async def test_malformed_single_call_no_hidden_retry():
    # Single-call contract: a malformed batch is rejected ONCE; no second
    # paid attempt is ever made (the valid "next" response is never consumed).
    (concrete_advice, _, _), mock_advice, mock_planets = await _build_with_mocks([None, VALID_TEXTS])
    assert mock_advice.call_count == 1
    assert mock_planets.call_count == 1
    assert len(concrete_advice.rows) == 12
    for row in concrete_advice.rows:
        assert row.text == CONCRETE_ADVICE_FALLBACK_TEXT


@pytest.mark.asyncio
async def test_semantic_invalid_single_call_degraded():
    invalid = VALID_TEXTS.copy()
    for k in ["work", "money", "documents", "relationships"]:
        invalid[k] = "Latin words inside text."
    (concrete_advice, _, _), mock_advice, mock_planets = await _build_with_mocks([invalid])
    assert mock_advice.call_count == 1
    assert mock_planets.call_count == 1
    for row in concrete_advice.rows:
        assert row.text == CONCRETE_ADVICE_FALLBACK_TEXT
        assert "Latin" not in row.text


@pytest.mark.asyncio
async def test_malformed_degraded_no_raise_no_bad_text():
    (concrete_advice, _, _), mock_advice, mock_planets = await _build_with_mocks([None])
    assert mock_advice.call_count == 1
    assert mock_planets.call_count == 1
    assert len(concrete_advice.rows) == 12
    for row in concrete_advice.rows:
        assert row.text == CONCRETE_ADVICE_FALLBACK_TEXT


@pytest.mark.asyncio
async def test_partial_accept_single_attempt_applies_valid_rows_only():
    partial = VALID_TEXTS.copy()
    # 9 valid + 3 invalid (Latin) -> the SINGLE attempt is accepted with
    # >= 9 valid rows; valid rows applied, the rest keep the fallback.
    for k in ["work", "money", "documents"]:
        partial[k] = "Latin words inside text."
    (concrete_advice, _, _), mock_advice, _ = await _build_with_mocks([partial])
    assert mock_advice.call_count == 1
    by_key = {row.key: row.text for row in concrete_advice.rows}
    for k in ["work", "money", "documents"]:
        assert by_key[k] == CONCRETE_ADVICE_FALLBACK_TEXT
    for k in ["relationships", "sport", "communication", "health", "decisions",
              "travel", "creativity", "study", "shopping"]:
        assert by_key[k] == VALID_TEXTS[k]


# -- endpoint + cache contract ------------------------------------------------

def _sidecar_client_mock() -> MagicMock:
    mock_client = MagicMock()
    mock_client.get_natal = AsyncMock(return_value={
        "planets": [{"name": "Sun", "longitude": 69.5, "latitude": 0.0, "speed": 1.0, "sign": "Gemini"}],
        "houses": [
            {"number": i + 1, "cusp": float(30 * i), "sign": s}
            for i, s in enumerate([
                "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
            ])
        ],
        "special_points": [],
        "house_system": "PLACIDUS",
    })
    mock_client.get_transits = AsyncMock(return_value={
        "planets": [{"name": "Sun", "longitude": 150.0, "latitude": 0.0, "speed": 1.0, "sign": "Virgo"}],
        "special_points": [],
    })
    return mock_client


async def _day_request(async_client, make_initdata, advice_side_effect, cache_spy):
    raw = make_initdata(user_id=8003, username="advice-retry")
    await async_client.post("/api/auth/telegram", json={"initData": raw})
    await async_client.put("/api/profile", json={
        "gender": "male",
        "birth": {
            "birthday": "1990-01-15", "birthTime": "12:00",
            "birthCity": "Moscow", "birthLat": 55.75, "birthLon": 37.61,
            "birthTz": "Europe/Moscow",
        }
    })
    with patch("app.services.natal_context_service.get_solarsage_client") as client_factory, \
         patch("app.services.today_service.get_solarsage_client", client_factory), \
         patch("app.services.today_service.TodayService._cache_payload", cache_spy), \
         patch("app.services.llm_service.LLMService.generate_concrete_advice", new_callable=AsyncMock) as mock_advice, \
         patch("app.services.llm_service.LLMService.generate_planet_interpretations", new_callable=AsyncMock) as mock_planets, \
         patch("app.services.llm_service.LLMService.generate_headline", new_callable=AsyncMock) as mock_headline, \
         patch("app.services.llm_service.LLMService.generate_reading", new_callable=AsyncMock) as mock_reading, \
         patch("app.services.llm_service.LLMService.generate_notes", new_callable=AsyncMock) as mock_notes, \
         patch("app.services.llm_service.LLMService.generate_why_sections", new_callable=AsyncMock) as mock_why, \
         patch.object(settings, "openrouter_api_key", "test-key"):
        client_factory.return_value = _sidecar_client_mock()
        mock_advice.side_effect = advice_side_effect
        mock_planets.return_value = {"Sun": "Солнце помогает делам."}
        mock_headline.return_value = None
        mock_reading.return_value = None
        mock_notes.return_value = None
        mock_why.return_value = None
        resp = await async_client.get("/api/day/today")
    return resp, mock_advice


@pytest.mark.asyncio
async def test_endpoint_degraded_returns_200_and_skips_cache(async_client, make_initdata, db_session):
    cache_spy = AsyncMock()
    resp, mock_advice = await _day_request(async_client, make_initdata, [None], cache_spy)
    assert resp.status_code == 200, resp.text
    rows = resp.json()["concreteAdvice"]["rows"]
    assert len(rows) == 12
    assert all(r["text"] == CONCRETE_ADVICE_FALLBACK_TEXT for r in rows)
    assert mock_advice.call_count == 1
    cache_spy.assert_not_called()  # degraded batch never poisons the cache


@pytest.mark.asyncio
async def test_endpoint_accepted_result_is_cached(async_client, make_initdata, db_session):
    cache_spy = AsyncMock()
    resp, mock_advice = await _day_request(async_client, make_initdata, [VALID_TEXTS], cache_spy)
    assert resp.status_code == 200, resp.text
    rows = resp.json()["concreteAdvice"]["rows"]
    assert all(r["text"] == VALID_TEXTS[r["key"]] for r in rows)
    assert mock_advice.call_count == 1  # exactly one external advice call
    cache_spy.assert_called_once()  # valid result stays cacheable


# -- llm_service level: output budget + safe rejection log --------------------

@pytest.mark.asyncio
async def test_concrete_advice_output_budget_2400():
    from app.services.llm_service import LLMService

    service = LLMService()
    with patch.object(LLMService, "_generate_text", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = '{"work": "текст"}'
        await service.generate_concrete_advice(
            [{"key": "work", "label": "Работа", "verdict": "good", "evidence": []}]
        )
        mock_gen.assert_called_once()
        assert mock_gen.call_args.kwargs["max_tokens"] == 2400


@pytest.mark.asyncio
async def test_parse_rejection_log_has_no_raw_response():
    from app.services.llm_service import LLMService

    service = LLMService()
    raw_bad = '{"work": "обрезанный ответ без закрывающей скобки'
    with patch.object(LLMService, "_generate_text", new_callable=AsyncMock) as mock_gen, \
         patch("app.services.llm_service.log_event") as mock_log:
        mock_gen.return_value = raw_bad
        result = await service.generate_concrete_advice(
            [{"key": "work", "label": "Работа", "verdict": "good", "evidence": []}]
        )
        assert result is None
        mock_log.assert_called_once()
        _, kwargs = mock_log.call_args
        assert mock_log.call_args.args[0] == "llm.response_rejected"
        assert kwargs["payload"] == {"reason": "schema_invalid"}
        assert "response" not in kwargs["payload"]
        # The raw model response must never reach the log envelope.
        assert raw_bad not in str(kwargs)


# -- evidence projection caps + provider schema request -----------------------

@pytest.mark.asyncio
async def test_advice_contexts_capped_three_unique_but_wire_evidence_full():
    # The LLM projection carries at most 3 unique evidence entries per
    # sphere; the wire row.evidence keeps the complete set.
    from app.services.today_interpretation_service import TodayInterpretationService
    from app.schemas.normalization import AstroSignal

    many_signals = [
        AstroSignal(type="aspect", planet="Transit_Sun", target_planet=t,
                    aspect_type="trine", orb=1.0, strength=0.9)
        for t in ["Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Pluto"]
    ]
    service = TodayInterpretationService()
    captured = {}

    with patch("app.services.llm_service.LLMService.generate_concrete_advice", new_callable=AsyncMock) as mock_advice, \
         patch("app.services.llm_service.LLMService.generate_planet_interpretations", new_callable=AsyncMock) as mock_planets, \
         patch("app.core.config.settings.openrouter_api_key", "test-key"):
        mock_advice.return_value = VALID_TEXTS
        mock_planets.return_value = None

        async def capture(contexts, evidence_packet=None):
            captured["contexts"] = contexts
            return VALID_TEXTS
        mock_advice.side_effect = capture

        concrete_advice, _, _ = await service.build(
            target_date=date(2026, 7, 5),
            day_status="supportive",
            scoring_result={"day_status": "supportive", "sphere_scores": {}},
            signals=many_signals,
            semantic_layer=None,
            day_chart=None,
            planet_influences=[],
            sphere_scores=[],
            important_items=[],
        )

    # Wire evidence untouched: the aspect-signal sphere rows keep all their
    # evidence entries (no cap on the payload side).
    total_wire = sum(len(row.evidence) for row in concrete_advice.rows)
    assert total_wire >= 6

    # LLM projection: at most 3 unique entries per sphere, deterministic.
    for ctx in captured["contexts"]:
        titles = [ev.get("title") for ev in ctx["evidence"]]
        assert len(ctx["evidence"]) <= 3
        assert len(titles) == len(set(titles))


@pytest.mark.asyncio
async def test_generate_concrete_advice_sends_strict_schema():
    from app.services.llm_service import LLMService, _CONCRETE_ADVICE_JSON_SCHEMA

    service = LLMService()
    with patch.object(LLMService, "_generate_text", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = '{"work": "текст"}'
        await service.generate_concrete_advice(
            [{"key": "work", "label": "Работа", "verdict": "good", "evidence": []}]
        )
        mock_gen.assert_called_once()
        schema = mock_gen.call_args.kwargs.get("json_schema")
        assert schema is _CONCRETE_ADVICE_JSON_SCHEMA
        assert schema["strict"] is True
        assert schema["schema"]["additionalProperties"] is False
        assert len(schema["schema"]["required"]) == 12
        assert set(schema["schema"]["properties"].keys()) == set(schema["schema"]["required"])
        for field_schema in schema["schema"]["properties"].values():
            assert field_schema["type"] == "object"
            assert set(field_schema["properties"].keys()) == {"story", "why", "advice"}


@pytest.mark.asyncio
async def test_concrete_advice_request_body_has_strict_json_schema():
    # Real request-body proof over httpx (no network): the advice batch goes
    # out with provider-enforced Structured Outputs, and ONLY that.
    from app.services.llm_service import LLMService, _CONCRETE_ADVICE_JSON_SCHEMA

    mock_resp = MagicMock()
    mock_resp.json = MagicMock(return_value={
        "choices": [{"message": {"content": '{"work": "текст"}'}}]
    })
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_resp)

    service = LLMService()
    with patch("app.services.llm_service.httpx.AsyncClient") as mock_class, \
         patch("app.services.llm_service.settings") as mock_settings:
        mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_class.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_settings.openrouter_api_key = "test-key"
        mock_settings.openrouter_base_url = "https://openrouter.example/api/v1"
        mock_settings.openrouter_site_url = ""
        mock_settings.openrouter_app_name = "test"
        mock_settings.llm_model = "openai/gpt-4.1-nano"
        await service.generate_concrete_advice(
            [{"key": "work", "label": "Работа", "verdict": "good", "evidence": []}]
        )

    body = mock_client.post.call_args.kwargs["json"]
    assert body["response_format"] == {
        "type": "json_schema",
        "json_schema": _CONCRETE_ADVICE_JSON_SCHEMA,
    }
    assert body["provider"] == {"require_parameters": True}
    schema = body["response_format"]["json_schema"]
    assert schema["strict"] is True
    assert schema["schema"]["additionalProperties"] is False
    assert len(schema["schema"]["required"]) == 12
    assert set(schema["schema"]["properties"].keys()) == set(schema["schema"]["required"])


@pytest.mark.asyncio
async def test_concrete_advice_details_structuring_and_fallback():
    """Verify structured drilldown details populate row.details and fallback cleanly to None."""
    from datetime import date as Date
    from app.services.today_interpretation_service import TodayInterpretationService
    from app.services.llm_service import LLMService

    keys = [
        "work", "money", "documents", "relationships", "sport", "communication",
        "health", "decisions", "travel", "creativity", "study", "shopping"
    ]

    structured_candidate = {
        key: {
            "story": "Персональная история дня для этой сферы. Это важный момент для внимания.",
            "why": ["Фоновый фактор сферы деятельности"],
            "advice": "Действуй взвешенно и спокойно.",
        }
        for key in keys
    }

    service = TodayInterpretationService()
    with patch.object(LLMService, "generate_concrete_advice", new_callable=AsyncMock) as mock_llm, \
         patch("app.core.config.settings") as mock_settings:
        mock_settings.openrouter_api_key = "test-key"
        mock_settings.anthropic_api_key = ""
        mock_settings.deepseek_api_key = ""
        mock_llm.return_value = structured_candidate

        mock_sem = MagicMock()
        mock_sem.day_theme = "Тема дня"

        advice_block, summary, chart = await service.build(
            target_date=Date(2026, 7, 27),
            day_status="steady",
            scoring_result={"day_status": "steady", "sphere_scores": {}},
            signals=[],
            semantic_layer=mock_sem,
            day_chart=None,
            planet_influences=[],
            sphere_scores=[],
            important_items=[],
        )

        rows = advice_block.rows
        assert len(rows) == 12
        for r in rows:
            assert r.details is not None
            assert r.details.story.startswith("Персональная история")
            assert isinstance(r.details.why, list)
            assert r.details.advice.startswith("Действуй взвешенно")
            assert r.text == r.details.advice


def test_banned_jargon_validator_rejects_astrology_terms_and_abstractions():
    """Verify LLMClaimValidator rejects details with astrology jargon in story/why/advice."""
    from app.services.llm_claim_validator import LLMClaimValidator, has_banned_jargon

    validator = LLMClaimValidator()

    # Banned jargon check
    assert has_banned_jargon("Транзитный аспект создает суету") is True
    assert has_banned_jargon("Активированы важные аспекты") is True
    assert has_banned_jargon("Влияние планеты удваивается") is True
    assert has_banned_jargon("День складывается активно") is True
    assert has_banned_jargon("Много внутренней энергии", row_key="work") is True
    assert has_banned_jargon("Много физической энергии", row_key="sport") is False

    # Story with jargon -> details rejected (returns None)
    res_jargon_story = validator.validate_concrete_advice_details(
        row_key="work",
        verdict="good",
        details={
            "story": "Транзитный аспект подталкивает к переговорам.",
            "why": ["Долгий цикл развития"],
            "advice": "Действуй спокойно.",
        },
        evidence=[],
    )
    assert res_jargon_story is None

    # Why with jargon -> details rejected (returns None)
    res_jargon_why = validator.validate_concrete_advice_details(
        row_key="work",
        verdict="good",
        details={
            "story": "Встречи проходят результативно и приносят плоды.",
            "why": ["У тебя есть поддержка в финансах и активные аспекты"],
            "advice": "Действуй спокойно.",
        },
        evidence=[],
    )
    assert res_jargon_why is None

    # Valid human details -> accepted
    res_valid = validator.validate_concrete_advice_details(
        row_key="work",
        verdict="good",
        details={
            "story": "Сегодня подходящий момент завершить давно откладываемый проект.",
            "why": ["Долгий цикл про рабочий статус задевает текущие задачи"],
            "advice": "Сосредоточься на главном приоритете.",
        },
        evidence=[],
    )
    assert res_valid is not None
    assert res_valid["story"].startswith("Сегодня подходящий момент")
    assert res_valid["advice"] == "Сосредоточься на главном приоритете."
