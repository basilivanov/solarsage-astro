# ############################################################################
# AI_HEADER: TEST_TODAY-SPHERE-DRILLDOWN-API — deterministic sphere endpoint coverage.
# ROLE: Proves owner/full-access drilldown authorization, projection consistency,
#   deterministic ordering, and absence of narrative/LLM fields.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-SPHERE-DRILLDOWN-API
# purpose: Validate GET /api/day/snapshots/{id}/spheres/{key} at the HTTP boundary.
# owns:
#   - apps/api/tests/test_today_sphere_drilldown_api.py
# inputs: authenticated test sessions, snapshot rows, and access ledger rows.
# outputs: assertions for wire shape, access matrix, ownership, and consistency.
# dependencies: API router, drilldown service, Today projection, test DB fixtures.
# side_effects: isolated in-memory DB writes; no external calls.
# emitted_logs: none.
# invariants:
#   - foreign/missing snapshots are uniform 404;
#   - preview/locked requests never project evidence;
#   - response events equal the existing Today payload projection filtered by sphere.
# failure_policy: assertions fail closed on privacy or deterministic-wire drift.
# END_MODULE_CONTRACT: M-TEST-TODAY-SPHERE-DRILLDOWN-API

# START_MODULE_MAP: M-TEST-TODAY-SPHERE-DRILLDOWN-API
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - SNAPSHOT_FIXTURES: valid deterministic snapshot and factor ledger builders.
#   - HAPPY_PATH: owner/full-access wire consistency.
#   - ACCESS_MATRIX: preview/locked/ownership/path validation.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-SPHERE-DRILLDOWN-API

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AccessLedger, TodaySnapshot, User
from app.schemas.access import ContentAccessState
from app.services.today_convergence_projection import project_snapshot_payload


UTC = timezone.utc


async def _login(async_client: AsyncClient, make_initdata, user_id: int) -> None:
    response = await async_client.post(
        "/api/auth/telegram",
        json={"initData": make_initdata(user_id=user_id, username=f"drilldown_{user_id}")},
    )
    assert response.status_code == 200


def _factor(target_date: date, event_id: str, *, event_class: str, polarity: str) -> dict[str, object]:
    exact_at = datetime.combine(target_date, time(15, 40), tzinfo=UTC).isoformat()
    return {
        "canonical_event_id": event_id,
        "event_class": event_class,
        "technique_horizon": "today",
        "source_key": f"activation-{event_id}",
        "semantic_key": f"semantic-{event_id}",
        "driver_key": f"driver-{event_id}",
        "product_spheres": ["work", "documents"],
        "polarity": polarity,
        "evidence_level": "high" if event_id == "evt-1" else "medium",
        "exact_at": exact_at,
        "active_from": datetime.combine(target_date, time(13), tzinfo=UTC).isoformat(),
        "active_until": datetime.combine(target_date, time(18), tzinfo=UTC).isoformat(),
    }


def _snapshot(owner_id: UUID, target_date: date, *, snapshot_id: UUID | None = None) -> TodaySnapshot:
    snapshot_id = snapshot_id or uuid4()
    factors = [
        _factor(target_date, "evt-1", event_class="aspect", polarity="tense"),
        _factor(target_date, "evt-2", event_class="structural", polarity="mixed"),
    ]
    return TodaySnapshot(
        id=snapshot_id,
        user_id=owner_id,
        target_date=target_date,
        timezone="UTC",
        profile_hash="profile-hash",
        input_hash=snapshot_id.hex.ljust(64, "0"),
        canon_hash="canon-hash",
        formula_version="today-convergence-2",
        calculation_version="ss-calc-1.3.0",
        ephemeris_artifact_id="ephemeris-1",
        birth_time_mode="exact",
        birth_time_range={"start": "12:34", "end": "12:34"},
        deterministic_result_json={
            "schema_version": "today-deterministic-result.v1",
            "state": "convergence_today",
            "day_tone": "tense",
            "selected": {
                "convergences": [
                    {
                        "group_id": "cvg-drilldown",
                        "anchor_event_id": "evt-1",
                        "member_event_ids": ["evt-1", "evt-2"],
                        "evidence_event_ids": ["evt-1", "evt-2"],
                        "primary_sphere": "work",
                        "secondary_sphere": "documents",
                        "polarity": "tense",
                        "evidence_level": "high",
                    }
                ],
                "main_event": None,
                "impulses": [],
                "selected_unit_ids": ["evt-1", "evt-2"],
                "selected_spheres": ["work", "documents"],
            },
        },
        canonical_input_json={
            "birth_time": {
                "mode": "exact",
                "bucket": None,
                "range": {"start": "12:34", "end": "12:34"},
                "capabilities": {
                    "houses": True,
                    "angles": True,
                    "lots": True,
                    "exact_timing": True,
                },
            },
            "factor_units": factors,
        },
        published_at=datetime.combine(target_date, time(8), tzinfo=UTC),
    )


def _full_access(owner_id: UUID, target_date: date) -> AccessLedger:
    return AccessLedger(
        user_id=owner_id,
        entry_type="subscription",
        days_granted=30,
        start_date=target_date - timedelta(days=1),
        end_date=target_date + timedelta(days=30),
    )


