# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_BILLING_PURCHASE_STATUS — purchase status API.
# ROLE: Proves the owner-only GET /api/payment/purchase/{id} contract: 401
#       unauthenticated, 503 disabled, 404 unknown/foreign (no existence
#       leak), pending with confirmation, canceled payment, fulfilled states.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-BILLING-PURCHASE-STATUS
# purpose: Directed endpoint tests for the authenticated purchase status read
#   used by the post-redirect polling flow. The endpoint answers from local
#   rows only and never calls the provider.
# owns:
#   - apps/api/tests/test_billing_purchase_status.py
# inputs: async client with Telegram session, test DB rows.
# outputs: assertions on status codes and response payloads.
# dependencies: app.api.payment, BillingService, fixtures.
# side_effects: test DB rows only.
# emitted_logs: none.
# invariants:
#   - A foreign purchase id is indistinguishable from an unknown one (404).
#   - confirmation_url is exposed only while the payment is pending.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-BILLING-PURCHASE-STATUS

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.db.models import Payment, Purchase, User
from app.services.product_catalog import seed_products


async def _auth(async_client: AsyncClient, make_initdata, tg: int) -> None:
    initdata = make_initdata(user_id=tg, username="bill")
    r = await async_client.post("/api/auth/telegram", json={"initData": initdata})
    assert r.status_code == 200


async def _user_id(db_session, tg: int) -> uuid.UUID:
    return (await db_session.execute(select(User).where(User.tg_user_id == tg))).scalar_one().id


async def _pending_purchase(db_session, tg: int, slug: str = "horary_3") -> tuple[Purchase, Payment]:
    user_id = await _user_id(db_session, tg)
    purchase = Purchase(user_id=user_id, product_slug=slug, status="pending", context_hash="")
    db_session.add(purchase)
    await db_session.flush()
    payment = Payment(
        user_id=user_id,
        amount=12000,
        currency="RUB",
        status="pending",
        provider="yookassa",
        product_slug=slug,
        idempotence_key=f"purchase-{purchase.id}",
        provider_payment_id=f"prov-{purchase.id}",
        confirmation_url="https://pay.example/confirm",
    )
    db_session.add(payment)
    await db_session.flush()
    purchase.payment_id = payment.id
    await db_session.commit()
    return purchase, payment


@pytest.mark.asyncio
async def test_purchase_status_requires_auth(async_client: AsyncClient) -> None:
    r = await async_client.get(f"/api/payment/purchase/{uuid.uuid4()}")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_purchase_status_disabled_returns_503(
    async_client: AsyncClient, make_initdata, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "yookassa_enabled", False)
    await _auth(async_client, make_initdata, 8200)
    r = await async_client.get(f"/api/payment/purchase/{uuid.uuid4()}")
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_purchase_status_pending_returns_confirmation(
    async_client: AsyncClient, make_initdata, db_session, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "yookassa_enabled", True)
    await seed_products(db_session)
    await _auth(async_client, make_initdata, 8201)
    purchase, payment = await _pending_purchase(db_session, 8201)

    r = await async_client.get(f"/api/payment/purchase/{purchase.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["purchaseId"] == str(purchase.id)
    assert body["productSlug"] == "horary_3"
    assert body["status"] == "pending"
    assert body["providerPaymentId"] == payment.provider_payment_id
    assert body["confirmationUrl"] == "https://pay.example/confirm"


@pytest.mark.asyncio
async def test_purchase_status_canceled_payment(
    async_client: AsyncClient, make_initdata, db_session, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "yookassa_enabled", True)
    await seed_products(db_session)
    await _auth(async_client, make_initdata, 8202)
    purchase, payment = await _pending_purchase(db_session, 8202)
    payment.status = "canceled"
    await db_session.commit()

    r = await async_client.get(f"/api/payment/purchase/{purchase.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "canceled"
    assert body["confirmationUrl"] is None


@pytest.mark.asyncio
async def test_purchase_status_fulfilled_states(
    async_client: AsyncClient, make_initdata, db_session, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "yookassa_enabled", True)
    await seed_products(db_session)
    await _auth(async_client, make_initdata, 8203)
    purchase, _payment = await _pending_purchase(db_session, 8203)
    purchase.status = "consumed"
    await db_session.commit()

    r = await async_client.get(f"/api/payment/purchase/{purchase.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "consumed"
    assert body["confirmationUrl"] is None


@pytest.mark.asyncio
async def test_purchase_status_unknown_and_foreign_are_the_same_404(
    async_client: AsyncClient, make_initdata, db_session, monkeypatch
) -> None:
    """Owner-only: a foreign id must be indistinguishable from an unknown id
    (no cross-user existence leak)."""
    monkeypatch.setattr(settings, "yookassa_enabled", True)
    await seed_products(db_session)
    await _auth(async_client, make_initdata, 8204)
    purchase, _payment = await _pending_purchase(db_session, 8204)

    # A different user sees only 404 for someone else's purchase.
    await _auth(async_client, make_initdata, 8205)
    r = await async_client.get(f"/api/payment/purchase/{purchase.id}")
    assert r.status_code == 404
    r = await async_client.get(f"/api/payment/purchase/{uuid.uuid4()}")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "PURCHASE_NOT_FOUND"
