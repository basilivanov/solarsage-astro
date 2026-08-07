# ############################################################################
# AI_HEADER: TEST_CHECKIN_SNAPSHOT_LINEAGE — snapshot-linked check-in coverage.
# ROLE: Proves the W3 check-in wire, SQL selection, immutable lineage, and logs.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-CHECKIN-SNAPSHOT-LINEAGE
# purpose: Validate snapshot-linked evening check-in behavior at schema, service,
#   and authenticated API boundaries without changing snapshot/impression code.
# owns:
#   - apps/api/tests/test_checkin_snapshot_lineage.py
# inputs: Pydantic payloads, fake async sessions, and isolated API database rows.
# outputs: Validation, lineage, update, ordering, and structured-log evidence.
# dependencies: checkin schemas/service/API, TodaySnapshot and EveningCheckin models.
# side_effects: Isolated test database writes and captured log calls only.
# emitted_logs: checkin.lineage_bound, checkin.lineage_absent, checkin.lineage_preserved.
# invariants: client cannot provide lineage; owner/date and published impression SQL
#   predicates remain server-owned; edits never rebind lineage.
# failure_policy: assertions fail closed on contract or privacy drift.
# END_MODULE_CONTRACT: M-TEST-CHECKIN-SNAPSHOT-LINEAGE

# START_MODULE_MAP: M-TEST-CHECKIN-SNAPSHOT-LINEAGE
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - SCHEMA_BOUNDARY: CanonicalSphere validation and camelCase response fields.
#   - LINEAGE_SELECTION: owner/date/published snapshot selection and ordering.
#   - IMMUTABLE_UPDATE: edits preserve initial and legacy-null lineage.
#   - OBSERVABILITY: exact event names and payloads without identity data.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-CHECKIN-SNAPSHOT-LINEAGE

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EveningCheckin, TodaySnapshot, User
from app.schemas.checkin import CheckinCreate, CheckinResponse
from app.services.checkin_service import CheckinService


OWNER_ID = UUID("11111111-1111-4111-8111-111111111111")
SNAPSHOT_ID = UUID("22222222-2222-4222-8222-222222222222")
OTHER_SNAPSHOT_ID = UUID("33333333-3333-4333-8333-333333333333")
TARGET_DATE = date(2026, 7, 31)
UTC = timezone.utc


class Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return ScalarValues(self.value)


class ScalarValues:
    def __init__(self, value):
        self.value = value or []

    def all(self):
        return list(self.value)

    def __iter__(self):
        return iter(self.value)


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.statements = []
        self.commit_count = 0
        self.refreshed = []

    async def execute(self, statement):
        self.statements.append(statement)
        return Result(self.responses.pop(0))

    def add(self, value):
        return None

    async def commit(self):
        self.commit_count += 1

    async def refresh(self, value):
        self.refreshed.append(value)


def snapshot(
    owner_id: UUID = OWNER_ID,
    snapshot_id: UUID = SNAPSHOT_ID,
    *,
    first_day_seen_at: datetime | None = None,
    first_lookahead_seen_at: datetime | None = None,
    published_at: datetime | None = None,
    target_date: date = TARGET_DATE,
) -> TodaySnapshot:
    return TodaySnapshot(
        id=snapshot_id,
        user_id=owner_id,
        target_date=target_date,
        timezone="UTC",
        profile_hash="p" * 64,
        input_hash=str(snapshot_id).replace("-", "")[:64].ljust(64, "0"),
        canon_hash="c" * 64,
        formula_version="today-convergence-2",
        calculation_version="calc-1",
        ephemeris_artifact_id="artifact-1",
        birth_time_mode="exact",
        birth_time_range={"start": "14:30", "end": "14:30"},
        deterministic_result_json={
            "state": "quiet_day",
            "selected": {"spheres": ["work"]},
        },
        canonical_input_json={"target": target_date.isoformat()},
        first_day_seen_at=first_day_seen_at,
        first_lookahead_seen_at=first_lookahead_seen_at,
        published_at=published_at or datetime(2026, 7, 31, 8, tzinfo=UTC),
    )


