import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_payment_intent_is_unavailable_without_real_provider(
    async_client: AsyncClient,
    make_initdata,
):
    user_raw = make_initdata(user_id=22345, username="payblocked")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    response = await async_client.post(
        "/api/payment/create-intent",
        json={
            "amount": 29900,
            "currency": "RUB",
            "description": "Подписка на 1 месяц",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "PAYMENT_UNAVAILABLE"


@pytest.mark.asyncio
async def test_payment_webhook_is_unavailable_without_provider_verification(
    async_client: AsyncClient,
):
    response = await async_client.post(
        "/api/payment/webhook",
        json={
            "event_type": "payment.succeeded",
            "payment_id": "1",
            "status": "succeeded",
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "PAYMENT_UNAVAILABLE"
