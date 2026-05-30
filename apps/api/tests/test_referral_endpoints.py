# AI_HEADER
# module: M-TEST-REFERRAL-ENDPOINTS
# wave: W-ACCESS.2
# purpose: Referral endpoints tests

import pytest
from httpx import AsyncClient


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
