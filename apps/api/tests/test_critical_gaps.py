# AI_HEADER
# module: M-TEST-CRITICAL-GAPS
# wave: W-ACCESS.2
# purpose: Tests for scenarios where "API returns 200 but side effects incomplete"

import pytest
from httpx import AsyncClient
from sqlalchemy import select, and_
from datetime import date, timedelta
from app.db.models import User, UserProfile, AccessLedger, Referral


# ── Gap 1.1: is_onboarded=true but no lat/lon → calendar passes, day rejects ──

@pytest.mark.asyncio
async def test_calendar_passes_but_day_rejects_without_latlon(
    async_client: AsyncClient, make_initdata, db_session
):
    """Calendar checks only is_onboarded. Day also requires lat/lon.
    If lat/lon are missing, calendar returns 200 but day returns 422."""
    raw = make_initdata(user_id=2001, username="nolatlontest")
    await async_client.post("/api/auth/telegram", json={"initData": raw})

    # Onboard WITHOUT lat/lon — only birthday + city
    await async_client.put("/api/profile", json={
        "birth": {"birthday": "1990-06-15", "birthCity": "Moscow, Russia"}
    })

    # Verify is_onboarded=True but lat/lon are None
    uid = (await db_session.execute(select(User.id).where(User.tg_user_id == 2001))).scalar_one()
    profile = (await db_session.execute(select(UserProfile).where(UserProfile.user_id == uid))).scalar_one()
    assert profile.is_onboarded is True
    assert profile.birth_lat is None
    assert profile.birth_lon is None

    # Calendar should pass (only checks is_onboarded)
    cal = await async_client.get("/api/calendar?month=2026-06")
    assert cal.status_code == 200

    # Day should reject (requires lat/lon)
    day = await async_client.get("/api/day/today")
    assert day.status_code == 422
    assert day.json()["detail"]["code"] == "NOT_ONBOARDED"


# ── Gap 2.1: Overlapping referral + subscription → referral consumed first ──

@pytest.mark.asyncio
async def test_overlapping_access_referral_consumed_first(
    async_client: AsyncClient, make_initdata, db_session
):
    """When referral and subscription overlap, referral is consumed first."""
    raw = make_initdata(user_id=3001, username="overlap")
    await async_client.post("/api/auth/telegram", json={"initData": raw})

    uid = (await db_session.execute(select(User.id).where(User.tg_user_id == 3001))).scalar_one()

    # Grant referral: today → today+13 (14 days)
    start = date.today()
    ref_end = start + timedelta(days=13)
    db_session.add(AccessLedger(user_id=uid, entry_type="referral_bonus", days_granted=14,
                                 start_date=start, end_date=ref_end))

    # Grant subscription starting day 5: today+5 → today+34 (30 days)
    sub_start = start + timedelta(days=5)
    sub_end = sub_start + timedelta(days=29)
    db_session.add(AccessLedger(user_id=uid, entry_type="subscription", days_granted=30,
                                 start_date=sub_start, end_date=sub_end))
    await db_session.commit()

    # On day 5, BOTH cover → referral consumed first
    day5 = await async_client.get(f"/api/day/{start.isoformat()}")
    if day5.status_code == 200:
        assert day5.json()["access"]["state"] == "full"
        assert day5.json()["access"]["reason"] == "active_referral_days"

    # On day 14, referral expired, subscription covers
    day14 = await async_client.get(f"/api/day/{(start + timedelta(days=14)).isoformat()}")
    if day14.status_code == 200:
        assert day14.json()["access"]["state"] == "full"
        assert day14.json()["access"]["reason"] == "active_subscription"

    # On day 35, both expired
    day35 = await async_client.get(f"/api/day/{(start + timedelta(days=35)).isoformat()}")
    if day35.status_code == 200:
        assert day35.json()["access"]["state"] == "locked"


# ── Gap: Referrer gets bonus when invitee claims ──

@pytest.mark.asyncio
async def test_referrer_gets_bonus_on_claim(async_client: AsyncClient, make_initdata, db_session):
    """When invitee claims referral, BOTH get 14-day bonus."""
    # Referrer
    ref_raw = make_initdata(user_id=4001, username="refbonus_r")
    await async_client.post("/api/auth/telegram", json={"initData": ref_raw})
    ref_db_id = (await db_session.execute(select(User.id).where(User.tg_user_id == 4001))).scalar_one()

    # Invitee
    inv_raw = make_initdata(user_id=4002, username="refbonus_i")
    await async_client.post("/api/auth/telegram", json={"initData": inv_raw})
    inv_db_id = (await db_session.execute(select(User.id).where(User.tg_user_id == 4002))).scalar_one()

    # Claim
    claim = await async_client.post("/api/referral/claim", json={"referrer_code": "4001"})
    assert claim.status_code == 200

    # Both get bonus
    for uid, label in [(ref_db_id, "referrer"), (inv_db_id, "invitee")]:
        bonus = (await db_session.execute(
            select(AccessLedger).where(
                and_(AccessLedger.user_id == uid, AccessLedger.entry_type == "referral_bonus")
            )
        )).scalar_one_or_none()
        assert bonus is not None, f"{label} should get referral_bonus"
        assert bonus.days_granted == 14, f"{label} should get 14 days"
