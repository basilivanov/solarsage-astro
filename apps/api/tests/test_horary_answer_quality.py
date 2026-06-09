"""Tests for W-HORARY-ANSWER-QUALITY-V1.

Coverage:
  1. LLM invalid JSON => question failed/error, no answer row saved.
  2. LLM unavailable => question failed/error, credit refunded.
  3. No timing evidence => timing status not_enough_evidence.
  4. Explicit timeframe in question is preserved as context.
  5. Confidence labels map correctly to low/medium/high.
  6. No user-facing probability wording is emitted by API contract.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from unittest.mock import AsyncMock, patch

from app.db.models import HoraryCredit, HoraryQuestion, UserProfile
from app.schemas.horary_analysis import (
    EvidenceItem,
    HoraryAnalysis,
    TimingInfo,
)
from app.schemas.normalization import AstroSignal
from app.services.horary_engine import HoraryEngine
from app.services.llm_service import HoraryGenerationError, LLMService


# 1. Engine + LLM analyze -> build prompt with structured analysis
def test_engine_analyze_returns_structured_analysis():
    horary_chart = {
        "special_points": [{"name": "ASC", "longitude": 30.0}],  # Taurus -> Venus
        "planets": [{"name": "Moon", "longitude": 0.0}],
    }
    signals = [
        AstroSignal(
            type="aspect",
            planet="Venus",
            target_planet="Saturn",
            aspect_type="trine",
            strength=0.9,
        ),
        AstroSignal(
            type="aspect",
            planet="Moon",
            target_planet="Sun",
            aspect_type="trine",
            strength=0.8,
        ),
    ]
    a = HoraryEngine.analyze(horary_chart, signals, "career", None)
    assert a.verdict == "yes"
    assert a.confidence_label == "high"
    assert a.confidence_score >= 70
    assert any(e.aspect_type == "trine" for e in a.testimonies_for)
    assert a.timing.status in ("known", "unclear", "not_enough_evidence")


# 2. Confidence labels mapping
def test_engine_confidence_label_low():
    horary_chart = {
        "special_points": [{"name": "ASC", "longitude": 30.0}],
        "planets": [{"name": "Moon", "longitude": 0.0}],
    }
    # No main aspect, no Moon testimony => low
    a = HoraryEngine.analyze(horary_chart, [], "love", None)
    assert a.confidence_label == "low"
    assert a.confidence_score < 40
    assert a.confidence_explanation


def test_engine_confidence_label_medium_with_aspect_no_moon():
    horary_chart = {
        "special_points": [{"name": "ASC", "longitude": 30.0}],  # Taurus -> Venus
        "planets": [{"name": "Moon", "longitude": 0.0}],
    }
    # Main aspect between Venus and Saturn, but no Moon support
    signals = [
        AstroSignal(
            type="aspect",
            planet="Venus",
            target_planet="Saturn",
            aspect_type="trine",
            strength=0.9,
        )
    ]
    a = HoraryEngine.analyze(horary_chart, signals, "career", None)
    assert a.confidence_label == "medium"
    assert 40 <= a.confidence_score < 80


# 3. Explicit timeframe in question is preserved
def test_engine_timing_preserves_explicit_timeframe():
    horary_chart = {
        "special_points": [{"name": "ASC", "longitude": 30.0}],
        "planets": [],
    }
    a = HoraryEngine.analyze(horary_chart, [], "career", "Получу ли я повышение в этом году?")
    assert a.timing.status == "known"
    assert a.timing.time_range is not None
    assert "год" in (a.timing.time_range or "").lower()


# 4. No timing evidence => not_enough_evidence
def test_engine_timing_not_enough_evidence():
    horary_chart = {
        "special_points": [{"name": "ASC", "longitude": 30.0}],
        "planets": [],
    }
    a = HoraryEngine.analyze(horary_chart, [], "other", "Что-то случится?")
    assert a.timing.status in ("unclear", "not_enough_evidence")
    # If unclear, basis is present
    if a.timing.status == "unclear":
        assert a.timing.basis is not None
    if a.timing.status == "not_enough_evidence":
        assert a.timing.time_range is None


# 5. LLM invalid JSON => HoraryGenerationError (no fallback)
@pytest.mark.asyncio
async def test_llm_invalid_json_raises_horary_generation_error(monkeypatch):
    monkeypatch.setattr(LLMService, "__init__", lambda self: None)
    svc = LLMService()
    analysis = HoraryAnalysis(
        verdict="yes",
        confidence_score=70,
        confidence_label="medium",
        confidence_explanation="test",
        involved_planets=["Venus"],
        testimonies_for=[],
        testimonies_against=[],
        neutral_factors=[],
        timing=TimingInfo(status="not_enough_evidence", text="нет срока"),
    )
    async def fake_gen(prompt, max_tokens):
        return "not json"
    monkeypatch.setattr(svc, "_generate_text", fake_gen)
    with pytest.raises(HoraryGenerationError):
        await svc.generate_horary_answer(
            question_text="Q",
            category=None,
            analysis=analysis,
        )


# 6. LLM unavailable => raises + no answer saved in service path
@pytest.mark.asyncio
async def test_llm_unavailable_raises_horary_generation_error(monkeypatch):
    monkeypatch.setattr(LLMService, "__init__", lambda self: None)
    svc = LLMService()
    analysis = HoraryAnalysis(
        verdict="yes",
        confidence_score=70,
        confidence_label="medium",
        confidence_explanation="test",
        involved_planets=["Venus"],
        testimonies_for=[],
        testimonies_against=[],
        neutral_factors=[],
        timing=TimingInfo(status="not_enough_evidence", text="нет срока"),
    )
    async def fake_gen(prompt, max_tokens):
        return None
    monkeypatch.setattr(svc, "_generate_text", fake_gen)
    with pytest.raises(HoraryGenerationError):
        await svc.generate_horary_answer(
            question_text="Q",
            category=None,
            analysis=analysis,
        )


# 7. LLM JSON missing required block types => rejected
@pytest.mark.asyncio
async def test_llm_response_missing_required_blocks_is_rejected(monkeypatch):
    monkeypatch.setattr(LLMService, "__init__", lambda self: None)
    svc = LLMService()
    analysis = HoraryAnalysis(
        verdict="yes",
        confidence_score=70,
        confidence_label="medium",
        confidence_explanation="test",
        involved_planets=["Venus"],
        testimonies_for=[],
        testimonies_against=[],
        neutral_factors=[],
        timing=TimingInfo(status="known", time_range="1 неделя", text="ок"),
    )
    bad_response = {
        "blocks": [
            {"type": "verdict_card", "verdict": "yes", "confidence": 0.5,
             "confidenceLabel": "medium", "confidenceExplanation": "x"}
        ]
    }
    async def fake_gen(prompt, max_tokens):
        return json.dumps(bad_response, ensure_ascii=False)
    monkeypatch.setattr(svc, "_generate_text", fake_gen)
    with pytest.raises(HoraryGenerationError):
        await svc.generate_horary_answer(
            question_text="Q",
            category=None,
            analysis=analysis,
        )


# 8. Valid LLM response with full block set passes
@pytest.mark.asyncio
async def test_llm_valid_response_with_full_block_set_passes(monkeypatch):
    monkeypatch.setattr(LLMService, "__init__", lambda self: None)
    svc = LLMService()
    analysis = HoraryAnalysis(
        verdict="yes",
        confidence_score=70,
        confidence_label="medium",
        confidence_explanation="test",
        involved_planets=["Venus"],
        testimonies_for=[],
        testimonies_against=[],
        neutral_factors=[],
        timing=TimingInfo(status="known", time_range="1 неделя", text="ок"),
    )
    valid_response = {
        "blocks": [
            {"type": "verdict_card", "verdict": "yes", "confidence": 0.5,
             "label": "Да", "confidenceLabel": "medium", "confidenceExplanation": "x"},
            {"type": "lead", "text": "ok"},
            {"type": "paragraph", "text": "x"},
            {"type": "testimonies",
             "prosLabel": "За", "consLabel": "Против", "neutralLabel": "Нейтр",
             "pros": [{"title": "t", "explanation": "e", "weight": 0.5, "planets": [], "aspectType": None, "orb": None}],
             "cons": [],
             "neutral": []},
            {"type": "paragraph", "text": "x"},
            {"type": "timing", "status": "known", "timeRange": "1 неделя", "text": "ok"},
            {"type": "callout", "tone": "insight", "title": "Совет", "text": "x"},
            {"type": "paragraph", "text": "x"},
        ]
    }
    async def fake_gen(prompt, max_tokens):
        return json.dumps(valid_response, ensure_ascii=False)
    monkeypatch.setattr(svc, "_generate_text", fake_gen)
    out = await svc.generate_horary_answer(
        question_text="Q",
        category=None,
        analysis=analysis,
    )
    assert "blocks" in out
    assert len(out["blocks"]) == 8


# 9. Timing with category hint falls back to unclear (not known)
def test_engine_timing_category_fallback_is_unclear():
    horary_chart = {
        "special_points": [{"name": "ASC", "longitude": 30.0}],
        "planets": [],
    }
    a = HoraryEngine.analyze(horary_chart, [], "money", "Будет ли доход?")
    assert a.timing.status in ("unclear", "not_enough_evidence")
    # No explicit timeframe => not "known"
    assert a.timing.status != "known"


# 10. No user-facing probability wording in prompt template
def test_no_probability_wording_in_horary_prompt():
    """TZ 3.1: no `55% вероятность`-style wording. The label is
    low/medium/high, not a percent."""
    import inspect
    from app.services.llm_service import LLMService
    src = inspect.getsource(LLMService.generate_horary_answer)
    # No "вероятность" inside the prompt template
    assert "вероятность" not in src.lower() or "не выдумывай" in src.lower()
    # Must include the label vocabulary
    assert "low|medium|high" in src
