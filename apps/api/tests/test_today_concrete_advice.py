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
        assert row.verdict == "neutral"  # Fallback to neutral because no direct scores or aspect signals
        assert len(row.evidence) == 1
        assert row.evidence[0].kind == "day_status"

    # Verify counts match row verdicts
    assert concrete_advice.counts.good == 0
    assert concrete_advice.counts.caution == 0
    assert concrete_advice.counts.avoid == 0
    assert concrete_advice.counts.neutral == 12


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
    valid_mock_texts = {
        "work": "СЕНТИНЕЛ РАБОТА",
        "money": "СЕНТИНЕЛ ДЕНЬГИ",
        "documents": "СЕНТИНЕЛ ДОКУМЕНТЫ",
        "relationships": "СЕНТИНЕЛ ОТНОШЕНИЯ",
        "sport": "СЕНТИНЕЛ СПОРТ",
        "communication": "СЕНТИНЕЛ ОБЩЕНИЕ",
        "health": "СЕНТИНЕЛ ЗДОРОВЬЕ",
        "decisions": "СЕНТИНЕЛ РЕШЕНИЯ",
        "travel": "СЕНТИНЕЛ ПОЕЗДКИ",
        "creativity": "СЕНТИНЕЛ ТВОРЧЕСТВО",
        "study": "СЕНТИНЕЛ УЧЕБА",
        "shopping": "СЕНТИНЕЛ ПОКУПКИ"
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

    # Helper: under the new degraded contract an attempt with < 9 valid rows
    # is rejected atomically; BOTH attempts reject => no raise, all 12 rows
    # keep the honest fallback and no invalid text is ever shown.
    async def assert_degraded(mock_output):
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
                planet_influences=[],
                sphere_scores=[],
                important_items=[],
            )
            assert mock_llm.call_count == 2  # exactly one bounded retry
            for row in concrete_advice.rows:
                assert row.text == "Рекомендация временно недоступна."
                assert "СЕНТИНЕЛ" not in row.text
                assert "Transit_" not in row.text
                assert "Марс" not in row.text

    # 1. Latin text rejected (invalidate 4 keys -> 8 valid < 9)
    invalid_latin = valid_mock_texts.copy()
    for k in ["work", "money", "documents", "relationships"]:
        invalid_latin[k] = "СЕНТИНЕЛ work СЕНТИНЕЛ"
    await assert_degraded(invalid_latin)

    # 2. Transit_ / Natal_ rejected (invalidate 4 keys)
    invalid_prefix = valid_mock_texts.copy()
    for k in ["work", "money", "documents", "relationships"]:
        invalid_prefix[k] = "СЕНТИНЕЛ Transit_Moon СЕНТИНЕЛ"
    await assert_degraded(invalid_prefix)

    # 3. Missing key rejected (wrong exact key set)
    invalid_missing = valid_mock_texts.copy()
    del invalid_missing["work"]
    await assert_degraded(invalid_missing)

    # 4. Extra key rejected (wrong exact key set)
    invalid_extra = valid_mock_texts.copy()
    invalid_extra["extra_key"] = "СЕНТИНЕЛ"
    await assert_degraded(invalid_extra)

    # 5. Hallucinated planet rejected (invalidate 4 keys)
    invalid_hallucination = valid_mock_texts.copy()
    for k in ["work", "money", "documents", "relationships"]:
        invalid_hallucination[k] = "СЕНТИНЕЛ Марс СЕНТИНЕЛ"
    await assert_degraded(invalid_hallucination)


