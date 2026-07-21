#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: SCRIPT_BILLING_REBILL — operator-runnable recurrent rebill job.
# ROLE: Runs BillingService.rebill_due_subscriptions once through the
#       canonical app session; hard-gated by YOOKASSA_RECURRENT_ENABLED.
# DEPENDENCIES: apps/api app package, DATABASE_URL env
# ############################################################################

# START_MODULE_CONTRACT: M-SCRIPT-BILLING-REBILL
# purpose: Single-shot operator job for recurrent rebilling (cron/systemd
#   timer equivalent, no Prefect/new harness).
# owns:
#   - scripts/billing_rebill.py
# inputs: DATABASE_URL (+ standard app env), YOOKASSA_RECURRENT_ENABLED.
# outputs: exit 0 with the attempts count on stdout; non-zero on errors.
# dependencies: app.db.session.SessionLocal, BillingService.
# side_effects: provider charges ONLY when YOOKASSA_RECURRENT_ENABLED=true;
#   otherwise exits 0 doing nothing.
# emitted_logs: billing.rebill_started / billing.rebill_skipped (via service).
# invariants:
#   - Kill-switch first: disabled recurrent means zero charges, always.
#   - No scheduler of its own — the operator's cron/timer invokes it.
# failure_policy: exit 1 on unexpected failure (safe to re-run next cycle).
# END_MODULE_CONTRACT: M-SCRIPT-BILLING-REBILL

from __future__ import annotations

import asyncio
import sys


async def _run() -> int:
    from app.core.config import settings
    from app.db.session import SessionLocal
    from app.services.billing_service import BillingService

    if not settings.yookassa_recurrent_enabled:
        print("rebill skipped: YOOKASSA_RECURRENT_ENABLED=false")
        return 0

    async with SessionLocal() as session:
        attempts = await BillingService(session).rebill_due_subscriptions()
    print(f"rebill attempts: {attempts}")
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001 — job boundary, exit code is the contract
        print(f"rebill failed: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
