
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_REFERRAL_ENDPOINTS
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for referral_endpoints.py behavior
# owns:
#   - apps/api/tests/test_referral_endpoints.py
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
# module: M-TEST-REFERRAL-ENDPOINTS
# wave: W-ACCESS.2
# purpose: Referral endpoints tests

import pytest
from httpx import AsyncClient
from sqlalchemy import select, and_
from app.db.models import User, AccessLedger


@pytest.mark.asyncio
async def test_claim_referral_success(async_client: AsyncClient, make_initdata, db_session):
    """Successful referral claim grants 14d bonus."""
    # Create referrer
    referrer_raw = make_initdata(user_id=1111, username="referrer")
    await async_client.post("/api/auth/telegram", json={"initData": referrer_raw})

    # Create invitee
    invitee_raw = make_initdata(user_id=2222, username="invitee")
    await async_client.post("/api/auth/telegram", json={"initData": invitee_raw})

    # Claim referral
    response = await async_client.post("/api/referral/claim", json={
        "referrer_code": "1111"
    })

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["days_granted"] == 14
    assert "access_until" in data
    assert "message" in data

    # Verify REFERRER also got bonus (not just invitee)
    ref_id = (await db_session.execute(select(User.id).where(User.tg_user_id == 1111))).scalar_one()
    ref_bonus = (await db_session.execute(
        select(AccessLedger).where(
            and_(AccessLedger.user_id == ref_id, AccessLedger.entry_type == "referral_bonus")
        )
    )).scalar_one_or_none()
    assert ref_bonus is not None, "Referrer should get referral_bonus in access_ledger"
    assert ref_bonus.days_granted == 14


@pytest.mark.asyncio
async def test_claim_referral_already_claimed(async_client: AsyncClient, make_initdata):
    """Cannot claim referral twice."""
    # Create referrer
    referrer_raw = make_initdata(user_id=1111, username="referrer")
    await async_client.post("/api/auth/telegram", json={"initData": referrer_raw})

    # Create invitee
    invitee_raw = make_initdata(user_id=2222, username="invitee")
    await async_client.post("/api/auth/telegram", json={"initData": invitee_raw})

    # Claim referral first time
    await async_client.post("/api/referral/claim", json={"referrer_code": "1111"})

    # Try to claim again
    response = await async_client.post("/api/referral/claim", json={"referrer_code": "1111"})

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "ALREADY_CLAIMED"


@pytest.mark.asyncio
async def test_claim_referral_invalid_code(async_client: AsyncClient, make_initdata):
    """Invalid referrer code → 400."""
    # Create invitee
    invitee_raw = make_initdata(user_id=2222, username="invitee")
    await async_client.post("/api/auth/telegram", json={"initData": invitee_raw})

    # Try to claim with invalid code
    response = await async_client.post("/api/referral/claim", json={"referrer_code": "invalid"})

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_CODE"


@pytest.mark.asyncio
async def test_claim_referral_not_found(async_client: AsyncClient, make_initdata):
    """Referrer not found → 404."""
    # Create invitee
    invitee_raw = make_initdata(user_id=2222, username="invitee")
    await async_client.post("/api/auth/telegram", json={"initData": invitee_raw})

    # Try to claim with non-existent referrer
    response = await async_client.post("/api/referral/claim", json={"referrer_code": "9999"})

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "REFERRER_NOT_FOUND"


@pytest.mark.asyncio
async def test_claim_referral_self_referral(async_client: AsyncClient, make_initdata):
    """Cannot refer yourself → 400."""
    # Create user
    user_raw = make_initdata(user_id=1111, username="user")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    # Try to refer yourself
    response = await async_client.post("/api/referral/claim", json={"referrer_code": "1111"})

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "SELF_REFERRAL"


@pytest.mark.asyncio
async def test_get_referral_info(async_client: AsyncClient, make_initdata, db_session):
    """GET /api/referral returns invite info for authenticated user."""
    raw = make_initdata(user_id=3333, username="inviter")
    await async_client.post("/api/auth/telegram", json={"initData": raw})

    response = await async_client.get("/api/referral")
    assert response.status_code == 200

    data = response.json()
    assert "inviteCode" in data
    assert "inviteUrl" in data
    assert "totalInvited" in data
    assert data["totalInvited"] == 0
    assert data["inviteCode"] == "3333"
    assert "startapp=3333" in data["inviteUrl"]
    assert "/app" in data["inviteUrl"]


@pytest.mark.asyncio
async def test_get_referral_info_with_invites(async_client: AsyncClient, make_initdata, db_session):
    """GET /api/referral counts invited users."""
    # Referrer
    referrer_raw = make_initdata(user_id=4444, username="referrer2")
    await async_client.post("/api/auth/telegram", json={"initData": referrer_raw})

    # Switch to invitee and claim
    invitee_raw = make_initdata(user_id=5555, username="invitee2")
    await async_client.post("/api/auth/telegram", json={"initData": invitee_raw})
    await async_client.post("/api/referral/claim", json={"referrer_code": "4444"})

    # Switch back to referrer and check stats
    await async_client.post("/api/auth/telegram", json={"initData": referrer_raw})
    response = await async_client.get("/api/referral")
    assert response.status_code == 200
    data = response.json()
    assert data["totalInvited"] == 1


@pytest.mark.asyncio
async def test_get_referral_info_unauthorized(async_client: AsyncClient):
    """GET /api/referral requires auth."""
    # Clear cookies by making request without them
    response = await async_client.get("/api/referral")
    assert response.status_code == 401
