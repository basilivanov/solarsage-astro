# ############################################################################
# AI_HEADER: TEST_TODAY-SNAPSHOT-SERVICE — atomic snapshot publication tests.
# ROLE: Proves typed PostgreSQL insert-on-conflict publication, owned lookup,
#       immutable JSON boundaries, sanitized failures, and registry/source rules.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-SNAPSHOT-SERVICE
# purpose: Validate the pure service contract around TodaySnapshot publication.
# owns:
#   - apps/api/tests/test_today_snapshot_service.py
# inputs: Typed snapshot documents, UUID owners, fake async sessions, and registry files.
# outputs: Unit evidence for insert, conflict reuse, owned lookup, errors, and logs.
# dependencies: today_snapshot_service, today_convergence_snapshot, TodaySnapshot, SQLAlchemy PostgreSQL compiler.
# side_effects: Fake session calls only; no database or network.
# emitted_logs: day.snapshot_published, day.snapshot_conflict_reused, day.snapshot_lookup_hit, day.snapshot_lookup_miss, system.error.
# invariants: no check-then-insert, no update path, no raw identity/JSON in logs.
# failure_policy: typed persistence failure only for SQLAlchemy errors; unexpected programming errors propagate.
# END_MODULE_CONTRACT: M-TEST-TODAY-SNAPSHOT-SERVICE

# START_MODULE_MAP: M-TEST-TODAY-SNAPSHOT-SERVICE
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - INPUT_BOUNDARY: strict owner/document validation before SQL.
#   - PUBLICATION: typed row values and PostgreSQL conflict reuse.
#   - OWNED_LOOKUP: owner-scoped hit/miss without existence leakage.
#   - FAILURE_AND_REGISTRY: sanitized SQL failure, source, and event parity.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-SNAPSHOT-SERVICE

from __future__ import annotations

import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import OperationalError

from app.db.models import TodaySnapshot
from app.services.today_convergence_snapshot import TodayConvergenceSnapshotDocument
from app.services.today_snapshot_service import (
    TodaySnapshotPersistenceError,
    TodaySnapshotPublication,
    TodaySnapshotService,
)


OWNER_ID = UUID("11111111-1111-4111-8111-111111111111")
OTHER_OWNER_ID = UUID("22222222-2222-4222-8222-222222222222")
SNAPSHOT_ID = UUID("33333333-3333-4333-8333-333333333333")


def document() -> TodayConvergenceSnapshotDocument:
    return TodayConvergenceSnapshotDocument(
        target_date=date(2026, 7, 31),
        timezone="Europe/Moscow",
        profile_hash="p" * 64,
        input_hash="i" * 64,
        canon_hash="c" * 64,
        formula_version="formula-1",
        calculation_version="calc-1",
        ephemeris_artifact_id="artifact-1",
        birth_time_mode="exact",
        birth_time_range={"start": "14:30", "end": "14:30"},
        canonical_input_json={"nested": {"input": [1, 2]}},
        deterministic_result_json={"state": "quiet_day", "selected": {"convergences": []}},
    )


def row(owner_id: UUID = OWNER_ID, snapshot_id: UUID = SNAPSHOT_ID) -> TodaySnapshot:
    value = document()
    return TodaySnapshot(
        id=snapshot_id,
        user_id=owner_id,
        target_date=value.target_date,
        timezone=value.timezone,
        profile_hash=value.profile_hash,
        input_hash=value.input_hash,
        canon_hash=value.canon_hash,
        formula_version=value.formula_version,
        calculation_version=value.calculation_version,
        ephemeris_artifact_id=value.ephemeris_artifact_id,
        birth_time_mode=value.birth_time_mode,
        birth_time_range=deepcopy(value.birth_time_range),
        deterministic_result_json=deepcopy(value.deterministic_result_json),
        canonical_input_json=deepcopy(value.canonical_input_json),
    )


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, responses=None, execute_error=None):
        self.responses = list(responses or [])
        self.execute_error = execute_error
        self.statements = []
        self.operations = []
        self.commit_count = 0
        self.rollback_count = 0

    async def execute(self, statement):
        self.statements.append(statement)
        self.operations.append("execute")
        if self.execute_error is not None:
            raise self.execute_error
        return Result(self.responses.pop(0))

    async def commit(self):
        self.commit_count += 1
        self.operations.append("commit")

    async def rollback(self):
        self.rollback_count += 1
        self.operations.append("rollback")


def compiled(statement) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))


@pytest.mark.asyncio
async def test_invalid_owner_or_document_fails_before_session_call() -> None:
    session = FakeSession()
    service = TodaySnapshotService(session)

    with pytest.raises(TypeError, match="user_id"):
        await service.publish_or_load("not-a-uuid", document())
    with pytest.raises(TypeError, match="document"):
        await service.publish_or_load(OWNER_ID, object())

    assert session.statements == []
    assert session.commit_count == 0


