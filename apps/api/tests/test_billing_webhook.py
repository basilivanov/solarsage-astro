# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_BILLING_WEBHOOK — webhook endpoint contract.
# ROLE: Proves the webhook IP allowlist policy (official YooKassa ranges +
#       env override) and that the endpoint processes only verified events.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-BILLING-WEBHOOK
# purpose: Directed tests for the webhook source policy and endpoint flow.
# owns:
#   - apps/api/tests/test_billing_webhook.py
# inputs: fake request objects, async client, mocked provider.
# outputs: assertions on 403/200 flows and fulfillment.
# dependencies: app.api.payment._webhook_source_allowed, BillingService.
# side_effects: test DB rows only.
# emitted_logs: none.
# invariants:
#   - Non-allowlisted source -> 403; allowlisted unknown payment -> no grant;
#     forged amount/status -> rejected; valid -> fulfilled exactly once.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-BILLING_WEBHOOK

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.api.payment import _webhook_source_allowed
from app.core.config import settings
from app.db.models import AccessLedger, Payment, User
from app.services.billing_service import BillingService
from app.services.product_catalog import seed_products


def _request_with_host(host: str):
    return SimpleNamespace(client=SimpleNamespace(host=host))


def test_webhook_source_policy_official_ranges(monkeypatch) -> None:
    monkeypatch.setattr(settings, "yookassa_webhook_ip_allowlist", "")
    assert _webhook_source_allowed(_request_with_host("185.71.76.1")) is True
    assert _webhook_source_allowed(_request_with_host("185.71.77.30")) is True
    assert _webhook_source_allowed(_request_with_host("77.75.156.11")) is True
    assert _webhook_source_allowed(_request_with_host("77.75.154.129")) is True
    assert _webhook_source_allowed(_request_with_host("8.8.8.8")) is False
    assert _webhook_source_allowed(_request_with_host("10.0.0.5")) is False


def test_webhook_source_policy_override(monkeypatch) -> None:
    monkeypatch.setattr(settings, "yookassa_webhook_ip_allowlist", "192.0.2.0/24")
    assert _webhook_source_allowed(_request_with_host("192.0.2.9")) is True
    assert _webhook_source_allowed(_request_with_host("185.71.76.1")) is False


class FakeClient:
    def __init__(self, remote: dict):
        self.remote = remote
        self.next_id = 0

    async def create_initial_payment(self, **kwargs):
        self.next_id += 1
        return {
            "provider_payment_id": f"prov-wh-{self.next_id:03d}",
            "confirmation_url": "https://pay.example/init",
            "status": "pending",
        }

    async def create_one_time_payment(self, **kwargs):
        self.next_id += 1
        return {
            "provider_payment_id": f"prov-wh-{self.next_id:03d}",
            "confirmation_url": "https://pay.example/once",
            "status": "pending",
        }

    async def get_payment(self, provider_payment_id: str) -> dict:
        return self.remote[provider_payment_id]


def _remote(payment: Payment, owner_id: str, **overrides) -> dict:
    remote = {
        "provider_payment_id": payment.provider_payment_id,
        "status": "succeeded",
        "paid": True,
        "amount_value": f"{payment.amount // 100}.{payment.amount % 100:02d}",
        "currency": payment.currency,
        "metadata": {
            "user_id": str(payment.user_id),
            "owner_id": owner_id,
            "product_slug": payment.product_slug,
        },
        "payment_method_id": "pm-1",
        "payment_method_saved": True,
    }
    remote.update(overrides)
    return remote


async def _make_pending_payment(db_session, tg: int) -> tuple[User, Payment, str]:
    from app.db.models import User as UserModel

    await seed_products(db_session)
    user = UserModel(id=uuid.uuid4(), tg_user_id=tg)
    db_session.add(user)
    await db_session.commit()
    service = BillingService(db_session)
    started = await service.start_subscription(user.id, "subscription_month")
    payment = (await db_session.execute(select(Payment))).scalar_one()
    return user, payment, str(started["subscription_id"])


@pytest.mark.asyncio
async def test_webhook_forged_source_returns_403(
    async_client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "yookassa_enabled", True)
    monkeypatch.setattr("app.api.payment._webhook_source_allowed", lambda request: False)
    r = await async_client.post(
        "/api/payment/webhook/yookassa",
        json={"type": "notification", "event": "payment.succeeded", "object": {"id": "prov-forged"}},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_webhook_disabled_returns_503(async_client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "yookassa_enabled", False)
    r = await async_client.post(
        "/api/payment/webhook/yookassa",
        json={"type": "notification", "event": "payment.succeeded", "object": {"id": "prov-1"}},
    )
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_webhook_success_fulfills_once(
    async_client: AsyncClient, db_session, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "yookassa_enabled", True)
    monkeypatch.setattr("app.api.payment._webhook_source_allowed", lambda request: True)

    # Provider fake must exist BEFORE any payment is created.
    remote: dict = {}
    monkeypatch.setattr(
        "app.services.billing_service.get_yookassa_client",
        lambda: FakeClient(remote),
    )
    user, payment, subscription_id = await _make_pending_payment(db_session, 900020)
    remote[payment.provider_payment_id] = _remote(payment, subscription_id)

    body = {"type": "notification", "event": "payment.succeeded", "object": {"id": payment.provider_payment_id}}
    r = await async_client.post("/api/payment/webhook/yookassa", json=body)
    assert r.status_code == 200
    ledger = (await db_session.execute(select(AccessLedger))).scalars().all()
    assert len(ledger) == 1

    # Duplicate delivery does not double-grant.
    r = await async_client.post("/api/payment/webhook/yookassa", json=body)
    assert r.status_code == 200
    ledger = (await db_session.execute(select(AccessLedger))).scalars().all()
    assert len(ledger) == 1


@pytest.mark.asyncio
async def test_webhook_amount_mismatch_rejected(
    async_client: AsyncClient, db_session, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "yookassa_enabled", True)
    monkeypatch.setattr("app.api.payment._webhook_source_allowed", lambda request: True)

    remote: dict = {}
    monkeypatch.setattr(
        "app.services.billing_service.get_yookassa_client",
        lambda: FakeClient(remote),
    )
    user, payment, subscription_id = await _make_pending_payment(db_session, 900021)
    remote[payment.provider_payment_id] = _remote(payment, subscription_id, amount_value="1.00")

    r = await async_client.post(
        "/api/payment/webhook/yookassa",
        json={"type": "notification", "event": "payment.succeeded", "object": {"id": payment.provider_payment_id}},
    )
    assert r.status_code == 200  # ack without fulfillment
    assert (await db_session.execute(select(Payment))).scalar_one().status == "pending"
    assert (await db_session.execute(select(AccessLedger))).scalars().all() == []


@pytest.mark.asyncio
async def test_webhook_unknown_payment_does_not_fail(
    async_client: AsyncClient, db_session, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "yookassa_enabled", True)
    monkeypatch.setattr("app.api.payment._webhook_source_allowed", lambda request: True)
    monkeypatch.setattr(
        "app.services.billing_service.get_yookassa_client",
        lambda: FakeClient({}),
    )
    r = await async_client.post(
        "/api/payment/webhook/yookassa",
        json={"type": "notification", "event": "payment.succeeded", "object": {"id": "prov-unknown"}},
    )
    assert r.status_code == 200
