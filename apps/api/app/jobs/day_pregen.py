# ############################################################################
# AI_HEADER: MODULE_JOBS_DAY_PREGEN — nightly Today convergence CLI entrypoint.
# ROLE: Opens the canonical database session and delegates one bounded P5 run
#       to TodayPregenService.
# ############################################################################

# START_MODULE_CONTRACT: M-JOBS-DAY-PREGEN
# purpose: Keep the existing `python -m app.jobs.day_pregen` entrypoint as a
#   thin one-shot shell for the new Today convergence pre-generation service.
# owns:
#   - apps/api/app/jobs/day_pregen.py
# inputs: process environment for Settings and the canonical SessionLocal.
# outputs: exit 0 after a completed/capped run; exit 1 for invalid settings or
#   an unhandled database/cohort failure.
# dependencies: M-DB-SESSION, M-CONFIG, M-TODAY-PREGEN-SERVICE.
# side_effects: delegates snapshot and leased narrative writes; never writes
#   impressions or legacy payload-cache rows itself.
# emitted_logs: delegated day.pregen_started, day.pregen_user_finished,
#   day.pregen_completed.
# invariants: no calculation, access, LLM, or persistence orchestration lives in
#   this CLI module; no legacy payload-service import is allowed.
# failure_policy: PregenConfigurationError is converted to process exit 1;
#   other exceptions propagate with the existing CLI behavior.
# END_MODULE_CONTRACT: M-JOBS-DAY-PREGEN

# START_MODULE_MAP: M-JOBS-DAY-PREGEN
# public_entrypoints:
#   - run_day_pregen
#   - main
# semantic_blocks:
#   - CLI_SHELL: canonical session lifecycle and service delegation
# owned_tests:
#   - apps/api/tests/test_day_pregen_job.py
# END_MODULE_MAP: M-JOBS-DAY-PREGEN

from __future__ import annotations

import asyncio

from app.db.session import SessionLocal
from app.services.today_pregen_service import (
    PregenConfigurationError,
    PregenRunSummary,
    TodayPregenService,
)


# START_BLOCK: CLI_SHELL
async def run_day_pregen() -> PregenRunSummary:
    # START_FUNCTION_CONTRACT: F-M-JOBS-DAY-PREGEN.run_day_pregen
    # purpose: Run one service-owned pre-generation pass in the canonical DB scope.
    # inputs: process configuration and SessionLocal; no CLI filters.
    # returns: typed PregenRunSummary after all bounded work completes.
    # side_effects: opens/closes one cohort session and delegates user sessions,
    #   snapshot publication, narrative leases, and provider calls.
    # emitted_logs: delegated day.pregen_started, day.pregen_user_finished,
    #   day.pregen_completed.
    # error_behavior: invalid settings raises PregenConfigurationError; all other
    #   service errors propagate to the process boundary.
    # END_FUNCTION_CONTRACT: F-M-JOBS-DAY-PREGEN.run_day_pregen
    async with SessionLocal() as db:
        return await TodayPregenService(
            db,
            session_factory=SessionLocal,
        ).run()


def main() -> None:
    # START_FUNCTION_CONTRACT: F-M-JOBS-DAY-PREGEN.main
    # purpose: Preserve the standalone module entrypoint for the dev timer.
    # inputs: none beyond process environment.
    # returns: None on successful one-shot completion.
    # side_effects: runs the async CLI shell and may terminate with exit 1.
    # emitted_logs: delegated lifecycle events.
    # error_behavior: invalid settings are explicitly mapped to exit 1; other
    #   failures propagate and retain a non-zero process exit.
    # END_FUNCTION_CONTRACT: F-M-JOBS-DAY-PREGEN.main
    try:
        asyncio.run(run_day_pregen())
    except PregenConfigurationError as exc:
        raise SystemExit(1) from exc


# END_BLOCK: CLI_SHELL


if __name__ == "__main__":
    main()
