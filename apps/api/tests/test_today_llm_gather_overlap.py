# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_TODAY_LLM_GATHER_OVERLAP
# ROLE: Proves real concurrency of the six independent Today LLM calls.
# DEPENDENCIES: pytest, pytest-asyncio, httpx, unittest.mock
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-LLM-GATHER-OVERLAP
# purpose: Prove with a single shared barrier and timing that all six Today LLM
#   calls (headline, reading, notes, why, concrete-advice batch,
#   planet-interpretation batch) run concurrently inside the bounded
#   request-local task group (10s LLM phase deadline, cancelled+awaited) —
#   none may complete before all six have started — that payload semantics and
#   fallbacks are preserved, and that no coroutines leak.
# owns:
#   - apps/api/tests/test_today_llm_gather_overlap.py
# inputs: endpoint request with mocked sidecar client and LLM methods
# outputs: pytest assertions
# dependencies: conftest fixtures (async_client, make_initdata, db_session)
# side_effects: none (all externals mocked)
# emitted_logs: n/a (tests)
# invariants:
#   - One shared barrier covers all six calls: any sequential or only
#     partially-parallel executor deadlocks (release never fires) and fails.
#   - Payload placeholder/fallback semantics stay byte-identical to the
#     pre-gather contract.
# failure_policy: hard assertion failures; no skipped proofs.
# END_MODULE_CONTRACT: M-TEST-TODAY-LLM-GATHER-OVERLAP

from __future__ import annotations

import asyncio
import time

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.config import settings

CANONICAL_12_KEYS = [
    "work", "money", "documents", "relationships", "sport", "communication",
    "health", "decisions", "travel", "creativity", "study", "shopping",
]


