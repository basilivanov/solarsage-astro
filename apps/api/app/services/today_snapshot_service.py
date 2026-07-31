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
# outputs: TodaySnapshotPublication, TodaySnapshotImpression, or owner-scoped TodaySnapshot | None.
# dependencies: PostgreSQL SQLAlchemy insert/select, TodaySnapshot model,
#   TodayConvergenceSnapshotDocument, structured logging registry.
# side_effects: inserts/reads/commits TodaySnapshot rows, records immutable first-seen
#   timestamps, and emits publication, lineage, impression, lookup, and error events.
# emitted_logs: day.snapshot_published, day.snapshot_conflict_reused,
#   day.snapshot_superseded, day.impression_recorded, day.impression_rejected,
#   day.snapshot_lookup_hit, day.snapshot_lookup_miss, system.error.
# invariants: identity is owner/date/input/formula/calculation/canon; supersession is
#   same-owner/date and single-child; deterministic fields and first-seen timestamps
#   are immutable; no re-execution, raw identity, or caller-owned JSON mutation.
# failure_policy: type errors fail before SQL; SQLAlchemy errors rollback and
#   raise TodaySnapshotPersistenceError with stable reason; unexpected errors propagate.
# END_MODULE_CONTRACT: M-TODAY-SNAPSHOT-SERVICE

# START_MODULE_MAP: M-TODAY-SNAPSHOT-SERVICE
# public_entrypoints:
#   - TodaySnapshotPublication
#   - TodaySnapshotImpression
#   - TodaySnapshotLineageError
#   - TodaySnapshotPersistenceError
#   - TodaySnapshotService.publish_or_load
#   - TodaySnapshotService.publish_superseding
#   - TodaySnapshotService.record_impression
#   - TodaySnapshotService.load_owned
# semantic_blocks:
#   - PUBLISH: atomic PostgreSQL insert and committed conflict winner.
#   - SUPERSESSION: same-owner/date chain successor publication.
#   - IMPRESSION: atomic independent day/lookahead first-seen timestamps.
#   - LOAD_OWNED: one owner-scoped lookup with indistinguishable miss semantics.
#   - LOGGING: sanitized publication, lookup, and SQL failure events.
# owned_tests:
#   - apps/api/tests/test_today_snapshot_service.py
#   - apps/api/tests/test_today_snapshot_postgres.py
#   - apps/api/tests/test_today_snapshot_lineage.py
#   - apps/api/tests/test_today_snapshot_lineage_postgres.py
# END_MODULE_MAP: M-TODAY-SNAPSHOT-SERVICE

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log_block, log_event
from app.db.models import TodaySnapshot
from app.services.today_convergence_snapshot import TodayConvergenceSnapshotDocument


class TodaySnapshotPersistenceError(ValueError):
    """Raised when a snapshot SQL boundary cannot complete safely."""


class TodaySnapshotLineageError(ValueError):
    """Raised when a supersession or impression relation is not admissible."""


@dataclass(frozen=True)
class TodaySnapshotPublication:
    """Committed snapshot row and whether this call inserted or reused it."""

    snapshot: TodaySnapshot
    outcome: Literal["published", "conflict_reused"]


@dataclass(frozen=True)
class TodaySnapshotImpression:
    """Committed first-seen timestamp for one public snapshot surface."""

    snapshot_id: UUID
    surface: Literal["day", "lookahead"]
    outcome: Literal["recorded", "existing"]
    seen_at: datetime


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


