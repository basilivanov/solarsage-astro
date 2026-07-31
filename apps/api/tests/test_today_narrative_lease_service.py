# ############################################################################
# AI_HEADER: TEST_TODAY-NARRATIVE-LEASE-SERVICE — persistent narrative lease tests.
# ROLE: Proves validation, PostgreSQL transition intent, CAS completion, and
#       privacy-safe structured events for the single-flight narrative boundary.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-NARRATIVE-LEASE-SERVICE
# purpose: Validate the TodayNarrativeLeaseService without a real database.
# owns:
#   - apps/api/tests/test_today_narrative_lease_service.py
# inputs: UUIDs, aware UTC times, fake async sessions, and validated JSON objects.
# outputs: Focused evidence for lease transitions, CAS, rollback, and logs.
# dependencies: today_narrative_lease_service, TodaySnapshot, TodaySnapshotNarrative, PostgreSQL SQL compilation.
# side_effects: Fake session calls only; no database, provider, or network.
# emitted_logs: day.narrative_lease_acquired, day.narrative_lease_recovered,
#   day.narrative_lease_skipped, day.narrative_lease_completed,
#   day.narrative_lease_failed, system.error.
# invariants: no provider call, no public payload mutation, no UUID/content in logs.
# failure_policy: invalid inputs fail before SQL; SQLAlchemy failures rollback into
#   a stable persistence error; stale completion is a non-error outcome.
# END_MODULE_CONTRACT: M-TEST-TODAY-NARRATIVE-LEASE-SERVICE

# START_MODULE_MAP: M-TEST-TODAY-NARRATIVE-LEASE-SERVICE
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - INPUT_BOUNDARY: strict UUID/time/version/content validation.
#   - ACQUIRE_TRANSITIONS: insert, skip, recovery, retry, and rollback intent.
#   - COMPLETION_CAS: ready/unavailable completion and stale claim protection.
#   - LOGGING_AND_PRIVACY: exact events, payloads, and negative privacy assertions.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-NARRATIVE-LEASE-SERVICE

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import OperationalError

from app.db.models import TodaySnapshot, TodaySnapshotNarrative
from app.services.today_narrative_lease_service import (
    NarrativeLeaseClaim,
    NarrativeLeaseCompletion,
    NarrativeLeaseSkip,
    TodayNarrativeLeaseError,
    TodayNarrativeLeasePersistenceError,
    TodayNarrativeLeaseService,
)


SNAPSHOT_ID = UUID("33333333-3333-4333-8333-333333333333")
NARRATIVE_ID = UUID("44444444-4444-4444-8444-444444444444")
PROMPT_VERSION = "today-narrative-v1"
NOW = datetime(2026, 7, 31, 9, 0, tzinfo=timezone.utc)
DURATION = timedelta(minutes=5)


class Result:
    def __init__(self, value=None, *, rowcount: int | None = None):
        self.value = value
        self.rowcount = rowcount

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
        return self.responses.pop(0)

    async def commit(self):
        self.commit_count += 1
        self.operations.append("commit")

    async def rollback(self):
        self.rollback_count += 1
        self.operations.append("rollback")


def snapshot(*, published: bool = True) -> TodaySnapshot:
    return TodaySnapshot(id=SNAPSHOT_ID, published_at=NOW if published else None)


def narrative(
    status: str,
    *,
    content_json=None,
    attempt_count: int = 1,
    lease_until: datetime | None = NOW + DURATION,
    next_retry_at: datetime | None = None,
    last_error_code: str | None = None,
) -> TodaySnapshotNarrative:
    return TodaySnapshotNarrative(
        id=NARRATIVE_ID,
        snapshot_id=SNAPSHOT_ID,
        prompt_version=PROMPT_VERSION,
        status=status,
        content_json=content_json,
        attempt_count=attempt_count,
        lease_until=lease_until,
        next_retry_at=next_retry_at,
        last_error_code=last_error_code,
    )


def scalar(value) -> Result:
    return Result(value)


