# ############################################################################
# AI_HEADER: MODULE_TESTS_PROMO_CAMPAIGN_SERVICE
# ROLE: Unit and domain tests for PromoCampaignService preview, redeem, locking, and observability contracts (Phase 06A, 06B & 06C1).
# DEPENDENCIES: pytest, sqlalchemy, app.db.models, app.services.promo_campaign_service
# GRACE_ANCHORS: [PROMO_CAMPAIGN_SERVICE_TESTS]
# WAVE: W-NAMED-PROMO-CAMPAIGN
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-PROMO-CAMPAIGN-SERVICE
# purpose: Validate promo token format rules, hash calculation, campaign preview & redeem state validation (invalid, inactive, expired, full, already redeemed ordering), start/end boundaries, base vs strict profile completeness, grant creation, credit expiry, natal reuse, FOR UPDATE lock statements, and structured log events without PII.
# owns:
#   - apps/api/tests/test_promo_campaign_service.py
# inputs: AsyncSession database fixture and User/PromoCampaign/Product DB records
# outputs: Pytest execution assertions
# dependencies:
#   - app.services.promo_campaign_service (PromoCampaignService, PromoDomainError, hash_promo_token, PROMO_TOKEN_REGEX)
#   - app.db.models (User, UserProfile, PromoCampaign, PromoRedemption, Product, Purchase, HoraryCredit, AccessLedger)
# side_effects: database transactions in test runner
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
#   - test_default_happy_path_redeem
#   - test_existing_future_access_defers_promo_start
#   - test_existing_fulfilled_natal_entitlement_reused
#   - test_unlock_natal_false_accepts_base_complete_profile
#   - test_natal_incomplete_raises_profile_incomplete_without_mutations
#   - test_duplicate_sequential_redeem_raises_already_redeemed
#   - test_redeem_validation_error_codes
#   - test_event_order_commit_before_success_log
#   - test_domain_rejection_logs_only_promo_redemption_rejected
#   - test_injected_flush_failure_parameterized
#   - test_injected_commit_failure_rolls_back_and_logs_failed
#   - test_privacy_no_token_hash_or_name_in_logs
#   - test_postgresql_compiled_selects_include_for_update
# owned_tests:
#   - apps/api/tests/test_promo_campaign_service.py
# END_MODULE_MAP: M-TESTS-PROMO-CAMPAIGN-SERVICE

import json
import uuid
import unittest.mock
import pytest
from datetime import date, time, datetime, timedelta, timezone
from decimal import Decimal as D
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    User,
    UserProfile,
    PromoCampaign,
    PromoRedemption,
    AccessLedger,
    HoraryCredit,
    Product,
    Purchase,
    Subscription,
    Payment,
)
from app.services.natal_context_service import NatalContextService
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


async def seed_natal_product(db_session: AsyncSession) -> None:
    res = await db_session.execute(select(Product).where(Product.slug == "natal_full_report"))
    if res.scalar_one_or_none() is None:
        p = Product(
            slug="natal_full_report",
            name="Полный натальный отчёт",
            description="Натальный отчёт",
            product_type="one_time",
            price_kopecks=39900,
            currency="RUB",
            period_days=None,
            horary_quota=None,
            is_active=True,
        )
        db_session.add(p)
        await db_session.commit()


# ── Preview Tests ─────────────────────────────────────────────────────────────

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
    user_id = user.id

    now = datetime.now(timezone.utc)
    token = "m7q4n9x2r5kd"

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

    redemption = PromoRedemption(campaign_id=campaign.id, user_id=user_id)
    db_session.add(redemption)
    await db_session.commit()

    with pytest.raises(PromoDomainError) as exc:
        await service.preview(user_id, token, now=now)
    assert exc.value.code == "ALREADY_REDEEMED"
    assert exc.value.safe_message == "Промокод уже активирован"

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

    with pytest.raises(PromoDomainError) as exc:
        await service.preview(user_id, "m7q4n9x2r5kd", now=now)
    assert exc.value.code == "INVALID_CODE"

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
    user_id = user.id

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

    preview_data = await service.preview(user_id, "m7q4n9x2r5kd", now=start_time)
    assert preview_data.offer.display_name == "Boundary Promo"

    before_start = start_time - timedelta(microseconds=1)
    with pytest.raises(PromoDomainError) as exc:
        await service.preview(user_id, "m7q4n9x2r5kd", now=before_start)
    assert exc.value.code == "INVALID_CODE"


