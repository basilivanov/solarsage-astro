# ############################################################################
# AI_HEADER: MODULE_TESTS_DAY_PREGEN_JOB — structured logging contract tests.
# ROLE: Proves legacy day pregen keeps its tuple/cache behavior while emitting
#       privacy-safe lifecycle events through the canonical logging API.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-JOBS-DAY-PREGEN
# purpose: Exercise the legacy day_pregen batch around completed, fast-path,
#   and failed user/date operations.
# owns:
#   - apps/api/tests/test_day_pregen_job.py
# inputs: monkeypatched selection, services, clock, and logging functions.
# outputs: Assertions over return tuple, event multiplicity, payloads, and
#   privacy-safe logging context.
# dependencies:
#   - app.jobs.day_pregen
#   - pytest
# side_effects: none (all database, service, clock, and logging boundaries are
#   replaced with test doubles).
# emitted_logs: none (captures the job's canonical log_event calls).
# invariants:
#   - each case emits one start, one user outcome, and one batch summary;
#   - raw user identifiers and exception text never appear in captured events.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TEST-JOBS-DAY-PREGEN

# START_MODULE_MAP: M-TEST-JOBS-DAY-PREGEN
# public_entrypoints: []
# semantic_blocks:
#   - PREGEN_LOGGING_TESTS: completed, fast-path, and failed lifecycle cases
# owned_tests: self
# END_MODULE_MAP: M-TEST-JOBS-DAY-PREGEN

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.jobs import day_pregen

RAW_USER_ID = "raw-user-id-42"
RAW_TG_ID = 987654321
HASHED_USER_ID = "h1_" + "a" * 24
EXCEPTION_TEXT = "database secret connection details"


# START_BLOCK: PREGEN_LOGGING_TESTS
def _configure_case(monkeypatch: pytest.MonkeyPatch, *, duration_seconds: float, fail: bool):
    user = SimpleNamespace(id=RAW_USER_ID, tg_user_id=RAW_TG_ID)
    profile = SimpleNamespace(current_tz="UTC", birth_tz="UTC")
    events: list[tuple[str, dict[str, Any]]] = []
    contexts: list[dict[str, str]] = []
    service_calls: list[dict[str, Any]] = []

    async def select_active_users(_db, _active_days, _limit):
        return [(user, profile)]

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

    class FakeAccessService:
        def __init__(self, _db):
            pass

        async def can_access_day(self, user_id, target):
            service_calls.append({"kind": "access", "user_id": user_id, "target": target})
            return "full"

    class FakeTodayService:
        def __init__(self, _db):
            pass

        async def get_today_payload(self, **kwargs):
            service_calls.append({"kind": "today", **kwargs})
            if fail:
                raise RuntimeError(EXCEPTION_TEXT)

    clock = iter((100.0, 100.0, 100.0 + duration_seconds))

    monkeypatch.setattr(day_pregen, "_select_active_users", select_active_users)
    monkeypatch.setattr(day_pregen, "SessionLocal", lambda: FakeSession())
    monkeypatch.setattr(day_pregen, "AccessService", FakeAccessService)
    monkeypatch.setattr(day_pregen, "TodayService", FakeTodayService)
    monkeypatch.setattr(day_pregen, "monotonic", lambda: next(clock))
    monkeypatch.setattr(day_pregen, "hash_user_id", lambda value: HASHED_USER_ID)
    monkeypatch.setattr(day_pregen, "bind_log_context", lambda **kwargs: contexts.append(kwargs))
    monkeypatch.setattr(
        day_pregen,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    return events, contexts, service_calls


async def _run_case(monkeypatch: pytest.MonkeyPatch, *, duration_seconds: float, fail: bool):
    events, contexts, service_calls = _configure_case(
        monkeypatch,
        duration_seconds=duration_seconds,
        fail=fail,
    )
    result = await day_pregen.pregen_for_users(
        object(),
        days_ahead=1,
        active_days=14,
        concurrency=3,
        limit=None,
        tg_id=None,
    )
    return result, events, contexts, service_calls


def _assert_common_contract(
    result: tuple[int, int, int],
    events: list[tuple[str, dict[str, Any]]],
    contexts: list[dict[str, str]],
    service_calls: list[dict[str, Any]],
) -> None:
    assert [event for event, _kwargs in events] == [
        "day.pregen_started",
        "day.pregen_user_finished",
        "day.pregen_completed",
    ]
    assert events[0][1]["payload"] == {
        "users_total": 1,
        "days_ahead": 1,
        "concurrency": 3,
    }
    assert events[2][1]["payload"] == {
        "completed": result[0],
        "fast_path": result[1],
        "failed": result[2],
    }
    assert contexts[0]["slice"] == "W-P0-G"
    assert contexts[0]["module"] == "M-JOBS-DAY-PREGEN"
    assert contexts[0]["block"] == "PREGEN_JOB"
    assert contexts[0]["correlation_id"]
    assert contexts[1] == {"user_id_hash": HASHED_USER_ID}
    assert service_calls[0]["kind"] == "access"
    assert service_calls[0]["user_id"] == RAW_USER_ID
    assert service_calls[1]["kind"] == "today"
    assert service_calls[1]["user_id"] == RAW_USER_ID
    assert service_calls[1]["selection_context"] is None

    serialized = json.dumps({"events": events, "contexts": contexts}, default=str)
    assert RAW_USER_ID not in serialized
    assert str(RAW_TG_ID) not in serialized
    assert EXCEPTION_TEXT not in serialized


@pytest.mark.asyncio
async def test_completed_path_emits_slow_outcome_and_tuple(monkeypatch: pytest.MonkeyPatch) -> None:
    result, events, contexts, service_calls = await _run_case(
        monkeypatch,
        duration_seconds=1.25,
        fail=False,
    )

    assert result == (1, 0, 0)
    _assert_common_contract(result, events, contexts, service_calls)
    assert events[1][1]["payload"] == {
        "outcome": "completed",
        "duration_ms": 1250.0,
    }


@pytest.mark.asyncio
async def test_fast_path_emits_legacy_fast_outcome_and_tuple(monkeypatch: pytest.MonkeyPatch) -> None:
    result, events, contexts, service_calls = await _run_case(
        monkeypatch,
        duration_seconds=0.25,
        fail=False,
    )

    assert result == (0, 1, 0)
    _assert_common_contract(result, events, contexts, service_calls)
    assert events[1][1]["payload"] == {
        "outcome": "fast_path",
        "duration_ms": 250.0,
    }


@pytest.mark.asyncio
async def test_exactly_one_second_preserves_legacy_fast_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    result, events, contexts, service_calls = await _run_case(
        monkeypatch,
        duration_seconds=1.0,
        fail=False,
    )

    assert result == (0, 1, 0)
    _assert_common_contract(result, events, contexts, service_calls)
    assert events[1][1]["payload"] == {
        "outcome": "fast_path",
        "duration_ms": 1000.0,
    }


@pytest.mark.asyncio
async def test_failed_path_emits_redacted_failure_and_tuple(monkeypatch: pytest.MonkeyPatch) -> None:
    result, events, contexts, service_calls = await _run_case(
        monkeypatch,
        duration_seconds=0.5,
        fail=True,
    )

    assert result == (0, 0, 1)
    _assert_common_contract(result, events, contexts, service_calls)
    assert events[1][1]["level"] == "error"
    assert events[1][1]["payload"] == {
        "outcome": "failed",
        "duration_ms": 500.0,
        "error_type": "RuntimeError",
    }


# END_BLOCK: PREGEN_LOGGING_TESTS
