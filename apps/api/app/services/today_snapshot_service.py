# ############################################################################
# AI_HEADER: MODULE_TODAY-SNAPSHOT-SERVICE — atomic PostgreSQL snapshot publication.
# ROLE: Publishes one validated TodayConvergenceSnapshotDocument per owner and
#       deterministic identity, reusing the committed PostgreSQL conflict winner.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-SNAPSHOT-SERVICE
# purpose: Persist an already validated deterministic snapshot with PostgreSQL
#   INSERT ... ON CONFLICT DO NOTHING semantics and owner-scoped lookup.
# owns:
#   - apps/api/app/services/today_snapshot_service.py
# inputs: AsyncSession, real UUID owner, and exact TodayConvergenceSnapshotDocument.
# outputs: TodaySnapshotPublication or owner-scoped TodaySnapshot | None.
# dependencies: PostgreSQL SQLAlchemy insert/select, TodaySnapshot model,
#   TodayConvergenceSnapshotDocument, structured logging registry.
# side_effects: inserts/reads/commits TodaySnapshot rows and emits four typed events.
# emitted_logs: day.snapshot_published, day.snapshot_conflict_reused,
#   day.snapshot_lookup_hit, day.snapshot_lookup_miss, system.error.
# invariants: identity is owner/date/input/formula/calculation/canon; no update,
#   re-execution, check-then-insert, raw identity, or caller-owned JSON mutation.
# failure_policy: type errors fail before SQL; SQLAlchemy errors rollback and
#   raise TodaySnapshotPersistenceError with stable reason; unexpected errors propagate.
# END_MODULE_CONTRACT: M-TODAY-SNAPSHOT-SERVICE

# START_MODULE_MAP: M-TODAY-SNAPSHOT-SERVICE
# public_entrypoints:
#   - TodaySnapshotPublication
#   - TodaySnapshotPersistenceError
#   - TodaySnapshotService.publish_or_load
#   - TodaySnapshotService.load_owned
# semantic_blocks:
#   - PUBLISH: atomic PostgreSQL insert and committed conflict winner.
#   - LOAD_OWNED: one owner-scoped lookup with indistinguishable miss semantics.
#   - LOGGING: sanitized publication, lookup, and SQL failure events.
# owned_tests:
#   - apps/api/tests/test_today_snapshot_service.py
#   - apps/api/tests/test_today_snapshot_postgres.py
# END_MODULE_MAP: M-TODAY-SNAPSHOT-SERVICE

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log_block, log_event
from app.db.models import TodaySnapshot
from app.services.today_convergence_snapshot import TodayConvergenceSnapshotDocument


class TodaySnapshotPersistenceError(ValueError):
    """Raised when a snapshot SQL boundary cannot complete safely."""


@dataclass(frozen=True)
class TodaySnapshotPublication:
    """Committed snapshot row and whether this call inserted or reused it."""

    snapshot: TodaySnapshot
    outcome: Literal["published", "conflict_reused"]


def _document_payload(document: TodayConvergenceSnapshotDocument) -> dict[str, object]:
    result = document.deterministic_result_json
    if not isinstance(result, dict) or not isinstance(result.get("state"), str):
        raise TypeError("document deterministic_result_json state")
    if not isinstance(document.birth_time_mode, str):
        raise TypeError("document birth_time_mode")
    return {"state": result["state"], "birth_time_mode": document.birth_time_mode}


def _log_event(event: str, *, block: str, payload: dict[str, object] | None = None, error: dict[str, str] | None = None) -> None:
    try:
        with log_block(slice="W-TODAY-CONVERGENCE", module="M-TODAY-SNAPSHOT-SERVICE", block=block):
            log_event(event, msg="today snapshot boundary", payload=payload, error=error)
    except Exception:
        # The logging contract is non-blocking for the business transaction.
        pass


def _persistence_failure() -> TodaySnapshotPersistenceError:
    return TodaySnapshotPersistenceError("today_snapshot:persistence")


