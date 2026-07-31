# ############################################################################
# AI_HEADER: TEST_TODAY_DAY_HISTORY_API — published snapshot history API coverage.
# ROLE: Proves history ownership, ordering, access gating, and compact wire shape.
# ############################################################################

# START_MODULE_CONTRACT: TEST-TODAY-DAY-HISTORY-API
# purpose: Verify GET /api/readings/day-history for the P4-D3A contract.
# owns:
#   - apps/api/tests/test_today_day_history_api.py
# inputs: authenticated test users and TodaySnapshot rows in the in-memory DB.
# outputs: published-only, descending-order, bounded-limit, locked-access, and
#   no-cold-calculation evidence.
# dependencies: M-API-READINGS, M-TODAY-DAY-HISTORY, TodaySnapshot, test fixtures.
# side_effects: in-memory database writes and mocked access/external boundaries.
# emitted_logs: none (test harness).
# invariants: item keys are exactly the compact history contract; legacy fields absent.
# failure_policy: assertion failure blocks the Readings history slice.
# END_MODULE_CONTRACT: TEST-TODAY-DAY-HISTORY-API

# START_MODULE_MAP: TEST-TODAY-DAY-HISTORY-API
# public_entrypoints:
#   - test_day_history_requires_auth
#   - test_day_history_published_heads_are_descending_and_compact
#   - test_day_history_default_limit_and_validation
#   - test_day_history_locked_access_hides_items
# semantic_blocks:
#   - AUTH_REQUIRED: session boundary.
#   - SNAPSHOT_INDEX: ownership, published heads, order, and wire fields.
#   - LIMIT_VALIDATION: default and 1..60 bounds.
#   - LOCKED_ACCESS: empty history with access projection.
# owned_tests:
#   - self
# END_MODULE_MAP: TEST-TODAY-DAY-HISTORY-API

from __future__ import annotations

from datetime import UTC, date as Date, datetime, timedelta
from hashlib import sha256
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TodaySnapshot, User


NOW = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)


# START_BLOCK: TEST_DATA
async def _login_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
    user_id: int,
) -> User:
    response = await async_client.post(
        "/api/auth/telegram",
        json={"initData": make_initdata(user_id=user_id)},
    )
    assert response.status_code == 200
    return (
        await db_session.execute(select(User).where(User.tg_user_id == user_id))
    ).scalar_one()


def _snapshot(
    user_id,
    target_date: Date,
    *,
    state: str = "quiet_day",
    day_tone: str = "steady",
    spheres: list[str] | None = None,
    impulses: list[dict[str, str]] | None = None,
    supersedes_snapshot_id=None,
) -> TodaySnapshot:
    snapshot_id = uuid4()
    return TodaySnapshot(
        id=snapshot_id,
        user_id=user_id,
        target_date=target_date,
        timezone="UTC",
        profile_hash="p" * 64,
        input_hash=sha256(f"{snapshot_id}:{target_date}".encode()).hexdigest(),
        canon_hash="c" * 64,
        formula_version="today-convergence-2",
        calculation_version="calc-1",
        ephemeris_artifact_id="artifact-1",
        birth_time_mode="exact",
        birth_time_range={"start": "14:30", "end": "14:30"},
        deterministic_result_json={
            "state": state,
            "day_tone": day_tone,
            "selected": {
                "selected_spheres": spheres or [],
                "impulses": impulses or [],
            },
        },
        canonical_input_json={"target_date": target_date.isoformat()},
        published_at=NOW,
        supersedes_snapshot_id=supersedes_snapshot_id,
    )
# END_BLOCK: TEST_DATA


# START_BLOCK: AUTH_REQUIRED
@pytest.mark.asyncio
async def test_day_history_requires_auth(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/readings/day-history")
    assert response.status_code == 401
# END_BLOCK: AUTH_REQUIRED


# START_BLOCK: SNAPSHOT_INDEX
@pytest.mark.asyncio
async def test_day_history_published_heads_are_descending_and_compact(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    user = await _login_user(async_client, db_session, make_initdata, user_id=8800)
    other_user = User(tg_user_id=8801)
    db_session.add(other_user)
    await db_session.flush()

    parent = _snapshot(user.id, Date(2026, 7, 30), state="quiet_day")
    child = _snapshot(
        user.id,
        Date(2026, 7, 30),
        state="convergence_today",
        day_tone="supportive",
        spheres=["work", "decisions", "money"],
        impulses=[{"event_id": "one"}, {"event_id": "two"}],
        supersedes_snapshot_id=parent.id,
    )
    older = _snapshot(user.id, Date(2026, 7, 29), state="quiet_day", day_tone="mixed")
    foreign = _snapshot(other_user.id, Date(2026, 7, 31), state="convergence_today")
    db_session.add_all([parent, child, older, foreign])
    await db_session.commit()

    response = await async_client.get("/api/readings/day-history?limit=10")
    assert response.status_code == 200
    payload = response.json()

    assert payload["access"]["state"] == "preview"
    assert [item["date"] for item in payload["items"]] == ["2026-07-30", "2026-07-29"]
    assert payload["items"][0]["snapshotId"] == str(child.id)
    assert payload["items"][0]["state"] == "convergence_today"
    assert payload["items"][0]["dayTone"] == "supportive"
    assert payload["items"][0]["sphereKeys"] == ["work", "decisions", "money"]
    assert payload["items"][0]["impulseCount"] == 2
    assert set(payload["items"][0]) == {
        "date",
        "snapshotId",
        "state",
        "dayTone",
        "sphereKeys",
        "impulseCount",
    }
    assert "reading" not in payload["items"][0]
    assert "dayStatus" not in payload["items"][0]
# END_BLOCK: SNAPSHOT_INDEX


# START_BLOCK: LIMIT_VALIDATION
@pytest.mark.asyncio
async def test_day_history_default_limit_and_validation(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    user = await _login_user(async_client, db_session, make_initdata, user_id=8802)
    db_session.add_all(
        [
            _snapshot(user.id, Date(2026, 7, 1) + timedelta(days=index))
            for index in range(16)
        ]
    )
    await db_session.commit()

    default_response = await async_client.get("/api/readings/day-history")
    assert default_response.status_code == 200
    assert len(default_response.json()["items"]) == 14

    for value in ("0", "61", "-1"):
        response = await async_client.get(f"/api/readings/day-history?limit={value}")
        assert response.status_code == 422

    capped_response = await async_client.get("/api/readings/day-history?limit=60")
    assert capped_response.status_code == 200
    assert len(capped_response.json()["items"]) == 16
# END_BLOCK: LIMIT_VALIDATION


# START_BLOCK: LOCKED_ACCESS
@pytest.mark.asyncio
async def test_day_history_locked_access_hides_items(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    user = await _login_user(async_client, db_session, make_initdata, user_id=8803)
    db_session.add(_snapshot(user.id, Date(2026, 7, 30)))
    await db_session.commit()

    from app.schemas.access import ContentAccessState
    from app.services.access_service import AccessService

    access_check = AsyncMock(
        return_value=ContentAccessState(
            state="locked",
            reason="outside_access_window",
        )
    )
    with patch.object(AccessService, "can_access_day", access_check), \
        patch("app.clients.solarsage_client.get_solarsage_client", side_effect=AssertionError("sidecar")), \
        patch("app.services.today_service.TodayService", side_effect=AssertionError("today service")):
        response = await async_client.get("/api/readings/day-history")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["access"]["state"] == "locked"
    access_check.assert_awaited_once()
# END_BLOCK: LOCKED_ACCESS
