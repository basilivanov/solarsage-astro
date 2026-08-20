# ############################################################################
# AI_HEADER: MODULE_TESTS_PROMO_PENDING_AUTO_APPLY — test auto-apply of pending promo token upon onboarding.
# ROLE: Tests for automatic redemption of User.pending_promo_token on PUT /api/profile completion.
# DEPENDENCIES: pytest, httpx, sqlalchemy, app.db.models, app.services.promo_campaign_service
# GRACE_ANCHORS: [PROMO_AUTO_APPLY_TESTS]
# WAVE: W-NAMED-PROMO-CAMPAIGN
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-PROMO-PENDING-AUTO-APPLY
# purpose: Verify that User.pending_promo_token is automatically redeemed upon onboarding completion,
#   cleared on success or terminal error, preserved on PROFILE_INCOMPLETE, and that PUT /api/profile
#   always returns HTTP 200.
# owns:
#   - apps/api/tests/test_promo_pending_auto_apply.py
# inputs: async_client, db_session, make_initdata fixtures
# outputs: pytest assertions
# dependencies:
#   - app.db.models (User, UserProfile, PromoCampaign, PromoRedemption, AccessLedger, HoraryCredit)
#   - app.services.promo_campaign_service (hash_promo_token)
# side_effects: database writes in isolated test DB
# invariants:
#   - PUT /api/profile response remains 200 regardless of promo outcome
#   - terminal promo errors clear pending token; non-terminal preserve it
# failure_policy: pytest assertion failures
# END_MODULE_CONTRACT: M-TESTS-PROMO-PENDING-AUTO-APPLY

# START_MODULE_MAP: M-TESTS-PROMO-PENDING-AUTO-APPLY
# public_entrypoints:
#   - test_auto_apply_happy_path_on_onboarding_completion
#   - test_auto_apply_clears_token_on_expired_campaign
#   - test_auto_apply_clears_token_on_full_campaign
#   - test_auto_apply_preserves_token_on_profile_incomplete
#   - test_put_profile_without_pending_token_unaffected
#   - test_auto_apply_unexpected_exception_still_returns_200
#   - test_put_profile_partial_not_onboarded_does_not_trigger_auto_apply
# semantic_blocks:
#   - AUTO_APPLY_TESTS: test cases for pending promo auto-apply behavior
# owned_tests:
#   - apps/api/tests/test_promo_pending_auto_apply.py
# END_MODULE_MAP: M-TESTS-PROMO-PENDING-AUTO-APPLY

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal as D

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AccessLedger,
    HoraryCredit,
    PromoCampaign,
    PromoRedemption,
    User,
    UserProfile,
)
from app.services.promo_campaign_service import hash_promo_token


def _create_campaign(
    *,
    token: str = "m7q4n9x2r5kd",
    display_name: str = "Test Auto-Apply Promo",
    active: bool = True,
    starts_delta_days: int = -1,
    ends_delta_days: int = 30,
    max_redemptions: int = 100,
    redemptions_used: int = 0,
    access_days: int = 30,
    bonus_credits: int = 10,
    unlock_natal: bool = False,
) -> PromoCampaign:
    now = datetime.now(timezone.utc)
    return PromoCampaign(
        display_name=display_name,
        code_hash=hash_promo_token(token),
        active=active,
        activation_starts_at=now + timedelta(days=starts_delta_days),
        activation_ends_at=now + timedelta(days=ends_delta_days),
        max_redemptions=max_redemptions,
        redemptions_used=redemptions_used,
        access_days=access_days,
        bonus_credits=bonus_credits,
        unlock_natal=unlock_natal,
    )


