# ############################################################################
# AI_HEADER: MODULE_JOBS_BILLING_REBILL — operator-runnable recurrent rebill job.
# ROLE: Runs BillingService.rebill_due_subscriptions once through the
#       canonical app session; hard-gated by YOOKASSA_RECURRENT_ENABLED.
#       Lives INSIDE the installed app package so the canonical invocation is
#       `python -m app.jobs.billing_rebill` in the API container (one-shot
#       compose profile), never a mutable host checkout.
# DEPENDENCIES: app package, DATABASE_URL env
# ############################################################################

# START_MODULE_CONTRACT: M-JOBS-BILLING-REBILL
# purpose: Single-shot operator job for recurrent rebilling (cron-driven via
#   the canonical compose one-shot profile; no Prefect/new harness).
# owns:
#   - apps/api/app/jobs/billing_rebill.py
# inputs: DATABASE_URL (+ standard app env), YOOKASSA_RECURRENT_ENABLED.
# outputs: exit 0 with the attempts count as a structured log event; non-zero
#   on errors.
# dependencies: app.db.session.SessionLocal, BillingService,
#   app.core.logging (log_event, bind_log_context).
# side_effects: provider charges ONLY when YOOKASSA_RECURRENT_ENABLED=true;
#   otherwise exits 0 doing nothing (structured skip event).
# emitted_logs: billing.rebill_skipped, billing.rebill_completed, system.error
#   (via this module); billing.rebill_started (via service).
# invariants:
#   - Kill-switch first: disabled recurrent means zero charges, always.
#   - No scheduler of its own — the operator's cron/timer invokes it through
#     the canonical compose one-shot profile (runbook §2.2).
#   - No raw print(): every operator-visible line is a canonical structured
#     log event; exceptions are redacted to their type name only.
# failure_policy: exit 1 on unexpected failure (safe to re-run next cycle).
# END_MODULE_CONTRACT: M-JOBS-BILLING-REBILL

# START_MODULE_MAP: M-JOBS-BILLING-REBILL
# public_entrypoints:
#   - main
# semantic_blocks:
#   - REBILL_JOB: kill-switch gate, service run, structured outcome events
# owned_tests:
#   - apps/api/tests/test_billing_rebill_job.py
# END_MODULE_MAP: M-JOBS-BILLING-REBILL

from __future__ import annotations

import asyncio
from uuid import uuid4


# START_BLOCK: REBILL_JOB
async def _run() -> int:
    from app.core.config import settings
    from app.core.logging import log_event
    from app.db.session import SessionLocal
    from app.services.billing_service import BillingService

    if not settings.yookassa_recurrent_enabled:
        # Kill-switch first: the disabled path is structurally observable,
        # never a raw stdout line.
        log_event(
            "billing.rebill_skipped",
            msg="rebill skipped: YOOKASSA_RECURRENT_ENABLED=false",
        )
        return 0

    async with SessionLocal() as session:
        attempts = await BillingService(session).rebill_due_subscriptions()
    log_event(
        "billing.rebill_completed",
        msg="rebill job completed",
        payload={"attempts": attempts},
    )
    return 0


def main() -> int:
    # START_FUNCTION_CONTRACT: F-M-JOBS-BILLING-REBILL.main
    # purpose: Job entrypoint — binds the canonical log context and runs the
    #   rebill pass; the exit code is the operator contract.
    # inputs: process env (DATABASE_URL, YOOKASSA_RECURRENT_ENABLED).
    # returns: 0 on success/skip, 1 on unexpected failure.
    # side_effects: structured log events; provider charges when enabled.
    # emitted_logs: billing.rebill_skipped, billing.rebill_completed, system.error.
    # error_behavior: unexpected exceptions are logged redacted (type name
    #   only) as system.error and mapped to exit 1; never re-raised raw.
    # END_FUNCTION_CONTRACT: F-M-JOBS-BILLING-REBILL.main
    from app.core.logging import bind_log_context, log_event

    bind_log_context(
        correlation_id=f"rebill-{uuid4().hex[:12]}",
        slice="W-6.1",
        module="M-JOBS-BILLING-REBILL",
        block="REBILL_JOB",
    )
    try:
        return asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001 — job boundary, exit code is the contract
        log_event(
            "system.error",
            level="error",
            msg="rebill job failed",
            error={"kind": type(exc).__name__},
        )
        return 1
# END_BLOCK: REBILL_JOB


if __name__ == "__main__":
    raise SystemExit(main())
