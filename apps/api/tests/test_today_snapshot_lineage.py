# ############################################################################
# AI_HEADER: TEST_TODAY-SNAPSHOT-LINEAGE — deterministic supersession and impression contracts.
# ROLE: RED/GREEN unit coverage for packet-34 service, schema, migration, and event boundaries.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-SNAPSHOT-LINEAGE
# purpose: Prove packet-34 lineage and impression behavior without a database.
# owns:
#   - apps/api/tests/test_today_snapshot_lineage.py
# inputs: Typed snapshot documents, fake async sessions, and canonical source files.
# outputs: Unit evidence for supersession, impressions, strict inputs, migration, and logs.
# dependencies: today_snapshot_service, today_convergence_snapshot, Pydantic, packet-34 registries.
# side_effects: Fake session calls only; no database or network.
# emitted_logs: day.snapshot_superseded, day.impression_recorded, day.impression_rejected.
# invariants: no raw IDs/log payloads, no SQLite lineage proof, no legacy imports.
# failure_policy: assertions fail closed when packet-34 surfaces are absent or incorrect.
# END_MODULE_CONTRACT: M-TEST-TODAY-SNAPSHOT-LINEAGE

# START_MODULE_MAP: M-TEST-TODAY-SNAPSHOT-LINEAGE
# public_entrypoints:
#   - test_superseding_publication_preserves_parent_and_document
#   - test_superseding_publication_rejects_naive_observed_at_before_sql
#   - test_impression_records_and_repeats_without_overwriting
#   - test_impression_rejects_invalid_surface_relation_without_sql
#   - test_event_registry_and_migration_revision_are_packet_34_complete
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-SNAPSHOT-LINEAGE

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy.dialects import postgresql

from app.db.models import TodaySnapshot
from app.schemas.today_convergence import TodaySnapshotImpressionRequest
from app.services.today_convergence_snapshot import TodayConvergenceSnapshotDocument
from app.services.today_snapshot_service import (
    TodaySnapshotImpression,
    TodaySnapshotService,
)


OWNER_ID = UUID("11111111-1111-4111-8111-111111111111")
PARENT_ID = UUID("22222222-2222-4222-8222-222222222222")
CHILD_ID = UUID("33333333-3333-4333-8333-333333333333")
SEEN_AT = datetime(2026, 7, 31, 9, 0, tzinfo=timezone.utc)


def document(*, target_date: date = date(2026, 7, 31), state: str = "quiet_day") -> TodayConvergenceSnapshotDocument:
    return TodayConvergenceSnapshotDocument(
        target_date=target_date,
        timezone="UTC",
        profile_hash="p" * 64,
        input_hash="i" * 64,
        canon_hash="c" * 64,
        formula_version="formula-1",
        calculation_version="calc-1",
        ephemeris_artifact_id="artifact-1",
        birth_time_mode="exact",
        birth_time_range={"start": "14:30", "end": "14:30"},
        canonical_input_json={"target": target_date.isoformat()},
        deterministic_result_json={"state": state, "selected": {"convergences": []}},
    )


def row(
    *,
    snapshot_id: UUID,
    owner_id: UUID = OWNER_ID,
    target_date: date = date(2026, 7, 31),
    first_day_seen_at: datetime | None = None,
    first_lookahead_seen_at: datetime | None = None,
    state: str = "quiet_day",
    supersedes_snapshot_id: UUID | None = None,
) -> TodaySnapshot:
    value = document(target_date=target_date, state=state)
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
        first_day_seen_at=first_day_seen_at,
        first_lookahead_seen_at=first_lookahead_seen_at,
        supersedes_snapshot_id=supersedes_snapshot_id,
    )


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def first(self):
        if isinstance(self.value, list):
            return self.value[0] if self.value else None
        return self.value


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.statements = []
        self.commit_count = 0
        self.rollback_count = 0

    async def execute(self, statement):
        self.statements.append(statement)
        return Result(self.responses.pop(0))

    async def commit(self):
        self.commit_count += 1

    async def rollback(self):
        self.rollback_count += 1


@pytest.mark.asyncio
async def test_superseding_publication_preserves_parent_and_document() -> None:
    parent = row(snapshot_id=PARENT_ID)
    child = row(snapshot_id=CHILD_ID, supersedes_snapshot_id=PARENT_ID)
    session = FakeSession([parent, None, CHILD_ID, child])

    publication = await TodaySnapshotService(session).publish_superseding(
        OWNER_ID,
        document(),
        PARENT_ID,
        observed_at=SEEN_AT,
    )

    assert publication.snapshot is child
    assert publication.snapshot.supersedes_snapshot_id == PARENT_ID
    assert publication.outcome in {"published", "conflict_reused"}
    insert_sql = str(session.statements[2].compile(dialect=postgresql.dialect()))
    assert "supersedes_snapshot_id" in insert_sql


