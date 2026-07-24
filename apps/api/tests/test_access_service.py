# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_ACCESS_SERVICE
# ROLE: Unit tests for AccessService and AccessLedger grant primitives.
# DEPENDENCIES: pytest, sqlalchemy, app.services.access_service, app.db.models
# GRACE_ANCHORS: [ACCESS_SERVICE_TESTS]
# WAVE: W-ACCESS.1, W-NAMED-PROMO-CAMPAIGN
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-ACCESS-SERVICE
# purpose: Validate access control checks, summary generation, next_grant_start calculations, grant_subscription return values, commit=False transaction boundaries, and days <= 0 validation.
# owns:
#   - apps/api/tests/test_access_service.py
# inputs: AsyncSession database fixture and User fixtures
# outputs: Pytest execution assertions
# dependencies:
#   - app.services.access_service (AccessService)
#   - app.db.models (User, AccessLedger)
# side_effects: database transactions in test runner
# failure_policy: raise assertions
# END_MODULE_CONTRACT: M-TESTS-ACCESS-SERVICE

# START_MODULE_MAP: M-TESTS-ACCESS-SERVICE
# public_entrypoints:
#   - test_no_access_entries
#   - test_referral_bonus_14_days
#   - test_referral_plus_subscription
#   - test_next_grant_start_no_ledger
#   - test_next_grant_start_expired_ledger
#   - test_next_grant_start_active_future_multiple_ledgers
#   - test_grant_subscription_returns_row_with_id_and_inclusive_end
#   - test_grant_subscription_commit_false_and_rollback
#   - test_grant_subscription_invalid_days_raises_value_error
# owned_tests:
#   - apps/api/tests/test_access_service.py
# END_MODULE_MAP: M-TESTS-ACCESS-SERVICE

import pytest
from datetime import date, timedelta, timezone, datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.access_service import AccessService
from app.db.models import User, AccessLedger


@pytest.mark.asyncio
async def test_no_access_entries(db_session: AsyncSession):
    """UC-ACCESS-CHECK S3: No access entries → preview."""
    user = User(tg_user_id=12345, tg_username="test")
    db_session.add(user)
    await db_session.commit()

    service = AccessService(db_session)
    state = await service.can_access_day(user.id, datetime.now(timezone.utc).date())

    assert state.state == "preview"
    assert state.reason == "expired_access"
    assert state.referral_days_left is None
    assert state.subscription_active is None


@pytest.mark.asyncio
async def test_referral_bonus_14_days(db_session: AsyncSession):
    """UC-ACCESS-CHECK S1: 14d referral_bonus → days 0..13 full, day 14 preview."""
    user = User(tg_user_id=12345, tg_username="test")
    db_session.add(user)
    await db_session.commit()

    service = AccessService(db_session)
    start_date = datetime.now(timezone.utc).date()
    await service.grant_referral_bonus(user.id, start_date)

    # Check day 0 (today)
    state = await service.can_access_day(user.id, start_date)
    assert state.state == "full"
    assert state.reason == "active_referral_days"
    assert state.referral_days_left == 14
    assert state.subscription_active is None

    # Check day 13 (last day)
    state = await service.can_access_day(user.id, start_date + timedelta(days=13))
    assert state.state == "full"
    assert state.reason == "active_referral_days"
    assert state.referral_days_left == 1

    # Check day 14 (locked - future without access)
    state = await service.can_access_day(user.id, start_date + timedelta(days=14))
    assert state.state == "locked"
    assert state.reason == "outside_access_window"


@pytest.mark.asyncio
async def test_referral_plus_subscription(db_session: AsyncSession):
    """UC-ACCESS-CHECK S2: 14d referral + 30d subscription → consumption order."""
    user = User(tg_user_id=12345, tg_username="test")
    db_session.add(user)
    await db_session.commit()

    service = AccessService(db_session)
    start_date = datetime.now(timezone.utc).date()

    # Grant referral bonus (days 0..13)
    await service.grant_referral_bonus(user.id, start_date)

    # Grant subscription (days 14..43)
    await service.grant_subscription(user.id, start_date + timedelta(days=14), days=30)

    # Check day 0 (referral)
    state = await service.can_access_day(user.id, start_date)
    assert state.state == "full"
    assert state.reason == "active_referral_days"
    assert state.referral_days_left == 14
    assert state.subscription_active is None

    # Check day 13 (last referral day)
    state = await service.can_access_day(user.id, start_date + timedelta(days=13))
    assert state.state == "full"
    assert state.reason == "active_referral_days"
    assert state.referral_days_left == 1

    # Check day 14 (subscription starts)
    state = await service.can_access_day(user.id, start_date + timedelta(days=14))
    assert state.state == "full"
    assert state.reason == "active_subscription"
    assert state.referral_days_left is None
    assert state.subscription_active is True

    # Check day 43 (last subscription day)
    state = await service.can_access_day(user.id, start_date + timedelta(days=43))
    assert state.state == "full"
    assert state.reason == "active_subscription"
    assert state.subscription_active is True

    # Check day 44 (locked - future without access)
    state = await service.can_access_day(user.id, start_date + timedelta(days=44))
    assert state.state == "locked"
    assert state.reason == "outside_access_window"


