
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_ACCESS_SERVICE
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Module — apps/api/tests/test_access_service.py
# owns:
#   - apps/api/tests/test_access_service.py
# inputs: varies
# outputs: varies
# dependencies: local modules
# side_effects: varies
# emitted_logs: n/a
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

# AI_HEADER
# module: M-TEST-ACCESS-SERVICE
# wave: W-ACCESS.1
# purpose: Access service tests

import pytest
from datetime import date, timedelta, timezone, datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.access_service import AccessService
from app.db.models import User


@pytest.mark.asyncio
async def test_no_access_entries(db_session: AsyncSession):
    """UC-ACCESS-CHECK S3: No access entries → preview."""
    # Create user
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
    # Create user
    user = User(tg_user_id=12345, tg_username="test")
    db_session.add(user)
    await db_session.commit()

    # Grant referral bonus
    service = AccessService(db_session)
    start_date = datetime.now(timezone.utc).date()
    await service.grant_referral_bonus(user.id, start_date)

    # Check day 0 (today)
    state = await service.can_access_day(user.id, start_date)
    assert state.state == "full"
    assert state.reason == "active_referral_days"
    assert state.referral_days_left == 13
    assert state.subscription_active is None

    # Check day 13 (last day)
    state = await service.can_access_day(user.id, start_date + timedelta(days=13))
    assert state.state == "full"
    assert state.reason == "active_referral_days"
    assert state.referral_days_left == 0

    # Check day 14 (locked - future without access)
    state = await service.can_access_day(user.id, start_date + timedelta(days=14))
    assert state.state == "locked"
    assert state.reason == "outside_access_window"


@pytest.mark.asyncio
async def test_referral_plus_subscription(db_session: AsyncSession):
    """UC-ACCESS-CHECK S2: 14d referral + 30d subscription → consumption order."""
    # Create user
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
    assert state.referral_days_left == 13
    assert state.subscription_active is None

    # Check day 13 (last referral day)
    state = await service.can_access_day(user.id, start_date + timedelta(days=13))
    assert state.state == "full"
    assert state.reason == "active_referral_days"
    assert state.referral_days_left == 0

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