class BarrierGroup:
    # START_BLOCK: BARRIER_GROUP
    # purpose: Prove full start-before-end overlap of a named coroutine group.
    # A sequential executor deadlocks here (release never fires), so passing
    # the barrier is a hard concurrency proof, not a string check.
    def __init__(self, names: list[str], barrier_timeout: float = 3.0):
        self.names = set(names)
        self.release = asyncio.Event()
        self.barrier_timeout = barrier_timeout
        self.events: list[tuple[str, str]] = []

    def mock(self, name: str, ret=None):
        async def _mock(*args, **kwargs):
            self.events.append((name, "start"))
            if self.names.issubset({n for n, e in self.events if e == "start"}):
                self.release.set()
            try:
                await asyncio.wait_for(self.release.wait(), timeout=self.barrier_timeout)
            except asyncio.TimeoutError as exc:
                raise AssertionError(
                    f"no overlap: group {sorted(self.names)} never fully started (sequential execution?)"
                ) from exc
            self.events.append((name, "end"))
            return ret
        return _mock

    def assert_full_overlap(self) -> None:
        start_idx = [i for i, (_, kind) in enumerate(self.events) if kind == "start"]
        end_idx = [i for i, (_, kind) in enumerate(self.events) if kind == "end"]
        assert start_idx and end_idx, f"barrier group never ran: {self.events}"
        assert len(start_idx) == len(self.names), f"not all group members started: {self.events}"
        assert max(start_idx) < min(end_idx), (
            f"not a full overlap: some member ended before all started: {self.events}"
        )
    # END_BLOCK: BARRIER_GROUP


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
async def test_six_llm_calls_overlap_with_preserved_semantics(
    async_client: AsyncClient, make_initdata, db_session
):
    # START_BLOCK: OVERLAP_PROOF
    raw = make_initdata(user_id=8002, username="overlap")
    await async_client.post("/api/auth/telegram", json={"initData": raw})
    await async_client.put("/api/profile", json={
        "gender": "male",
        "birth": {
            "birthday": "1990-01-15", "birthTime": "12:00",
            "birthCity": "Moscow", "birthLat": 55.75, "birthLon": 37.61,
            "birthTz": "Europe/Moscow",
        }
    })

    all_calls = BarrierGroup(["headline", "reading", "notes", "why", "advice", "planets"])
    # One shared barrier across ALL six LLM calls: release fires only when every
    # one of headline/reading/notes/why/advice/planets has started, so no call
    # may complete before all six are in flight. Two independent group barriers
    # would NOT prove cross-group overlap (outer could finish before inner
    # starts); a partially-parallel executor (e.g. inner pair sequential, or
    # inner gather awaited only after the outer four complete) deadlocks here.
    advice_payload = {k: "Спокойный и ровный день для дел и забот." for k in CANONICAL_12_KEYS}
    planet_payload = {"Sun": "Солнце поддерживает ваши планы сегодня."}

    with patch("app.services.natal_context_service.get_solarsage_client") as client_factory, \
         patch("app.services.today_service.get_solarsage_client", client_factory), \
         patch("app.services.today_service.LLMService") as ts_llm_class, \
         patch("app.services.today_interpretation_service.LLMService") as ti_llm_class, \
         patch.object(settings, "openrouter_api_key", "test-overlap-key"):
        client_factory.return_value = _sidecar_client_mock()

        ts = ts_llm_class.return_value
        ts.generate_headline = all_calls.mock("headline", None)
        ts.generate_reading = all_calls.mock("reading", None)
        ts.generate_notes = all_calls.mock("notes", None)
        ts.generate_why_sections = all_calls.mock("why", None)

        ti = ti_llm_class.return_value
        ti.generate_concrete_advice = all_calls.mock("advice", advice_payload)
        ti.generate_planet_interpretations = all_calls.mock("planets", planet_payload)

        t0 = time.perf_counter()
        resp = await async_client.get("/api/day/today")
        elapsed = time.perf_counter() - t0

    assert resp.status_code == 200, resp.text
    all_calls.assert_full_overlap()
    # Sequential execution of six 3s-barriered calls cannot finish under 3s;
    # concurrent execution finishes as soon as the shared release fires.
    assert elapsed < all_calls.barrier_timeout, (
        f"request took {elapsed:.2f}s — calls look sequential, not gathered"
    )

    day = resp.json()
    # Fallback semantics preserved for the four None-returning calls.
    assert day["headline"] == "Ваш персональный разбор дня"
    assert "Данные временно недоступны" in day["notes"]
    assert "Данные временно недоступны" in day["reading"]["paragraphs"][0]
    assert day["whyThisHappens"]["sections"][0]["title"] == "Данные временно недоступны"
    # Batch application preserved: concrete advice rows carry the batch text
    # and the day summary block exists; planet interpretation applied.
    advice_rows = day["concreteAdvice"]["rows"]
    assert advice_rows, "concrete advice rows must exist"
    assert all(r["text"] == "Спокойный и ровный день для дел и забот." for r in advice_rows)
    assert day["daySummary"]["facts"] is not None
    if day.get("dayChart") and day["dayChart"].get("transitPlanets"):
        interps = [p.get("interpretation") for p in day["dayChart"]["transitPlanets"]]
        assert "Солнце поддерживает ваши планы сегодня." in interps

    # No coroutine leaks: nothing from our mocks remains pending.
    await asyncio.sleep(0.05)
    pending = [t for t in asyncio.all_tasks() if not t.done()]
    leaked = [
        t.get_coro().__qualname__ for t in pending
        if t.get_coro() is not None and "_mock" in t.get_coro().__qualname__
    ]
    assert not leaked, f"coroutine leak after gather: {leaked}"
    # END_BLOCK: OVERLAP_PROOF


