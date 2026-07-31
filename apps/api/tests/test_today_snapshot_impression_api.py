# ############################################################################
# AI_HEADER: TEST_API_TODAY-SNAPSHOT-IMPRESSION — authenticated impression endpoint.
# ROLE: Proves the packet-34 HTTP contract without importing legacy Today routes.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-API-TODAY-SNAPSHOT-IMPRESSION
# purpose: Validate authentication, strict request handling, 404 privacy, and 204 impression recording.
# owns:
#   - apps/api/tests/test_today_snapshot_impression_api.py
# inputs: AsyncClient, Telegram test auth, and isolated SQLite API fixture data.
# outputs: HTTP contract evidence for POST /api/day/snapshots/{id}/impression.
# dependencies: new Today convergence router, require_session, TodaySnapshot model.
# side_effects: Isolated test database writes only.
# emitted_logs: day.impression_recorded, day.impression_rejected.
# invariants: no user ID/time/date in request, no legacy route import, foreign/missing 404 is uniform.
# failure_policy: assertions fail when auth, validation, or public status contract drifts.
# END_MODULE_CONTRACT: M-TEST-API-TODAY-SNAPSHOT-IMPRESSION

# START_MODULE_MAP: M-TEST-API-TODAY-SNAPSHOT-IMPRESSION
# public_entrypoints:
#   - test_impression_requires_authenticated_session
#   - test_impression_accepts_strict_request_and_returns_204
#   - test_impression_malformed_body_is_422
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-API-TODAY-SNAPSHOT-IMPRESSION

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TodaySnapshot, User


def _snapshot(user_id, *, target_date: date) -> TodaySnapshot:
    return TodaySnapshot(
        id=uuid4(),
        user_id=user_id,
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
        deterministic_result_json={"state": "quiet_day"},
        canonical_input_json={"target": target_date.isoformat()},
    )


@pytest.mark.asyncio
async def test_impression_requires_authenticated_session(async_client) -> None:
    response = await async_client.post(
        f"/api/day/snapshots/{uuid4()}/impression",
        json={"surface": "day"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_impression_accepts_strict_request_and_returns_204(
    async_client,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    login = await async_client.post(
        "/api/auth/telegram",
        json={"initData": make_initdata(user_id=234501, username="snapshot_impression")},
    )
    assert login.status_code == 200
    user = (await db_session.execute(select(User).where(User.tg_user_id == 234501))).scalar_one()
    target_date = datetime.now(timezone.utc).date()
    snapshot = _snapshot(user.id, target_date=target_date)
    db_session.add(snapshot)
    await db_session.commit()

    response = await async_client.post(
        f"/api/day/snapshots/{snapshot.id}/impression",
        json={"surface": "day"},
    )

    assert response.status_code == 204
    await db_session.refresh(snapshot)
    assert snapshot.first_day_seen_at is not None


@pytest.mark.asyncio
async def test_impression_malformed_body_is_422(async_client, make_initdata) -> None:
    login = await async_client.post(
        "/api/auth/telegram",
        json={"initData": make_initdata(user_id=234502, username="snapshot_bad_body")},
    )
    assert login.status_code == 200

    response = await async_client.post(
        f"/api/day/snapshots/{uuid4()}/impression",
        json={"surface": "day", "userId": str(uuid4())},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_impression_missing_foreign_and_invalid_relations_are_uniform_404(
    async_client,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    login = await async_client.post(
        "/api/auth/telegram",
        json={"initData": make_initdata(user_id=234503, username="snapshot_404")},
    )
    assert login.status_code == 200
    owner = (await db_session.execute(select(User).where(User.tg_user_id == 234503))).scalar_one()
    foreign = User(tg_user_id=234504)
    db_session.add(foreign)
    await db_session.flush()

    today = datetime.now(timezone.utc).date()
    foreign_snapshot = _snapshot(foreign.id, target_date=today)
    stale_snapshot = _snapshot(owner.id, target_date=today - timedelta(days=1))
    source = _snapshot(owner.id, target_date=today)
    invalid_target = _snapshot(owner.id, target_date=today)
    invalid_target.input_hash = "x" * 64
    db_session.add_all([foreign_snapshot, stale_snapshot, source, invalid_target])
    await db_session.commit()
    foreign_snapshot_id = foreign_snapshot.id
    stale_snapshot_id = stale_snapshot.id
    source_id = source.id
    invalid_target_id = invalid_target.id

    responses = [
        await async_client.post(f"/api/day/snapshots/{uuid4()}/impression", json={"surface": "day"}),
        await async_client.post(f"/api/day/snapshots/{foreign_snapshot_id}/impression", json={"surface": "day"}),
        await async_client.post(f"/api/day/snapshots/{stale_snapshot_id}/impression", json={"surface": "day"}),
        await async_client.post(
            f"/api/day/snapshots/{invalid_target_id}/impression",
            json={"surface": "lookahead", "sourceSnapshotId": str(source_id)},
        ),
    ]

    assert [response.status_code for response in responses] == [404, 404, 404, 404]
    assert all(
        response.json()["detail"] == {"code": "SNAPSHOT_NOT_FOUND", "message": "Snapshot not found"}
        for response in responses
    )