@pytest.mark.asyncio
async def test_end_exclusive_boundary(db_session: AsyncSession):
    """Test activation_ends_at is exclusive: valid 1 microsecond before, expired at exact end."""
    service = PromoCampaignService(db_session)
    user = User(tg_user_id=2002, tg_username="boundary_user2")
    db_session.add(user)
    await db_session.commit()
    user_id = user.id

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

    before_end = end_time - timedelta(microseconds=1)
    preview_data = await service.preview(user_id, "abc23456789a", now=before_end)
    assert preview_data.offer.display_name == "Boundary Promo 2"

    with pytest.raises(PromoDomainError) as exc:
        await service.preview(user_id, "abc23456789a", now=end_time)
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
    user_id = user.id

    profile = create_test_user_profile(user_id, has_time=False)
    db_session.add(profile)
    await db_session.commit()

    service = PromoCampaignService(db_session)
    preview_data = await service.preview(user_id, "m7q4n9x2r5kd", now=now)

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
    u1_id = u1.id
    u2_id = u2.id

    p1 = create_test_user_profile(u1_id, has_time=False)
    p2 = create_test_user_profile(u2_id, has_time=True)
    db_session.add_all([p1, p2])
    await db_session.commit()

    service = PromoCampaignService(db_session)

    prev1 = await service.preview(u1_id, "m7q4n9x2r5kd", now=now)
    assert prev1.profile_complete is False

    prev2 = await service.preview(u2_id, "m7q4n9x2r5kd", now=now)
    assert prev2.profile_complete is True


@pytest.mark.asyncio
async def test_preview_makes_zero_mutations(db_session: AsyncSession):
    """Test preview makes zero mutations to database tables."""
    now = datetime.now(timezone.utc)
    campaign = create_test_campaign(token="m7q4n9x2r5kd", now=now)
    user = User(tg_user_id=444, tg_username="u4")
    db_session.add_all([campaign, user])
    await db_session.commit()
    user_id = user.id
    campaign_id = campaign.id

    profile = create_test_user_profile(user_id)
    db_session.add(profile)
    await db_session.commit()

    service = PromoCampaignService(db_session)
    await service.preview(user_id, "m7q4n9x2r5kd", now=now)

    res_red = await db_session.execute(select(PromoRedemption))
    assert len(res_red.scalars().all()) == 0

    res_led = await db_session.execute(select(AccessLedger))
    assert len(res_led.scalars().all()) == 0

    res_cred = await db_session.execute(select(HoraryCredit))
    assert len(res_cred.scalars().all()) == 0

    res_pur = await db_session.execute(select(Purchase))
    assert len(res_pur.scalars().all()) == 0

    res_camp = await db_session.execute(select(PromoCampaign).where(PromoCampaign.id == campaign_id))
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