class TodaySnapshotService:
    """PostgreSQL-only publication and owner lookup boundary."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # START_BLOCK: PUBLISH
    async def publish_or_load(
        self,
        user_id: UUID,
        document: TodayConvergenceSnapshotDocument,
    ) -> TodaySnapshotPublication:
        # START_FUNCTION_CONTRACT: F-M-TODAY-SNAPSHOT-SERVICE.publish_or_load
        # purpose: Atomically insert one typed snapshot or return the committed conflict winner.
        # inputs: real UUID user_id and exact TodayConvergenceSnapshotDocument.
        # returns: committed row with published or conflict_reused outcome.
        # side_effects: PostgreSQL insert/select/commit; sanitized structured events.
        # emitted_logs: day.snapshot_published, day.snapshot_conflict_reused, system.error.
        # error_behavior: type errors before SQL; SQLAlchemy errors rollback and become typed persistence errors; unexpected errors propagate.
        # END_FUNCTION_CONTRACT: F-M-TODAY-SNAPSHOT-SERVICE.publish_or_load
        if not isinstance(user_id, UUID):
            raise TypeError("user_id must be UUID")
        if type(document) is not TodayConvergenceSnapshotDocument:
            raise TypeError("document must be TodayConvergenceSnapshotDocument")
        payload = _document_payload(document)
        candidate_id = uuid4()
        values = {
            "id": candidate_id,
            "user_id": user_id,
            "target_date": document.target_date,
            "timezone": document.timezone,
            "profile_hash": document.profile_hash,
            "input_hash": document.input_hash,
            "canon_hash": document.canon_hash,
            "formula_version": document.formula_version,
            "calculation_version": document.calculation_version,
            "ephemeris_artifact_id": document.ephemeris_artifact_id,
            "birth_time_mode": document.birth_time_mode,
            "birth_time_range": deepcopy(document.birth_time_range),
            "deterministic_result_json": deepcopy(document.deterministic_result_json),
            "canonical_input_json": deepcopy(document.canonical_input_json),
        }
        statement = (
            postgres_insert(TodaySnapshot)
            .values(**values)
            .on_conflict_do_nothing(constraint="uq_today_snapshots_identity")
            .returning(TodaySnapshot.id)
        )
        identity = (
            TodaySnapshot.user_id == user_id,
            TodaySnapshot.target_date == document.target_date,
            TodaySnapshot.input_hash == document.input_hash,
            TodaySnapshot.formula_version == document.formula_version,
            TodaySnapshot.calculation_version == document.calculation_version,
            TodaySnapshot.canon_hash == document.canon_hash,
        )
        try:
            inserted_id = (await self.db.execute(statement)).scalar_one_or_none()
            if inserted_id is not None:
                snapshot = (await self.db.execute(select(TodaySnapshot).where(TodaySnapshot.id == inserted_id))).scalar_one_or_none()
                if snapshot is None:
                    await self.db.rollback()
                    _log_event(
                        "system.error",
                        block="PUBLISH",
                        error={"type": "PublishedSnapshotMissing"},
                    )
                    raise _persistence_failure()
                await self.db.commit()
                _log_event("day.snapshot_published", block="PUBLISH", payload=payload)
                return TodaySnapshotPublication(snapshot=snapshot, outcome="published")

            snapshot = (await self.db.execute(select(TodaySnapshot).where(*identity))).scalar_one_or_none()
            if snapshot is None:
                await self.db.rollback()
                _log_event(
                    "system.error",
                    block="PUBLISH",
                    error={"type": "ConflictWinnerMissing"},
                )
                raise _persistence_failure()
            await self.db.commit()
            _log_event("day.snapshot_conflict_reused", block="PUBLISH", payload=payload)
            return TodaySnapshotPublication(snapshot=snapshot, outcome="conflict_reused")
        except SQLAlchemyError as exc:
            try:
                await self.db.rollback()
            except Exception:
                pass
            _log_event("system.error", block="PUBLISH", error={"type": type(exc).__name__})
            raise _persistence_failure() from exc
    # END_BLOCK: PUBLISH

    # START_BLOCK: LOAD_OWNED
    async def load_owned(self, user_id: UUID, snapshot_id: UUID) -> TodaySnapshot | None:
        # START_FUNCTION_CONTRACT: F-M-TODAY-SNAPSHOT-SERVICE.load_owned
        # purpose: Load one snapshot only when both row ID and authenticated owner match.
        # inputs: real UUID owner and snapshot ID.
        # returns: TodaySnapshot on owned hit, otherwise None for foreign/missing rows.
        # side_effects: one PostgreSQL SELECT and lookup event; no writes.
        # emitted_logs: day.snapshot_lookup_hit, day.snapshot_lookup_miss, system.error.
        # error_behavior: type errors before SQL; SQLAlchemy errors become typed persistence errors.
        # END_FUNCTION_CONTRACT: F-M-TODAY-SNAPSHOT-SERVICE.load_owned
        if not isinstance(user_id, UUID):
            raise TypeError("user_id must be UUID")
        if not isinstance(snapshot_id, UUID):
            raise TypeError("snapshot_id must be UUID")
        try:
            result = await self.db.execute(
                select(TodaySnapshot).where(
                    TodaySnapshot.id == snapshot_id,
                    TodaySnapshot.user_id == user_id,
                )
            )
            snapshot = result.scalar_one_or_none()
        except SQLAlchemyError as exc:
            try:
                await self.db.rollback()
            except Exception:
                pass
            _log_event("system.error", block="LOAD_OWNED", error={"type": type(exc).__name__})
            raise _persistence_failure() from exc
        event = "day.snapshot_lookup_hit" if snapshot is not None else "day.snapshot_lookup_miss"
        _log_event(event, block="LOAD_OWNED", payload={"lookup": "owned_id"})
        return snapshot
    # END_BLOCK: LOAD_OWNED


__all__ = [
    "TodaySnapshotPersistenceError",
    "TodaySnapshotPublication",
    "TodaySnapshotService",
]
