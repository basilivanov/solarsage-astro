# ############################################################################
# AI_HEADER: MODULE_JOBS_DAY_PREGEN — nightly pre-generation of tomorrow's day payload.
# ROLE: Pre-computes /api/day payloads for active users and emits the legacy
#       pregen lifecycle through the canonical structured logging API.
# ############################################################################

# START_MODULE_CONTRACT: M-JOBS-DAY-PREGEN
# purpose: For every recently active user with a complete natal profile, build
#   tomorrow's TodayPayload via the canonical TodayService path (same cache
#   identity, same flags as live requests).
# owns:
#   - apps/api/app/jobs/day_pregen.py
# inputs: env DATABASE_URL etc.; --days-ahead (default 1), --active-days (14),
#   --concurrency (3), --limit (optional debug cap), --tg-id (debug single user).
# outputs: exit 0 on batch completion (per-user failures logged and skipped),
#   exit 1 on unhandled error.
# dependencies:
#   - M-DB-SESSION, M-TODAY-SERVICE, M-ACCESS-SERVICE, sidecar, LLM providers.
#   - M-OBSERVABILITY-LOGGING, M-LOG-IDENTITY.
# side_effects: sidecar/LLM calls; writes today_payloads_cache rows via the
#   canonical service; structured lifecycle logs.
# emitted_logs: day.pregen_started, day.pregen_user_finished,
#   day.pregen_completed.
# invariants:
#   - Payloads come ONLY from TodayService.get_today_payload (no hand-built cache).
#   - Already-cached user/date pairs are cheap no-ops.
#   - Per-user failure never aborts the batch.
# failure_policy: per-user exception is logged with type-only error_type and
#   swallowed; batch completes.
# END_MODULE_CONTRACT: M-JOBS-DAY-PREGEN

# START_MODULE_MAP: M-JOBS-DAY-PREGEN
# public_entrypoints:
#   - main
#   - pregen_for_users
# semantic_blocks:
#   - PREGEN_JOB: select active users and pre-generate their next day payloads
# owned_tests:
#   - apps/api/tests/test_day_pregen_job.py
# END_MODULE_MAP: M-JOBS-DAY-PREGEN

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from time import monotonic
from uuid import uuid4

from sqlalchemy import select

from app.core.log_identity import hash_user_id
from app.core.logging import bind_log_context, log_event
from app.db.models import Session, User, UserProfile
from app.db.session import SessionLocal
from app.services.access_service import AccessService
from app.services.today_service import TodayService


async def _select_active_users(db, active_days: int, limit: int | None) -> list[tuple[User, UserProfile]]:
    """Users with a session issued within active_days and a complete birth identity."""
    since = datetime.now(timezone.utc) - timedelta(days=active_days)
    stmt = (
        select(User, UserProfile)
        .join(UserProfile, UserProfile.user_id == User.id)
        .join(Session, Session.user_id == User.id)
        .where(Session.issued_at >= since)
        .where(UserProfile.birthday.is_not(None))
        .where(UserProfile.birth_tz.is_not(None))
        .where(UserProfile.birth_lat.is_not(None))
        .where(UserProfile.birth_lon.is_not(None))
        .group_by(User.id, UserProfile.user_id)
    )
    if limit:
        stmt = stmt.limit(limit)
    return list((await db.execute(stmt)).all())