# ── Redeem Tests (Phase 06B & 06C1) ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_default_happy_path_redeem(db_session: AsyncSession):
    """Test default happy path creates subscription ledger, gift credit with exact expiry, delivered purchase, redemption refs all, counter=1, no Subscription/Payment."""
    await seed_natal_product(db_session)

    now = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    token = "m7q4n9x2r5kd"

    campaign = create_test_campaign(
        display_name="Summer Full Pack",
        token=token,
        access_days=30,
        bonus_credits=50,
        unlock_natal=True,
        now=now,
    )
    user = User(tg_user_id=7001, tg_username="happy_user")
    db_session.add_all([campaign, user])
    await db_session.commit()
    user_id = user.id
    campaign_id = campaign.id

    profile = create_test_user_profile(user_id, has_time=True)
    db_session.add(profile)
    await db_session.commit()

    service = PromoCampaignService(db_session)
    redeem_data = await service.redeem(user_id, token, now=now)

    assert redeem_data.offer.display_name == "Summer Full Pack"
    assert redeem_data.offer.access_days == 30
    assert redeem_data.offer.bonus_credits == 50
    assert redeem_data.offer.unlock_natal is True

    assert redeem_data.grants.access_starts_at == date(2026, 7, 24)
    assert redeem_data.grants.access_until == date(2026, 8, 22)
    assert redeem_data.grants.bonus_credits == 50
    assert redeem_data.grants.bonus_credits_expires_at == datetime(
        2026, 8, 23, 0, 0, 0, tzinfo=timezone.utc
    )
    assert redeem_data.grants.natal_unlocked is True
    assert redeem_data.grants.natal_already_owned is False

    res_led = await db_session.execute(select(AccessLedger).where(AccessLedger.user_id == user_id))
    ledgers = res_led.scalars().all()
    assert len(ledgers) == 1
    assert ledgers[0].entry_type == "subscription"
    assert ledgers[0].days_granted == 30
    assert ledgers[0].start_date == date(2026, 7, 24)
    assert ledgers[0].end_date == date(2026, 8, 22)

    res_cred = await db_session.execute(select(HoraryCredit).where(HoraryCredit.user_id == user_id))
    credits = res_cred.scalars().all()
    assert len(credits) == 1
    assert credits[0].source == "gift"
    assert credits[0].amount == 50
    assert credits[0].used_amount == 0
    assert credits[0].access_week_start is None
    assert credits[0].access_week_end is None
    assert credits[0].expires_at is not None
    assert credits[0].expires_at.year == 2026
    assert credits[0].expires_at.month == 8
    assert credits[0].expires_at.day == 23
    assert credits[0].expires_at.hour == 0
    assert credits[0].expires_at.minute == 0
    assert credits[0].expires_at.second == 0
    meta = json.loads(credits[0].metadata_json)
    assert meta == {"grant_type": "promo", "campaign_id": str(campaign_id)}

    res_pur = await db_session.execute(select(Purchase).where(Purchase.user_id == user_id))
    purchases = res_pur.scalars().all()
    assert len(purchases) == 1
    assert purchases[0].product_slug == "natal_full_report"
    assert purchases[0].status == "delivered"
    assert purchases[0].payment_id is None
    assert purchases[0].horary_quota_added is None
    context_hash = NatalContextService.compute_profile_hash(profile)
    assert purchases[0].context_hash == context_hash

    res_red = await db_session.execute(select(PromoRedemption).where(PromoRedemption.user_id == user_id))
    redemptions = res_red.scalars().all()
    assert len(redemptions) == 1
    assert redemptions[0].campaign_id == campaign_id
    assert redemptions[0].access_ledger_id == ledgers[0].id
    assert redemptions[0].credit_id == credits[0].id
    assert redemptions[0].natal_purchase_id == purchases[0].id

    res_camp = await db_session.execute(select(PromoCampaign).where(PromoCampaign.id == campaign_id))
    assert res_camp.scalar_one().redemptions_used == 1

    res_sub = await db_session.execute(select(Subscription))
    assert len(res_sub.scalars().all()) == 0
    res_pay = await db_session.execute(select(Payment))
    assert len(res_pay.scalars().all()) == 0