def _aware_utc(value: datetime | None, name: str) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise TypeError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _document_timezone(document: TodayConvergenceSnapshotDocument) -> ZoneInfo:
    try:
        return ZoneInfo(document.timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise TodaySnapshotLineageError("today_snapshot:invalid_timezone") from exc


def _validate_document(document: TodayConvergenceSnapshotDocument) -> ZoneInfo:
    if type(document) is not TodayConvergenceSnapshotDocument:
        raise TypeError("document must be TodayConvergenceSnapshotDocument")
    if type(document.target_date) is not date:
        raise TypeError("document target_date must be date")
    if not isinstance(document.timezone, str):
        raise TypeError("document timezone must be str")
    return _document_timezone(document)


def _identity_matches(
    snapshot: TodaySnapshot,
    user_id: UUID,
    document: TodayConvergenceSnapshotDocument,
) -> bool:
    return (
        snapshot.user_id == user_id
        and snapshot.target_date == document.target_date
        and snapshot.input_hash == document.input_hash
        and snapshot.formula_version == document.formula_version
        and snapshot.calculation_version == document.calculation_version
        and snapshot.canon_hash == document.canon_hash
    )


def _stored_seen_at(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class TodaySnapshotService:
    """PostgreSQL-only publication and owner lookup boundary."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _publish_document(
        self,
        user_id: UUID,
        document: TodayConvergenceSnapshotDocument,
        *,
        supersedes_snapshot_id: UUID | None,
    ) -> TodaySnapshotPublication:
        payload = _document_payload(document)
        values = {
            "id": uuid4(),
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
            "supersedes_snapshot_id": supersedes_snapshot_id,
        }
        statement = postgres_insert(TodaySnapshot).values(**values)
        if supersedes_snapshot_id is None:
            statement = statement.on_conflict_do_nothing(constraint="uq_today_snapshots_identity")
        else:
            statement = statement.on_conflict_do_nothing()
        statement = statement.returning(TodaySnapshot.id)
        identity = (
            TodaySnapshot.user_id == user_id,
            TodaySnapshot.target_date == document.target_date,
            TodaySnapshot.input_hash == document.input_hash,
            TodaySnapshot.formula_version == document.formula_version,
            TodaySnapshot.calculation_version == document.calculation_version,
            TodaySnapshot.canon_hash == document.canon_hash,
        )
        operation_block = "SUPERSESSION" if supersedes_snapshot_id is not None else "PUBLISH"
        try:
            inserted_id = (await self.db.execute(statement)).scalar_one_or_none()
            if inserted_id is None:
                snapshot = (await self.db.execute(select(TodaySnapshot).where(*identity))).scalar_one_or_none()
                if snapshot is not None:
                    if supersedes_snapshot_id is not None and snapshot.supersedes_snapshot_id != supersedes_snapshot_id:
                        await self.db.rollback()
                        _log_event("system.error", block=operation_block, error={"type": "SupersessionConflict"})
                        raise TodaySnapshotLineageError("today_snapshot:supersession_conflict")
                    await self.db.commit()
                    if supersedes_snapshot_id is None:
                        _log_event("day.snapshot_conflict_reused", block="PUBLISH", payload=payload)
                    else:
                        _log_event("day.snapshot_superseded", block="SUPERSESSION", payload={"outcome": "conflict_reused"})
                    return TodaySnapshotPublication(snapshot=snapshot, outcome="conflict_reused")
                if supersedes_snapshot_id is not None:
                    child = (
                        await self.db.execute(
                            select(TodaySnapshot).where(
                                TodaySnapshot.user_id == user_id,
                                TodaySnapshot.supersedes_snapshot_id == supersedes_snapshot_id,
                            )
                        )
                    ).scalar_one_or_none()
                    await self.db.rollback()
                    if child is not None:
                        _log_event(
                            "system.error",
                            block="SUPERSESSION",
                            error={"type": "SupersessionFork"},
                        )
                        raise TodaySnapshotLineageError("today_snapshot:supersession_fork")
                await self.db.rollback()
                _log_event("system.error", block=operation_block, error={"type": "ConflictWinnerMissing"})
                raise _persistence_failure()

            snapshot = (
                await self.db.execute(select(TodaySnapshot).where(TodaySnapshot.id == inserted_id))
            ).scalar_one_or_none()
            if snapshot is None:
                await self.db.rollback()
                _log_event("system.error", block=operation_block, error={"type": "PublishedSnapshotMissing"})
                raise _persistence_failure()
            await self.db.commit()
            if supersedes_snapshot_id is None:
                _log_event("day.snapshot_published", block="PUBLISH", payload=payload)
            else:
                _log_event(
                    "day.snapshot_superseded",
                    block="SUPERSESSION",
                    payload={"outcome": "published"},
                )
            return TodaySnapshotPublication(snapshot=snapshot, outcome="published")
        except SQLAlchemyError as exc:
            try:
                await self.db.rollback()
            except Exception:
                pass
            _log_event("system.error", block=operation_block, error={"type": type(exc).__name__})
            raise _persistence_failure() from exc

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
        _validate_document(document)
        return await self._publish_document(user_id, document, supersedes_snapshot_id=None)
    # END_BLOCK: PUBLISH

    # START_BLOCK: SUPERSESSION
    async def publish_superseding(
        self,
        user_id: UUID,
        document: TodayConvergenceSnapshotDocument,
        supersedes_snapshot_id: UUID,
        *,
        observed_at: datetime | None = None,
    ) -> TodaySnapshotPublication:
        # START_FUNCTION_CONTRACT: F-M-TODAY-SNAPSHOT-SERVICE.publish_superseding
        # purpose: Publish one same-owner/date snapshot as a deterministic chain successor.
        # inputs: UUID owner, exact document, UUID parent, and optional aware observation time.
        # returns: Committed publication with published or conflict_reused outcome.
        # side_effects: Owner-scoped reads, PostgreSQL insert/commit, sanitized events.
        # emitted_logs: day.snapshot_superseded, system.error.
        # error_behavior: Typed lineage errors for invalid parent/date/fork; SQL errors become persistence errors.
        # END_FUNCTION_CONTRACT: F-M-TODAY-SNAPSHOT-SERVICE.publish_superseding
        if not isinstance(user_id, UUID):
            raise TypeError("user_id must be UUID")
        if not isinstance(supersedes_snapshot_id, UUID):
            raise TypeError("supersedes_snapshot_id must be UUID")
        zone = _validate_document(document)
        effective_at = _aware_utc(observed_at, "observed_at")
        if document.target_date < effective_at.astimezone(zone).date():
            raise TodaySnapshotLineageError("today_snapshot:past_target")
        try:
            parent = (
                await self.db.execute(
                    select(TodaySnapshot).where(
                        TodaySnapshot.id == supersedes_snapshot_id,
                        TodaySnapshot.user_id == user_id,
                    )
                )
            ).scalar_one_or_none()
            if parent is None:
                await self.db.rollback()
                _log_event("system.error", block="SUPERSESSION", error={"type": "ParentNotFound"})
                raise TodaySnapshotLineageError("today_snapshot:parent_not_found")
            if parent.target_date != document.target_date:
                await self.db.rollback()
                _log_event("system.error", block="SUPERSESSION", error={"type": "ParentDateMismatch"})
                raise TodaySnapshotLineageError("today_snapshot:parent_date")
            child = (
                await self.db.execute(
                    select(TodaySnapshot).where(
                        TodaySnapshot.user_id == user_id,
                        TodaySnapshot.supersedes_snapshot_id == supersedes_snapshot_id,
                    )
                )
            ).scalar_one_or_none()
            if child is not None:
                if _identity_matches(child, user_id, document) and child.supersedes_snapshot_id == supersedes_snapshot_id:
                    await self.db.commit()
                    _log_event(
                        "day.snapshot_superseded",
                        block="SUPERSESSION",
                        payload={"outcome": "conflict_reused"},
                    )
                    return TodaySnapshotPublication(snapshot=child, outcome="conflict_reused")
                await self.db.rollback()
                _log_event("system.error", block="SUPERSESSION", error={"type": "SupersessionFork"})
                raise TodaySnapshotLineageError("today_snapshot:supersession_fork")
        except SQLAlchemyError as exc:
            try:
                await self.db.rollback()
            except Exception:
                pass
            _log_event("system.error", block="SUPERSESSION", error={"type": type(exc).__name__})
            raise _persistence_failure() from exc
        return await self._publish_document(
            user_id,
            document,
            supersedes_snapshot_id=supersedes_snapshot_id,
        )
    # END_BLOCK: SUPERSESSION

    # START_BLOCK: IMPRESSION
    async def record_impression(
        self,
        user_id: UUID,
        snapshot_id: UUID,
        surface: Literal["day", "lookahead"],
        *,
        source_snapshot_id: UUID | None = None,
        observed_at: datetime | None = None,
    ) -> TodaySnapshotImpression | None:
        # START_FUNCTION_CONTRACT: F-M-TODAY-SNAPSHOT-SERVICE.record_impression
        # purpose: Atomically record or reuse the first UTC exposure timestamp for one surface.
        # inputs: UUID owner/snapshot, day or lookahead surface, optional source UUID, aware test time.
        # returns: Recorded/existing impression, or None for owner/missing/invalid relation.
        # side_effects: Owner-scoped SELECT and conditional PostgreSQL write/commit.
        # emitted_logs: day.impression_recorded, day.impression_rejected, system.error.
        # error_behavior: SQLAlchemy failures rollback and become sanitized persistence errors.
        # END_FUNCTION_CONTRACT: F-M-TODAY-SNAPSHOT-SERVICE.record_impression
        if not isinstance(user_id, UUID):
            raise TypeError("user_id must be UUID")
        if not isinstance(snapshot_id, UUID):
            raise TypeError("snapshot_id must be UUID")
        if source_snapshot_id is not None and not isinstance(source_snapshot_id, UUID):
            raise TypeError("source_snapshot_id must be UUID")
        if surface not in {"day", "lookahead"}:
            raise TypeError("surface must be day or lookahead")
        seen_at = _aware_utc(observed_at, "observed_at")
        if surface == "day" and source_snapshot_id is not None:
            _log_event(
                "day.impression_rejected",
                block="IMPRESSION",
                payload={"surface": surface, "reason": "invalid_relation"},
            )
            return None
        try:
            snapshot = (
                await self.db.execute(
                    select(TodaySnapshot).where(
                        TodaySnapshot.id == snapshot_id,
                        TodaySnapshot.user_id == user_id,
                    )
                )
            ).scalar_one_or_none()
            if snapshot is None:
                await self.db.rollback()
                _log_event(
                    "day.impression_rejected",
                    block="IMPRESSION",
                    payload={"surface": surface, "reason": "not_found"},
                )
                return None
            try:
                snapshot_zone = ZoneInfo(snapshot.timezone)
            except (ZoneInfoNotFoundError, ValueError) as exc:
                raise TodaySnapshotLineageError("today_snapshot:invalid_timezone") from exc

            if surface == "day":
                if snapshot.target_date != seen_at.astimezone(snapshot_zone).date():
                    raise TodaySnapshotLineageError("today_snapshot:invalid_relation")
            else:
                if source_snapshot_id is None:
                    raise TodaySnapshotLineageError("today_snapshot:source_required")
                source = (
                    await self.db.execute(
                        select(TodaySnapshot).where(
                            TodaySnapshot.id == source_snapshot_id,
                            TodaySnapshot.user_id == user_id,
                        )
                    )
                ).scalar_one_or_none()
                if source is None:
                    await self.db.rollback()
                    _log_event(
                        "day.impression_rejected",
                        block="IMPRESSION",
                        payload={"surface": surface, "reason": "not_found"},
                    )
                    return None
                try:
                    source_zone = ZoneInfo(source.timezone)
                except (ZoneInfoNotFoundError, ValueError) as exc:
                    raise TodaySnapshotLineageError("today_snapshot:invalid_timezone") from exc
                source_local_date = seen_at.astimezone(source_zone).date()
                source_state = source.deterministic_result_json.get("state") if isinstance(source.deterministic_result_json, dict) else None
                if (
                    source.target_date != source_local_date
                    or snapshot.target_date != source.target_date + timedelta(days=1)
                    or source_state != "quiet_day"
                ):
                    raise TodaySnapshotLineageError("today_snapshot:invalid_relation")

            seen_column = TodaySnapshot.first_day_seen_at if surface == "day" else TodaySnapshot.first_lookahead_seen_at
            updated = (
                await self.db.execute(
                    update(TodaySnapshot)
                    .where(
                        TodaySnapshot.id == snapshot_id,
                        TodaySnapshot.user_id == user_id,
                        seen_column.is_(None),
                    )
                    .values({seen_column: seen_at})
                    .returning(TodaySnapshot.id, seen_column)
                )
            ).first()
            if updated is not None:
                recorded_at = _stored_seen_at(updated[1])
                await self.db.commit()
                _log_event(
                    "day.impression_recorded",
                    block="IMPRESSION",
                    payload={"surface": surface, "outcome": "recorded"},
                )
                return TodaySnapshotImpression(snapshot_id, surface, "recorded", recorded_at)

            current = (
                await self.db.execute(
                    select(TodaySnapshot).where(
                        TodaySnapshot.id == snapshot_id,
                        TodaySnapshot.user_id == user_id,
                    )
                )
            ).scalar_one_or_none()
            if current is None:
                await self.db.rollback()
                _log_event(
                    "day.impression_rejected",
                    block="IMPRESSION",
                    payload={"surface": surface, "reason": "not_found"},
                )
                return None
            original = current.first_day_seen_at if surface == "day" else current.first_lookahead_seen_at
            if original is None:
                await self.db.rollback()
                _log_event("system.error", block="IMPRESSION", error={"type": "ImpressionWinnerMissing"})
                raise _persistence_failure()
            await self.db.commit()
            _log_event(
                "day.impression_recorded",
                block="IMPRESSION",
                payload={"surface": surface, "outcome": "existing"},
            )
            return TodaySnapshotImpression(snapshot_id, surface, "existing", _stored_seen_at(original))
        except TodaySnapshotLineageError:
            await self.db.rollback()
            _log_event(
                "day.impression_rejected",
                block="IMPRESSION",
                payload={"surface": surface, "reason": "invalid_relation"},
            )
            return None
        except SQLAlchemyError as exc:
            try:
                await self.db.rollback()
            except Exception:
                pass
            _log_event("system.error", block="IMPRESSION", error={"type": type(exc).__name__})
            raise _persistence_failure() from exc
    # END_BLOCK: IMPRESSION

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
    "TodaySnapshotImpression",
    "TodaySnapshotLineageError",
    "TodaySnapshotPersistenceError",
    "TodaySnapshotPublication",
    "TodaySnapshotService",
]
