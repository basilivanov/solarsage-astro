# ############################################################################
# AI_HEADER: TEST_JOBS_DAY_PREGEN — thin CLI shell contract tests.
# ROLE: Proves the module entrypoint only owns session setup, delegation, and
#       invalid-configuration exit mapping.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-JOBS-DAY-PREGEN
# purpose: Verify that the timer entrypoint delegates the complete P5 workflow
#   to TodayPregenService and preserves a non-zero invalid-settings exit.
# owns:
#   - apps/api/tests/test_day_pregen_job.py
# inputs: fake async session context, fake service, and controlled asyncio.run.
# outputs: assertions over delegation and CLI exit behavior.
# dependencies: app.jobs.day_pregen, pytest.
# side_effects: none; all database/service boundaries are replaced.
# emitted_logs: none.
# invariants: the job module contains no workflow implementation or legacy
#   payload-service import.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TEST-JOBS-DAY-PREGEN

# START_MODULE_MAP: M-TEST-JOBS-DAY-PREGEN
# public_entrypoints: []
# semantic_blocks:
#   - CLI_SHELL: run_day_pregen and main delegation
# owned_tests: self
# END_MODULE_MAP: M-TEST-JOBS-DAY-PREGEN

from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from app.jobs import day_pregen
from app.services.today_pregen_service import PregenConfigurationError


# START_BLOCK: CLI_SHELL
@pytest.mark.asyncio
async def test_run_day_pregen_opens_session_and_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    database = object()
    factory_calls: list[str] = []
    service_calls: list[tuple[object, object]] = []
    summary = SimpleNamespace(outcome="completed")

    class SessionContext:
        async def __aenter__(self):
            factory_calls.append("enter")
            return database

        async def __aexit__(self, *_args):
            factory_calls.append("exit")
            return False

    def session_factory():
        factory_calls.append("factory")
        return SessionContext()

    class FakeService:
        def __init__(self, db, *, session_factory):
            service_calls.append((db, session_factory))

        async def run(self):
            return summary

    monkeypatch.setattr(day_pregen, "SessionLocal", session_factory)
    monkeypatch.setattr(day_pregen, "TodayPregenService", FakeService)

    result = await day_pregen.run_day_pregen()

    assert result is summary
    assert factory_calls == ["factory", "enter", "exit"]
    assert service_calls == [(database, session_factory)]


def test_main_maps_invalid_settings_to_exit_one(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(awaitable):
        awaitable.close()
        raise PregenConfigurationError("day_pregen_concurrency")

    monkeypatch.setattr(day_pregen.asyncio, "run", fail)

    with pytest.raises(SystemExit) as exc_info:
        day_pregen.main()

    assert exc_info.value.code == 1


def test_job_source_has_no_legacy_payload_service_import() -> None:
    source = inspect.getsource(day_pregen)
    assert "from app.services.today_service" not in source
    assert "TodayService(" not in source


# END_BLOCK: CLI_SHELL