def test_checkin_schema_accepts_all_canonical_spheres_null_and_empty() -> None:
    values = [
        "work", "finance", "documents", "relationships", "sport", "communication",
        "health", "home_family", "travel", "creativity", "study", "friends_goals",
    ]

    assert CheckinCreate(target_date=TARGET_DATE, mood=3, observed_spheres=values).observed_spheres == values
    assert CheckinCreate(target_date=TARGET_DATE, mood=3, observed_spheres=None).observed_spheres is None
    assert CheckinCreate(target_date=TARGET_DATE, mood=3, observed_spheres=[]).observed_spheres == []


@pytest.mark.parametrize(
    "observed_spheres",
    [
        ["unknown"],
        ["work", "work"],
        ["work"] * 13,
    ],
)
def test_checkin_schema_rejects_unknown_duplicate_or_oversized_spheres(observed_spheres) -> None:
    with pytest.raises(ValidationError):
        CheckinCreate(target_date=TARGET_DATE, mood=3, observed_spheres=observed_spheres)


def test_checkin_response_serializes_lineage_in_camel_case() -> None:
    value = CheckinResponse(
        id=1,
        target_date=TARGET_DATE,
        mood=3,
        tags=[],
        note=None,
        streak=1,
        filled_at=datetime(2026, 7, 31, 18, tzinfo=UTC),
        created_at=datetime(2026, 7, 31, 18, tzinfo=UTC),
        observed_spheres=["work"],
        forecast_snapshot_id=SNAPSHOT_ID,
        prediction_seen_at=datetime(2026, 7, 31, 9, tzinfo=UTC),
        prediction_seen_surface="day",
    )

    payload = value.model_dump(by_alias=True)
    assert payload["observedSpheres"] == ["work"]
    assert payload["forecastSnapshotId"] == SNAPSHOT_ID
    assert payload["predictionSeenAt"].tzinfo == UTC
    assert payload["predictionSeenSurface"] == "day"


