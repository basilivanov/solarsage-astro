# ############################################################################
# AI_HEADER: MODULE_TESTS_TODAY_CONCRETE_ADVICE
# ROLE: Unit tests for TodayInterpretationService and LLM concrete advice merge.
# ############################################################################

import pytest
from datetime import date
from unittest.mock import AsyncMock, patch

from app.schemas.normalization import AstroSignal
from app.schemas.today import PlanetInfluence, SphereScore, ConcreteAdviceEvidence
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
async def test_today_interpretation_service_no_key_fallback():
    """No LLM keys results in 'Рекомендация временно недоступна.' fallback."""
    service = TodayInterpretationService()

    # Force LLM keys to empty
    with patch("app.core.config.settings.openrouter_api_key", ""), \
         patch("app.core.config.settings.anthropic_api_key", ""):

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

        assert len(concrete_advice.rows) == 12
        for row in concrete_advice.rows:
            assert row.text == "Рекомендация временно недоступна."


@pytest.mark.asyncio
async def test_llm_concrete_advice_validation_and_fallback():
    service = TodayInterpretationService()

    # Case 1: LLM returns valid Russian texts for all 12 keys
    # Each row must only mention allowed planets/aspects/houses from its evidence.
    # To keep it simple, we provide row evidence for the planets/aspects we mention.
    valid_mock_texts = {
        "work": "Хороший день для новых дел.",
        "money": "Сократи траты сегодня.",
        "documents": "Подходящее время для оформления.",
        "relationships": "Удачный день для сближения.",
        "sport": "Энергия на пике, можно потренироваться.",
        "communication": "Переговоры пройдут гладко.",
        "health": "Тело полно сил, позаботься о себе.",
        "decisions": "Решения даются легко.",
        "travel": "Дорога будет легкой.",
        "creativity": "Вдохновение бьет ключом.",
        "study": "Память цепкая, учи информацию.",
        "shopping": "Покупки прослужат долго."
    }

    # Test valid case under patch
    with patch("app.services.llm_service.LLMService.generate_concrete_advice", new_callable=AsyncMock) as mock_llm, \
         patch("app.core.config.settings.openrouter_api_key", "abc123xyz"):
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

    # Helper to assert validation failure (raises ValueError)
    async def assert_fails(mock_output):
        with patch("app.services.llm_service.LLMService.generate_concrete_advice", new_callable=AsyncMock) as mock_llm, \
             patch("app.core.config.settings.openrouter_api_key", "abc123xyz"):
            mock_llm.return_value = mock_output
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

    # 1. Latin text fails (invalidate 4 keys)
    invalid_latin = valid_mock_texts.copy()
    for k in ["work", "money", "documents", "relationships"]:
        invalid_latin[k] = "Хороший день для work задач."
    await assert_fails(invalid_latin)

    # 2. Transit_ / Natal_ fails (invalidate 4 keys)
    invalid_prefix = valid_mock_texts.copy()
    for k in ["work", "money", "documents", "relationships"]:
        invalid_prefix[k] = "Сократи траты — Transit_Moon в Раке."
    await assert_fails(invalid_prefix)

    # 3. Missing key fails
    invalid_missing = valid_mock_texts.copy()
    del invalid_missing["work"]
    await assert_fails(invalid_missing)

    # 4. Extra key fails
    invalid_extra = valid_mock_texts.copy()
    invalid_extra["extra_key"] = "Лишний текст."
    await assert_fails(invalid_extra)

    # 5. Hallucinated planet fails (e.g. work evidence has no Mars aspect, but LLM mentions Mars aspect)
    # Since evidence is empty in service.build call above, mentioning ANY planet or aspect should fail!
    invalid_hallucination = valid_mock_texts.copy()
    for k in ["work", "money", "documents", "relationships"]:
        invalid_hallucination[k] = "Работа сегодня подсвечена Марсом."
    await assert_fails(invalid_hallucination)


@pytest.mark.asyncio
async def test_today_interpretation_service_allowed_evidence_planets():
    """Text mentioning a planet from evidence passes, but other planets fail."""
    service = TodayInterpretationService()

    # work has Mars evidence, so mentioning Mars is allowed, but Venus is not.
    mock_output = {
        "work": "Марс дает энергию для новых дел.", # Allowed (Mars in evidence)
        "money": "Сократи траты сегодня.",
        "documents": "Подходящее время для оформления.",
        "relationships": "Удачный день для сближения.",
        "sport": "Энергия на пике, можно потренироваться.",
        "communication": "Переговоры пройдут гладко.",
        "health": "Тело полно сил, позаботься о себе.",
        "decisions": "Решения даются легко.",
        "travel": "Дорога будет легкой.",
        "creativity": "Вдохновение бьет ключом.",
        "study": "Память цепкая, учи информацию.",
        "shopping": "Покупки прослужат долго."
    }

    # Test that allowed planet passes
    with patch("app.services.llm_service.LLMService.generate_concrete_advice", new_callable=AsyncMock) as mock_llm, \
         patch("app.core.config.settings.openrouter_api_key", "abc123xyz"):
        mock_llm.return_value = mock_output

        concrete_advice, _, _ = await service.build(
            target_date=date(2026, 7, 5),
            day_status="supportive",
            scoring_result={"day_status": "supportive", "sphere_scores": {}},
            signals=[],
            semantic_layer=None,
            day_chart=None,
            planet_influences=[PlanetInfluence(name="Mars", score=6.5, rank=1)], # Mars influence creates Mars evidence for work!
            sphere_scores=[],
            important_items=[],
        )

        assert concrete_advice.rows[0].text == "Марс дает энергию для новых дел."

    # Test that mentioning Venus (not in evidence) fails
    invalid_output = mock_output.copy()
    invalid_output["work"] = "Венера помогает в работе сегодня."

    with patch("app.services.llm_service.LLMService.generate_concrete_advice", new_callable=AsyncMock) as mock_llm, \
         patch("app.core.config.settings.openrouter_api_key", "abc123xyz"):
        mock_llm.return_value = invalid_output
        with pytest.raises(ValueError):
            # Invalidate 4 keys to trigger ValueError
            for k in ["work", "money", "documents", "relationships"]:
                invalid_output[k] = "Венера помогает в работе сегодня."
            await service.build(
                target_date=date(2026, 7, 5),
                day_status="supportive",
                scoring_result={"day_status": "supportive", "sphere_scores": {}},
                signals=[],
                semantic_layer=None,
                day_chart=None,
                planet_influences=[PlanetInfluence(name="Mars", score=6.5, rank=1)],
                sphere_scores=[],
                important_items=[],
            )