@pytest.mark.asyncio
async def test_today_interpretation_service_allowed_evidence_planets():
    """Text mentioning a planet from evidence passes, but other planets fail."""
    service = TodayInterpretationService()

    mock_output = {
        "work": "Марс дает энергию.",
        "money": "СЕНТИНЕЛ",
        "documents": "СЕНТИНЕЛ",
        "relationships": "СЕНТИНЕЛ",
        "sport": "СЕНТИНЕЛ",
        "communication": "СЕНТИНЕЛ",
        "health": "СЕНТИНЕЛ",
        "decisions": "СЕНТИНЕЛ",
        "travel": "СЕНТИНЕЛ",
        "creativity": "СЕНТИНЕЛ",
        "study": "СЕНТИНЕЛ",
        "shopping": "СЕНТИНЕЛ"
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

        assert concrete_advice.rows[0].text == "Марс дает энергию."

    # Test that mentioning Venus (not in evidence) is rejected — under the
    # degraded contract both attempts reject => all rows keep the fallback.
    invalid_output = mock_output.copy()
    for k in ["work", "money", "documents", "relationships"]:
        invalid_output[k] = "Венера помогает."

    with patch("app.services.llm_service.LLMService.generate_concrete_advice", new_callable=AsyncMock) as mock_llm, \
         patch("app.core.config.settings.openrouter_api_key", "abc123xyz"):
        mock_llm.return_value = invalid_output
        concrete_advice, _, _ = await service.build(
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
        assert mock_llm.call_count == 2
        for row in concrete_advice.rows:
            assert row.text == "Рекомендация временно недоступна."
            assert "Венера" not in row.text


@pytest.mark.asyncio
async def test_today_interpretation_service_test_key_enables_llm():
    """A key containing 'test' (e.g. 'test-key') still enables the LLM path."""
    service = TodayInterpretationService()

    mock_output = {k: "СЕНТИНЕЛ" for k in ["work", "money", "documents", "relationships", "sport", "communication", "health", "decisions", "travel", "creativity", "study", "shopping"]}

    with patch("app.services.llm_service.LLMService.generate_concrete_advice", new_callable=AsyncMock) as mock_llm, \
         patch("app.core.config.settings.openrouter_api_key", "test-key"):
        mock_llm.return_value = mock_output

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

        assert mock_llm.called
        assert concrete_advice.rows[0].text == "СЕНТИНЕЛ"


@pytest.mark.asyncio
async def test_concrete_advice_contradiction_prevention():
    """Ensure that rows do not have verdict/evidence contradictions.
    - No 'good' row with primary square/opposition evidence.
    - No 'caution'/'avoid' row with only soft-aspect primary evidence.
    """
    service = TodayInterpretationService()

    # 1. Test direct score sphere with good verdict but only tense aspect signals
    # It should fall back to sphere_score or house, but NOT select the tense aspect.
    signals = [
        AstroSignal(
            type="aspect",
            planet="Transit_Mars",
            target_planet="Saturn",
            aspect_type="square",
            orb=1.5,
            strength=0.9,
        )
    ]
    sphere_scores = [
        SphereScore(key="career_ambition", score=7.5, rank=1)  # Mapped to 'decisions' via BACKEND_TO_PRODUCT_KEY_MAP
    ]

    concrete_advice, _, _ = await service.build(
        target_date=date(2026, 7, 5),
        day_status="supportive",
        scoring_result={"day_status": "supportive", "sphere_scores": {"career_ambition": 7.5}},
        signals=signals,
        semantic_layer=None,
        day_chart=None,
        planet_influences=[],
        sphere_scores=sphere_scores,
        important_items=[],
    )

    # Find the row for decisions
    decisions_row = next(r for r in concrete_advice.rows if r.key == "decisions")
    assert decisions_row.verdict == "good"
    assert len(decisions_row.evidence) > 0
    # The primary evidence must NOT be the square aspect
    assert decisions_row.evidence[0].kind != "aspect"
    assert decisions_row.evidence[0].kind == "sphere_score"

    # 2. Test direct score sphere with caution verdict but only soft aspect signals
    # It should fall back to sphere_score or house, but NOT select the soft aspect.
    signals = [
        AstroSignal(
            type="aspect",
            planet="Transit_Mars",
            target_planet="Saturn",
            aspect_type="trine",
            orb=1.5,
            strength=0.9,
        )
    ]
    sphere_scores = [
        SphereScore(key="career_ambition", score=2.5, rank=1)  # Mapped to 'decisions'
    ]

    concrete_advice, _, _ = await service.build(
        target_date=date(2026, 7, 5),
        day_status="supportive",
        scoring_result={"day_status": "supportive", "sphere_scores": {"career_ambition": 2.5}},
        signals=signals,
        semantic_layer=None,
        day_chart=None,
        planet_influences=[],
        sphere_scores=sphere_scores,
        important_items=[],
    )

    decisions_row = next(r for r in concrete_advice.rows if r.key == "decisions")
    assert decisions_row.verdict == "caution"
    assert len(decisions_row.evidence) > 0
    # The primary evidence must NOT be the trine aspect
    assert decisions_row.evidence[0].kind != "aspect"
    assert decisions_row.evidence[0].kind == "sphere_score"

    # 3. Test no-direct-score sphere (e.g. shopping, Venus maps to shopping)
    # If Venus has only a square aspect, verdict must be caution and evidence must be that aspect.
    signals = [
        AstroSignal(
            type="aspect",
            planet="Transit_Venus",
            target_planet="Uranus",
            aspect_type="square",
            orb=1.0,
            strength=0.8,
        )
    ]
    concrete_advice, _, _ = await service.build(
        target_date=date(2026, 7, 5),
        day_status="supportive",
        scoring_result={"day_status": "supportive", "sphere_scores": {}},
        signals=signals,
        semantic_layer=None,
        day_chart=None,
        planet_influences=[],
        sphere_scores=[],
        important_items=[],
    )

    shopping_row = next(r for r in concrete_advice.rows if r.key == "shopping")
    assert shopping_row.verdict == "caution"
    assert len(shopping_row.evidence) == 1
    assert shopping_row.evidence[0].kind == "aspect"
    assert shopping_row.evidence[0].aspect_type == "square"
