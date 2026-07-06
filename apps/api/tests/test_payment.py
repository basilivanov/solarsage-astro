
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_PAYMENT
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for payment.py behavior
# owns:
#   - apps/api/tests/test_payment.py
# inputs: Endpoint params, request body
# outputs: Parsed response / typed data
# dependencies: local modules
# side_effects: Network calls to API
# emitted_logs: n/a (tests)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# AI_HEADER
# module: M-TEST-PAYMENT
# wave: W-6.1
# purpose: Payment tests

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_payment_intent(async_client: AsyncClient, make_initdata):
    """Payment intent is disabled until a real provider is wired."""
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

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "PAYMENT_UNAVAILABLE"


@pytest.mark.asyncio
async def test_payment_webhook_updates_status(async_client: AsyncClient, make_initdata):
    """Webhook is disabled until provider verification exists."""
    webhook_response = await async_client.post(
        "/api/payment/webhook",
        json={
            "event_type": "payment.succeeded",
            "payment_id": "1",
            "status": "succeeded",
        }
    )

    assert webhook_response.status_code == 503
    assert webhook_response.json()["detail"]["code"] == "PAYMENT_UNAVAILABLE"