@pytest.mark.asyncio
async def test_existing_future_access_defers_promo_start(db_session: AsyncSession):
    """Test existing active/future access defers promo start to day after latest end."""
    await seed_natal_product(db_session)

    now = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    token = "m7q4n9x2r5kd"

    user = User(tg_user_id=7002, tg_username="existing_access_user")
    db_session.add(user)
    await db_session.commit()
    user_id = user.id

    existing_ledger = AccessLedger(
        user_id=user_id,
        entry_type="subscription",
        days_granted=30,
        start_date=date(2026, 7, 17),
        end_date=date(2026, 8, 15),
    )
    campaign = create_test_campaign(token=token, access_days=10, bonus_credits=20, unlock_natal=False, now=now)
    db_session.add_all([existing_ledger, campaign])
    await db_session.commit()

    profile = create_test_user_profile(user_id)
    db_session.add(profile)
    await db_session.commit()

    service = PromoCampaignService(db_session)
    redeem_data = await service.redeem(user_id, token, now=now)

    assert redeem_data.grants.access_starts_at == date(2026, 8, 16)
    assert redeem_data.grants.access_until == date(2026, 8, 25)
    assert redeem_data.grants.bonus_credits_expires_at == datetime(
        2026, 8, 26, 0, 0, 0, tzinfo=timezone.utc
    )


@pytest.mark.asyncio
async def test_existing_fulfilled_natal_entitlement_reused(db_session: AsyncSession):
    """Test existing fulfilled natal purchase for same user+context is reused and does not create duplicate Purchase."""
    await seed_natal_product(db_session)

    now = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    token = "m7q4n9x2r5kd"

    user = User(tg_user_id=7003, tg_username="natal_owner")
    db_session.add(user)
    await db_session.commit()
    user_id = user.id

    profile = create_test_user_profile(user_id, has_time=True)
    db_session.add(profile)
    await db_session.commit()

    context_hash = NatalContextService.compute_profile_hash(profile)

    existing_purchase = Purchase(
        user_id=user_id,
        product_slug="natal_full_report",
        status="delivered",
        payment_id=None,
        horary_quota_added=None,
        context_hash=context_hash,
    )
    campaign = create_test_campaign(token=token, access_days=0, bonus_credits=0, unlock_natal=True, now=now)
    db_session.add_all([existing_purchase, campaign])
    await db_session.commit()

    service = PromoCampaignService(db_session)
    redeem_data = await service.redeem(user_id, token, now=now)

    assert redeem_data.grants.natal_unlocked is True
    assert redeem_data.grants.natal_already_owned is True

    res_pur = await db_session.execute(select(Purchase).where(Purchase.user_id == user_id))
    purchases = res_pur.scalars().all()
    assert len(purchases) == 1
    assert purchases[0].id == existing_purchase.id

    res_red = await db_session.execute(select(PromoRedemption).where(PromoRedemption.user_id == user_id))
    redemption = res_red.scalar_one()
    assert redemption.access_ledger_id is None
    assert redemption.credit_id is None
    assert redemption.natal_purchase_id == existing_purchase.id


@pytest.mark.asyncio
async def test_unlock_natal_false_accepts_base_complete_profile(db_session: AsyncSession):
    """Test campaign with unlock_natal=False accepts base-complete profile without birth_time and creates only enabled grants."""
    now = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    token = "m7q4n9x2r5kd"

    user = User(tg_user_id=7004, tg_username="base_user")
    campaign = create_test_campaign(
        token=token,
        access_days=14,
        bonus_credits=0,
        unlock_natal=False,
        now=now,
    )
    db_session.add_all([user, campaign])
    await db_session.commit()
    user_id = user.id

    profile = create_test_user_profile(user_id, has_time=False)
    db_session.add(profile)
    await db_session.commit()

    service = PromoCampaignService(db_session)
    redeem_data = await service.redeem(user_id, token, now=now)

    assert redeem_data.grants.access_starts_at == date(2026, 7, 24)
    assert redeem_data.grants.access_until == date(2026, 8, 6)
    assert redeem_data.grants.bonus_credits == 0
    assert redeem_data.grants.natal_unlocked is False
    assert redeem_data.grants.bonus_credits_expires_at is None

    res_red = await db_session.execute(select(PromoRedemption).where(PromoRedemption.user_id == user_id))
    redemption = res_red.scalar_one()
    assert redemption.access_ledger_id is not None
    assert redemption.credit_id is None
    assert redemption.natal_purchase_id is None


