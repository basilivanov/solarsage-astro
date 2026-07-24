# ############################################################################
# AI_HEADER: MODULE_TESTS_PROMO_CAMPAIGN_SERVICE
# ROLE: Unit and domain tests for PromoCampaignService preview and token contracts (Phase 06A).
# DEPENDENCIES: pytest, sqlalchemy, app.db.models, app.services.promo_campaign_service
# GRACE_ANCHORS: [PROMO_CAMPAIGN_SERVICE_TESTS]
# WAVE: W-NAMED-PROMO-CAMPAIGN
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-PROMO-CAMPAIGN-SERVICE
# purpose: Validate promo token format rules, hash calculation, campaign preview state validation (invalid, inactive, expired, full, already redeemed ordering), start/end boundaries, base vs strict profile completeness, and PII protection in error messages.
# owns:
#   - apps/api/tests/test_promo_campaign_service.py
# inputs: AsyncSession database fixture and User/PromoCampaign DB records
# outputs: Pytest execution assertions
# dependencies:
#   - app.services.promo_campaign_service (PromoCampaignService, PromoDomainError, hash_promo_token, PROMO_TOKEN_REGEX)
#   - app.db.models (User, UserProfile, PromoCampaign, PromoRedemption)
# side_effects: read-only database queries in test runner
# failure_policy: raise assertions
# END_MODULE_CONTRACT: M-TESTS-PROMO-CAMPAIGN-SERVICE

# START_MODULE_MAP: M-TESTS-PROMO-CAMPAIGN-SERVICE
# public_entrypoints:
#   - test_promo_token_regex_and_hash_helpers
#   - test_invalid_token_format_rejects_without_db_lookup
#   - test_already_redeemed_takes_precedence_over_inactive_expired_full
#   - test_unknown_inactive_and_not_started_campaign_raises_invalid_code
#   - test_start_inclusive_boundary
#   - test_end_exclusive_boundary
#   - test_full_capacity_campaign_raises_campaign_full
#   - test_preview_offer_fields_and_completeness_unlock_natal_false
#   - test_preview_completeness_unlock_natal_true
#   - test_preview_makes_zero_mutations
#   - test_raw_token_and_hash_never_in_error_object
# owned_tests:
#   - apps/api/tests/test_promo_campaign_service.py
# END_MODULE_MAP: M-TESTS-PROMO-CAMPAIGN-SERVICE

import uuid
import unittest.mock
import pytest
from datetime import date, time, datetime, timedelta, timezone
from decimal import Decimal as D
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserProfile, PromoCampaign, PromoRedemption, AccessLedger, HoraryCredit, Purchase
from app.services.promo_campaign_service import (
    PromoCampaignService,
    PromoDomainError,
    hash_promo_token,
    PROMO_TOKEN_REGEX,
)


def create_test_campaign(
    display_name="Test Promo",
    token="m7q4n9x2r5kd",
    active=True,
    starts_delta_days=-1,
    ends_delta_days=30,
    max_redemptions=100,
    redemptions_used=0,
    access_days=30,
    bonus_credits=50,
    unlock_natal=True,
    now=None,
) -> PromoCampaign:
    current_time = now or datetime.now(timezone.utc)
    code_hash = hash_promo_token(token)
    return PromoCampaign(
        display_name=display_name,
        code_hash=code_hash,
        active=active,
        activation_starts_at=current_time + timedelta(days=starts_delta_days),
        activation_ends_at=current_time + timedelta(days=ends_delta_days),
        max_redemptions=max_redemptions,
        redemptions_used=redemptions_used,
        access_days=access_days,
        bonus_credits=bonus_credits,
        unlock_natal=unlock_natal,
    )


def create_test_user_profile(user_id: uuid.UUID, has_time=True) -> UserProfile:
    return UserProfile(
        user_id=user_id,
        first_name="TestUser",
        gender="female",
        is_onboarded=True,
        birthday=date(1990, 1, 1),
        birth_time=time(12, 0, 0) if has_time else None,
        birth_city="Moscow",
        birth_lat=D("55.75"),
        birth_lon=D("37.62"),
        birth_tz="Europe/Moscow",
    )


