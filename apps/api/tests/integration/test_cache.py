
# ############################################################################
# AI_HEADER: MODULE_INTEGRATION_TEST_CACHE
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for cache.py behavior
# owns:
#   - apps/api/tests/integration/test_cache.py
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
# module: M-TEST-CACHE
# wave: W-5.2
# purpose: Cache layer tests

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserProfile


@pytest.mark.asyncio
async def test_cache_miss_then_hit(async_client: AsyncClient, make_initdata, db_session: AsyncSession):
    """First call generates, second call returns cached."""
    # Signup + onboard
    user_id = 5555
    user_raw = make_initdata(user_id=user_id, username="cacheuser")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})
    await async_client.put("/api/profile", json={
        "gender": "male",
        "birth": {
            "birthday": "1990-01-15",
            "birthTime": "14:30",
            "birthCity": "Moscow",
            "birthLat": 55.7558,
            "birthLon": 37.6173,
            "birthTz": "Europe/Moscow"
        }
    })

    # Manually set is_onboarded=True
    stmt = select(User).where(User.tg_user_id == user_id)
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()
    if user:
        stmt = update(UserProfile).where(UserProfile.user_id == user.id).values(is_onboarded=True)
        await db_session.execute(stmt)
        await db_session.commit()

    # First call (cache miss)
    response1 = await async_client.get("/api/day/today")
    if response1.status_code != 200:
        print(f"Response status: {response1.status_code}")
        print(f"Response body: {response1.text}")
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["meta"]["cached"] is False

    # Second call (cache hit)
    response2 = await async_client.get("/api/day/today")
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["meta"]["cached"] is True

    # Headline should be the same
    assert data1["headline"] == data2["headline"]


@pytest.mark.asyncio
async def test_cache_invalidation_on_profile_edit(async_client: AsyncClient, make_initdata, db_session: AsyncSession):
    """Profile edit invalidates cache."""
    # Signup + onboard
    user_id = 6666
    user_raw = make_initdata(user_id=user_id, username="invaliduser")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})
    await async_client.put("/api/profile", json={
        "gender": "male",
        "birth": {
            "birthday": "1990-01-15",
            "birthTime": "14:30",
            "birthCity": "Moscow",
            "birthLat": 55.7558,
            "birthLon": 37.6173,
            "birthTz": "Europe/Moscow"
        }
    })

    # Manually set is_onboarded=True
    stmt = select(User).where(User.tg_user_id == user_id)
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()
    if user:
        stmt = update(UserProfile).where(UserProfile.user_id == user.id).values(is_onboarded=True)
        await db_session.execute(stmt)
        await db_session.commit()

    # First call (cache miss)
    response1 = await async_client.get("/api/day/today")
    assert response1.status_code == 200
    assert response1.json()["meta"]["cached"] is False

    # Edit profile (should invalidate cache)
    await async_client.put("/api/profile", json={
        "gender": "male",
        "birth": {
            "birthday": "1990-01-15",
            "birthTime": "14:30",
            "birthCity": "Moscow",
            "birthLat": 55.7558,
            "birthLon": 37.6173,
            "birthTz": "Europe/Moscow"
        }
    })

    # Third call (cache miss again after invalidation)
    response3 = await async_client.get("/api/day/today")
    assert response3.status_code == 200
    assert response3.json()["meta"]["cached"] is False
