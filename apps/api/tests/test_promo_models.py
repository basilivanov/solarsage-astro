# ############################################################################
# AI_HEADER: MODULE_TESTS_PROMO_MODELS
# ROLE: Unit tests for PromoCampaign and PromoRedemption ORM models and DB constraints.
# DEPENDENCIES: pytest, sqlalchemy, app.db.models
# GRACE_ANCHORS: [PROMO_MODELS_TESTS]
# WAVE: W-NAMED-PROMO-CAMPAIGN
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-PROMO-MODELS
# purpose: Validate ORM models, unique constraints, check constraints, foreign keys, and nullable fields for promo campaigns and redemptions.
# owns:
#   - apps/api/tests/test_promo_models.py
# inputs: AsyncSession database fixture
# outputs: Pytest execution assertions
# dependencies:
#   - app.db.models (User, PromoCampaign, PromoRedemption)
# side_effects: database transactions in test runner
# failure_policy: raise assertions
# END_MODULE_CONTRACT: M-TESTS-PROMO-MODELS

# START_MODULE_MAP: M-TESTS-PROMO-MODELS
# public_entrypoints:
#   - test_valid_promo_campaign_and_redemption_insert
#   - test_duplicate_code_hash_rejected
#   - test_duplicate_campaign_user_redemption_rejected
#   - test_invalid_window_rejected
#   - test_equal_window_rejected
#   - test_invalid_max_redemptions_rejected
#   - test_redemptions_used_exceeds_max_rejected
#   - test_negative_redemptions_used_rejected
#   - test_negative_access_days_rejected
#   - test_negative_bonus_credits_rejected
#   - test_credits_require_access_days_rejected
#   - test_at_least_one_benefit_required_rejected
#   - test_nullable_grant_references_accepted
# owned_tests:
#   - apps/api/tests/test_promo_models.py
# END_MODULE_MAP: M-TESTS-PROMO-MODELS

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, PromoCampaign, PromoRedemption


@pytest.mark.asyncio
async def test_valid_promo_campaign_and_redemption_insert(db_session: AsyncSession):
    """Test valid campaign creation and redemption insert."""
    now = datetime.now(timezone.utc)
    campaign = PromoCampaign(
        display_name="Summer Promo 2026",
        code_hash="a" * 64,
        active=True,
        activation_starts_at=now - timedelta(days=1),
        activation_ends_at=now + timedelta(days=30),
        max_redemptions=100,
        redemptions_used=0,
        access_days=14,
        bonus_credits=10,
        unlock_natal=True,
    )
    db_session.add(campaign)
    await db_session.commit()

    user = User(tg_user_id=987654321, tg_username="promouser")
    db_session.add(user)
    await db_session.commit()

    redemption = PromoRedemption(
        campaign_id=campaign.id,
        user_id=user.id,
        access_ledger_id=None,
        credit_id=None,
        natal_purchase_id=None,
    )
    db_session.add(redemption)
    await db_session.commit()

    assert campaign.id is not None
    assert redemption.id is not None
    assert redemption.campaign_id == campaign.id
    assert redemption.user_id == user.id