def test_promo_token_regex_and_hash_helpers():
    """Test Base58 fullmatch regex and lowercase 64-char SHA-256 hash generation."""
    valid_tokens = ["m7q4n9x2r5kd", "abc23456789a", "23456789abcd"]
    for t in valid_tokens:
        assert PROMO_TOKEN_REGEX.fullmatch(t) is not None
        h = hash_promo_token(t)
        assert len(h) == 64
        assert h == h.lower()

    invalid_tokens = [
        "short",
        "m7q4n9x2r5kdm7q4n",
        "M7Q4N9X2R5KD",
        "123456789012345",
        "m7q0n9x2r5kd",
        "m7q4n9x2r5kd\n",
        " m7q4n9x2r5kd ",
    ]
    for t in invalid_tokens:
        assert PROMO_TOKEN_REGEX.fullmatch(t) is None


@pytest.mark.asyncio
async def test_invalid_token_format_rejects_without_db_lookup():
    """Test malformed tokens raise PromoDomainError(INVALID_CODE) without executing DB queries."""
    mock_session = unittest.mock.AsyncMock()
    service = PromoCampaignService(mock_session)
    user_id = uuid.uuid4()

    invalid_tokens = [
        "short",
        "m7q4n9x2r5kdm7q4n",
        "UPPERCASE_12345",
        "m7q4n9x2r5kd\n",
        " m7q4n9x2r5kd ",
        "m7q0n9x2r5kd",
        "m7q1n9x2r5kd",
        "123456789012345",
    ]

    for bad_token in invalid_tokens:
        mock_session.execute.reset_mock()
        with pytest.raises(PromoDomainError) as exc_info:
            await service.preview(user_id, bad_token)

        err = exc_info.value
        assert err.code == "INVALID_CODE"
        assert err.safe_message == "Неверный промокод"
        mock_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_already_redeemed_takes_precedence_over_inactive_expired_full(db_session: AsyncSession):
    """Test that an existing redemption returns ALREADY_REDEEMED immediately, even if campaign is inactive/expired/full."""
    service = PromoCampaignService(db_session)
    user = User(tg_user_id=1001, tg_username="redeemer")
    db_session.add(user)
    await db_session.commit()

    now = datetime.now(timezone.utc)
    token = "m7q4n9x2r5kd"

    # Campaign is inactive, expired, AND full
    campaign = create_test_campaign(
        token=token,
        active=False,
        starts_delta_days=-10,
        ends_delta_days=-1,
        max_redemptions=5,
        redemptions_used=5,
        now=now,
    )
    db_session.add(campaign)
    await db_session.commit()

    # Existing redemption
    redemption = PromoRedemption(campaign_id=campaign.id, user_id=user.id)
    db_session.add(redemption)
    await db_session.commit()

    # User with redemption gets ALREADY_REDEEMED
    with pytest.raises(PromoDomainError) as exc:
        await service.preview(user.id, token, now=now)
    assert exc.value.code == "ALREADY_REDEEMED"
    assert exc.value.safe_message == "Промокод уже активирован"

    # User WITHOUT redemption gets INVALID_CODE (since active=False)
    other_user_id = uuid.uuid4()
    with pytest.raises(PromoDomainError) as exc2:
        await service.preview(other_user_id, token, now=now)
    assert exc2.value.code == "INVALID_CODE"


@pytest.mark.asyncio
async def test_unknown_inactive_and_not_started_campaign_raises_invalid_code(db_session: AsyncSession):
    """Test non-existent, inactive, or future campaigns raise INVALID_CODE for new users."""
    service = PromoCampaignService(db_session)
    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # 1. Non-existent campaign
    with pytest.raises(PromoDomainError) as exc:
        await service.preview(user_id, "m7q4n9x2r5kd", now=now)
    assert exc.value.code == "INVALID_CODE"

    # 3. Not-yet-started campaign
    future_token = "abc23456789a"
    c_future = create_test_campaign(
        token=future_token,
        starts_delta_days=5,
        ends_delta_days=30,
        now=now,
    )
    db_session.add(c_future)
    await db_session.commit()

    with pytest.raises(PromoDomainError) as exc:
        await service.preview(user_id, future_token, now=now)
    assert exc.value.code == "INVALID_CODE"

    # 2. Inactive campaign
    c_inactive = create_test_campaign(token="m7q4n9x2r5kd", active=False, now=now)
    db_session.add(c_inactive)
    await db_session.commit()

    with pytest.raises(PromoDomainError) as exc:
        await service.preview(user_id, "m7q4n9x2r5kd", now=now)
    assert exc.value.code == "INVALID_CODE"


