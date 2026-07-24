# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_PROMO_API
# ROLE: API tests for /api/promo/preview and /api/promo/redeem HTTP endpoints.
# DEPENDENCIES: pytest, httpx, app.main, app.services.promo_campaign_service
# GRACE_ANCHORS: [TEST_PROMO_API]
# WAVE: W-NAMED-PROMO-CAMPAIGN
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-PROMO-API
# purpose: Test session authentication, success response shapes, incomplete profile rules, status code error matrix (400, 409, 410), Cache-Control no-store headers, safe 400 validation parsing, and privacy (no token/PII leaks).
# owns:
#   - apps/api/tests/test_promo_api.py
# inputs: async_client, make_initdata, db_session
# outputs: pytest execution assertions
# dependencies:
#   - app.services.promo_campaign_service (hash_promo_token)
#   - app.db.models (PromoCampaign, PromoRedemption, UserProfile)
# side_effects: database transactions in test runner
# failure_policy: raise assertions
# END_MODULE_CONTRACT: M-TEST-PROMO-API

# START_MODULE_MAP: M-TEST-PROMO-API
# public_entrypoints:
#   - test_unauthenticated_promo_endpoints_return_401
#   - test_promo_preview_success_shape_and_no_store_header
#   - test_incomplete_profile_preview_200_redeem_409_without_mutations
#   - test_promo_redeem_success_and_idempotent_duplicate
#   - test_promo_error_matrix_status_codes
#   - test_malformed_body_and_validation_errors_return_safe_400
#   - test_privacy_no_sentinel_token_leak_in_body_or_logs
# owned_tests:
#   - apps/api/tests/test_promo_api.py
# END_MODULE_MAP: M-TEST-PROMO-API

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal as D
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models import PromoCampaign, PromoRedemption, UserProfile
from app.services.profile_service import get_or_create_user
from app.services.promo_campaign_service import hash_promo_token
from app.services.telegram_auth import TelegramUser


def create_test_campaign(
    display_name="API Test Promo",
    token="m7q4n9x2r5kd",
    active=True,
    starts_delta_days=-1,
    ends_delta_days=30,
    max_redemptions=100,
    redemptions_used=0,
    access_days=14,
    bonus_credits=25,
    unlock_natal=True,
) -> PromoCampaign:
    current_time = datetime.now(timezone.utc)
    return PromoCampaign(
        display_name=display_name,
        code_hash=hash_promo_token(token),
        active=active,
        activation_starts_at=current_time + timedelta(days=starts_delta_days),
        activation_ends_at=current_time + timedelta(days=ends_delta_days),
        max_redemptions=max_redemptions,
        redemptions_used=redemptions_used,
        access_days=access_days,
        bonus_credits=bonus_credits,
        unlock_natal=unlock_natal,
    )


@pytest.mark.asyncio
async def test_unauthenticated_promo_endpoints_return_401(async_client: AsyncClient) -> None:
    resp_prev = await async_client.post("/api/promo/preview", json={"token": "m7q4n9x2r5kd"})
    assert resp_prev.status_code == 401

    resp_red = await async_client.post("/api/promo/redeem", json={"token": "m7q4n9x2r5kd"})
    assert resp_red.status_code == 401