def compiled(statement) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("snapshot_id", "prompt_version", "now", "lease_duration"),
    [
        ("not-a-uuid", PROMPT_VERSION, NOW, DURATION),
        (SNAPSHOT_ID, "", NOW, DURATION),
        (SNAPSHOT_ID, "x" * 65, NOW, DURATION),
        (SNAPSHOT_ID, PROMPT_VERSION, datetime(2026, 7, 31, 9, 0), DURATION),
        (SNAPSHOT_ID, PROMPT_VERSION, NOW, timedelta(0)),
        (SNAPSHOT_ID, PROMPT_VERSION, NOW, timedelta(hours=1, seconds=1)),
    ],
)
async def test_acquire_rejects_invalid_boundary_values_before_sql(
    snapshot_id, prompt_version, now, lease_duration
) -> None:
    session = FakeSession()

    with pytest.raises((TypeError, ValueError)):
        await TodayNarrativeLeaseService(session).acquire(
            snapshot_id, prompt_version, now, lease_duration
        )

    assert session.statements == []
    assert session.commit_count == 0


@pytest.mark.asyncio
async def test_missing_or_unpublished_snapshot_does_not_create_narrative() -> None:
    for stored_snapshot in (None, snapshot(published=False)):
        session = FakeSession(responses=[scalar(stored_snapshot)])

        with pytest.raises(TodayNarrativeLeaseError, match="snapshot_not_published"):
            await TodayNarrativeLeaseService(session).acquire(
                SNAPSHOT_ID, PROMPT_VERSION, NOW, DURATION
            )

        assert len(session.statements) == 1
        assert session.rollback_count == 1