# START_BLOCK: HAPPY_PATH
@pytest.mark.asyncio
async def test_drilldown_requires_authenticated_session(async_client: AsyncClient):
    response = await async_client.get(
        f"/api/day/snapshots/{uuid4()}/spheres/work",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_owner_full_drilldown_matches_today_projection_without_llm_fields(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
):
    await _login(async_client, make_initdata, 236001)
    owner = (await db_session.execute(select(User).where(User.tg_user_id == 236001))).scalar_one()
    target_date = date(2026, 7, 31)
    snapshot = _snapshot(owner.id, target_date)
    db_session.add_all([snapshot, _full_access(owner.id, target_date)])
    await db_session.commit()

    response = await async_client.get(
        f"/api/day/snapshots/{snapshot.id}/spheres/work",
    )

    assert response.status_code == 200
    data = response.json()
    access = ContentAccessState(
        state="full",
        reason="active_subscription",
        subscription_active=True,
        access_until=(target_date + timedelta(days=30)).isoformat(),
    )
    projected = project_snapshot_payload(snapshot, None, access)
    expected_events = [
        event.model_dump(mode="json", by_alias=True)
        for event in projected.events
        if event.sphere == "work"
    ]

    assert data["snapshotId"] == str(snapshot.id)
    assert data["sphere"] == "work"
    assert data["state"] == "convergence_today"
    assert data["dayTone"] == "tense"
    assert data["birthTimeMode"] == "exact"
    assert data["events"] == expected_events
    assert data["convergence"] == {
        "id": "cvg-drilldown",
        "primarySphere": "work",
        "secondarySphere": "documents",
        "polarity": "tense",
        "evidenceLevel": "high",
        "eventIds": ["evt-1", "evt-2"],
    }
    assert set(data) == {"snapshotId", "sphere", "state", "dayTone", "birthTimeMode", "events", "convergence"}
    assert all(set(event) == {"id", "kind", "sphere", "polarity", "evidenceLevel", "time", "sourceIds"} for event in data["events"])
    assert not any(key in data for key in ("summary", "meaning", "action", "narrative", "llm"))
# END_BLOCK: HAPPY_PATH


# START_BLOCK: ACCESS_MATRIX
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("target_date", "expected_reason"),
    [
        (date(2020, 1, 1), "preview"),
        (date(2099, 1, 1), "locked"),
    ],
)
async def test_drilldown_preview_and_locked_never_project_evidence(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
    target_date: date,
    expected_reason: str,
):
    await _login(async_client, make_initdata, 236002 if expected_reason == "preview" else 236003)
    tg_user_id = 236002 if expected_reason == "preview" else 236003
    owner = (await db_session.execute(select(User).where(User.tg_user_id == tg_user_id))).scalar_one()
    snapshot = _snapshot(owner.id, target_date)
    db_session.add(snapshot)
    await db_session.commit()

    with patch(
        "app.services.today_sphere_drilldown_service.project_snapshot_payload",
        side_effect=AssertionError("projection must not run without full access"),
    ):
        response = await async_client.get(
            f"/api/day/snapshots/{snapshot.id}/spheres/work",
        )

    assert response.status_code == 403
    assert response.json() == {"detail": {"code": "ACCESS_REQUIRED"}}
    assert expected_reason in {"preview", "locked"}


@pytest.mark.asyncio
async def test_drilldown_cross_user_and_missing_snapshot_are_uniform_404(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
):
    await _login(async_client, make_initdata, 236004)
    owner = (await db_session.execute(select(User).where(User.tg_user_id == 236004))).scalar_one()
    foreign = User(tg_user_id=236005, tg_username="foreign_drilldown")
    db_session.add(foreign)
    await db_session.flush()
    snapshot = _snapshot(foreign.id, date(2026, 7, 31))
    db_session.add(snapshot)
    await db_session.commit()

    foreign_response = await async_client.get(
        f"/api/day/snapshots/{snapshot.id}/spheres/work",
    )
    missing_response = await async_client.get(
        f"/api/day/snapshots/{uuid4()}/spheres/work",
    )

    assert foreign_response.status_code == 404
    assert missing_response.status_code == 404
    assert foreign_response.json() == missing_response.json()
    assert owner.id != foreign.id


@pytest.mark.asyncio
async def test_drilldown_rejects_invalid_and_unselected_spheres(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
):
    await _login(async_client, make_initdata, 236006)
    owner = (await db_session.execute(select(User).where(User.tg_user_id == 236006))).scalar_one()
    target_date = date(2026, 7, 31)
    snapshot = _snapshot(owner.id, target_date)
    db_session.add_all([snapshot, _full_access(owner.id, target_date)])
    await db_session.commit()

    invalid = await async_client.get(
        f"/api/day/snapshots/{snapshot.id}/spheres/not-a-sphere",
    )
    absent = await async_client.get(
        f"/api/day/snapshots/{snapshot.id}/spheres/money",
    )

    assert invalid.status_code == 422
    assert invalid.json() == {"detail": {"code": "INVALID_SPHERE"}}
    assert absent.status_code == 404
    assert absent.json() == {"detail": {"code": "SPHERE_NOT_IN_SNAPSHOT"}}
# END_BLOCK: ACCESS_MATRIX