@pytest.mark.asyncio
async def test_publication_copies_all_typed_fields_and_json_values() -> None:
    value = document()
    session = FakeSession(responses=[SNAPSHOT_ID, row()])
    service = TodaySnapshotService(session)

    publication = await service.publish_or_load(OWNER_ID, value)

    assert isinstance(publication, TodaySnapshotPublication)
    assert publication.outcome == "published"
    assert publication.snapshot.id == SNAPSHOT_ID
    statement_sql = compiled(session.statements[0])
    assert "ON CONFLICT ON CONSTRAINT uq_today_snapshots_identity DO NOTHING" in statement_sql
    params = session.statements[0].compile(dialect=postgresql.dialect()).params
    assert params["user_id"] == OWNER_ID
    assert params["target_date"] == value.target_date
    assert params["timezone"] == value.timezone
    assert params["profile_hash"] == value.profile_hash
    assert params["input_hash"] == value.input_hash
    assert params["canon_hash"] == value.canon_hash
    assert params["formula_version"] == value.formula_version
    assert params["calculation_version"] == value.calculation_version
    assert params["ephemeris_artifact_id"] == value.ephemeris_artifact_id
    assert params["birth_time_mode"] == value.birth_time_mode
    assert params["birth_time_range"] == value.birth_time_range
    assert params["canonical_input_json"] == value.canonical_input_json
    assert params["deterministic_result_json"] == value.deterministic_result_json
    assert params["canonical_input_json"] is not value.canonical_input_json
    assert params["canonical_input_json"]["nested"] is not value.canonical_input_json["nested"]
    assert session.operations == ["execute", "execute", "commit"]


@pytest.mark.asyncio
async def test_conflict_returns_committed_winner_without_update_or_mutation() -> None:
    value = document()
    winner = row()
    session = FakeSession(responses=[None, winner])
    service = TodaySnapshotService(session)

    publication = await service.publish_or_load(OWNER_ID, value)

    assert publication.outcome == "conflict_reused"
    assert publication.snapshot is winner
    assert all("UPDATE" not in compiled(statement) for statement in session.statements)
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_logging_failure_does_not_change_committed_publication(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.today_snapshot_service.log_event",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("logging unavailable")),
    )
    session = FakeSession(responses=[SNAPSHOT_ID, row()])

    publication = await TodaySnapshotService(session).publish_or_load(OWNER_ID, document())

    assert publication.outcome == "published"
    assert publication.snapshot.id == SNAPSHOT_ID
    assert session.commit_count == 1
    assert session.rollback_count == 0


@pytest.mark.asyncio
async def test_owned_lookup_requires_owner_and_logs_hit_or_miss(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        "app.services.today_snapshot_service.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    hit_session = FakeSession(responses=[row()])
    hit = await TodaySnapshotService(hit_session).load_owned(OWNER_ID, SNAPSHOT_ID)
    miss_session = FakeSession(responses=[None])
    miss = await TodaySnapshotService(miss_session).load_owned(OTHER_OWNER_ID, SNAPSHOT_ID)

    assert hit is not None
    assert miss is None
    lookup_sql = compiled(hit_session.statements[0])
    assert "today_snapshots.id" in lookup_sql
    assert "today_snapshots.user_id" in lookup_sql
    assert [event[0] for event in events] == ["day.snapshot_lookup_hit", "day.snapshot_lookup_miss"]
    assert events[0][1]["payload"] == {"lookup": "owned_id"}
    assert events[1][1]["payload"] == {"lookup": "owned_id"}
    assert str(OWNER_ID) not in json.dumps(events)
    assert str(SNAPSHOT_ID) not in json.dumps(events)


@pytest.mark.asyncio
async def test_sqlalchemy_failure_rolls_back_and_logs_sanitized_error(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        "app.services.today_snapshot_service.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    db_error = OperationalError("INSERT secret statement", {}, RuntimeError("raw params"))
    session = FakeSession(execute_error=db_error)

    with pytest.raises(TodaySnapshotPersistenceError, match="today_snapshot:persistence"):
        await TodaySnapshotService(session).publish_or_load(OWNER_ID, document())

    assert session.rollback_count == 1
    error_events = [event for event in events if event[0] == "system.error"]
    assert len(error_events) == 1
    assert error_events[0][1]["error"] == {"type": "OperationalError"}
    assert "secret" not in json.dumps(error_events)
    assert "raw params" not in json.dumps(error_events)


@pytest.mark.asyncio
async def test_unexpected_non_sql_error_propagates(monkeypatch) -> None:
    session = FakeSession(execute_error=RuntimeError("programming bug"))

    with pytest.raises(RuntimeError, match="programming bug"):
        await TodaySnapshotService(session).publish_or_load(OWNER_ID, document())

    assert session.rollback_count == 0


def test_service_source_has_postgres_insert_without_check_update_retry_or_legacy_path() -> None:
    source = Path(__file__).resolve().parents[1].joinpath("app/services/today_snapshot_service.py").read_text(
        encoding="utf-8"
    )

    assert "on_conflict_do_nothing" in source
    assert "select(" in source
    assert "UPDATE" not in source
    assert "retry" not in source.lower()
    assert "today_service" not in source
    assert "llm" not in source.lower()


def test_snapshot_event_names_are_identical_in_xml_python_and_typescript() -> None:
    expected = {
        "day.snapshot_published",
        "day.snapshot_conflict_reused",
        "day.snapshot_lookup_hit",
        "day.snapshot_lookup_miss",
    }
    root = Path(__file__).resolve().parents[3]
    xml = (root / "grace/canon/observability.xml").read_text(encoding="utf-8")
    python = (root / "apps/api/app/core/logging_events.py").read_text(encoding="utf-8")
    typescript = (root / "lib/log/events.gen.ts").read_text(encoding="utf-8")

    assert all(f'name="{event}"' in xml for event in expected)
    assert all(f'"{event}"' in python for event in expected)
    assert all(f'"{event}"' in typescript for event in expected)
