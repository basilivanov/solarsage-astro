# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_BILLING_START_ENDPOINTS — start 502 boundary.
# ROLE: Proves the stable PROVIDER_UNAVAILABLE 502 contract on
#       subscription/purchase start when the provider create call fails —
#       never a raw 500, never provider text; reservations stay intact.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-BILLING-START-ENDPOINTS
# purpose: Directed endpoint tests for provider-failure mapping on start.
# owns:
#   - apps/api/tests/test_billing_start_endpoints.py
# inputs: async client with Telegram session, failing provider client.
# outputs: assertions on 502 code/body and durable reservation state.
# dependencies: app.api.payment, BillingService, fixtures.
# side_effects: test DB rows only.
# emitted_logs: none.
# invariants:
#   - 502 body carries code PROVIDER_UNAVAILABLE and no provider internals.
#   - The durable pending reservation survives for the same-key retry.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-BILLING-START-ENDPOINTS

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.db.models import Payment, Purchase, Subscription
from app.services.product_catalog import seed_products
from app.services.yookassa_client import YooKassaError


class FailingClient:
    async def create_initial_payment(self, **kwargs):
        raise YooKassaError("yookassa transport error: raw text with secret-1 and 10.0.0.1")

    async def create_one_time_payment(self, **kwargs):
        raise YooKassaError("yookassa transport error: raw text with secret-1 and 10.0.0.1")

    async def create_recurrent_payment(self, **kwargs):
        raise YooKassaError("yookassa transport error")

    async def get_payment(self, provider_payment_id: str) -> dict:
        raise YooKassaError("yookassa transport error")


async def _auth(async_client: AsyncClient, make_initdata, tg: int) -> None:
    initdata = make_initdata(user_id=tg, username="bill")
    r = await async_client.post("/api/auth/telegram", json={"initData": initdata})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_subscription_start_provider_failure_is_stable_502(
    async_client: AsyncClient, make_initdata, db_session, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "yookassa_enabled", True)
    monkeypatch.setattr(settings, "yookassa_return_url", "https://app.example/return")
    monkeypatch.setattr(
        "app.services.billing_service.get_yookassa_client",
        lambda: FailingClient(),
    )
    await seed_products(db_session)
    await _auth(async_client, make_initdata, 8300)

    r = await async_client.post(
        "/api/payment/subscription/start",
        json={"productSlug": "subscription_month"},
    )
    assert r.status_code == 502
    assert r.json()["detail"]["code"] == "PROVIDER_UNAVAILABLE"
    assert "secret-1" not in r.text
    assert "10.0.0.1" not in r.text

    # The durable reservation survives (same-key retry path intact).
    sub = (await db_session.execute(select(Subscription))).scalar_one()
    assert sub.status == "pending"
    payment = (await db_session.execute(select(Payment))).scalar_one()
    assert payment.status == "pending"
    assert payment.idempotence_key is not None
    assert payment.first_attempt_at is not None


@pytest.mark.asyncio
async def test_purchase_start_provider_failure_is_stable_502(
    async_client: AsyncClient, make_initdata, db_session, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "yookassa_enabled", True)
    monkeypatch.setattr(settings, "yookassa_return_url", "https://app.example/return")
    monkeypatch.setattr(
        "app.services.billing_service.get_yookassa_client",
        lambda: FailingClient(),
    )
    await seed_products(db_session)
    await _auth(async_client, make_initdata, 8301)

    r = await async_client.post(
        "/api/payment/purchase/start",
        json={"productSlug": "horary_1"},
    )
    assert r.status_code == 502
    assert r.json()["detail"]["code"] == "PROVIDER_UNAVAILABLE"
    assert "secret-1" not in r.text

    purchase = (await db_session.execute(select(Purchase))).scalar_one()
    assert purchase.status == "pending"
    payment = (await db_session.execute(select(Payment))).scalar_one()
    assert payment.status == "pending"
    assert payment.idempotence_key is not None
    assert payment.first_attempt_at is not None
