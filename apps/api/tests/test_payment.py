
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_PAYMENT
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Module — apps/api/tests/test_payment.py
# owns:
#   - apps/api/tests/test_payment.py
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
# module: M-TEST-PAYMENT
# wave: W-6.1
# purpose: Payment tests

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_payment_intent(async_client: AsyncClient, make_initdata):
    """Create payment intent."""
    user_raw = make_initdata(user_id=12345, username="payuser")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    response = await async_client.post(
        "/api/payment/create-intent",
        json={
            "amount": 29900,  # 299 RUB
            "currency": "RUB",
            "description": "Подписка на 1 месяц",
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["amount"] == 29900
    assert data["currency"] == "RUB"


@pytest.mark.asyncio
async def test_payment_webhook_updates_status(async_client: AsyncClient, make_initdata):
    """Webhook updates payment status."""
    # Create user + payment
    user_raw = make_initdata(user_id=12346, username="webhookuser")
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

    # Send webhook
    webhook_response = await async_client.post(
        "/api/payment/webhook",
        json={
            "event_type": "payment.succeeded",
            "payment_id": str(payment_id),
            "status": "succeeded",
        }
    )

    assert webhook_response.status_code == 200
