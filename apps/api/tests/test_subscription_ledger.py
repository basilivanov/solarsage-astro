
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
# purpose: Disabled payment boundary and direct subscription ledger tests

from datetime import date, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models import AccessLedger, ChatQuota, Payment, User
from app.services.access_service import AccessService


@pytest.mark.asyncio
async def test_direct_subscription_grant_covers_requested_days(
    async_client: AsyncClient,
    make_initdata,
    db_session,
):
    """AccessService subscription grants remain independently testable."""
    user_raw = make_initdata(user_id=12349, username="accessuser")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    result = await db_session.execute(
        select(User).where(User.tg_user_id == 12349)
    )
    user = result.scalar_one()

    start_date = date.today()
    await AccessService(db_session).grant_subscription(
        user_id=user.id,
        start_date=start_date,
        days=30,
    )

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

    assert entry.start_date <= start_date <= entry.end_date
    future = start_date + timedelta(days=15)
    assert entry.start_date <= future <= entry.end_date