@pytest.mark.asyncio
async def test_duplicate_code_hash_rejected(db_session: AsyncSession):
    """Test unique constraint on code_hash."""
    now = datetime.now(timezone.utc)
    shared_hash = "b" * 64

    c1 = PromoCampaign(
        display_name="Promo 1",
        code_hash=shared_hash,
        activation_starts_at=now,
        activation_ends_at=now + timedelta(days=10),
        max_redemptions=50,
    )
    db_session.add(c1)
    await db_session.commit()

    c2 = PromoCampaign(
        display_name="Promo 2",
        code_hash=shared_hash,
        activation_starts_at=now,
        activation_ends_at=now + timedelta(days=10),
        max_redemptions=50,
    )
    db_session.add(c2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_duplicate_campaign_user_redemption_rejected(db_session: AsyncSession):
    """Test unique constraint on (campaign_id, user_id)."""
    now = datetime.now(timezone.utc)
    campaign = PromoCampaign(
        display_name="OnePerUser Promo",
        code_hash="c" * 64,
        activation_starts_at=now,
        activation_ends_at=now + timedelta(days=10),
        max_redemptions=10,
    )
    user = User(tg_user_id=11223344, tg_username="dupeuser")
    db_session.add_all([campaign, user])
    await db_session.commit()

    r1 = PromoRedemption(campaign_id=campaign.id, user_id=user.id)
    db_session.add(r1)
    await db_session.commit()

    r2 = PromoRedemption(campaign_id=campaign.id, user_id=user.id)
    db_session.add(r2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_invalid_window_rejected(db_session: AsyncSession):
    """Test CheckConstraint activation_ends_at > activation_starts_at."""
    now = datetime.now(timezone.utc)
    campaign = PromoCampaign(
        display_name="Inverted Window",
        code_hash="d" * 64,
        activation_starts_at=now + timedelta(days=5),
        activation_ends_at=now,  # ends before start!
        max_redemptions=10,
    )
    db_session.add(campaign)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_equal_window_rejected(db_session: AsyncSession):
    """Test CheckConstraint activation_ends_at > activation_starts_at with equal timestamps."""
    now = datetime.now(timezone.utc)
    campaign = PromoCampaign(
        display_name="Zero Duration Window",
        code_hash="d2" * 32,
        activation_starts_at=now,
        activation_ends_at=now,  # ends equal to start!
        max_redemptions=10,
    )
    db_session.add(campaign)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_invalid_max_redemptions_rejected(db_session: AsyncSession):
    """Test CheckConstraint max_redemptions > 0."""
    now = datetime.now(timezone.utc)
    campaign = PromoCampaign(
        display_name="Zero Max Redemptions",
        code_hash="e" * 64,
        activation_starts_at=now,
        activation_ends_at=now + timedelta(days=1),
        max_redemptions=0,
    )
    db_session.add(campaign)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_redemptions_used_exceeds_max_rejected(db_session: AsyncSession):
    """Test CheckConstraint redemptions_used <= max_redemptions."""
    now = datetime.now(timezone.utc)
    campaign = PromoCampaign(
        display_name="Overused Promo",
        code_hash="f" * 64,
        activation_starts_at=now,
        activation_ends_at=now + timedelta(days=1),
        max_redemptions=5,
        redemptions_used=6,
    )
    db_session.add(campaign)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_negative_redemptions_used_rejected(db_session: AsyncSession):
    """Test CheckConstraint redemptions_used >= 0."""
    now = datetime.now(timezone.utc)
    campaign = PromoCampaign(
        display_name="Negative Used Promo",
        code_hash="f2" * 32,
        activation_starts_at=now,
        activation_ends_at=now + timedelta(days=1),
        max_redemptions=5,
        redemptions_used=-1,
    )
    db_session.add(campaign)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_negative_access_days_rejected(db_session: AsyncSession):
    """Test CheckConstraint access_days >= 0."""
    now = datetime.now(timezone.utc)
    campaign = PromoCampaign(
        display_name="Negative Access Days Promo",
        code_hash="f3" * 32,
        activation_starts_at=now,
        activation_ends_at=now + timedelta(days=1),
        max_redemptions=5,
        access_days=-1,
    )
    db_session.add(campaign)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_negative_bonus_credits_rejected(db_session: AsyncSession):
    """Test CheckConstraint bonus_credits >= 0."""
    now = datetime.now(timezone.utc)
    campaign = PromoCampaign(
        display_name="Negative Bonus Credits Promo",
        code_hash="f4" * 32,
        activation_starts_at=now,
        activation_ends_at=now + timedelta(days=1),
        max_redemptions=5,
        access_days=10,
        bonus_credits=-1,
    )
    db_session.add(campaign)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_credits_require_access_days_rejected(db_session: AsyncSession):
    """Test CheckConstraint bonus_credits = 0 OR access_days > 0."""
    now = datetime.now(timezone.utc)
    campaign = PromoCampaign(
        display_name="Credits Without Access",
        code_hash="1" * 64,
        activation_starts_at=now,
        activation_ends_at=now + timedelta(days=1),
        max_redemptions=10,
        access_days=0,
        bonus_credits=20,
    )
    db_session.add(campaign)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_at_least_one_benefit_required_rejected(db_session: AsyncSession):
    """Test CheckConstraint access_days > 0 OR bonus_credits > 0 OR unlock_natal = TRUE."""
    now = datetime.now(timezone.utc)
    campaign = PromoCampaign(
        display_name="No Benefits Promo",
        code_hash="2" * 64,
        activation_starts_at=now,
        activation_ends_at=now + timedelta(days=1),
        max_redemptions=10,
        access_days=0,
        bonus_credits=0,
        unlock_natal=False,
    )
    db_session.add(campaign)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_nullable_grant_references_accepted(db_session: AsyncSession):
    """Test nullable grant FK references are accepted when benefits are disabled."""
    now = datetime.now(timezone.utc)
    campaign = PromoCampaign(
        display_name="Natal Only Promo",
        code_hash="3" * 64,
        activation_starts_at=now,
        activation_ends_at=now + timedelta(days=1),
        max_redemptions=10,
        access_days=0,
        bonus_credits=0,
        unlock_natal=True,
    )
    user = User(tg_user_id=55667788, tg_username="nataluser")
    db_session.add_all([campaign, user])
    await db_session.commit()

    redemption = PromoRedemption(
        campaign_id=campaign.id,
        user_id=user.id,
        access_ledger_id=None,
        credit_id=None,
        natal_purchase_id=None,
    )
    db_session.add(redemption)
    await db_session.commit()

    assert redemption.access_ledger_id is None
    assert redemption.credit_id is None
    assert redemption.natal_purchase_id is None