@pytest.mark.asyncio
async def test_promo_preview_success_shape_and_no_store_header(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    campaign = create_test_campaign(token="m7q4n9x2r5ke")
    db_session.add(campaign)
    await db_session.commit()

    raw_init = make_initdata(user_id=990001, username="promo_api_1")
    await async_client.post("/api/auth/telegram", json={"initData": raw_init})

    resp = await async_client.post("/api/promo/preview", json={"token": "m7q4n9x2r5ke"})
    assert resp.status_code == 200
    assert resp.headers.get("Cache-Control") == "no-store"

    data = resp.json()
    assert "offer" in data
    assert data["offer"]["displayName"] == "API Test Promo"
    assert data["offer"]["accessDays"] == 14
    assert data["offer"]["bonusCredits"] == 25
    assert data["offer"]["unlockNatal"] is True
    assert "profileComplete" in data


@pytest.mark.asyncio
async def test_incomplete_profile_preview_200_redeem_409_without_mutations(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    campaign = create_test_campaign(token="m7q4n9x2r5kf")
    db_session.add(campaign)
    await db_session.commit()

    raw_init = make_initdata(user_id=990002, username="promo_api_2")
    await async_client.post("/api/auth/telegram", json={"initData": raw_init})

    # User profile is incomplete (no birth date/time/place)
    prev_resp = await async_client.post("/api/promo/preview", json={"token": "m7q4n9x2r5kf"})
    assert prev_resp.status_code == 200
    assert prev_resp.headers.get("Cache-Control") == "no-store"
    assert prev_resp.json()["profileComplete"] is False

    red_resp = await async_client.post("/api/promo/redeem", json={"token": "m7q4n9x2r5kf"})
    assert red_resp.status_code == 409
    assert red_resp.headers.get("Cache-Control") == "no-store"

    err_data = red_resp.json()
    assert err_data["detail"]["code"] == "PROFILE_INCOMPLETE"
    assert "Заполните профиль" in err_data["detail"]["message"]

    # Verify no redemption created in database
    redemptions = (await db_session.scalars(select(PromoRedemption))).all()
    assert len(redemptions) == 0


@pytest.mark.asyncio
async def test_promo_redeem_success_and_idempotent_duplicate(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    campaign = create_test_campaign(token="m7q4n9x2r5kg")
    db_session.add(campaign)
    await db_session.commit()

    raw_init = make_initdata(user_id=990003, username="promo_api_3")
    await async_client.post("/api/auth/telegram", json={"initData": raw_init})

    tg_user = TelegramUser(id=990003, username="promo_api_3", first_name="PromoUser3")
    user, _ = await get_or_create_user(db_session, tg_user)

    # Complete user profile
    profile = await db_session.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db_session.add(profile)

    profile.first_name = "PromoUser3"
    profile.gender = "female"
    profile.birthday = date(1992, 5, 10)
    profile.birth_time = time(14, 30)
    profile.birth_city = "Moscow"
    profile.birth_lat = D("55.75")
    profile.birth_lon = D("37.61")
    profile.birth_tz = "Europe/Moscow"
    profile.is_onboarded = True
    await db_session.commit()

    # First redeem
    resp1 = await async_client.post("/api/promo/redeem", json={"token": "m7q4n9x2r5kg"})
    assert resp1.status_code == 200
    assert resp1.headers.get("Cache-Control") == "no-store"

    data1 = resp1.json()
    assert data1["status"] == "redeemed"
    assert data1["offer"]["displayName"] == "API Test Promo"
    assert data1["grants"]["bonusCredits"] == 25
    assert data1["grants"]["natalUnlocked"] is True

    # Duplicate redeem attempt
    resp2 = await async_client.post("/api/promo/redeem", json={"token": "m7q4n9x2r5kg"})
    assert resp2.status_code == 409
    assert resp2.headers.get("Cache-Control") == "no-store"
    assert resp2.json()["detail"]["code"] == "ALREADY_REDEEMED"


@pytest.mark.asyncio
async def test_promo_error_matrix_status_codes(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    raw_init = make_initdata(user_id=990004, username="promo_api_4")
    await async_client.post("/api/auth/telegram", json={"initData": raw_init})

    # 1. Invalid code (non-existent token format or unknown token) -> 400 INVALID_CODE
    resp_inv = await async_client.post("/api/promo/preview", json={"token": "m7q4n9x2r5kh"})
    assert resp_inv.status_code == 400
    assert resp_inv.headers.get("Cache-Control") == "no-store"
    assert resp_inv.json()["detail"]["code"] == "INVALID_CODE"

    # 2. Expired campaign -> 410 CAMPAIGN_EXPIRED
    expired_campaign = create_test_campaign(token="m7q4n9x2r5kj", starts_delta_days=-10, ends_delta_days=-1)
    db_session.add(expired_campaign)
    await db_session.commit()

    resp_exp = await async_client.post("/api/promo/preview", json={"token": "m7q4n9x2r5kj"})
    assert resp_exp.status_code == 410
    assert resp_exp.headers.get("Cache-Control") == "no-store"
    assert resp_exp.json()["detail"]["code"] == "CAMPAIGN_EXPIRED"

    # 3. Exhausted campaign -> 409 CAMPAIGN_FULL
    full_campaign = create_test_campaign(token="m7q4n9x2r5kk", max_redemptions=5, redemptions_used=5)
    db_session.add(full_campaign)
    await db_session.commit()

    resp_full = await async_client.post("/api/promo/preview", json={"token": "m7q4n9x2r5kk"})
    assert resp_full.status_code == 409
    assert resp_full.headers.get("Cache-Control") == "no-store"
    assert resp_full.json()["detail"]["code"] == "CAMPAIGN_FULL"


@pytest.mark.asyncio
async def test_malformed_body_and_validation_errors_return_safe_400(
    async_client: AsyncClient, make_initdata
) -> None:
    raw_init = make_initdata(user_id=990005, username="promo_api_5")
    await async_client.post("/api/auth/telegram", json={"initData": raw_init})

    # Missing token field
    resp_empty = await async_client.post("/api/promo/preview", json={})
    assert resp_empty.status_code == 400
    assert resp_empty.headers.get("Cache-Control") == "no-store"
    assert resp_empty.json() == {"detail": {"code": "INVALID_CODE", "message": "Неверный промокод"}}

    # Non-string type
    resp_num = await async_client.post("/api/promo/preview", json={"token": 99999})
    assert resp_num.status_code == 400
    assert resp_num.headers.get("Cache-Control") == "no-store"
    assert resp_num.json() == {"detail": {"code": "INVALID_CODE", "message": "Неверный промокод"}}

    # Extra field (extra="forbid")
    resp_extra = await async_client.post(
        "/api/promo/preview",
        json={"token": "m7q4n9x2r5kd", "forbidden": "field"},
    )
    assert resp_extra.status_code == 400
    assert resp_extra.headers.get("Cache-Control") == "no-store"
    assert resp_extra.json() == {"detail": {"code": "INVALID_CODE", "message": "Неверный промокод"}}

    # Raw string / invalid JSON
    resp_malformed = await async_client.post(
        "/api/promo/preview",
        content="not a json",
        headers={"Content-Type": "application/json"},
    )
    assert resp_malformed.status_code == 400
    assert resp_malformed.headers.get("Cache-Control") == "no-store"
    assert resp_malformed.json() == {"detail": {"code": "INVALID_CODE", "message": "Неверный промокод"}}


@pytest.mark.asyncio
async def test_privacy_no_sentinel_token_leak_in_body_or_logs(
    async_client: AsyncClient, make_initdata, caplog
) -> None:
    raw_init = make_initdata(user_id=990006, username="promo_api_6")
    await async_client.post("/api/auth/telegram", json={"initData": raw_init})

    sentinel_token = "sentinel_secret_token_12345"

    resp = await async_client.post("/api/promo/preview", json={"token": sentinel_token})
    assert resp.status_code == 400

    # Ensure sentinel token never appears in error response body
    assert sentinel_token not in resp.text

    # Ensure sentinel token never appears in captured log records
    for record in caplog.records:
        assert sentinel_token not in record.getMessage()