@pytest.mark.asyncio
async def test_next_grant_start_no_ledger(db_session: AsyncSession):
    """Test next_grant_start returns requested_start when user has no ledger entries."""
    user = User(tg_user_id=123, tg_username="user1")
    db_session.add(user)
    await db_session.commit()

    service = AccessService(db_session)
    requested = date(2026, 7, 24)

    start = await service.next_grant_start(user.id, requested)
    assert start == requested


@pytest.mark.asyncio
async def test_next_grant_start_expired_ledger(db_session: AsyncSession):
    """Test next_grant_start returns requested_start when all ledger entries ended before requested_start."""
    user = User(tg_user_id=124, tg_username="user2")
    db_session.add(user)
    await db_session.commit()

    service = AccessService(db_session)
    # Entry ends on 2026-07-10
    await service.grant_subscription(user.id, date(2026, 7, 1), days=10, commit=True)

    requested = date(2026, 7, 24)
    start = await service.next_grant_start(user.id, requested)
    assert start == requested


@pytest.mark.asyncio
async def test_next_grant_start_active_future_multiple_ledgers(db_session: AsyncSession):
    """Test next_grant_start returns day after max end_date among multiple ledgers."""
    user = User(tg_user_id=125, tg_username="user3")
    db_session.add(user)
    await db_session.commit()

    service = AccessService(db_session)
    # Entry 1: referral ending 2026-07-20
    await service.grant_referral_bonus(user.id, date(2026, 7, 7))
    # Entry 2: subscription ending 2026-08-15
    await service.grant_subscription(user.id, date(2026, 7, 17), days=30, commit=True)

    requested = date(2026, 7, 24)
    start = await service.next_grant_start(user.id, requested)
    # max end_date is 2026-08-15 -> next_grant_start should be 2026-08-16
    assert start == date(2026, 8, 16)


@pytest.mark.asyncio
async def test_grant_subscription_returns_row_with_id_and_inclusive_end(db_session: AsyncSession):
    """Test grant_subscription returns AccessLedger row with assigned ID and inclusive end_date."""
    user = User(tg_user_id=126, tg_username="user4")
    db_session.add(user)
    await db_session.commit()

    service = AccessService(db_session)
    start_date = date(2026, 7, 24)
    entry = await service.grant_subscription(user.id, start_date, days=30, commit=True)

    assert isinstance(entry, AccessLedger)
    assert entry.id is not None
    assert entry.user_id == user.id
    assert entry.entry_type == "subscription"
    assert entry.days_granted == 30
    assert entry.start_date == start_date
    assert entry.end_date == date(2026, 8, 22)  # 2026-07-24 + 29 days


@pytest.mark.asyncio
async def test_grant_subscription_commit_false_and_rollback(db_session: AsyncSession):
    """Test grant_subscription with commit=False stages row with ID, which disappears on rollback."""
    user = User(tg_user_id=127, tg_username="user5")
    db_session.add(user)
    await db_session.commit()

    service = AccessService(db_session)
    entry = await service.grant_subscription(user.id, date(2026, 7, 24), days=15, commit=False)

    assert entry.id is not None

    # Visible in same session/transaction
    result = await db_session.execute(select(AccessLedger).where(AccessLedger.id == entry.id))
    staged = result.scalar_one_or_none()
    assert staged is not None

    # Rollback transaction
    await db_session.rollback()

    # Disappears after rollback
    result_after = await db_session.execute(select(AccessLedger).where(AccessLedger.id == entry.id))
    assert result_after.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_grant_subscription_invalid_days_raises_value_error(db_session: AsyncSession):
    """Test grant_subscription raises ValueError for days <= 0 without mutating DB."""
    user = User(tg_user_id=128, tg_username="user6")
    db_session.add(user)
    await db_session.commit()

    service = AccessService(db_session)

    with pytest.raises(ValueError, match="Subscription days must be positive"):
        await service.grant_subscription(user.id, date(2026, 7, 24), days=0, commit=True)

    with pytest.raises(ValueError, match="Subscription days must be positive"):
        await service.grant_subscription(user.id, date(2026, 7, 24), days=-5, commit=False)

    result = await db_session.execute(select(AccessLedger).where(AccessLedger.user_id == user.id))
    assert len(result.scalars().all()) == 0