@pytest.mark.asyncio
async def test_slow_branch_cancelled_at_deadline_fast_siblings_kept(
    async_client: AsyncClient, make_initdata, db_session, monkeypatch
):
    # START_BLOCK: DEADLINE_PROOF
    # A slow why-branch must be cancelled+awaited at the request-local LLM
    # phase deadline while fast siblings keep their results; the endpoint
    # completes near the deadline (never the slow branch's full duration)
    # and no task leaks.
    raw = make_initdata(user_id=8005, username="deadline")
    await async_client.post("/api/auth/telegram", json={"initData": raw})
    await async_client.put("/api/profile", json={
        "gender": "male",
        "birth": {
            "birthday": "1990-01-15", "birthTime": "12:00",
            "birthCity": "Moscow", "birthLat": 55.75, "birthLon": 37.61,
            "birthTz": "Europe/Moscow",
        }
    })

    from app.services import today_service as ts_module
    monkeypatch.setattr(ts_module, "LLM_PHASE_DEADLINE_SECONDS", 0.5)

    completed: list[str] = []

    async def fast(name):
        async def _impl(*args, **kwargs):
            await asyncio.sleep(0.01)
            completed.append(name)
            return None
        return _impl

    slow_started = asyncio.Event()

    async def slow_why(*args, **kwargs):
        slow_started.set()
        await asyncio.sleep(5)
        return None

    with patch("app.services.natal_context_service.get_solarsage_client") as client_factory, \
         patch("app.services.today_service.get_solarsage_client", client_factory), \
         patch("app.services.today_service.LLMService") as ts_llm_class, \
         patch("app.services.today_interpretation_service.LLMService") as ti_llm_class, \
         patch.object(settings, "openrouter_api_key", "test-key"):
        client_factory.return_value = _sidecar_client_mock()

        ts = ts_llm_class.return_value
        ts.generate_headline = await fast("headline")
        ts.generate_reading = await fast("reading")
        ts.generate_notes = await fast("notes")
        ts.generate_why_sections = slow_why

        ti = ti_llm_class.return_value
        ti.generate_concrete_advice = await fast("advice")
        ti.generate_planet_interpretations = await fast("planets")

        t0 = time.perf_counter()
        resp = await async_client.get("/api/day/today")
        elapsed = time.perf_counter() - t0

    assert resp.status_code == 200, resp.text
    # Completed near the logical deadline (0.5s), never the 5s slow branch.
    assert elapsed < 3.0, f"endpoint took {elapsed:.2f}s — slow branch not cancelled"
    # Fast siblings finished; the slow branch started but was cancelled.
    assert "headline" in completed and "notes" in completed
    assert slow_started.is_set()

    await asyncio.sleep(0.05)
    pending = [t for t in asyncio.all_tasks() if not t.done()]
    leaked = [
        t.get_coro().__qualname__ for t in pending
        if t.get_coro() is not None and "slow_why" in t.get_coro().__qualname__
    ]
    assert not leaked, f"leaked cancelled branch: {leaked}"
    # END_BLOCK: DEADLINE_PROOF


