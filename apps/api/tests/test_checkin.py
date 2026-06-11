
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_CHECKIN
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for checkin.py behavior
# owns:
#   - apps/api/tests/test_checkin.py
# inputs: Endpoint params, request body
# outputs: Parsed response / typed data
# dependencies: local modules
# side_effects: Network calls to API
# emitted_logs: n/a (tests)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# ############################################################################
# AI_HEADER
# module: M-TEST-CHECKIN
# wave: W-8.1, W-8.2
# purpose: Evening checkin tests
# ############################################################################

import pytest
from httpx import AsyncClient
from datetime import date


@pytest.mark.asyncio
async def test_create_checkin(async_client: AsyncClient, make_initdata):
    """Create evening checkin."""
    user_raw = make_initdata(user_id=12353, username="checkinuser")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    response = await async_client.post(
        "/api/checkin",
        json={
            "target_date": date.today().isoformat(),
            "mood": "great",
            "notes": "Отличный день!",
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mood"] == "great"
    assert data["notes"] == "Отличный день!"


@pytest.mark.asyncio
async def test_get_checkin(async_client: AsyncClient, make_initdata):
    """Get checkin for specific date."""
    user_raw = make_initdata(user_id=12354, username="checkinuser2")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    # Create checkin
    today = date.today()
    await async_client.post(
        "/api/checkin",
        json={
            "target_date": today.isoformat(),
            "mood": "good",
            "notes": None,
        }
    )

    # Get checkin
    response = await async_client.get(f"/api/checkin/{today.isoformat()}")

    assert response.status_code == 200
    data = response.json()
    assert data["mood"] == "good"


@pytest.mark.asyncio
async def test_upsert_checkin(async_client: AsyncClient, make_initdata):
    """Update existing checkin."""
    user_raw = make_initdata(user_id=12355, username="checkinuser3")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    today = date.today()

    # Create
    await async_client.post(
        "/api/checkin",
        json={"target_date": today.isoformat(), "mood": "neutral", "notes": None}
    )

    # Update
    response = await async_client.post(
        "/api/checkin",
        json={"target_date": today.isoformat(), "mood": "great", "notes": "Стало лучше!"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["mood"] == "great"
    assert data["notes"] == "Стало лучше!"