@pytest.mark.asyncio
async def test_start_inclusive_boundary(db_session: AsyncSession):
    """Test activation_starts_at is inclusive: valid at start, invalid microsecond before."""
    service = PromoCampaignService(db_session)
    user = User(tg_user_id=2001, tg_username="boundary_user")
    db_session.add(user)
    await db_session.commit()

    start_time = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2026, 8, 10, 12, 0, 0, tzinfo=timezone.utc)

    campaign = PromoCampaign(
        display_name="Boundary Promo",
        code_hash=hash_promo_token("m7q4n9x2r5kd"),
        active=True,
        activation_starts_at=start_time,
        activation_ends_at=end_time,
        max_redemptions=10,
    )
    db_session.add(campaign)
    await db_session.commit()

    # 1. Exact start_time -> valid
    preview_data = await service.preview(user.id, "m7q4n9x2r5kd", now=start_time)
    assert preview_data.offer.display_name == "Boundary Promo"

    # 2. 1 microsecond before start_time -> INVALID_CODE
    before_start = start_time - timedelta(microseconds=1)
    with pytest.raises(PromoDomainError) as exc:
        await service.preview(user.id, "m7q4n9x2r5kd", now=before_start)
    assert exc.value.code == "INVALID_CODE"


@pytest.mark.asyncio
async def test_end_exclusive_boundary(db_session: AsyncSession):
    """Test activation_ends_at is exclusive: valid 1 microsecond before, expired at exact end."""
    service = PromoCampaignService(db_session)
    user = User(tg_user_id=2002, tg_username="boundary_user2")
    db_session.add(user)
    await db_session.commit()

    start_time = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2026, 8, 10, 12, 0, 0, tzinfo=timezone.utc)

    campaign = PromoCampaign(
        display_name="Boundary Promo 2",
        code_hash=hash_promo_token("abc23456789a"),
        active=True,
        activation_starts_at=start_time,
        activation_ends_at=end_time,
        max_redemptions=10,
    )
    db_session.add(campaign)
    await db_session.commit()

    # 1. 1 microsecond before end_time -> valid
    before_end = end_time - timedelta(microseconds=1)
    preview_data = await service.preview(user.id, "abc23456789a", now=before_end)
    assert preview_data.offer.display_name == "Boundary Promo 2"

    # 2. Exact end_time -> CAMPAIGN_EXPIRED
    with pytest.raises(PromoDomainError) as exc:
        await service.preview(user.id, "abc23456789a", now=end_time)
    assert exc.value.code == "CAMPAIGN_EXPIRED"


@pytest.mark.asyncio
async def test_full_capacity_campaign_raises_campaign_full(db_session: AsyncSession):
    """Test campaign with redemptions_used >= max_redemptions raises PromoDomainError(CAMPAIGN_FULL)."""
    service = PromoCampaignService(db_session)
    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    c_full = create_test_campaign(token="m7q4n9x2r5kd", max_redemptions=10, redemptions_used=10, now=now)
    db_session.add(c_full)
    await db_session.commit()

    with pytest.raises(PromoDomainError) as exc:
        await service.preview(user_id, "m7q4n9x2r5kd", now=now)

    assert exc.value.code == "CAMPAIGN_FULL"
    assert exc.value.safe_message == "Лимит активаций промокода исчерпан"


