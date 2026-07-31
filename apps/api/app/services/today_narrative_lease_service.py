# ############################################################################
# AI_HEADER: MODULE_TODAY-NARRATIVE-LEASE-SERVICE — PostgreSQL narrative single-flight lease.
# ROLE: Owns the persistence boundary that gives one worker a claim for one
#       published snapshot/prompt version and prevents stale completion writes.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-NARRATIVE-LEASE-SERVICE
# purpose: Persist one versioned Today narrative lease with atomic PostgreSQL
#   acquire/recovery/retry transitions and compare-and-set completion.
# owns:
#   - apps/api/app/services/today_narrative_lease_service.py
# inputs: AsyncSession, optional aware-UTC clock, published snapshot UUID, prompt
#   version, aware UTC time, lease duration, immutable claim, and already
#   validated JSON object/error code.
# outputs: Immutable claim/skip/completion dataclasses or typed boundary errors.
# dependencies: PostgreSQL SQLAlchemy insert/select/update, TodaySnapshot,
#   TodaySnapshotNarrative, structured logging registry.
# side_effects: Reads/inserts/updates/commits narrative rows and emits sanitized
#   lease lifecycle events; never calls a provider or changes public Today data.
# emitted_logs: day.narrative_lease_acquired, day.narrative_lease_recovered,
#   day.narrative_lease_skipped, day.narrative_lease_completed,
#   day.narrative_lease_failed, system.error.
# invariants: one row per snapshot/prompt version; attempt starts at one and
#   increments once per claim; ready has object content; unavailable has null
#   content; stale claims cannot mutate a newer row; logs contain no UUID/content.
# failure_policy: invalid inputs fail before SQL; expected SQLAlchemy failures
#   rollback and become stable persistence errors; unexpected errors propagate;
#   stale completion returns a non-error stale outcome.
# END_MODULE_CONTRACT: M-TODAY-NARRATIVE-LEASE-SERVICE

# START_MODULE_MAP: M-TODAY-NARRATIVE-LEASE-SERVICE
# public_entrypoints:
#   - NarrativeLeaseClaim
#   - NarrativeLeaseSkip
#   - NarrativeLeaseCompletion
#   - TodayNarrativeLeaseError
#   - TodayNarrativeLeasePersistenceError
#   - TodayNarrativeLeaseService.acquire
#   - TodayNarrativeLeaseService.complete_ready
#   - TodayNarrativeLeaseService.complete_unavailable
#   - TodayNarrativeLeaseService.load
# semantic_blocks:
#   - INPUT_BOUNDARY: validate immutable service inputs before SQL.
#   - ACQUIRE: published-snapshot proof, conflict-safe insert, and locked transitions.
#   - COMPLETION_CAS: claim-identity compare-and-set terminal transitions.
#   - LOAD: versioned narrative lookup.
#   - LOGGING: non-blocking sanitized lifecycle events.
# owned_tests:
#   - apps/api/tests/test_today_narrative_lease_service.py
#   - apps/api/tests/test_today_narrative_lease_postgres.py
# END_MODULE_MAP: M-TODAY-NARRATIVE-LEASE-SERVICE

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Literal
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log_block, log_event
from app.db.models import TodaySnapshot, TodaySnapshotNarrative


LeaseAcquireOutcome = Literal["created", "retry", "recovered"]
LeaseSkipStatus = Literal["ready", "pending", "unavailable"]
LeaseSkipReason = Literal["ready", "in_flight", "cooldown", "exhausted"]

_ERROR_CODE_RE = re.compile(r"^[a-z0-9_.-]{1,64}$")
_MAX_LEASE_DURATION = timedelta(hours=1)


class TodayNarrativeLeaseError(ValueError):
    """Raised when a requested snapshot/prompt relation is not admissible."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class TodayNarrativeLeasePersistenceError(ValueError):
    """Raised when the persistence boundary cannot complete safely."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class NarrativeLeaseClaim:
    """The exact identity a worker must present to complete a lease."""

    narrative_id: UUID
    snapshot_id: UUID
    prompt_version: str
    attempt_count: int
    lease_until: datetime
    outcome: LeaseAcquireOutcome


@dataclass(frozen=True)
class NarrativeLeaseSkip:
    """A committed row that gives the caller no provider-call permission."""

    narrative_id: UUID
    snapshot_id: UUID
    prompt_version: str
    status: LeaseSkipStatus
    reason: LeaseSkipReason
    retry_at: datetime | None


