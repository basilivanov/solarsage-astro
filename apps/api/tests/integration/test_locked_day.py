
# ############################################################################
# AI_HEADER: MODULE_INTEGRATION_TEST_LOCKED_DAY
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for locked_day.py behavior
# owns:
#   - apps/api/tests/integration/test_locked_day.py
# inputs: Query params, models
# outputs: Records / query results
# dependencies: local modules
# side_effects: Database reads/writes; Network calls to API
# emitted_logs: n/a (tests)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# AI_HEADER
# module: M-TEST-LOCKED-DAY
# wave: W-ACCESS.3
# purpose: Integration tests for locked day preview payload

import pytest
from httpx import AsyncClient
from datetime import timedelta, timezone, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.today_convergence import TodayConvergencePayload


def _parse_convergence_payload(data: dict) -> TodayConvergencePayload:
    """Validate the public sphere/facet convergence envelope, not legacy Today."""
    assert "headline" not in data
    assert "reading" not in data
    assert "dayStatus" not in data
    return TodayConvergencePayload.model_validate(data)


async def _onboard_user(async_client: AsyncClient, db_session: AsyncSession, make_initdata, user_id: int):
    """Helper: login and create onboarded profile."""
    from app.db.models import User, UserProfile
    from sqlalchemy import select, update

    # Login
    raw = make_initdata(user_id=user_id)
    await async_client.post("/api/auth/telegram", json={"initData": raw})

    # Create profile with birth data
    await async_client.put("/api/profile", json={
        "firstName": "Test User",
        "gender": "male",
        "birth": {
            "birthday": "1990-01-15",
            "birthTime": "14:30:00",
            "birthTimeMode": "exact",
            "birthCity": "Moscow",
            "birthLat": 55.7558,
            "birthLon": 37.6173,
            "birthTz": "Europe/Moscow"
        }
    })

    # Set is_onboarded=True
    stmt = select(User).where(User.tg_user_id == user_id)
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        stmt = update(UserProfile).where(UserProfile.user_id == user.id).values(is_onboarded=True)
        await db_session.execute(stmt)
        await db_session.commit()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_locked_day_returns_locked_envelope(async_client: AsyncClient, make_initdata, db_session: AsyncSession):
    """
    W-ACCESS.3: Locked day returns the new empty convergence envelope.

    Test that days beyond referral bonus (day 15+) return locked preview.
    """
    # Signup + onboard
    await _onboard_user(async_client, db_session, make_initdata, user_id=7777)

    # Request day beyond referral bonus (day 20)
    future_date = (datetime.now(timezone.utc).date() + timedelta(days=20)).isoformat()

    response = await async_client.get(f"/api/day/{future_date}")
    assert response.status_code == 200

    data = response.json()

    # W-ACCESS.3: Should be locked
    assert data["access"]["state"] == "locked"
    assert data["access"]["reason"] == "outside_access_window"

    payload = _parse_convergence_payload(data)
    assert payload.state is None
    assert payload.content_state == "not_needed"
    assert payload.snapshot_id is None
    assert payload.convergences == []
    assert payload.events == []


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_access_day_returns_full_payload(async_client: AsyncClient, make_initdata, db_session: AsyncSession):
    """
    W-ACCESS.3: Full access day returns full payload (not preview).

    Test that days within referral bonus return full content.
    """
    from app.services.access_service import AccessService
    from sqlalchemy import select
    from app.db.models import User

    # Signup + onboard
    await _onboard_user(async_client, db_session, make_initdata, user_id=8888)

    # Get user and grant referral bonus
    result = await db_session.execute(select(User).where(User.tg_user_id == 8888))
    user = result.scalar_one()

    access_service = AccessService(db_session)
    await access_service.grant_referral_bonus(user.id, datetime.now(timezone.utc).date())

    # Request today (within referral bonus)
    response = await async_client.get("/api/day/today")
    assert response.status_code == 200

    data = response.json()

    # Should have full access
    assert data["access"]["state"] == "full"
    assert data["access"]["reason"] == "active_referral_days"

    payload = _parse_convergence_payload(data)
    assert payload.access.state == "full"
    if payload.content_state == "unavailable":
        assert payload.state == "unavailable"
        assert payload.snapshot_id is None
    else:
        assert payload.state in {"convergence_today", "quiet_day"}


@pytest.mark.asyncio
@pytest.mark.integration
async def test_locked_day_with_subscription(async_client: AsyncClient, make_initdata, db_session: AsyncSession):
    """
    W-ACCESS.3: Locked day becomes full access with subscription.

    Test that subscription grants access to locked days.
    """
    from app.services.access_service import AccessService
    from sqlalchemy import select
    from app.db.models import User

    # Signup + onboard
    await _onboard_user(async_client, db_session, make_initdata, user_id=9999)

    # Get user
    result = await db_session.execute(select(User).where(User.tg_user_id == 9999))
    user = result.scalar_one()

    # Grant subscription (365 days)
    access_service = AccessService(db_session)
    await access_service.grant_subscription(
        user.id,
        start_date=datetime.now(timezone.utc).date(),
        days=365
    )

    # Request day far in future (day 100)
    future_date = (datetime.now(timezone.utc).date() + timedelta(days=100)).isoformat()

    response = await async_client.get(f"/api/day/{future_date}")
    assert response.status_code == 200

    data = response.json()

    # Should have full access due to subscription
    assert data["access"]["state"] == "full"
    assert data["access"]["reason"] == "active_subscription"
    assert data["access"]["subscriptionActive"] is True

    payload = _parse_convergence_payload(data)
    assert payload.access.state == "full"
    if payload.content_state == "unavailable":
        assert payload.state == "unavailable"
    else:
        assert payload.state in {"convergence_today", "quiet_day"}
