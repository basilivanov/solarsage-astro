# ############################################################################
# AI_HEADER: MODULE_JOBS_SYNASTRY_RECONCILE
# ROLE: Reconcile job for stale/interrupted synastry report calculations.
# DEPENDENCIES: sqlalchemy, app.db.models, app.services.synastry_service
# GRACE_ANCHORS: [RECONCILE_JOB]
# ############################################################################

# START_MODULE_CONTRACT: M-JOBS-SYNASTRY-RECONCILE
# purpose: Pick up synastry reports stuck in pending/calculating/narrative_generating states and run pipeline to termination.
# owns:
#   - apps/api/app/jobs/synastry_reconcile.py
# inputs: DATABASE_URL env, optional limit and cutoff_minutes.
# outputs: Exit 0 on success/clean completion, 1 on unhandled errors.
# dependencies:
#   - M-DB-SESSION
#   - M-SYNASTRY-SERVICE
#   - M-OBSERVABILITY-LOGGING
# side_effects:
#   - executes report pipeline, updates DB report states, refunds credits if failed
# emitted_logs: llm.response_validated, system.error
# invariants:
#   - Only reads stale reports and delegates execution to SynastryService.run_report_pipeline
#   - No open DB transaction during external calls (managed by SynastryService)
# failure_policy: Exception on individual report is logged and swallowed so batch completes
# END_MODULE_CONTRACT: M-JOBS-SYNASTRY-RECONCILE

# START_MODULE_MAP: M-JOBS-SYNASTRY-RECONCILE
# public_entrypoints:
#   - main
#   - reconcile_stale_reports
# semantic_blocks:
#   - RECONCILE_JOB: Find stale synastry reports and run pipeline to completion
# owned_tests:
#   - apps/api/tests/test_synastry_reconcile.py
# END_MODULE_MAP: M-JOBS-SYNASTRY-RECONCILE

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_identity import hash_log_identifier
from app.core.logging import bind_log_context, log_event
from app.db.models import SynastryReport
from app.db.session import SessionLocal
from app.services.synastry_service import SynastryService


# START_BLOCK: RECONCILE_JOB
async def reconcile_stale_reports(
    db: AsyncSession,
    limit: int = 20,
    cutoff_minutes: int = 5,
) -> int:
    """Find synastry reports stuck in non-final states and execute pipeline."""
    # START_FUNCTION_CONTRACT: F-M-JOBS-SYNASTRY-RECONCILE.reconcile_stale_reports
    # purpose: Query stale pending/calculating/narrative_generating reports and process each via SynastryService.
    # inputs: db (AsyncSession), limit (int=20), cutoff_minutes (int=5)
    # returns: processed count (int)
    # side_effects: updates report states in DB
    # emitted_logs: llm.response_validated, system.error
    # error_behavior: logs error per report, continues processing remaining batch
    # END_FUNCTION_CONTRACT: F-M-JOBS-SYNASTRY-RECONCILE.reconcile_stale_reports
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=cutoff_minutes)

    stmt = (
        select(SynastryReport.id)
        .where(
            SynastryReport.invalidated_at.is_(None),
            or_(
                (SynastryReport.state == "pending") & (SynastryReport.created_at < cutoff),
                (SynastryReport.state.in_(["calculating", "narrative_generating"]))
                & (SynastryReport.updated_at < cutoff),
            ),
        )
        .order_by(SynastryReport.updated_at.asc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    stale_report_ids = list(result.scalars().all())

    if not stale_report_ids:
        return 0

    processed_count = 0

    for report_id in stale_report_ids:
        report_id_hash = hash_log_identifier("report", report_id)
        try:
            service = SynastryService(db)
            report = await service.run_report_pipeline(report_id)
            processed_count += 1

            if report.state == "ready":
                log_event(
                    "llm.response_validated",
                    msg="Synastry reconcile report completed successfully",
                    payload={"report_id_hash": report_id_hash},
                )
            else:
                log_event(
                    "system.error",
                    level="warning",
                    msg=f"Synastry reconcile report failed: {report.error_code}",
                    payload={"report_id_hash": report_id_hash, "error_code": report.error_code},
                )
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            log_event(
                "system.error",
                level="error",
                msg=f"Synastry reconcile task error: {type(exc).__name__}",
                payload={"report_id_hash": report_id_hash, "error_type": type(exc).__name__},
            )

    return processed_count


async def _run() -> int:
    async with SessionLocal() as db:
        await reconcile_stale_reports(db)
    return 0


def main() -> int:
    # START_FUNCTION_CONTRACT: F-M-JOBS-SYNASTRY-RECONCILE.main
    # purpose: CLI job entrypoint for synastry reconcile.
    # inputs: DATABASE_URL env
    # returns: 0 on success, 1 on unexpected failure
    # side_effects: runs reconcile job pass
    # emitted_logs: system.error
    # failure_policy: logs error and returns 1
    # END_FUNCTION_CONTRACT: F-M-JOBS-SYNASTRY-RECONCILE.main
    bind_log_context(
        correlation_id=f"synastry-reconcile-{uuid4().hex[:12]}",
        slice="W-SYNASTRY-MVP",
        module="M-JOBS-SYNASTRY-RECONCILE",
        block="RECONCILE_JOB",
    )
    try:
        return asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        log_event(
            "system.error",
            level="error",
            msg="Synastry reconcile job failed",
            payload={"error_kind": type(exc).__name__},
        )
        return 1
# END_BLOCK: RECONCILE_JOB


if __name__ == "__main__":
    raise SystemExit(main())