@pytest.mark.asyncio
async def test_interpretation_cancel_falls_back_deterministically(
    async_client: AsyncClient, make_initdata, db_session, monkeypatch
):
    # The interpretation branch itself is slow: it is cancelled at the
    # deadline and rebuilt via the honest deterministic force_no_llm path
    # (advice fallback rows), with exactly zero extra external calls.
    raw = make_initdata(user_id=8006, username="deadline2")
    await async_client.post("/api/auth/telegram", json={"initData": raw})
    await async_client.put("/api/profile", json={
        "gender": "male",
        "birth": {
            "birthday": "1990-01-15", "birthTime": "12:00",
            "birthCity": "Moscow", "birthLat": 55.75, "birthLon": 37.61,
            "birthTz": "Europe/Moscow",
        }
    })

    from app.services import today_service as ts_module
    monkeypatch.setattr(ts_module, "LLM_PHASE_DEADLINE_SECONDS", 0.5)

    advice_calls = 0

    async def fast_none(*args, **kwargs):
        await asyncio.sleep(0.01)
        return None

    async def slow_advice(*args, **kwargs):
        nonlocal advice_calls
        advice_calls += 1
        await asyncio.sleep(5)
        return None

    with patch("app.services.natal_context_service.get_solarsage_client") as client_factory, \
         patch("app.services.today_service.get_solarsage_client", client_factory), \
         patch("app.services.today_service.LLMService") as ts_llm_class, \
         patch("app.services.today_interpretation_service.LLMService") as ti_llm_class, \
         patch.object(settings, "openrouter_api_key", "test-key"):
        client_factory.return_value = _sidecar_client_mock()

        ts = ts_llm_class.return_value
        ts.generate_headline = fast_none
        ts.generate_reading = fast_none
        ts.generate_notes = fast_none
        ts.generate_why_sections = fast_none

        ti = ti_llm_class.return_value
        ti.generate_concrete_advice = slow_advice
        ti.generate_planet_interpretations = fast_none

        t0 = time.perf_counter()
        resp = await async_client.get("/api/day/today")
        elapsed = time.perf_counter() - t0

    assert resp.status_code == 200, resp.text
    assert elapsed < 3.0
    # Exactly one slow advice attempt; the force_no_llm fallback makes NO
    # further external calls (count stays 1).
    assert advice_calls == 1
    rows = resp.json()["concreteAdvice"]["rows"]
    assert len(rows) == 12


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
async def test_deadline_degraded_payload_never_cached_even_with_valid_advice(
    async_client: AsyncClient, make_initdata, db_session, monkeypatch
):
    # Slow why branch (times out) + fully valid 12-key advice: the endpoint
    # answers 200 with the honest why fallback, but _cache_payload is never
    # called — a deadline-degraded payload must not poison later reads.
    from app.services import today_service as ts_module
    monkeypatch.setattr(ts_module, "LLM_PHASE_DEADLINE_SECONDS", 0.5)

    raw = make_initdata(user_id=8008, username="deadcache")
    await async_client.post("/api/auth/telegram", json={"initData": raw})
    await async_client.put("/api/profile", json={
        "gender": "male",
        "birth": {
            "birthday": "1990-01-15", "birthTime": "12:00",
            "birthCity": "Moscow", "birthLat": 55.75, "birthLon": 37.61,
            "birthTz": "Europe/Moscow",
        }
    })

    valid_advice = {
        k: f"Спокойный день для дела номер {i}."
        for i, k in enumerate([
            "work", "money", "documents", "relationships", "sport", "communication",
            "health", "decisions", "travel", "creativity", "study", "shopping",
        ])
    }

    async def fast_none(*args, **kwargs):
        await asyncio.sleep(0.01)
        return None

    async def slow_why(*args, **kwargs):
        await asyncio.sleep(5)
        return None

    cache_spy = AsyncMock()
    with patch("app.services.natal_context_service.get_solarsage_client") as client_factory, \
         patch("app.services.today_service.get_solarsage_client", client_factory), \
         patch("app.services.today_service.TodayService._cache_payload", cache_spy), \
         patch("app.services.today_service.LLMService") as ts_llm_class, \
         patch("app.services.today_interpretation_service.LLMService") as ti_llm_class, \
         patch.object(settings, "openrouter_api_key", "test-key"):
        client_factory.return_value = _sidecar_client_mock()

        ts = ts_llm_class.return_value
        ts.generate_headline = fast_none
        ts.generate_reading = fast_none
        ts.generate_notes = fast_none
        ts.generate_why_sections = slow_why

        ti = ti_llm_class.return_value
        ti.generate_concrete_advice = AsyncMock(return_value=valid_advice)
        ti.generate_planet_interpretations = fast_none

        resp = await async_client.get("/api/day/today")

    assert resp.status_code == 200, resp.text
    rows = resp.json()["concreteAdvice"]["rows"]
    assert all(r["text"] == valid_advice[r["key"]] for r in rows)  # advice itself valid
    cache_spy.assert_not_called()