@pytest.mark.asyncio
async def test_natal_incomplete_raises_profile_incomplete_without_mutations(db_session: AsyncSession):
    """Test campaign with unlock_natal=True raises PROFILE_INCOMPLETE for base-complete user lacking birth_time without mutating DB."""
    await seed_natal_product(db_session)

    now = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    token = "m7q4n9x2r5kd"

    user = User(tg_user_id=7005, tg_username="incomplete_natal_user")
    campaign = create_test_campaign(token=token, unlock_natal=True, now=now)
    db_session.add_all([user, campaign])
    await db_session.commit()
    user_id = user.id
    campaign_id = campaign.id

    profile = create_test_user_profile(user_id, has_time=False)
    db_session.add(profile)
    await db_session.commit()

    service = PromoCampaignService(db_session)

    with pytest.raises(PromoDomainError) as exc:
        await service.redeem(user_id, token, now=now)

    assert exc.value.code == "PROFILE_INCOMPLETE"
    assert exc.value.safe_message == "Заполните профиль для активации промокода"

    res_red = await db_session.execute(select(PromoRedemption).where(PromoRedemption.user_id == user_id))
    assert len(res_red.scalars().all()) == 0

    for model in (AccessLedger, HoraryCredit, Purchase):
        rows = await db_session.execute(select(model).where(model.user_id == user_id))
        assert len(rows.scalars().all()) == 0

    res_camp = await db_session.execute(select(PromoCampaign).where(PromoCampaign.id == campaign_id))
    assert res_camp.scalar_one().redemptions_used == 0


@pytest.mark.asyncio
async def test_duplicate_sequential_redeem_raises_already_redeemed(db_session: AsyncSession):
    """Test duplicate sequential redeem raises ALREADY_REDEEMED and leaves counter and grant counts unchanged."""
    await seed_natal_product(db_session)

    now = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    token = "m7q4n9x2r5kd"

    user = User(tg_user_id=7006, tg_username="dupe_redeemer")
    campaign = create_test_campaign(token=token, now=now)
    db_session.add_all([user, campaign])
    await db_session.commit()
    user_id = user.id
    campaign_id = campaign.id

    profile = create_test_user_profile(user_id, has_time=True)
    db_session.add(profile)
    await db_session.commit()

    service = PromoCampaignService(db_session)

    r1 = await service.redeem(user_id, token, now=now)
    assert r1.offer.display_name == campaign.display_name

    with pytest.raises(PromoDomainError) as exc:
        await service.redeem(user_id, token, now=now)

    assert exc.value.code == "ALREADY_REDEEMED"

    res_red = await db_session.execute(select(PromoRedemption).where(PromoRedemption.user_id == user_id))
    assert len(res_red.scalars().all()) == 1

    res_camp = await db_session.execute(select(PromoCampaign).where(PromoCampaign.id == campaign_id))
    assert res_camp.scalar_one().redemptions_used == 1

    expected_counts = ((AccessLedger, 1), (HoraryCredit, 1), (Purchase, 1))
    for model, expected_count in expected_counts:
        rows = await db_session.execute(select(model).where(model.user_id == user_id))
        assert len(rows.scalars().all()) == expected_count