# START_BLOCK: PREGEN_JOB
async def pregen_for_users(
    db,
    *,
    days_ahead: int,
    active_days: int,
    concurrency: int,
    limit: int | None,
    tg_id: int | None,
) -> tuple[int, int, int]:
    # START_FUNCTION_CONTRACT: F-M-JOBS-DAY-PREGEN.pregen_for_users
    # purpose: Pre-generate next-day payloads for active users via the canonical service.
    # inputs: db; days_ahead, active_days, concurrency, limit, tg_id filters.
    # returns: (ok, skipped, failed) counts.
    # side_effects: TodayService calls (sidecar/LLM), cache writes, lifecycle logs.
    # emitted_logs: day.pregen_started, day.pregen_user_finished, day.pregen_completed.
    # error_behavior: per-user failure counted, type-only logged, and swallowed.
    # END_FUNCTION_CONTRACT: F-M-JOBS-DAY-PREGEN.pregen_for_users
    bind_log_context(
        correlation_id=f"day-pregen-{uuid4().hex[:12]}",
        slice="W-P0-G",
        module="M-JOBS-DAY-PREGEN",
        block="PREGEN_JOB",
    )

    if tg_id:
        rows = list((await db.execute(
            select(User, UserProfile).join(UserProfile, UserProfile.user_id == User.id).where(User.tg_user_id == tg_id)
        )).all())
    else:
        rows = await _select_active_users(db, active_days, limit)

    log_event(
        "day.pregen_started",
        payload={
            "users_total": len(rows),
            "days_ahead": days_ahead,
            "concurrency": concurrency,
        },
    )

    sem = asyncio.Semaphore(concurrency)
    counts = {"ok": 0, "skipped": 0, "failed": 0}

    async def one(user: User, profile: UserProfile) -> None:
        tz = profile.current_tz or profile.birth_tz or "UTC"
        try:
            from zoneinfo import ZoneInfo
            today_user = datetime.now(ZoneInfo(tz)).date()
        except Exception:  # noqa: BLE001
            today_user = datetime.now(timezone.utc).date()
        target = today_user + timedelta(days=days_ahead)

        async with sem:
            async with SessionLocal() as udb:
                operation_started = monotonic()
                payload_started: float | None = None
                try:
                    bind_log_context(user_id_hash=hash_user_id(user.id))
                    access_state = await AccessService(udb).can_access_day(user.id, target)
                    payload_started = monotonic()
                    await TodayService(udb).get_today_payload(
                        user_id=user.id,
                        target_date=target,
                        access_state=access_state,
                        selection_context=None,
                    )
                    elapsed = monotonic() - payload_started
                    duration_ms = max(0.0, elapsed * 1000)
                    outcome = "completed" if elapsed > 1.0 else "fast_path"
                    counts["ok" if outcome == "completed" else "skipped"] += 1
                    log_event(
                        "day.pregen_user_finished",
                        payload={
                            "outcome": outcome,
                            "duration_ms": duration_ms,
                        },
                    )
                except Exception as exc:  # noqa: BLE001
                    counts["failed"] += 1
                    duration_started = payload_started if payload_started is not None else operation_started
                    duration_ms = max(0.0, (monotonic() - duration_started) * 1000)
                    log_event(
                        "day.pregen_user_finished",
                        level="error",
                        payload={
                            "outcome": "failed",
                            "duration_ms": duration_ms,
                            "error_type": type(exc).__name__,
                        },
                    )

    await asyncio.gather(*(one(u, p) for u, p in rows))
    log_event(
        "day.pregen_completed",
        payload={
            "completed": counts["ok"],
            "fast_path": counts["skipped"],
            "failed": counts["failed"],
        },
    )
    return counts["ok"], counts["skipped"], counts["failed"]


def main() -> None:
    # START_FUNCTION_CONTRACT: F-M-JOBS-DAY-PREGEN.main
    # purpose: Run the standalone nightly day pre-generation job.
    # inputs: process arguments for days_ahead, active_days, concurrency, limit, tg_id.
    # returns: None; process success/failure remains the existing CLI contract.
    # side_effects: canonical day pre-generation calls and lifecycle logs.
    # emitted_logs: day.pregen_started, day.pregen_user_finished, day.pregen_completed.
    # error_behavior: propagates unhandled batch/CLI errors as before.
    # END_FUNCTION_CONTRACT: F-M-JOBS-DAY-PREGEN.main
    parser = argparse.ArgumentParser(description="Nightly day payload pre-generation")
    parser.add_argument("--days-ahead", type=int, default=1)
    parser.add_argument("--active-days", type=int, default=14)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--tg-id", type=int, default=None)
    args = parser.parse_args()

    async def run() -> None:
        async with SessionLocal() as db:
            await pregen_for_users(
                db,
                days_ahead=args.days_ahead,
                active_days=args.active_days,
                concurrency=args.concurrency,
                limit=args.limit,
                tg_id=args.tg_id,
            )

    asyncio.run(run())
# END_BLOCK: PREGEN_JOB


if __name__ == "__main__":
    main()