@pytest.mark.asyncio
async def test_superseding_publication_rejects_naive_observed_at_before_sql() -> None:
    session = FakeSession([])

    with pytest.raises(TypeError, match="aware"):
        await TodaySnapshotService(session).publish_superseding(
            OWNER_ID,
            document(),
            PARENT_ID,
            observed_at=datetime(2026, 7, 31, 9, 0),
        )

    assert session.statements == []


@pytest.mark.asyncio
async def test_plain_conflict_log_payload_is_exact(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        "app.services.today_snapshot_service.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )

    await TodaySnapshotService(FakeSession([None, row(snapshot_id=PARENT_ID)])).publish_or_load(
        OWNER_ID,
        document(),
    )

    assert events[-1] == (
        "day.snapshot_conflict_reused",
        {
            "msg": "today snapshot boundary",
            "payload": {"state": "quiet_day", "birth_time_mode": "exact"},
            "error": None,
        },
    )


@pytest.mark.asyncio
async def test_supersession_reuse_log_payload_is_exact(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        "app.services.today_snapshot_service.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    child = row(snapshot_id=CHILD_ID, supersedes_snapshot_id=PARENT_ID)

    await TodaySnapshotService(FakeSession([row(snapshot_id=PARENT_ID), child])).publish_superseding(
        OWNER_ID,
        document(),
        PARENT_ID,
        observed_at=SEEN_AT,
    )

    assert events[-1] == (
        "day.snapshot_superseded",
        {
            "msg": "today snapshot boundary",
            "payload": {"outcome": "conflict_reused"},
            "error": None,
        },
    )


@pytest.mark.asyncio
async def test_impression_records_and_repeats_without_overwriting() -> None:
    original = datetime(2026, 7, 31, 9, 0, tzinfo=timezone.utc)
    current = row(snapshot_id=CHILD_ID, first_day_seen_at=original)
    update_result = (CHILD_ID, SEEN_AT)
    session = FakeSession([current, update_result, current, None, current])

    first = await TodaySnapshotService(session).record_impression(
        OWNER_ID,
        CHILD_ID,
        "day",
        observed_at=SEEN_AT,
    )
    repeat = await TodaySnapshotService(session).record_impression(
        OWNER_ID,
        CHILD_ID,
        "day",
        observed_at=SEEN_AT,
    )

    assert isinstance(first, TodaySnapshotImpression)
    assert first.outcome == "recorded"
    assert repeat is not None and repeat.outcome == "existing"
    assert repeat.seen_at == original


@pytest.mark.asyncio
async def test_impression_rejects_invalid_surface_relation_without_sql() -> None:
    session = FakeSession([])

    result = await TodaySnapshotService(session).record_impression(
        OWNER_ID,
        CHILD_ID,
        "day",
        source_snapshot_id=PARENT_ID,
        observed_at=SEEN_AT,
    )

    assert result is None
    assert session.statements == []


@pytest.mark.asyncio
async def test_impression_missing_snapshot_or_source_rolls_back() -> None:
    missing_snapshot_session = FakeSession([None])
    assert (
        await TodaySnapshotService(missing_snapshot_session).record_impression(
            OWNER_ID, CHILD_ID, "day", observed_at=SEEN_AT
        )
        is None
    )
    assert missing_snapshot_session.rollback_count == 1

    missing_source_session = FakeSession([row(snapshot_id=CHILD_ID), None])
    assert (
        await TodaySnapshotService(missing_source_session).record_impression(
            OWNER_ID,
            CHILD_ID,
            "lookahead",
            source_snapshot_id=PARENT_ID,
            observed_at=SEEN_AT,
        )
        is None
    )
    assert missing_source_session.rollback_count == 1


def test_event_registry_and_migration_revision_are_packet_34_complete() -> None:
    root = Path(__file__).resolve().parents[3]
    migration = root / "apps/api/alembic/versions/0029_today_snapshot_lineage_guards.py"
    assert migration.exists()
    source = migration.read_text(encoding="utf-8")
    revision = "0029_today_snapshot_lineage"
    assert f'revision = "{revision}"' in source
    assert len(revision) <= 32
    assert 'down_revision = "0028_today_convergence_snapshots"' in source
    assert "CREATE TRIGGER" in source
    assert "CREATE OR REPLACE FUNCTION" in source
    assert "DROP TRIGGER" in source

    expected = {
        "day.snapshot_superseded",
        "day.impression_recorded",
        "day.impression_rejected",
    }
    for path in (
        root / "grace/canon/observability.xml",
        root / "apps/api/app/core/logging_events.py",
        root / "lib/log/events.gen.ts",
    ):
        text = path.read_text(encoding="utf-8")
        assert all(event in text for event in expected)


def test_impression_request_is_camel_case_strict() -> None:
    request = TodaySnapshotImpressionRequest.model_validate(
        {"surface": "lookahead", "sourceSnapshotId": str(PARENT_ID)}
    )
    assert request.source_snapshot_id == PARENT_ID
    with pytest.raises(ValueError):
        TodaySnapshotImpressionRequest.model_validate({"surface": "day", "extra": True})
