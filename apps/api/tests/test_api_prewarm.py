# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_API_PREWARM
# ROLE: Tests for the C1 startup database prewarm.
# DEPENDENCIES: pytest, app.main, app.core.logging_events
# GRACE_ANCHORS: [STARTUP_PREWARM_TESTS]
# WAVE: W-WHITE-SCREEN-RESILIENCE
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-API-PREWARM
# purpose: Verify that startup prewarm establishes a DB connection, executes
#   SELECT 1, emits exactly the canonical success/failure events, and remains
#   fail-open.
# owns:
#   - apps/api/tests/test_api_prewarm.py
# inputs: monkeypatched engine and log_event
# outputs: test assertions
# dependencies:
#   - app.main.prewarm_database_pool, app.main.lifespan
#   - app.core.logging_events.LogEventName
# side_effects: none (engine and logger are replaced)
# invariants:
#   - no test opens a real database connection
# failure_policy: raise on assertion failure
# END_MODULE_CONTRACT: M-TEST-API-PREWARM

# START_MODULE_MAP: M-TEST-API-PREWARM
# public_entrypoints:
#   - test_prewarm_connects_and_selects_one
#   - test_prewarm_logs_failure_and_does_not_raise
#   - test_prewarm_timeout_is_fail_open
#   - test_lifespan_invokes_prewarm
#   - test_prewarm_events_are_registered
# semantic_blocks:
#   - PREWARM_SUCCESS
#   - PREWARM_FAILURE
#   - PREWARM_TIMEOUT
#   - LIFESPAN_WIRING
#   - EVENT_REGISTRY
# owned_tests:
#   - apps/api/tests/test_api_prewarm.py
# END_MODULE_MAP: M-TEST-API-PREWARM

from __future__ import annotations

import asyncio
from typing import Any, get_args

import pytest

import app.main as main_module
from app.core.logging_events import LogEventName


class _FakeConnection:
    def __init__(self, statements: list[str], error: Exception | None = None) -> None:
        self._statements = statements
        self._error = error

    async def __aenter__(self) -> "_FakeConnection":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def execute(self, statement: Any) -> None:
        self._statements.append(str(statement))
        if self._error is not None:
            raise self._error


class _FakeEngine:
    def __init__(self, error: Exception | None = None) -> None:
        self.statements: list[str] = []
        self._error = error

    def connect(self) -> _FakeConnection:
        return _FakeConnection(self.statements, self._error)


def _capture_events(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []

    def capture(event: str, **kwargs: Any) -> None:
        events.append((event, kwargs))

    monkeypatch.setattr(main_module, "log_event", capture)
    return events


async def test_prewarm_connects_and_selects_one(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-API-PREWARM.test_prewarm_connects_and_selects_one
    # purpose: Verify the happy path checks out a connection, runs SELECT 1,
    #   and emits api.prewarm_ok with a numeric duration.
    # inputs: monkeypatched fake engine and log_event
    # returns: none
    # side_effects: none
    # emitted_logs: none (captured)
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-API-PREWARM.test_prewarm_connects_and_selects_one
    fake_engine = _FakeEngine()
    monkeypatch.setattr(main_module, "engine", fake_engine)
    events = _capture_events(monkeypatch)

    await main_module.prewarm_database_pool()

    assert fake_engine.statements == ["SELECT 1"]
    assert [event for event, _ in events] == ["api.prewarm_ok"]
    payload = events[0][1]["payload"]
    assert isinstance(payload["duration_ms"], (int, float))
    assert payload["duration_ms"] >= 0


async def test_prewarm_logs_failure_and_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-API-PREWARM.test_prewarm_logs_failure_and_does_not_raise
    # purpose: Verify a SELECT 1 failure emits api.prewarm_failed with a stable
    #   error_code and does not abort startup.
    # inputs: fake engine whose execute raises
    # returns: none
    # side_effects: none
    # emitted_logs: none (captured)
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-API-PREWARM.test_prewarm_logs_failure_and_does_not_raise
    fake_engine = _FakeEngine(error=RuntimeError("database unavailable"))
    monkeypatch.setattr(main_module, "engine", fake_engine)
    events = _capture_events(monkeypatch)

    await main_module.prewarm_database_pool()

    assert [event for event, _ in events] == ["api.prewarm_failed"]
    kwargs = events[0][1]
    assert kwargs["level"] == "error"
    assert kwargs["payload"]["error_code"] == "RuntimeError"


async def test_prewarm_timeout_is_fail_open(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-API-PREWARM.test_prewarm_timeout_is_fail_open
    # purpose: Verify a prewarm that exceeds the startup budget logs failure and
    #   does not propagate the timeout.
    # inputs: slow fake prewarm and a tiny timeout
    # returns: none
    # side_effects: none
    # emitted_logs: none (captured)
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-API-PREWARM.test_prewarm_timeout_is_fail_open
    async def slow_prewarm() -> None:
        await asyncio.sleep(0.05)

    monkeypatch.setattr(main_module, "_run_database_prewarm", slow_prewarm)
    monkeypatch.setattr(main_module, "PREWARM_TIMEOUT_SECONDS", 0.001)
    events = _capture_events(monkeypatch)

    await main_module.prewarm_database_pool()

    assert [event for event, _ in events] == ["api.prewarm_failed"]
    assert events[0][1]["payload"]["error_code"] == "TimeoutError"


async def test_lifespan_invokes_prewarm(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-API-PREWARM.test_lifespan_invokes_prewarm
    # purpose: Verify the FastAPI lifespan runs prewarm before yielding.
    # inputs: monkeypatched prewarm hook
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-API-PREWARM.test_lifespan_invokes_prewarm
    calls: list[bool] = []

    async def fake_prewarm() -> None:
        calls.append(True)

    monkeypatch.setattr(main_module, "prewarm_database_pool", fake_prewarm)

    async with main_module.lifespan(main_module.app):
        assert calls == [True]


def test_prewarm_events_are_registered() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-API-PREWARM.test_prewarm_events_are_registered
    # purpose: Verify the exact canonical event names are part of the closed registry.
    # inputs: LogEventName
    # returns: none
    # side_effects: none
    # emitted_logs: none
    # error_behavior: raises AssertionError on failure
    # END_FUNCTION_CONTRACT: F-M-TEST-API-PREWARM.test_prewarm_events_are_registered
    registered = set(get_args(LogEventName))
    assert {"api.prewarm_ok", "api.prewarm_failed"} <= registered