@pytest.mark.asyncio
async def test_new_snapshot_claim_is_created_with_attempt_one_and_exact_lease(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        "app.services.today_narrative_lease_service.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    session = FakeSession(responses=[scalar(snapshot()), scalar(NARRATIVE_ID)])

    result = await TodayNarrativeLeaseService(session).acquire(
        SNAPSHOT_ID, PROMPT_VERSION, NOW, DURATION
    )

    assert result == NarrativeLeaseClaim(
        narrative_id=NARRATIVE_ID,
        snapshot_id=SNAPSHOT_ID,
        prompt_version=PROMPT_VERSION,
        attempt_count=1,
        lease_until=NOW + DURATION,
        outcome="created",
    )
    params = session.statements[1].compile(dialect=postgresql.dialect()).params
    assert params["status"] == "pending"
    assert params["attempt_count"] == 1
    assert params["lease_until"] == NOW + DURATION
    assert "ON CONFLICT" in compiled(session.statements[1])
    assert events[0][0] == "day.narrative_lease_acquired"
    assert events[0][1]["payload"] == {"outcome": "created"}
    assert session.operations == ["execute", "execute", "commit"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("stored", "expected_status", "expected_reason", "expected_retry_at"),
    [
        (narrative("ready", content_json={"summary": "ok"}, lease_until=None), "ready", "ready", None),
        (narrative("pending", lease_until=NOW + DURATION), "pending", "in_flight", NOW + DURATION),
        (narrative("unavailable", lease_until=None, next_retry_at=NOW + DURATION, last_error_code="provider.timeout"), "unavailable", "cooldown", NOW + DURATION),
        (narrative("unavailable", lease_until=None, next_retry_at=None, last_error_code="provider.timeout"), "unavailable", "exhausted", None),
    ],
)
async def test_existing_ready_inflight_cooldown_and_exhausted_rows_skip(
    stored, expected_status, expected_reason, expected_retry_at
) -> None:
    session = FakeSession(responses=[scalar(snapshot()), scalar(None), scalar(stored)])

    result = await TodayNarrativeLeaseService(session).acquire(
        SNAPSHOT_ID, PROMPT_VERSION, NOW, DURATION
    )

    assert result == NarrativeLeaseSkip(
        narrative_id=NARRATIVE_ID,
        snapshot_id=SNAPSHOT_ID,
        prompt_version=PROMPT_VERSION,
        status=expected_status,
        reason=expected_reason,
        retry_at=expected_retry_at,
    )
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_expired_pending_row_is_recovered_with_attempt_increment() -> None:
    stored = narrative("pending", attempt_count=3, lease_until=NOW - timedelta(seconds=1))
    session = FakeSession(responses=[scalar(snapshot()), scalar(None), scalar(stored)])

    result = await TodayNarrativeLeaseService(session).acquire(
        SNAPSHOT_ID, PROMPT_VERSION, NOW, DURATION
    )

    assert result.outcome == "recovered"
    assert result.attempt_count == 4
    assert result.lease_until == NOW + DURATION
    assert stored.attempt_count == 4
    assert stored.lease_until == NOW + DURATION
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_due_unavailable_row_retries_and_clears_operational_fields() -> None:
    stored = narrative(
        "unavailable",
        attempt_count=2,
        lease_until=None,
        next_retry_at=NOW,
        last_error_code="provider.timeout",
    )
    session = FakeSession(responses=[scalar(snapshot()), scalar(None), scalar(stored)])

    result = await TodayNarrativeLeaseService(session).acquire(
        SNAPSHOT_ID, PROMPT_VERSION, NOW, DURATION
    )

    assert result.outcome == "retry"
    assert result.attempt_count == 3
    assert stored.status == "pending"
    assert stored.content_json is None
    assert stored.lease_until == NOW + DURATION
    assert stored.next_retry_at is None
    assert stored.last_error_code is None


@pytest.mark.asyncio
async def test_due_unavailable_corrupted_content_fails_closed_without_mutation_or_commit() -> None:
    stored = narrative(
        "unavailable",
        content_json={"corrupted": "content"},
        attempt_count=2,
        lease_until=None,
        next_retry_at=NOW,
        last_error_code="provider.timeout",
    )
    session = FakeSession(responses=[scalar(snapshot()), scalar(None), scalar(stored)])

    with pytest.raises(TodayNarrativeLeasePersistenceError, match="unavailable_content"):
        await TodayNarrativeLeaseService(session).acquire(
            SNAPSHOT_ID, PROMPT_VERSION, NOW, DURATION
        )

    assert stored.status == "unavailable"
    assert stored.content_json == {"corrupted": "content"}
    assert stored.attempt_count == 2
    assert stored.next_retry_at == NOW
    assert stored.last_error_code == "provider.timeout"
    assert session.commit_count == 0
    assert session.rollback_count == 1


@pytest.mark.asyncio
async def test_ready_completion_is_cas_and_stores_a_deep_copy(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        "app.services.today_narrative_lease_service.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    content = {"nested": {"value": [1, 2]}}
    claim = NarrativeLeaseClaim(
        NARRATIVE_ID, SNAPSHOT_ID, PROMPT_VERSION, 1, NOW + DURATION, "created"
    )
    session = FakeSession(responses=[Result(rowcount=1)])

    result = await TodayNarrativeLeaseService(session).complete_ready(claim, content)
    content["nested"]["value"].append(3)

    assert result == NarrativeLeaseCompletion(outcome="completed")
    params = session.statements[0].compile(dialect=postgresql.dialect()).params
    assert params["content_json"] == {"nested": {"value": [1, 2]}}
    assert params["status"] == "ready"
    assert "today_snapshot_narratives.status" in compiled(session.statements[0])
    assert events[0][0] == "day.narrative_lease_completed"
    assert events[0][1]["payload"] == {"outcome": "ready"}


@pytest.mark.asyncio
async def test_unavailable_completion_stores_null_content_and_stable_retry_fields() -> None:
    claim = NarrativeLeaseClaim(
        NARRATIVE_ID, SNAPSHOT_ID, PROMPT_VERSION, 1, NOW + DURATION, "created"
    )
    retry_at = NOW + timedelta(minutes=10)
    session = FakeSession(responses=[Result(rowcount=1)])

    result = await TodayNarrativeLeaseService(session, clock=lambda: NOW).complete_unavailable(
        claim, "provider.timeout", retry_at
    )

    assert result == NarrativeLeaseCompletion(outcome="completed")
    params = session.statements[0].compile(dialect=postgresql.dialect()).params
    assert params["content_json"] is None
    assert params["last_error_code"] == "provider.timeout"
    assert params["next_retry_at"] == retry_at


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content_json", "error_code", "next_retry_at"),
    [
        ([], "provider.timeout", NOW + timedelta(minutes=10)),
        ({"bad": object()}, "provider.timeout", NOW + timedelta(minutes=10)),
        ({"ok": True}, "Provider.Timeout", NOW + timedelta(minutes=10)),
        ({"ok": True}, "x" * 65, NOW + timedelta(minutes=10)),
        ({"ok": True}, "provider.timeout", datetime(2020, 1, 1, tzinfo=timezone.utc)),
        ({"ok": True}, "provider.timeout", datetime(2026, 7, 31, 9, 0)),
    ],
)
async def test_completion_rejects_invalid_content_error_or_retry_before_sql(
    content_json, error_code, next_retry_at
) -> None:
    claim = NarrativeLeaseClaim(
        NARRATIVE_ID, SNAPSHOT_ID, PROMPT_VERSION, 1, NOW + DURATION, "created"
    )
    session = FakeSession()
    service = TodayNarrativeLeaseService(session)

    if content_json != {"ok": True}:
        with pytest.raises((TypeError, ValueError)):
            await service.complete_ready(claim, content_json)
    else:
        with pytest.raises((TypeError, ValueError)):
            await service.complete_unavailable(claim, error_code, next_retry_at)

    assert session.statements == []


@pytest.mark.asyncio
async def test_recovery_retry_and_failure_events_use_exact_sanitized_payloads(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        "app.services.today_narrative_lease_service.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    expired = narrative("pending", lease_until=NOW - timedelta(seconds=1))
    recovered_session = FakeSession(responses=[scalar(snapshot()), scalar(None), scalar(expired)])
    recovered = await TodayNarrativeLeaseService(recovered_session).acquire(
        SNAPSHOT_ID, PROMPT_VERSION, NOW, DURATION
    )
    due = narrative("unavailable", lease_until=None, next_retry_at=NOW, last_error_code="provider.timeout")
    retry_session = FakeSession(responses=[scalar(snapshot()), scalar(None), scalar(due)])
    retry = await TodayNarrativeLeaseService(retry_session).acquire(
        SNAPSHOT_ID, PROMPT_VERSION, NOW, DURATION
    )
    failed_session = FakeSession(responses=[Result(rowcount=1)])
    await TodayNarrativeLeaseService(failed_session, clock=lambda: NOW).complete_unavailable(
        recovered, "provider.timeout", NOW + timedelta(minutes=10)
    )

    assert recovered.outcome == "recovered"
    assert retry.outcome == "retry"
    assert [(event, kwargs["payload"]) for event, kwargs in events] == [
        ("day.narrative_lease_recovered", {"outcome": "expired"}),
        ("day.narrative_lease_acquired", {"outcome": "retry"}),
        ("day.narrative_lease_failed", {"retry_scheduled": True}),
    ]
    assert str(SNAPSHOT_ID) not in json.dumps(events)
    assert "provider.timeout" not in json.dumps(events)


@pytest.mark.asyncio
async def test_stale_completion_is_non_mutating_and_sanitized(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        "app.services.today_narrative_lease_service.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    claim = NarrativeLeaseClaim(
        NARRATIVE_ID, SNAPSHOT_ID, PROMPT_VERSION, 1, NOW + DURATION, "created"
    )
    session = FakeSession(responses=[Result(rowcount=0)])

    result = await TodayNarrativeLeaseService(session).complete_ready(claim, {"secret": "content"})

    assert result == NarrativeLeaseCompletion(outcome="stale")
    assert events[0][0] == "system.error"
    assert events[0][1]["error"] == {"type": "narrative_lease_stale"}
    assert str(NARRATIVE_ID) not in json.dumps(events)
    assert "secret" not in json.dumps(events)


@pytest.mark.asyncio
async def test_ready_without_object_content_fails_closed() -> None:
    session = FakeSession(responses=[scalar(snapshot()), scalar(None), scalar(narrative("ready", content_json=None, lease_until=None))])

    with pytest.raises(TodayNarrativeLeasePersistenceError, match="ready_content"):
        await TodayNarrativeLeaseService(session).acquire(
            SNAPSHOT_ID, PROMPT_VERSION, NOW, DURATION
        )

    assert session.rollback_count == 1


@pytest.mark.asyncio
async def test_sqlalchemy_failure_rolls_back_with_stable_reason_and_no_raw_error(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        "app.services.today_narrative_lease_service.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    error = OperationalError("INSERT secret narrative", {}, RuntimeError("raw provider body"))
    session = FakeSession(execute_error=error)

    with pytest.raises(TodayNarrativeLeasePersistenceError, match="today_narrative_lease:persistence"):
        await TodayNarrativeLeaseService(session).acquire(
            SNAPSHOT_ID, PROMPT_VERSION, NOW, DURATION
        )

    assert session.rollback_count == 1
    assert events[0][0] == "system.error"
    assert events[0][1]["error"] == {"type": "OperationalError"}
    assert "secret" not in json.dumps(events)
    assert "raw provider body" not in json.dumps(events)