@pytest.mark.parametrize(
    "setup_kind, expected_code",
    [
        ("invalid_format", "INVALID_CODE"),
        ("unknown_campaign", "INVALID_CODE"),
        ("inactive", "INVALID_CODE"),
        ("not_started", "INVALID_CODE"),
        ("expired", "CAMPAIGN_EXPIRED"),
        ("full", "CAMPAIGN_FULL"),
    ],
)
@pytest.mark.asyncio
async def test_redeem_validation_error_codes(db_session: AsyncSession, setup_kind: str, expected_code: str):
    """Test redeem validation error codes for invalid format, unknown, inactive, not-started, expired, and full campaigns."""
    service = PromoCampaignService(db_session)
    user = User(tg_user_id=8000 + hash(setup_kind) % 1000, tg_username=f"user_{setup_kind}")
    db_session.add(user)
    await db_session.commit()
    user_id = user.id

    profile = create_test_user_profile(user_id, has_time=True)
    db_session.add(profile)
    await db_session.commit()

    now = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    token = "m7q4n9x2r5kd"

    if setup_kind == "invalid_format":
        token = "invalid_token_format"
    elif setup_kind == "unknown_campaign":
        token = "abc23456789a"
    elif setup_kind == "inactive":
        c = create_test_campaign(token=token, active=False, now=now)
        db_session.add(c)
        await db_session.commit()
    elif setup_kind == "not_started":
        c = create_test_campaign(token=token, starts_delta_days=5, ends_delta_days=30, now=now)
        db_session.add(c)
        await db_session.commit()
    elif setup_kind == "expired":
        c = create_test_campaign(token=token, starts_delta_days=-10, ends_delta_days=-1, now=now)
        db_session.add(c)
        await db_session.commit()
    elif setup_kind == "full":
        c = create_test_campaign(token=token, max_redemptions=5, redemptions_used=5, now=now)
        db_session.add(c)
        await db_session.commit()

    with pytest.raises(PromoDomainError) as exc:
        await service.redeem(user_id, token, now=now)

    assert exc.value.code == expected_code


# ── Observability & Fault-Injection Tests (Phase 06C1) ─────────────────────────

@pytest.mark.asyncio
async def test_event_order_commit_before_success_log(db_session: AsyncSession):
    """Test db.commit finishes BEFORE promo.redemption_succeeded log event is emitted."""
    await seed_natal_product(db_session)

    now = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    token = "m7q4n9x2r5kd"

    campaign = create_test_campaign(token=token, now=now)
    user = User(tg_user_id=9001, tg_username="log_order_user")
    db_session.add_all([campaign, user])
    await db_session.commit()
    user_id = user.id

    profile = create_test_user_profile(user_id, has_time=True)
    db_session.add(profile)
    await db_session.commit()

    call_order = []
    original_commit = db_session.commit

    async def mock_commit():
        call_order.append("commit")
        await original_commit()

    db_session.commit = mock_commit  # type: ignore[assignment]

    def mock_log_event(event, **kwargs):
        call_order.append(f"log:{event}")

    with unittest.mock.patch("app.services.promo_campaign_service.log_event", side_effect=mock_log_event):
        service = PromoCampaignService(db_session)
        await service.redeem(user_id, token, now=now)

    assert call_order == ["commit", "log:promo.redemption_succeeded"]


@pytest.mark.asyncio
async def test_domain_rejection_logs_only_promo_redemption_rejected(db_session: AsyncSession):
    """Test domain error during redeem logs promo.redemption_rejected with stable code and campaign_id."""
    now = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    token = "m7q4n9x2r5kd"

    campaign = create_test_campaign(token=token, active=False, now=now)
    user = User(tg_user_id=9002, tg_username="rejected_log_user")
    db_session.add_all([campaign, user])
    await db_session.commit()
    user_id = user.id
    campaign_id = campaign.id

    profile = create_test_user_profile(user_id, has_time=True)
    db_session.add(profile)
    await db_session.commit()

    logged_events = []

    def mock_log_event(event, **kwargs):
        logged_events.append((event, kwargs))

    with unittest.mock.patch("app.services.promo_campaign_service.log_event", side_effect=mock_log_event):
        service = PromoCampaignService(db_session)
        with pytest.raises(PromoDomainError) as exc:
            await service.redeem(user_id, token, now=now)

        assert exc.value.code == "INVALID_CODE"

    assert len(logged_events) == 1
    event_name, kwargs = logged_events[0]
    assert event_name == "promo.redemption_rejected"
    assert kwargs.get("payload") == {
        "error_code": "INVALID_CODE",
        "campaign_id": str(campaign_id),
    }


