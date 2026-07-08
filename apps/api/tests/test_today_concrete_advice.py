# ############################################################################
# AI_HEADER: MODULE_TESTS_TODAY_CONCRETE_ADVICE
# ROLE: Unit tests for TodayInterpretationService and LLM concrete advice merge.
# ############################################################################

import pytest
from datetime import date
from unittest.mock import AsyncMock, patch

from app.schemas.normalization import AstroSignal
from app.schemas.today import PlanetInfluence, SphereScore
from app.services.today_interpretation_service import TodayInterpretationService
from app.services.llm_service import LLMService

@pytest.mark.asyncio
async def test_today_interpretation_service_deterministic_builder():
    service = TodayInterpretationService()

    # Empty inputs to test deterministic fallbacks
    concrete_advice, day_summary, updated_day_chart = await service.build(
        target_date=date(2026, 7, 5),
        day_status="supportive",
        scoring_result={"day_status": "supportive", "sphere_scores": {}},
        signals=[],
        semantic_layer=None,
        day_chart=None,
        planet_influences=[],
        sphere_scores=[],
        important_items=[],
    )

    assert concrete_advice is not None
    assert len(concrete_advice.rows) == 12

    # Verify fixed product order
    expected_order = ["work", "money", "documents", "relationships", "sport", "communication", "health", "decisions", "travel", "creativity", "study", "shopping"]
    for idx, row in enumerate(concrete_advice.rows):
        assert row.key == expected_order[idx]
        assert row.verdict == "good"  # Fallback to day_status supportive
        assert len(row.evidence) == 1
        assert row.evidence[0].kind == "day_status"

    # Verify counts match row verdicts
    assert concrete_advice.counts.good == 12
    assert concrete_advice.counts.caution == 0
    assert concrete_advice.counts.avoid == 0
    assert concrete_advice.counts.neutral == 0


@pytest.mark.asyncio
async def test_llm_concrete_advice_validation_and_fallback():
    service = TodayInterpretationService()

    # Case 1: LLM returns valid Russian texts for all 12 keys
    valid_mock_texts = {
        "work": "Хороший день для новых рабочих задач.",
        "money": "Сократи траты — день для финансовой дисциплины.",
        "documents": "Подходящее время для оформления договоров.",
        "relationships": "Удачный день для сближения и свиданий.",
        "sport": "Энергия на пике, можно потренироваться.",
        "communication": "Переговоры пройдут гладко и продуктивно.",
        "health": "Тело полно сил, позаботься о себе.",
        "decisions": "Решения даются легко, интуиция работает.",
        "travel": "Дорога будет легкой, планируй поездку.",
        "creativity": "Вдохновение бьет ключом, садись за работу.",
        "study": "Память цепкая, учи сложную информацию.",
        "shopping": "Покупки принесут радость и прослужат долго."
    }

    # Case 2: LLM returns text with Latin characters (should be rejected)
    invalid_mock_texts = {k: f"{v} English" for k, v in valid_mock_texts.items()}

    # Test valid case under patch
    with patch("app.services.llm_service.LLMService.generate_concrete_advice", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = valid_mock_texts

        concrete_advice, _, _ = await service.build(
            target_date=date(2026, 7, 5),
            day_status="supportive",
            scoring_result={"day_status": "supportive", "sphere_scores": {}},
            signals=[],
            semantic_layer=None,
            day_chart=None,
            planet_influences=[],
            sphere_scores=[],
            important_items=[],
        )

        for row in concrete_advice.rows:
            assert row.text == valid_mock_texts[row.key]

    # Test invalid case: should trigger fallback/ValueError since keys are invalid
    with patch("app.services.llm_service.LLMService.generate_concrete_advice", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = invalid_mock_texts

        # When has_llm_keys is True (simulated), it should raise ValueError
        with patch("app.core.config.settings.openrouter_api_key", "fake_key"):
            with pytest.raises(ValueError):
                await service.build(
                    target_date=date(2026, 7, 5),
                    day_status="supportive",
                    scoring_result={"day_status": "supportive", "sphere_scores": {}},
                    signals=[],
                    semantic_layer=None,
                    day_chart=None,
                    planet_influences=[],
                    sphere_scores=[],
                    important_items=[],
                )
