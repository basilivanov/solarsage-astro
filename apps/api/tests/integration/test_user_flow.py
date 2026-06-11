
# ############################################################################
# AI_HEADER: MODULE_INTEGRATION_TEST_USER_FLOW
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Module — apps/api/tests/integration/test_user_flow.py
# owns:
#   - apps/api/tests/integration/test_user_flow.py
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
# module: M-TEST-INTEGRATION-USER-FLOW
# wave: W-TEST-1
# purpose: Integration tests for complete user flows

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
async def test_complete_user_flow(async_client: AsyncClient, make_initdata, db_session: AsyncSession):
    """
    Complete user flow: signup → onboard → day view → referral claim.
    """
    # Step 1 & 2: Signup + onboard
    await _onboard_user(async_client, db_session, make_initdata, user_id=7777)

    # Step 3: View today (should work but show preview - no access yet)
    response = await async_client.get("/api/day/today")
    assert response.status_code == 200
    data = response.json()
    assert "headline" in data
    assert "reading" in data
    # Access should be preview (no referral/subscription yet)
    assert data["access"]["state"] == "preview"

    # Step 4: Create referrer
    await _onboard_user(async_client, db_session, make_initdata, user_id=8888)

    # Step 5: Claim referral (back to original user)
    user_raw = make_initdata(user_id=7777, username="testuser")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})
    response = await async_client.post("/api/referral/claim", json={
        "referrer_code": "8888"
    })
    assert response.status_code == 200
    assert response.json()["days_granted"] == 14

    # Step 6: View today again (should have full access now)
    response = await async_client.get("/api/day/today")
    assert response.status_code == 200
    data = response.json()
    assert data["access"]["state"] == "full"
    assert data["access"]["referralDaysLeft"] is not None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_calendar_navigation_flow(async_client: AsyncClient, make_initdata, db_session: AsyncSession):
    """
    Calendar navigation flow: signup → onboard → calendar → day view.
    """
    # Signup + onboard
    await _onboard_user(async_client, db_session, make_initdata, user_id=9999)

    # View calendar
    response = await async_client.get("/api/calendar?month=2026-05")
    assert response.status_code == 200
    data = response.json()
    assert data["month"] == "2026-05"
    assert "days" in data
    assert len(data["days"]) > 0

    # Pick a day from calendar
    first_day = data["days"][0]
    day_date = first_day["date"]

    # View that day
    response = await async_client.get(f"/api/day/{day_date}")
    assert response.status_code == 200
    day_data = response.json()
    assert day_data["date"] == day_date


@pytest.mark.asyncio
@pytest.mark.integration
async def test_access_expiration_flow(async_client: AsyncClient, make_initdata, db_session: AsyncSession):
    """
    Access expiration flow: referral expires → preview mode.
    """
    from app.services.access_service import AccessService
    from sqlalchemy import select
    from app.db.models import User

    # Signup + onboard
    await _onboard_user(async_client, db_session, make_initdata, user_id=1010)

    # Grant referral bonus starting 20 days ago (expired)
    result = await db_session.execute(select(User).where(User.tg_user_id == 1010))
    user = result.scalar_one()

    access_service = AccessService(db_session)
    start_date = datetime.now(timezone.utc).date() - timedelta(days=20)
    await access_service.grant_referral_bonus(user.id, start_date)

    # View today (should be preview - referral expired)
    response = await async_client.get("/api/day/today")
    assert response.status_code == 200
    data = response.json()
    assert data["access"]["state"] == "preview"
    assert data["access"]["reason"] == "expired_access"
