# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_TODAY_LLM_GATHER_OVERLAP
# ROLE: Proves real concurrency of the six independent Today LLM calls.
# DEPENDENCIES: pytest, pytest-asyncio, httpx, unittest.mock
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-LLM-GATHER-OVERLAP
# purpose: Prove with a single shared barrier and timing that all six Today LLM
#   calls (headline, reading, notes, why, concrete-advice batch,
#   planet-interpretation batch) run concurrently via asyncio.gather — none may
#   complete before all six have started — that payload semantics and fallbacks
#   are preserved, and that no coroutines leak.
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