@pytest.mark.parametrize("flush_fail_index", [1, 2, 3, 4])
@pytest.mark.asyncio
async def test_injected_flush_failure_parameterized(db_session: AsyncSession, flush_fail_index: int):
    """Test injected db.flush error at any call stage rolls back all grants/redemption/counter and logs exactly failed event."""
    await seed_natal_product(db_session)

    now = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    token = "m7q4n9x2r5kd"

    campaign = create_test_campaign(token=token, now=now)
    user = User(tg_user_id=9100 + flush_fail_index, tg_username=f"flush_user_{flush_fail_index}")
    db_session.add_all([campaign, user])
    await db_session.commit()
    user_id = user.id
    campaign_id = campaign.id

    profile = create_test_user_profile(user_id, has_time=True)
    db_session.add(profile)
    await db_session.commit()

    original_flush = db_session.flush
    flush_counter = 0

    async def failing_flush():
        nonlocal flush_counter
        flush_counter += 1
        if flush_counter == flush_fail_index:
            raise RuntimeError(f"Injected flush failure on call {flush_fail_index}")
        await original_flush()

    db_session.flush = failing_flush  # type: ignore[assignment]

    logged_events = []

    def mock_log_event(event, **kwargs):
        logged_events.append((event, kwargs))

    with unittest.mock.patch("app.services.promo_campaign_service.log_event", side_effect=mock_log_event):
        service = PromoCampaignService(db_session)
        with pytest.raises(RuntimeError, match=f"Injected flush failure on call {flush_fail_index}"):
            await service.redeem(user_id, token, now=now)

    # Verify exactly 1 log event emitted and it is promo.redemption_failed
    assert len(logged_events) == 1
    assert logged_events[0][0] == "promo.redemption_failed"
    assert logged_events[0][1].get("payload") == {
        "error_kind": "RuntimeError",
        "campaign_id": str(campaign_id),
    }

    # Restore flush for DB state assertions
    db_session.flush = original_flush

    # Verify zero grants/redemption rows in DB and counter = 0
    for model in (AccessLedger, HoraryCredit, Purchase, PromoRedemption):
        rows = await db_session.execute(select(model).where(model.user_id == user_id))
        assert len(rows.scalars().all()) == 0

    res_camp = await db_session.execute(select(PromoCampaign).where(PromoCampaign.id == campaign_id))
    assert res_camp.scalar_one().redemptions_used == 0


@pytest.mark.asyncio
async def test_injected_commit_failure_rolls_back_and_logs_failed(db_session: AsyncSession):
    """Test injected db.commit error during redeem rolls back all rows and emits exactly promo.redemption_failed with no success event."""
    await seed_natal_product(db_session)

    now = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    token = "m7q4n9x2r5kd"

    campaign = create_test_campaign(token=token, now=now)
    user = User(tg_user_id=9004, tg_username="commit_fail_user")
    db_session.add_all([campaign, user])
    await db_session.commit()
    user_id = user.id
    campaign_id = campaign.id

    profile = create_test_user_profile(user_id, has_time=True)
    db_session.add(profile)
    await db_session.commit()

    original_commit = db_session.commit

    async def failing_commit():
        raise RuntimeError("Injected commit DB failure")

    db_session.commit = failing_commit  # type: ignore[assignment]

    logged_events = []

    def mock_log_event(event, **kwargs):
        logged_events.append((event, kwargs))

    with unittest.mock.patch("app.services.promo_campaign_service.log_event", side_effect=mock_log_event):
        service = PromoCampaignService(db_session)
        with pytest.raises(RuntimeError, match="Injected commit DB failure"):
            await service.redeem(user_id, token, now=now)

    assert len(logged_events) == 1
    assert logged_events[0][0] == "promo.redemption_failed"
    assert logged_events[0][1].get("payload") == {
        "error_kind": "RuntimeError",
        "campaign_id": str(campaign_id),
    }

    db_session.commit = original_commit

    for model in (AccessLedger, HoraryCredit, Purchase, PromoRedemption):
        rows = await db_session.execute(select(model).where(model.user_id == user_id))
        assert len(rows.scalars().all()) == 0

    res_camp = await db_session.execute(select(PromoCampaign).where(PromoCampaign.id == campaign_id))
    assert res_camp.scalar_one().redemptions_used == 0


