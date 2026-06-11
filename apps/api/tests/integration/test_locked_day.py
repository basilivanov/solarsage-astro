
# ############################################################################
# AI_HEADER: MODULE_INTEGRATION_TEST_LOCKED_DAY
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Module — apps/api/tests/integration/test_locked_day.py
# owns:
#   - apps/api/tests/integration/test_locked_day.py
# inputs: varies
# outputs: varies
# dependencies: local modules
# side_effects: varies
# emitted_logs: n/a
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

# AI_HEADER
# module: M-TEST-LOCKED-DAY
# wave: W-ACCESS.3
# purpose: Integration tests for locked day preview payload

import pytest
from httpx import AsyncClient
from datetime import date, timedelta, timezone, datetime
from sqlalchemy.ext.asyncio import AsyncSession


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
async def test_locked_day_returns_preview(async_client: AsyncClient, make_initdata, db_session: AsyncSession):
    """
    W-ACCESS.3: Locked day returns preview payload.

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

    # W-ACCESS.3: Preview payload characteristics
    assert "подписке" in data["headline"].lower() or "доступен" in data["headline"].lower()
    assert len(data["topFlags"]) == 0  # No flags for preview
    assert data["dayStatus"] == "steady"  # Neutral status
    assert len(data["reading"]["paragraphs"]) > 0
    assert "подпишитесь" in data["reading"]["paragraphs"][0].lower()

    # Meta should indicate fresh generation (not cached)
    assert data["meta"]["cached"] is False


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

    # Full payload characteristics (not preview)
    assert "подписке" not in data["headline"].lower()
    # Should have real day_status (not just "steady")
    assert data["dayStatus"] in ["steady", "challenging", "favorable"]
    # Should have real reading (not preview text)
    assert "подпишитесь" not in data["reading"]["paragraphs"][0].lower()


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

    # Should be full payload (not preview)
    assert "подписке" not in data["headline"].lower()