@dataclass(frozen=True)
class NarrativeLeaseCompletion:
    """Whether a completion still owned the exact claim identity."""

    outcome: Literal["completed", "stale"]


def _log_event(
    event: str,
    *,
    block: str,
    payload: dict[str, object] | None = None,
    error: dict[str, str] | None = None,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE-LEASE-SERVICE._log_event
    # purpose: Emit one lease event without allowing observability to affect DB behavior.
    # inputs: canonical event, semantic block, and sanitized payload/error.
    # returns: None.
    # side_effects: Writes one structured log event when logging is available.
    # emitted_logs: the event passed by the caller.
    # error_behavior: Swallows logging failures so business flow remains intact.
    # END_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE-LEASE-SERVICE._log_event
    try:
        with log_block(
            slice="W-TODAY-CONVERGENCE-W3",
            module="M-TODAY-NARRATIVE-LEASE-SERVICE",
            block=block,
        ):
            log_event(
                event,
                level="error" if error is not None else "info",
                msg="today narrative lease boundary",
                payload=payload,
                error=error,
            )
    except Exception:
        pass


def _persistence_failure() -> TodayNarrativeLeasePersistenceError:
    return TodayNarrativeLeasePersistenceError("today_narrative_lease:persistence")


def _validate_uuid(value: UUID, name: str) -> UUID:
    if not isinstance(value, UUID):
        raise TypeError(f"{name} must be UUID")
    return value


def _validate_prompt_version(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 64:
        raise ValueError("prompt_version must be nonblank and at most 64 characters")
    return value


def _aware_utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise TypeError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _validate_acquire_inputs(
    snapshot_id: UUID,
    prompt_version: str,
    now: datetime,
    lease_duration: timedelta,
) -> tuple[UUID, str, datetime, timedelta]:
    _validate_uuid(snapshot_id, "snapshot_id")
    _validate_prompt_version(prompt_version)
    normalized_now = _aware_utc(now, "now")
    if not isinstance(lease_duration, timedelta) or lease_duration <= timedelta(0):
        raise ValueError("lease_duration must be positive")
    if lease_duration > _MAX_LEASE_DURATION:
        raise ValueError("lease_duration must be at most one hour")
    return snapshot_id, prompt_version, normalized_now, lease_duration


def _validate_json_object(content_json: dict) -> dict:
    if not isinstance(content_json, dict):
        raise TypeError("content_json must be a JSON object")
    copied = deepcopy(content_json)
    try:
        json.dumps(copied, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("content_json must be JSON serializable") from exc
    return copied


def _validate_error_code(error_code: str) -> str:
    if not isinstance(error_code, str) or _ERROR_CODE_RE.fullmatch(error_code) is None:
        raise ValueError("error_code must match [a-z0-9_.-]{1,64}")
    return error_code


def _stored_utc(value: datetime | None, name: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _valid_ready_content(row: TodaySnapshotNarrative) -> dict:
    if not isinstance(row.content_json, dict):
        raise TodayNarrativeLeasePersistenceError("today_narrative_lease:ready_content")
    return row.content_json


def _validate_claim(claim: NarrativeLeaseClaim) -> NarrativeLeaseClaim:
    if not isinstance(claim, NarrativeLeaseClaim):
        raise TypeError("claim must be NarrativeLeaseClaim")
    _validate_uuid(claim.narrative_id, "claim.narrative_id")
    _validate_uuid(claim.snapshot_id, "claim.snapshot_id")
    _validate_prompt_version(claim.prompt_version)
    if type(claim.attempt_count) is not int or claim.attempt_count < 1:
        raise ValueError("claim.attempt_count must be positive")
    if claim.outcome not in {"created", "retry", "recovered"}:
        raise ValueError("claim.outcome is invalid")
    _aware_utc(claim.lease_until, "claim.lease_until")
    return claim


def _claim_where(claim: NarrativeLeaseClaim):
    return (
        TodaySnapshotNarrative.id == claim.narrative_id,
        TodaySnapshotNarrative.snapshot_id == claim.snapshot_id,
        TodaySnapshotNarrative.prompt_version == claim.prompt_version,
        TodaySnapshotNarrative.status == "pending",
        TodaySnapshotNarrative.attempt_count == claim.attempt_count,
        TodaySnapshotNarrative.lease_until == claim.lease_until,
    )


class TodayNarrativeLeaseService:
    """PostgreSQL-only single-flight narrative lease boundary."""

    def __init__(self, db: AsyncSession, clock: Callable[[], datetime] | None = None):
        if clock is not None and not callable(clock):
            raise TypeError("clock must be callable")
        self.db = db
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    # START_BLOCK: ACQUIRE
    async def acquire(
        self,
        snapshot_id: UUID,
        prompt_version: str,
        now: datetime,
        lease_duration: timedelta,
    ) -> NarrativeLeaseClaim | NarrativeLeaseSkip:
        # START_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE-LEASE-SERVICE.acquire
        # purpose: Prove a published snapshot and atomically create, recover,
        #   retry, or skip one narrative lease row.
        # inputs: UUID snapshot_id, nonblank prompt_version, aware UTC now, and
        #   positive duration bounded to one hour.
        # returns: Claim only when this caller owns provider-call permission;
        #   otherwise a committed skip result.
        # side_effects: PostgreSQL SELECT, conflict-safe INSERT, locked UPDATE,
        #   commit/rollback, and sanitized lifecycle logging.
        # emitted_logs: day.narrative_lease_acquired, day.narrative_lease_recovered,
        #   day.narrative_lease_skipped, system.error.
        # error_behavior: Missing/unpublished snapshot raises snapshot_not_published;
        #   invalid existing state raises typed persistence error; SQLAlchemy errors
        #   rollback and become stable persistence errors.
        # END_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE-LEASE-SERVICE.acquire
        snapshot_id, prompt_version, normalized_now, duration = _validate_acquire_inputs(
            snapshot_id, prompt_version, now, lease_duration
        )
        lease_until = normalized_now + duration
        try:
            snapshot = (
                await self.db.execute(
                    select(TodaySnapshot).where(
                        TodaySnapshot.id == snapshot_id,
                        TodaySnapshot.published_at.is_not(None),
                    )
                )
            ).scalar_one_or_none()
            if snapshot is None or snapshot.published_at is None:
                await self.db.rollback()
                raise TodayNarrativeLeaseError("snapshot_not_published")

            inserted = await self.db.execute(
                postgres_insert(TodaySnapshotNarrative)
                .values(
                    id=uuid4(),
                    snapshot_id=snapshot_id,
                    prompt_version=prompt_version,
                    status="pending",
                    content_json=None,
                    attempt_count=1,
                    lease_until=lease_until,
                    next_retry_at=None,
                    last_error_code=None,
                )
                .on_conflict_do_nothing(constraint="uq_today_snapshot_narratives_version")
                .returning(TodaySnapshotNarrative.id)
            )
            inserted_id = inserted.scalar_one_or_none()
            if inserted_id is not None:
                await self.db.commit()
                result = NarrativeLeaseClaim(
                    narrative_id=inserted_id,
                    snapshot_id=snapshot_id,
                    prompt_version=prompt_version,
                    attempt_count=1,
                    lease_until=lease_until,
                    outcome="created",
                )
                _log_event(
                    "day.narrative_lease_acquired",
                    block="ACQUIRE",
                    payload={"outcome": "created"},
                )
                return result

            row = (
                await self.db.execute(
                    select(TodaySnapshotNarrative)
                    .where(
                        TodaySnapshotNarrative.snapshot_id == snapshot_id,
                        TodaySnapshotNarrative.prompt_version == prompt_version,
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if row is None:
                await self.db.rollback()
                raise _persistence_failure()
            result = self._transition_existing(row, normalized_now, lease_until)
            await self.db.commit()
            if isinstance(result, NarrativeLeaseSkip):
                _log_event(
                    "day.narrative_lease_skipped",
                    block="ACQUIRE",
                    payload={"reason": result.reason},
                )
            elif result.outcome == "recovered":
                _log_event(
                    "day.narrative_lease_recovered",
                    block="ACQUIRE",
                    payload={"outcome": "expired"},
                )
            else:
                _log_event(
                    "day.narrative_lease_acquired",
                    block="ACQUIRE",
                    payload={"outcome": "retry"},
                )
            return result
        except TodayNarrativeLeaseError:
            raise
        except SQLAlchemyError as exc:
            try:
                await self.db.rollback()
            except Exception:
                pass
            _log_event("system.error", block="ACQUIRE", error={"type": type(exc).__name__})
            raise _persistence_failure() from exc
        except TodayNarrativeLeasePersistenceError:
            try:
                await self.db.rollback()
            except Exception:
                pass
            raise

    @staticmethod
    def _transition_existing(
        row: TodaySnapshotNarrative,
        now: datetime,
        lease_until: datetime,
    ) -> NarrativeLeaseClaim | NarrativeLeaseSkip:
        # START_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE-LEASE-SERVICE._transition_existing
        # purpose: Apply one locked-row state transition without a second claimant.
        # inputs: locked narrative row, normalized now, and exact new lease deadline.
        # returns: claim for retry/recovery or a skip result.
        # side_effects: Mutates only the narrative row fields permitted by the packet.
        # emitted_logs: none; caller emits after commit.
        # error_behavior: Invalid persisted state raises stable persistence error.
        # END_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE-LEASE-SERVICE._transition_existing
        if not isinstance(row.attempt_count, int) or row.attempt_count < 1:
            raise TodayNarrativeLeasePersistenceError("today_narrative_lease:attempt_count")
        stored_lease = _stored_utc(row.lease_until, "lease_until")
        stored_retry = _stored_utc(row.next_retry_at, "next_retry_at")
        if row.status == "ready":
            _valid_ready_content(row)
            return NarrativeLeaseSkip(
                row.id, row.snapshot_id, row.prompt_version, "ready", "ready", None
            )
        if row.status == "pending":
            if row.content_json is not None:
                raise TodayNarrativeLeasePersistenceError("today_narrative_lease:pending_content")
            if stored_lease is not None and stored_lease > now:
                return NarrativeLeaseSkip(
                    row.id,
                    row.snapshot_id,
                    row.prompt_version,
                    "pending",
                    "in_flight",
                    stored_lease,
                )
            row.attempt_count += 1
            row.lease_until = lease_until
            row.next_retry_at = None
            row.last_error_code = None
            return NarrativeLeaseClaim(
                row.id,
                row.snapshot_id,
                row.prompt_version,
                row.attempt_count,
                lease_until,
                "recovered",
            )
        if row.status == "unavailable" and row.content_json is not None:
            raise TodayNarrativeLeasePersistenceError("today_narrative_lease:unavailable_content")
        if row.status == "unavailable":
            if stored_retry is None:
                return NarrativeLeaseSkip(
                    row.id,
                    row.snapshot_id,
                    row.prompt_version,
                    "unavailable",
                    "exhausted",
                    None,
                )
            if stored_retry > now:
                return NarrativeLeaseSkip(
                    row.id,
                    row.snapshot_id,
                    row.prompt_version,
                    "unavailable",
                    "cooldown",
                    stored_retry,
                )
            row.status = "pending"
            row.attempt_count += 1
            row.content_json = None
            row.lease_until = lease_until
            row.next_retry_at = None
            row.last_error_code = None
            return NarrativeLeaseClaim(
                row.id,
                row.snapshot_id,
                row.prompt_version,
                row.attempt_count,
                lease_until,
                "retry",
            )
        raise TodayNarrativeLeasePersistenceError("today_narrative_lease:status")
    # END_BLOCK: ACQUIRE

    # START_BLOCK: COMPLETION_CAS
    async def complete_ready(
        self, claim: NarrativeLeaseClaim, content_json: dict
    ) -> NarrativeLeaseCompletion:
        # START_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE-LEASE-SERVICE.complete_ready
        # purpose: Complete an owned pending claim with an already validated JSON object.
        # inputs: exact immutable claim and JSON object content.
        # returns: completed when CAS matched, stale when another claim won.
        # side_effects: One conditional PostgreSQL UPDATE, commit/rollback, and log.
        # emitted_logs: day.narrative_lease_completed, system.error for stale.
        # error_behavior: invalid content fails before SQL; SQL errors rollback into
        #   persistence error; stale CAS never raises a business exception.
        # END_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE-LEASE-SERVICE.complete_ready
        _validate_claim(claim)
        copied = _validate_json_object(content_json)
        return await self._complete(
            claim,
            values={
                "status": "ready",
                "content_json": copied,
                "lease_until": None,
                "next_retry_at": None,
                "last_error_code": None,
            },
            event="day.narrative_lease_completed",
            payload={"outcome": "ready"},
        )

    async def complete_unavailable(
        self,
        claim: NarrativeLeaseClaim,
        error_code: str,
        next_retry_at: datetime | None,
    ) -> NarrativeLeaseCompletion:
        # START_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE-LEASE-SERVICE.complete_unavailable
        # purpose: Complete an owned claim as honest unavailable with stable error code.
        # inputs: exact immutable claim, machine error code, and nullable aware future retry;
        #   future validation uses the constructor-injected aware-UTC clock.
        # returns: completed when CAS matched, stale when another claim won.
        # side_effects: One conditional PostgreSQL UPDATE, commit/rollback, and log.
        # emitted_logs: day.narrative_lease_failed, system.error for stale.
        # error_behavior: invalid error/retry inputs fail before SQL; SQL errors rollback;
        #   stale CAS never raises a business exception.
        # END_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE-LEASE-SERVICE.complete_unavailable
        _validate_claim(claim)
        normalized_error = _validate_error_code(error_code)
        normalized_retry = None if next_retry_at is None else _aware_utc(next_retry_at, "next_retry_at")
        if normalized_retry is not None:
            current_utc = _aware_utc(self._clock(), "clock")
            if normalized_retry <= current_utc:
                raise ValueError("next_retry_at must be in the future")
        return await self._complete(
            claim,
            values={
                "status": "unavailable",
                "content_json": None,
                "lease_until": None,
                "next_retry_at": normalized_retry,
                "last_error_code": normalized_error,
            },
            event="day.narrative_lease_failed",
            payload={"retry_scheduled": normalized_retry is not None},
        )

    async def _complete(
        self,
        claim: NarrativeLeaseClaim,
        *,
        values: dict[str, object],
        event: str,
        payload: dict[str, object],
    ) -> NarrativeLeaseCompletion:
        try:
            result = await self.db.execute(
                update(TodaySnapshotNarrative).where(*_claim_where(claim)).values(**values)
            )
            rowcount = result.rowcount
            await self.db.commit()
            if rowcount:
                _log_event(event, block="COMPLETION_CAS", payload=payload)
                return NarrativeLeaseCompletion(outcome="completed")
            _log_event(
                "system.error",
                block="COMPLETION_CAS",
                error={"type": "narrative_lease_stale"},
            )
            return NarrativeLeaseCompletion(outcome="stale")
        except SQLAlchemyError as exc:
            try:
                await self.db.rollback()
            except Exception:
                pass
            _log_event("system.error", block="COMPLETION_CAS", error={"type": type(exc).__name__})
            raise _persistence_failure() from exc
    # END_BLOCK: COMPLETION_CAS

    # START_BLOCK: LOAD
    async def load(
        self, snapshot_id: UUID, prompt_version: str
    ) -> TodaySnapshotNarrative | None:
        # START_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE-LEASE-SERVICE.load
        # purpose: Load one narrative row by its immutable snapshot/prompt key.
        # inputs: UUID snapshot_id and nonblank prompt_version.
        # returns: matching narrative row or None.
        # side_effects: One PostgreSQL SELECT; rollback on SQL failure.
        # emitted_logs: system.error on SQL failure.
        # error_behavior: invalid inputs fail before SQL; SQL errors become stable
        #   persistence errors; unexpected errors propagate.
        # END_FUNCTION_CONTRACT: F-M-TODAY-NARRATIVE-LEASE-SERVICE.load
        _validate_uuid(snapshot_id, "snapshot_id")
        _validate_prompt_version(prompt_version)
        try:
            return (
                await self.db.execute(
                    select(TodaySnapshotNarrative).where(
                        TodaySnapshotNarrative.snapshot_id == snapshot_id,
                        TodaySnapshotNarrative.prompt_version == prompt_version,
                    )
                )
            ).scalar_one_or_none()
        except SQLAlchemyError as exc:
            try:
                await self.db.rollback()
            except Exception:
                pass
            _log_event("system.error", block="LOAD", error={"type": type(exc).__name__})
            raise _persistence_failure() from exc
    # END_BLOCK: LOAD


__all__ = [
    "NarrativeLeaseClaim",
    "NarrativeLeaseCompletion",
    "NarrativeLeaseSkip",
    "TodayNarrativeLeaseError",
    "TodayNarrativeLeasePersistenceError",
    "TodayNarrativeLeaseService",
]