@pytest.mark.asyncio
async def test_preview_offer_fields_and_completeness_unlock_natal_false(db_session: AsyncSession):
    """Test preview returns correct offer fields and evaluates base profile completeness when unlock_natal=False."""
    now = datetime.now(timezone.utc)
    campaign = create_test_campaign(
        display_name="Access Only Campaign",
        token="m7q4n9x2r5kd",
        access_days=14,
        bonus_credits=0,
        unlock_natal=False,
        now=now,
    )
    db_session.add(campaign)

    user = User(tg_user_id=111, tg_username="user1")
    db_session.add(user)
    await db_session.commit()

    profile = create_test_user_profile(user.id, has_time=False)
    db_session.add(profile)
    await db_session.commit()

    service = PromoCampaignService(db_session)
    preview_data = await service.preview(user.id, "m7q4n9x2r5kd", now=now)

    assert preview_data.offer.display_name == "Access Only Campaign"
    assert preview_data.offer.access_days == 14
    assert preview_data.offer.bonus_credits == 0
    assert preview_data.offer.unlock_natal is False
    assert preview_data.profile_complete is True


@pytest.mark.asyncio
async def test_preview_completeness_unlock_natal_true(db_session: AsyncSession):
    """Test preview evaluates strict natal completeness when unlock_natal=True."""
    now = datetime.now(timezone.utc)
    campaign = create_test_campaign(
        display_name="Full Natal Campaign",
        token="m7q4n9x2r5kd",
        access_days=30,
        bonus_credits=50,
        unlock_natal=True,
        now=now,
    )
    db_session.add(campaign)

    u1 = User(tg_user_id=222, tg_username="u1")
    u2 = User(tg_user_id=333, tg_username="u2")
    db_session.add_all([u1, u2])
    await db_session.commit()

    p1 = create_test_user_profile(u1.id, has_time=False)
    p2 = create_test_user_profile(u2.id, has_time=True)
    db_session.add_all([p1, p2])
    await db_session.commit()

    service = PromoCampaignService(db_session)

    prev1 = await service.preview(u1.id, "m7q4n9x2r5kd", now=now)
    assert prev1.profile_complete is False

    prev2 = await service.preview(u2.id, "m7q4n9x2r5kd", now=now)
    assert prev2.profile_complete is True


@pytest.mark.asyncio
async def test_preview_makes_zero_mutations(db_session: AsyncSession):
    """Test preview makes zero mutations to database tables."""
    now = datetime.now(timezone.utc)
    campaign = create_test_campaign(token="m7q4n9x2r5kd", now=now)
    user = User(tg_user_id=444, tg_username="u4")
    db_session.add_all([campaign, user])
    await db_session.commit()

    profile = create_test_user_profile(user.id)
    db_session.add(profile)
    await db_session.commit()

    service = PromoCampaignService(db_session)
    await service.preview(user.id, "m7q4n9x2r5kd", now=now)

    res_red = await db_session.execute(select(PromoRedemption))
    assert len(res_red.scalars().all()) == 0

    res_led = await db_session.execute(select(AccessLedger))
    assert len(res_led.scalars().all()) == 0

    res_cred = await db_session.execute(select(HoraryCredit))
    assert len(res_cred.scalars().all()) == 0

    res_pur = await db_session.execute(select(Purchase))
    assert len(res_pur.scalars().all()) == 0

    res_camp = await db_session.execute(select(PromoCampaign).where(PromoCampaign.id == campaign.id))
    c_updated = res_camp.scalar_one()
    assert c_updated.redemptions_used == 0


@pytest.mark.asyncio
async def test_raw_token_and_hash_never_in_error_object(db_session: AsyncSession):
    """Test raw token and code_hash are never present in error messages, repr, or attributes."""
    token = "m7q4n9x2r5kd"
    token_hash = hash_promo_token(token)

    service = PromoCampaignService(db_session)
    user_id = uuid.uuid4()

    with pytest.raises(PromoDomainError) as exc_info:
        await service.preview(user_id, token)

    err = exc_info.value
    error_dump = f"{str(err)} {repr(err)} {vars(err)} {err.code} {err.safe_message}"
    assert token not in error_dump
    assert token_hash not in error_dump
