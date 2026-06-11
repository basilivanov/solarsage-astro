
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_SUBSCRIPTION_LEDGER
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for subscription_ledger.py behavior
# owns:
#   - apps/api/tests/test_subscription_ledger.py
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
# module: M-TEST-SUBSCRIPTION-LEDGER
# wave: W-6.2
# purpose: Subscription ledger tests

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models import AccessLedger


@pytest.mark.asyncio
async def test_successful_payment_creates_subscription(async_client: AsyncClient, make_initdata, db_session):
    """Successful payment creates subscription entry."""
    # Create user + payment
    user_raw = make_initdata(user_id=12347, username="subuser")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    create_response = await async_client.post(
        "/api/payment/create-intent",
        json={
            "amount": 29900,
            "currency": "RUB",
            "description": "Подписка на 1 месяц",
        }
    )
    payment_id = create_response.json()["payment_id"]

    # Send webhook (success)
    await async_client.post(
        "/api/payment/webhook",
        json={
            "event_type": "payment.succeeded",
            "payment_id": str(payment_id),
            "status": "succeeded",
        }
    )

    # Check subscription entry created
    result = await db_session.execute(
        select(AccessLedger).where(AccessLedger.entry_type == "subscription")
    )
    entries = result.scalars().all()

    assert len(entries) == 1
    assert entries[0].days_granted == 30


@pytest.mark.asyncio
async def test_failed_payment_no_subscription(async_client: AsyncClient, make_initdata, db_session):
    """Failed payment does not create subscription."""
    # Create user + payment
    user_raw = make_initdata(user_id=12348, username="failuser")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    create_response = await async_client.post(
        "/api/payment/create-intent",
        json={
            "amount": 29900,
            "currency": "RUB",
            "description": "Test",
        }
    )
    payment_id = create_response.json()["payment_id"]

    # Send webhook (failed)
    await async_client.post(
        "/api/payment/webhook",
        json={
            "event_type": "payment.failed",
            "payment_id": str(payment_id),
            "status": "failed",
        }
    )

    # Check no subscription entry
    result = await db_session.execute(
        select(AccessLedger).where(AccessLedger.entry_type == "subscription")
    )
    entries = result.scalars().all()

    assert len(entries) == 0


@pytest.mark.asyncio
async def test_subscription_grants_access(async_client: AsyncClient, make_initdata, db_session):
    """Subscription entry grants access to days."""
    from datetime import date, timedelta
    from sqlalchemy import select
    from app.db.models import User

    # Create user
    user_raw = make_initdata(user_id=12349, username="accessuser")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    # Get user
    result = await db_session.execute(
        select(User).where(User.tg_user_id == 12349)
    )
    user = result.scalar_one()

    # Create payment + subscription
    create_response = await async_client.post(
        "/api/payment/create-intent",
        json={
            "amount": 29900,
            "currency": "RUB",
            "description": "Test",
        }
    )
    payment_id = create_response.json()["payment_id"]

    await async_client.post(
        "/api/payment/webhook",
        json={
            "event_type": "payment.succeeded",
            "payment_id": str(payment_id),
            "status": "succeeded",
        }
    )

    # Check subscription entry created and covers today + future
    result = await db_session.execute(
        select(AccessLedger).where(
            AccessLedger.user_id == user.id,
            AccessLedger.entry_type == "subscription"
        )
    )
    entries = result.scalars().all()

    assert len(entries) == 1
    entry = entries[0]
    assert entry.days_granted == 30

    # Check that subscription covers today
    today = date.today()
    assert entry.start_date <= today <= entry.end_date

    # Check that subscription covers future (15 days from now)
    future = today + timedelta(days=15)
    assert entry.start_date <= future <= entry.end_date