# START_BLOCK: AUTO_APPLY_TESTS
@pytest.mark.asyncio
async def test_auto_apply_happy_path_on_onboarding_completion(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    token = "sfnqpmfdwkuk"
    campaign = _create_campaign(token=token, access_days=30, bonus_credits=10, unlock_natal=False)
    db_session.add(campaign)
    await db_session.commit()

    # 1. Login with start_param promo token
    raw = make_initdata(user_id=701, start_param=token)
    login_res = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert login_res.status_code == 200

    user = (await db_session.execute(select(User).where(User.tg_user_id == 701))).scalar_one()
    assert user.pending_promo_token == token

    # 2. Complete onboarding via PUT /api/profile
    payload = {
        "firstName": "Volodya",
        "gender": "male",
        "birth": {
            "birthday": "1984-03-14",
            "birthTime": None,
            "birthTimeMode": "unknown",
            "birthCity": "Karaganda",
            "birthLat": 49.80,
            "birthLon": 73.10,
            "birthTz": "Asia/Almaty",
        },
    }
    put_res = await async_client.put("/api/profile", json=payload)
    assert put_res.status_code == 200
    body = put_res.json()
    assert body["isOnboarded"] is True

    # 3. Verify promo auto-applied
    await db_session.refresh(user)
    assert user.pending_promo_token is None

    redemptions = (
        await db_session.execute(
            select(PromoRedemption).where(
                PromoRedemption.campaign_id == campaign.id,
                PromoRedemption.user_id == user.id,
            )
        )
    ).scalars().all()
    assert len(redemptions) == 1

    access_entries = (
        await db_session.execute(
            select(AccessLedger).where(AccessLedger.user_id == user.id)
        )
    ).scalars().all()
    assert len(access_entries) == 1
    assert access_entries[0].entry_type == "subscription"

    credits = (
        await db_session.execute(
            select(HoraryCredit).where(HoraryCredit.user_id == user.id)
        )
    ).scalars().all()
    assert len(credits) == 1
    assert credits[0].amount == 10


@pytest.mark.asyncio
async def test_auto_apply_clears_token_on_expired_campaign(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    token = "k3n7q9x2r5m8"
    campaign = _create_campaign(
        token=token,
        starts_delta_days=-10,
        ends_delta_days=-1,  # Expired
    )
    db_session.add(campaign)
    await db_session.commit()

    raw = make_initdata(user_id=702, start_param=token)
    login_res = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert login_res.status_code == 200

    user = (await db_session.execute(select(User).where(User.tg_user_id == 702))).scalar_one()
    assert user.pending_promo_token == token

    payload = {
        "firstName": "Alex",
        "gender": "female",
        "birth": {
            "birthday": "1992-05-10",
            "birthTime": None,
            "birthTimeMode": "unknown",
            "birthCity": "Moscow",
            "birthLat": 55.75,
            "birthLon": 37.62,
            "birthTz": "Europe/Moscow",
        },
    }
    put_res = await async_client.put("/api/profile", json=payload)
    assert put_res.status_code == 200
    assert put_res.json()["isOnboarded"] is True

    # Terminal failure clears pending_promo_token
    await db_session.refresh(user)
    assert user.pending_promo_token is None

    redemptions = (
        await db_session.execute(
            select(PromoRedemption).where(PromoRedemption.user_id == user.id)
        )
    ).scalars().all()
    assert len(redemptions) == 0


@pytest.mark.asyncio
async def test_auto_apply_clears_token_on_full_campaign(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    token = "r4n7q9x2k5m8"
    campaign = _create_campaign(
        token=token,
        max_redemptions=5,
        redemptions_used=5,  # Full
    )
    db_session.add(campaign)
    await db_session.commit()

    raw = make_initdata(user_id=703, start_param=token)
    login_res = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert login_res.status_code == 200

    user = (await db_session.execute(select(User).where(User.tg_user_id == 703))).scalar_one()
    assert user.pending_promo_token == token

    payload = {
        "firstName": "Dmitry",
        "gender": "male",
        "birth": {
            "birthday": "1990-01-01",
            "birthTime": None,
            "birthTimeMode": "unknown",
            "birthCity": "Saint Petersburg",
            "birthLat": 59.93,
            "birthLon": 30.33,
            "birthTz": "Europe/Moscow",
        },
    }
    put_res = await async_client.put("/api/profile", json=payload)
    assert put_res.status_code == 200
    assert put_res.json()["isOnboarded"] is True

    await db_session.refresh(user)
    assert user.pending_promo_token is None

    redemptions = (
        await db_session.execute(
            select(PromoRedemption).where(PromoRedemption.user_id == user.id)
        )
    ).scalars().all()
    assert len(redemptions) == 0


@pytest.mark.asyncio
async def test_auto_apply_preserves_token_on_profile_incomplete(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    # Campaign requires natal unlock (strict profile with birth_time)
    token = "w8n7q9x2k5m8"
    campaign = _create_campaign(token=token, unlock_natal=True)
    db_session.add(campaign)
    await db_session.commit()

    raw = make_initdata(user_id=704, start_param=token)
    login_res = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert login_res.status_code == 200

    user = (await db_session.execute(select(User).where(User.tg_user_id == 704))).scalar_one()
    assert user.pending_promo_token == token

    # User completes base onboarding with unknown birth time (no birth_time)
    payload = {
        "firstName": "Elena",
        "gender": "female",
        "birth": {
            "birthday": "1995-07-20",
            "birthTime": None,
            "birthTimeMode": "unknown",
            "birthCity": "Novosibirsk",
            "birthLat": 55.03,
            "birthLon": 82.92,
            "birthTz": "Asia/Novosibirsk",
        },
    }
    put_res = await async_client.put("/api/profile", json=payload)
    assert put_res.status_code == 200
    assert put_res.json()["isOnboarded"] is True

    # PROFILE_INCOMPLETE should PRESERVE the token for later
    await db_session.refresh(user)
    assert user.pending_promo_token == token

    redemptions = (
        await db_session.execute(
            select(PromoRedemption).where(PromoRedemption.user_id == user.id)
        )
    ).scalars().all()
    assert len(redemptions) == 0


@pytest.mark.asyncio
async def test_put_profile_without_pending_token_unaffected(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    raw = make_initdata(user_id=705)
    login_res = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert login_res.status_code == 200

    user = (await db_session.execute(select(User).where(User.tg_user_id == 705))).scalar_one()
    assert user.pending_promo_token is None

    payload = {
        "firstName": "Olga",
        "gender": "female",
        "birth": {
            "birthday": "1988-11-15",
            "birthTime": "14:30:00",
            "birthTimeMode": "exact",
            "birthCity": "Samara",
            "birthLat": 53.20,
            "birthLon": 50.15,
            "birthTz": "Europe/Samara",
        },
    }
    put_res = await async_client.put("/api/profile", json=payload)
    assert put_res.status_code == 200
    assert put_res.json()["isOnboarded"] is True

    await db_session.refresh(user)
    assert user.pending_promo_token is None


@pytest.mark.asyncio
async def test_auto_apply_unexpected_exception_still_returns_200(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = "sfnqpmfdwkuk"
    raw = make_initdata(user_id=706, start_param=token)
    login_res = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert login_res.status_code == 200

    from unittest.mock import AsyncMock
    from app.services.promo_campaign_service import PromoCampaignService

    monkeypatch.setattr(
        PromoCampaignService,
        "redeem",
        AsyncMock(side_effect=RuntimeError("Database deadlock simulation")),
    )

    payload = {
        "firstName": "Anna",
        "gender": "female",
        "birth": {
            "birthday": "1994-06-12",
            "birthTime": None,
            "birthTimeMode": "unknown",
            "birthCity": "Kazan",
            "birthLat": 55.79,
            "birthLon": 49.12,
            "birthTz": "Europe/Moscow",
        },
    }
    put_res = await async_client.put("/api/profile", json=payload)
    assert put_res.status_code == 200
    assert put_res.json()["isOnboarded"] is True


@pytest.mark.asyncio
async def test_put_profile_partial_not_onboarded_does_not_trigger_auto_apply(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    token = "sfnqpmfdwkuk"
    campaign = _create_campaign(token=token)
    db_session.add(campaign)
    await db_session.commit()

    raw = make_initdata(user_id=707, start_param=token)
    login_res = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert login_res.status_code == 200

    user = (await db_session.execute(select(User).where(User.tg_user_id == 707))).scalar_one()
    assert user.pending_promo_token == token

    # Partial update: only firstName set, missing birthday/birthCity/gender
    payload = {"firstName": "OnlyName"}
    put_res = await async_client.put("/api/profile", json=payload)
    assert put_res.status_code == 200
    assert put_res.json()["isOnboarded"] is False

    await db_session.refresh(user)
    # Token must NOT be redeemed or cleared because profile is not yet onboarded
    assert user.pending_promo_token == token
# END_BLOCK: AUTO_APPLY_TESTS