@pytest.mark.asyncio
async def test_privacy_no_token_hash_or_name_in_logs(db_session: AsyncSession):
    """Test all emitted log event payloads for success, rejection, and failure contain zero PII (token/hash/display_name)."""
    await seed_natal_product(db_session)

    now = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    token = "m7q4n9x2r5kd"
    token_hash = hash_promo_token(token)

    campaign = create_test_campaign(display_name="SECRET_NAME_DONOT_LEAK", token=token, now=now)
    user = User(tg_user_id=9005, tg_username="pii_log_user")
    db_session.add_all([campaign, user])
    await db_session.commit()
    user_id = user.id

    profile = create_test_user_profile(user_id, has_time=True)
    db_session.add(profile)
    await db_session.commit()

    logged_calls = []

    def mock_log_event(event, **kwargs):
        logged_calls.append((event, kwargs))

    # 1. Test success log privacy
    with unittest.mock.patch("app.services.promo_campaign_service.log_event", side_effect=mock_log_event):
        service = PromoCampaignService(db_session)
        await service.redeem(user_id, token, now=now)

    # 2. Test rejection log privacy
    with unittest.mock.patch("app.services.promo_campaign_service.log_event", side_effect=mock_log_event):
        with pytest.raises(PromoDomainError):
            await service.redeem(user_id, token, now=now)

    # 3. Test failure log privacy
    original_flush = db_session.flush

    async def failing_flush():
        raise RuntimeError("Injected fail for privacy check")

    db_session.flush = failing_flush  # type: ignore[assignment]
    other_user = User(tg_user_id=9006, tg_username="pii_user2")
    db_session.add(other_user)
    # Use direct SQL insert or commit before flush override
    db_session.flush = original_flush
    await db_session.commit()

    p2 = create_test_user_profile(other_user.id, has_time=True)
    db_session.add(p2)
    await db_session.commit()

    db_session.flush = failing_flush  # type: ignore[assignment]

    with unittest.mock.patch("app.services.promo_campaign_service.log_event", side_effect=mock_log_event):
        with pytest.raises(RuntimeError):
            await service.redeem(other_user.id, token, now=now)

    db_session.flush = original_flush

    all_logs_str = str(logged_calls)
    assert token not in all_logs_str
    assert token_hash not in all_logs_str
    assert "SECRET_NAME_DONOT_LEAK" not in all_logs_str


@pytest.mark.asyncio
async def test_postgresql_compiled_selects_include_for_update(db_session: AsyncSession):
    """Test captured SQL statements executed during redeem both compile with FOR UPDATE in PostgreSQL dialect, with campaign locked before user."""
    await seed_natal_product(db_session)

    now = datetime(2026, 7, 24, 12, 0, 0, tzinfo=timezone.utc)
    token = "m7q4n9x2r5kd"

    campaign = create_test_campaign(token=token, now=now)
    user = User(tg_user_id=9007, tg_username="lock_capture_user")
    db_session.add_all([campaign, user])
    await db_session.commit()
    user_id = user.id

    profile = create_test_user_profile(user_id, has_time=True)
    db_session.add(profile)
    await db_session.commit()

    captured_statements = []
    original_execute = db_session.execute

    async def capture_execute(statement, *args, **kwargs):
        captured_statements.append(statement)
        return await original_execute(statement, *args, **kwargs)

    db_session.execute = capture_execute  # type: ignore[assignment]

    service = PromoCampaignService(db_session)
    await service.redeem(user_id, token, now=now)

    # Filter captured Select statements that use FOR UPDATE when compiled with PostgreSQL dialect
    pg_for_update_tables = []
    for stmt in captured_statements:
        try:
            compiled = str(stmt.compile(dialect=postgresql.dialect()))
            if "FOR UPDATE" in compiled:
                if "promo_campaigns" in compiled:
                    pg_for_update_tables.append("promo_campaigns")
                elif "users" in compiled:
                    pg_for_update_tables.append("users")
        except Exception:
            pass

    assert pg_for_update_tables == ["promo_campaigns", "users"]
