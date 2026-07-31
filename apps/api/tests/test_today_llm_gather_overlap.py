# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_TODAY_LLM_GATHER_OVERLAP
# ROLE: Preserves TodayService cancellation and LLM fallback unit proofs.
# DEPENDENCIES: pytest, pytest-asyncio, unittest.mock
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-LLM-GATHER-OVERLAP
# purpose: Preserve cancellation cleanup for legacy TodayService internals and
#   the LLM provider fallback/cancellation boundary after the day HTTP switch.
# owns:
#   - apps/api/tests/test_today_llm_gather_overlap.py
# inputs: TodayService/LLMService unit doubles
# outputs: pytest assertions
# dependencies: application services and unittest.mock
# side_effects: none (all externals mocked)
# emitted_logs: n/a (tests)
# invariants:
#   - Cancellation consumes every spawned child task.
# failure_policy: hard assertion failures; no skipped proofs.
# END_MODULE_CONTRACT: M-TEST-TODAY-LLM-GATHER-OVERLAP

from __future__ import annotations

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import settings


def _sidecar_client_mock() -> MagicMock:
    mock_client = MagicMock()
    mock_client.get_natal = AsyncMock(return_value={
        "planets": [
            {"name": "Sun", "longitude": 69.5, "latitude": 0.0, "speed": 1.0, "sign": "Gemini"},
            {"name": "Moon", "longitude": 120.0, "latitude": 0.0, "speed": 13.0, "sign": "Leo"},
            {"name": "Mercury", "longitude": 80.0, "latitude": 0.0, "speed": 1.5, "sign": "Gemini"},
            {"name": "Venus", "longitude": 100.0, "latitude": 0.0, "speed": 1.2, "sign": "Cancer"},
            {"name": "Mars", "longitude": 200.0, "latitude": 0.0, "speed": 0.5, "sign": "Libra"},
        ],
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
        "planets": [
            {"name": "Sun", "longitude": 150.0, "latitude": 0.0, "speed": 1.0, "sign": "Virgo"},
            {"name": "Moon", "longitude": 170.0, "latitude": 0.0, "speed": 13.0, "sign": "Libra"},
        ],
        "special_points": [],
    })
    return mock_client


@pytest.mark.asyncio
async def test_request_cancellation_cancels_all_llm_children(db_session):
    # START_BLOCK: CANCELLATION_PROOF
    # If the request task itself is cancelled mid-phase, every child LLM task
    # is cancelled and consumed; nothing keeps running, no paid call leaks,
    # and CancelledError propagates unmasked.
    from datetime import date as Date, time as Time
    from app.db.models import User, UserProfile
    from app.schemas.access import ContentAccessState
    from app.services.today_service import TodayService

    user = User(tg_user_id=880007, tg_username="cancelproof")
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserProfile(
        user_id=user.id, gender="male",
        birthday=Date(1990, 1, 15), birth_time=Time(12, 0),
        birth_city="Moscow", birth_lat=55.75, birth_lon=37.61,
        birth_tz="Europe/Moscow", is_onboarded=True,
    ))
    await db_session.commit()

    started_count = 0
    started = asyncio.Event()
    child_tasks: list[asyncio.Task] = []
    advice_calls = 0

    async def slow_once(*args, **kwargs):
        nonlocal started_count
        started_count += 1
        if started_count >= 5:
            started.set()
        await asyncio.sleep(30)
        return None

    async def slow_advice(*args, **kwargs):
        nonlocal advice_calls
        advice_calls += 1
        return await slow_once(*args, **kwargs)

    real_create_task = asyncio.create_task
    def spy_create_task(coro):
        task = real_create_task(coro)
        child_tasks.append(task)
        return task

    from app.services.day_scoring_runtime_service import DualRunResult
    from app.schemas.normalization import AstroSignal
    from app.schemas.natal import NatalContextData

    signals = [AstroSignal(type="aspect", planet="Transit_Moon", target_planet="Pluto",
                           aspect_type="opposition", orb=1.0, strength=0.9)]
    v1_result = {"day_status": "steady", "sphere_scores": {}, "top_signals": signals[:1]}
    from app.core.versions import LEGACY_SCORING_VERSION
    dual = DualRunResult(
        selected_result=v1_result, selected_scoring_version=LEGACY_SCORING_VERSION,
        v1_result=v1_result, v2_result=None, diff=None, v2_error=None,
    )

    mock_client = _sidecar_client_mock()

    with patch("app.services.today_service.get_solarsage_client", return_value=mock_client),          patch("app.services.today_service.NatalContextService.get_or_build_natal_context", AsyncMock(return_value=NatalContextData(house_system="PLACIDUS", planets=[], houses=[], aspects=[], angles=[]))),          patch("app.services.today_service.NormalizationService.normalize_day", return_value=signals),          patch.object(TodayService, "_get_yesterday_signals", AsyncMock(return_value=None)),          patch("app.services.today_service.DayScoringRuntimeService.compute", return_value=dual),          patch("app.services.today_service.LLMService") as ts_llm_class,          patch("app.services.today_interpretation_service.LLMService") as ti_llm_class,          patch("app.services.today_service.asyncio.create_task", side_effect=spy_create_task),          patch.object(settings, "openrouter_api_key", "test-key"):
        ts = ts_llm_class.return_value
        ts.generate_headline = slow_once
        ts.generate_reading = slow_once
        ts.generate_notes = slow_once
        ts.generate_why_sections = slow_once
        ti = ti_llm_class.return_value
        ti.generate_concrete_advice = slow_advice
        ti.generate_planet_interpretations = slow_once

        service = TodayService(db_session)
        access = ContentAccessState(state="full", reason="active_subscription")
        request_task = asyncio.get_running_loop().create_task(
            service.get_today_payload(
                user_id=user.id, target_date=Date(2026, 7, 8),
                access_state=access, skip_prefetch=True,
            )
        )
        await asyncio.wait_for(started.wait(), timeout=5)
        await asyncio.sleep(0.05)
        request_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await request_task

    # Every spawned child task is finished (cancelled or done) — none pending.
    assert child_tasks, "no child tasks were captured"
    for task in child_tasks:
        assert task.done(), "a child LLM task is still pending after cancellation"
    # The advice batch was attempted exactly once (never re-run by fallback).
    assert advice_calls == 1
    # END_BLOCK: CANCELLATION_PROOF

@pytest.mark.asyncio
async def test_llm_service_fallback_budget_and_cancellation():
    """Verify LLMService fallback budget check (remaining < 15s) and CancelledError propagation (doc 29 §6.3, §6.4)."""
    from app.services.llm_service import LLMService

    service = LLMService()

    # 1. Fallback budget test: remaining < 15s skips DeepSeek fallback
    with patch.object(service, "_openrouter_generate", side_effect=RuntimeError("OpenRouter down")), \
         patch.object(service, "_deepseek_generate", side_effect=RuntimeError("DeepSeek down")) as mock_deepseek:
        import time
        now = time.monotonic()
        # deadline_at is in 10 seconds (remaining = 10s < 15s)
        res = await service._generate_text("test prompt", max_tokens=100, deadline_at=now + 10.0)
        assert res is None
        mock_deepseek.assert_not_called()

    # 2. CancelledError test: CancelledError in provider is re-raised, not swallowed
    with patch.object(service, "_openrouter_generate", side_effect=asyncio.CancelledError()):
        with pytest.raises(asyncio.CancelledError):
            await service._generate_text("test prompt", max_tokens=100)