@pytest.mark.asyncio
async def test_llm_phase_completed_event_success_and_deadline(
    async_client: AsyncClient, make_initdata, db_session, monkeypatch
):
    # The phase emits day.llm_phase_completed exactly once per run:
    # outcome=completed with timed_out_branches=0 on success, and
    # outcome=deadline with the correct counts when a branch times out.
    from app.services import today_service as ts_module
    from app.core.logging import log_event as real_log_event

    events: list[tuple] = []

    def capture_log_event(event, **kwargs):
        if event == "day.llm_phase_completed":
            events.append((event, kwargs))
        return real_log_event(event, **kwargs)

    async def run_once(user_id: int, username: str, slow: bool):
        raw = make_initdata(user_id=user_id, username=username)
        await async_client.post("/api/auth/telegram", json={"initData": raw})
        await async_client.put("/api/profile", json={
            "gender": "male",
            "birth": {
                "birthday": "1990-01-15", "birthTime": "12:00",
                "birthCity": "Moscow", "birthLat": 55.75, "birthLon": 37.61,
                "birthTz": "Europe/Moscow",
            }
        })

        async def fast_none(*args, **kwargs):
            await asyncio.sleep(0.01)
            return None

        async def slow_none(*args, **kwargs):
            await asyncio.sleep(5)
            return None

        branch = slow_none if slow else fast_none
        with patch("app.services.natal_context_service.get_solarsage_client") as client_factory, \
             patch("app.services.today_service.get_solarsage_client", client_factory), \
             patch("app.services.today_service.LLMService") as ts_llm_class, \
             patch("app.services.today_interpretation_service.LLMService") as ti_llm_class, \
             patch("app.services.today_service.log_event", side_effect=capture_log_event), \
             patch.object(settings, "openrouter_api_key", "test-key"):
            client_factory.return_value = _sidecar_client_mock()
            ts = ts_llm_class.return_value
            ts.generate_headline = fast_none
            ts.generate_reading = fast_none
            ts.generate_notes = fast_none
            ts.generate_why_sections = branch
            ti = ti_llm_class.return_value
            ti.generate_concrete_advice = fast_none
            ti.generate_planet_interpretations = fast_none
            resp = await async_client.get("/api/day/today")
        assert resp.status_code == 200, resp.text

    await run_once(8009, "phaseok", slow=False)
    assert len(events) == 1
    _, kwargs = events[0]
    assert kwargs["payload"]["outcome"] == "completed"
    assert kwargs["payload"]["timed_out_branches"] == 0
    assert kwargs["payload"]["total_branches"] == 5
    assert kwargs["payload"]["completed_branches"] == 5
    assert kwargs["payload"]["deadline_ms"] == 10000

    monkeypatch.setattr(ts_module, "LLM_PHASE_DEADLINE_SECONDS", 0.5)
    events.clear()
    await run_once(8010, "phaseslow", slow=True)
    assert len(events) == 1
    _, kwargs = events[0]
    assert kwargs["payload"]["outcome"] == "deadline"
    assert kwargs["payload"]["timed_out_branches"] == 1
    assert kwargs["payload"]["completed_branches"] == 4
    assert kwargs["payload"]["deadline_ms"] == 500


@pytest.mark.asyncio
async def test_fresh_payload_meta_and_cache_key_share_prompt_version_3(
    async_client: AsyncClient, make_initdata, db_session
):
    # Public fresh meta.promptVersion == the cache key llm_prompt_version == 3:
    # a prompt/content change never lets a stale payload pass as current.
    raw = make_initdata(user_id=8011, username="pv3")
    await async_client.post("/api/auth/telegram", json={"initData": raw})
    await async_client.put("/api/profile", json={
        "gender": "male",
        "birth": {
            "birthday": "1990-01-15", "birthTime": "12:00",
            "birthCity": "Moscow", "birthLat": 55.75, "birthLon": 37.61,
            "birthTz": "Europe/Moscow",
        }
    })

    captured: list = []

    from app.services.today_service import TodayService

    async def capture_cache(self, user_id, target_date, payload, profile_hash, cache_key=None):
        captured.append(cache_key)

    async def fast_none(*args, **kwargs):
        await asyncio.sleep(0.01)
        return None

    valid_advice = {
        k: f"Спокойный день для дела номер {i}."
        for i, k in enumerate([
            "work", "money", "documents", "relationships", "sport", "communication",
            "health", "decisions", "travel", "creativity", "study", "shopping",
        ])
    }

    with patch("app.services.natal_context_service.get_solarsage_client") as client_factory, \
         patch("app.services.today_service.get_solarsage_client", client_factory), \
         patch.object(TodayService, "_cache_payload", new=capture_cache), \
         patch("app.services.today_service.LLMService") as ts_llm_class, \
         patch("app.services.today_interpretation_service.LLMService") as ti_llm_class, \
         patch.object(settings, "openrouter_api_key", "test-key"):
        client_factory.return_value = _sidecar_client_mock()
        ts = ts_llm_class.return_value
        ts.generate_headline = fast_none
        ts.generate_reading = fast_none
        ts.generate_notes = fast_none
        ts.generate_why_sections = fast_none
        ti = ti_llm_class.return_value
        ti.generate_concrete_advice = AsyncMock(return_value=valid_advice)
        ti.generate_planet_interpretations = fast_none
        resp = await async_client.get("/api/day/today")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meta"]["promptVersion"] == 3
    assert captured, "expected the cache key capture on the cacheable payload"
    assert captured[0].llm_prompt_version == 3