@pytest.mark.asyncio
async def test_new_checkin_binds_day_snapshot_and_emits_exact_log(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        "app.services.checkin_service.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    candidate = snapshot(first_day_seen_at=datetime(2026, 7, 31, 9, tzinfo=UTC))
    session = FakeSession([None, [], candidate])

    row = await CheckinService(session).create_checkin(
        OWNER_ID, TARGET_DATE, 4, 2, 5, ["calm"], "note", ["work", "finance"]
    )

    assert row.forecast_snapshot_id == SNAPSHOT_ID
    assert row.prediction_seen_at == candidate.first_day_seen_at
    assert row.prediction_seen_surface == "day"
    assert row.observed_spheres == ["work", "finance"]
    assert events == [
        ("checkin.lineage_bound", {"msg": "checkin snapshot lineage", "payload": {"surface": "day"}})
    ]
    assert str(OWNER_ID) not in json.dumps(events, default=str)
    assert str(SNAPSHOT_ID) not in json.dumps(events, default=str)


@pytest.mark.asyncio
async def test_new_checkin_without_impression_keeps_null_lineage_and_logs_absent(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        "app.services.checkin_service.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    session = FakeSession([None, [], None, None])

    row = await CheckinService(session).create_checkin(
        OWNER_ID, TARGET_DATE, 3, None, None, [], None, None
    )

    assert row.forecast_snapshot_id is None
    assert row.prediction_seen_at is None
    assert row.prediction_seen_surface is None
    assert events == [
        ("checkin.lineage_absent", {"msg": "checkin snapshot lineage", "payload": {"reason": "no_impression"}})
    ]


@pytest.mark.asyncio
async def test_lineage_query_contains_owner_date_published_and_deterministic_ordering() -> None:
    candidate = snapshot(first_day_seen_at=datetime(2026, 7, 31, 9, tzinfo=UTC))
    session = FakeSession([None, [], candidate])

    await CheckinService(session).create_checkin(
        OWNER_ID, TARGET_DATE, 3, None, None, [], None, None
    )

    query = str(session.statements[2].compile(dialect=postgresql.dialect()))
    assert "today_snapshots.user_id" in query
    assert "today_snapshots.target_date" in query
    assert "today_snapshots.published_at IS NOT NULL" in query
    assert "today_snapshots.first_day_seen_at IS NOT NULL" in query
    assert "ORDER BY today_snapshots.first_day_seen_at DESC" in query
    assert "today_snapshots.id DESC" in query

    lookahead = snapshot(first_lookahead_seen_at=datetime(2026, 7, 31, 9, tzinfo=UTC))
    lookahead_session = FakeSession([None, [], None, lookahead])
    await CheckinService(lookahead_session).create_checkin(
        OWNER_ID, TARGET_DATE, 3, None, None, [], None, None
    )
    lookahead_query = str(lookahead_session.statements[3].compile(dialect=postgresql.dialect()))
    assert "today_snapshots.first_lookahead_seen_at IS NOT NULL" in lookahead_query
    assert "today_snapshots.first_lookahead_seen_at DESC" in lookahead_query


@pytest.mark.asyncio
async def test_update_preserves_lineage_updates_spheres_and_emits_preserved(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        "app.services.checkin_service.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    existing = EveningCheckin(
        id=1,
        user_id=OWNER_ID,
        target_date=TARGET_DATE,
        mood="good",
        mood_score=4,
        streak=1,
        forecast_snapshot_id=SNAPSHOT_ID,
        prediction_seen_at=datetime(2026, 7, 31, 9, tzinfo=UTC),
        prediction_seen_surface="day",
        observed_spheres=["work"],
    )
    session = FakeSession([existing, []])

    row = await CheckinService(session).create_checkin(
        OWNER_ID, TARGET_DATE, 5, 3, 4, [], "updated", ["finance"]
    )

    assert row.forecast_snapshot_id == SNAPSHOT_ID
    assert row.prediction_seen_surface == "day"
    assert row.observed_spheres == ["finance"]
    assert events == [
        ("checkin.lineage_preserved", {"msg": "checkin snapshot lineage", "payload": {"has_lineage": True}})
    ]


@pytest.mark.asyncio
async def test_legacy_null_lineage_stays_null_on_update(monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        "app.services.checkin_service.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    existing = EveningCheckin(
        id=1, user_id=OWNER_ID, target_date=TARGET_DATE, mood="neutral", mood_score=3, streak=1
    )
    session = FakeSession([existing, []])

    row = await CheckinService(session).create_checkin(
        OWNER_ID, TARGET_DATE, 2, 1, 2, [], None, []
    )

    assert row.forecast_snapshot_id is None
    assert row.prediction_seen_at is None
    assert row.prediction_seen_surface is None
    assert events[-1] == (
        "checkin.lineage_preserved",
        {"msg": "checkin snapshot lineage", "payload": {"has_lineage": False}},
    )


async def _login(async_client: AsyncClient, make_initdata, user_id: int) -> None:
    response = await async_client.post(
        "/api/auth/telegram",
        json={"initData": make_initdata(user_id=user_id, username=f"lineage_{user_id}")},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_lookahead_only_copies_timestamp_and_surface(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    await _login(async_client, make_initdata, 235001)
    owner = (await db_session.execute(select(User).where(User.tg_user_id == 235001))).scalar_one()
    seen_at = datetime(2026, 7, 31, 11, tzinfo=UTC)
    candidate = snapshot(owner.id, uuid4(), first_lookahead_seen_at=seen_at)
    db_session.add(candidate)
    await db_session.commit()

    response = await async_client.post(
        "/api/checkin",
        json={"targetDate": TARGET_DATE.isoformat(), "mood": 4, "observedSpheres": ["work"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["forecastSnapshotId"] == str(candidate.id)
    assert data["predictionSeenAt"] == seen_at.isoformat().replace("+00:00", "Z")
    assert data["predictionSeenSurface"] == "lookahead"


@pytest.mark.asyncio
async def test_api_day_has_priority_over_newer_lookahead_and_edit_does_not_rebind(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    await _login(async_client, make_initdata, 235002)
    owner = (await db_session.execute(select(User).where(User.tg_user_id == 235002))).scalar_one()
    day = snapshot(
        owner.id,
        UUID("44444444-4444-4444-8444-444444444444"),
        first_day_seen_at=datetime(2026, 7, 31, 9, tzinfo=UTC),
        published_at=datetime(2026, 7, 31, 8, tzinfo=UTC),
    )
    lookahead = snapshot(
        owner.id,
        UUID("55555555-5555-4555-8555-555555555555"),
        first_lookahead_seen_at=datetime(2026, 7, 31, 12, tzinfo=UTC),
        published_at=datetime(2026, 7, 31, 12, tzinfo=UTC),
    )
    db_session.add_all([day, lookahead])
    await db_session.commit()

    first = await async_client.post(
        "/api/checkin",
        json={"targetDate": TARGET_DATE.isoformat(), "mood": 3, "observedSpheres": []},
    )
    assert first.status_code == 200
    first_data = first.json()
    assert first_data["forecastSnapshotId"] == str(day.id)
    assert first_data["predictionSeenSurface"] == "day"

    newer = snapshot(
        owner.id,
        UUID("66666666-6666-4666-8666-666666666666"),
        first_day_seen_at=datetime(2026, 7, 31, 13, tzinfo=UTC),
        published_at=datetime(2026, 7, 31, 13, tzinfo=UTC),
    )
    db_session.add(newer)
    await db_session.commit()
    second = await async_client.post(
        "/api/checkin",
        json={"targetDate": TARGET_DATE.isoformat(), "mood": 5, "observedSpheres": ["finance"]},
    )

    assert second.status_code == 200
    second_data = second.json()
    assert second_data["forecastSnapshotId"] == first_data["forecastSnapshotId"]
    assert second_data["predictionSeenAt"] == first_data["predictionSeenAt"]
    assert second_data["predictionSeenSurface"] == "day"
    assert second_data["observedSpheres"] == ["finance"]


@pytest.mark.asyncio
async def test_api_legacy_null_lineage_is_not_backfilled_after_impression(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    await _login(async_client, make_initdata, 235003)
    owner = (await db_session.execute(select(User).where(User.tg_user_id == 235003))).scalar_one()
    legacy = EveningCheckin(
        user_id=owner.id,
        target_date=TARGET_DATE,
        mood="neutral",
        mood_score=3,
        streak=1,
    )
    db_session.add(legacy)
    await db_session.commit()
    candidate = snapshot(owner.id, uuid4(), first_day_seen_at=datetime(2026, 7, 31, 9, tzinfo=UTC))
    db_session.add(candidate)
    await db_session.commit()

    response = await async_client.post(
        "/api/checkin",
        json={"targetDate": TARGET_DATE.isoformat(), "mood": 4},
    )

    assert response.status_code == 200
    assert response.json()["forecastSnapshotId"] is None
    await db_session.refresh(legacy)
    assert legacy.forecast_snapshot_id is None


def test_packet_registry_and_grace_docs_contain_lineage_events() -> None:
    root = Path(__file__).parents[3]
    logging_events = (root / "apps/api/app/core/logging_events.py").read_text()
    frontend_events = (root / "lib/log/events.gen.ts").read_text()
    observability = (root / "grace/canon/observability.xml").read_text()
    for event in (
        "checkin.lineage_bound",
        "checkin.lineage_absent",
        "checkin.lineage_preserved",
    ):
        assert f'"{event}"' in logging_events
        assert f'| "{event}"' in frontend_events
        assert f'<event name="{event}" owner="W-TODAY-CONVERGENCE-W3"' in observability
