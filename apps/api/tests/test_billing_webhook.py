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
#   - Non-allowlisted source -> 403; transient local gap (unknown payment,
#     missing owner) -> 500 so YooKassa redelivers; forged amount/status ->
#     rejected (200 ack, no grant); valid -> fulfilled exactly once (200).
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
from app.db.models import AccessLedger, HoraryCredit, Payment, Purchase, Subscription, User
from app.services.billing_service import BillingService
from app.services.product_catalog import seed_products


def _request(host: str, headers: dict | None = None):
    raw = {k.lower(): v for k, v in (headers or {}).items()}

    class _Headers:
        def get(self, name: str, default=None):
            return raw.get(name.lower(), default)

    return SimpleNamespace(client=SimpleNamespace(host=host), headers=_Headers())


def test_webhook_source_policy_official_ranges(monkeypatch) -> None:
    monkeypatch.setattr(settings, "yookassa_webhook_ip_allowlist", "")
    assert _webhook_source_allowed(_request("185.71.76.1")) is True
    assert _webhook_source_allowed(_request("185.71.77.30")) is True
    assert _webhook_source_allowed(_request("77.75.156.11")) is True
    assert _webhook_source_allowed(_request("77.75.154.129")) is True
    assert _webhook_source_allowed(_request("8.8.8.8")) is False
    assert _webhook_source_allowed(_request("10.0.0.5")) is False


def test_webhook_source_policy_override(monkeypatch) -> None:
    monkeypatch.setattr(settings, "yookassa_webhook_ip_allowlist", "192.0.2.0/24")
    assert _webhook_source_allowed(_request("192.0.2.9")) is True
    assert _webhook_source_allowed(_request("185.71.76.1")) is False


def test_webhook_trusted_proxy_forwarded_ip(monkeypatch) -> None:
    # Legitimate nginx (trusted loopback peer) forwarding a real YooKassa IP.
    monkeypatch.setattr(settings, "yookassa_webhook_ip_allowlist", "")
    monkeypatch.setattr(settings, "yookassa_trusted_proxy_cidrs", "127.0.0.1/32")
    assert _webhook_source_allowed(_request("127.0.0.1", {"X-Real-IP": "185.71.76.9"})) is True
    assert _webhook_source_allowed(_request("127.0.0.1", {"X-Forwarded-For": "77.75.156.35, 10.0.0.1"})) is True
    # Trusted proxy but missing/invalid forwarded header.
    assert _webhook_source_allowed(_request("127.0.0.1")) is False
    assert _webhook_source_allowed(_request("127.0.0.1", {"X-Real-IP": "not-an-ip"})) is False
    # Trusted proxy forwarding a NON-YooKassa address.
    assert _webhook_source_allowed(_request("127.0.0.1", {"X-Real-IP": "203.0.113.7"})) is False


def test_webhook_forged_forwarded_header_from_untrusted_peer(monkeypatch) -> None:
    # Forged header from an untrusted peer must never pass, even with a
    # YooKassa-looking value inside.
    monkeypatch.setattr(settings, "yookassa_webhook_ip_allowlist", "")
    monkeypatch.setattr(settings, "yookassa_trusted_proxy_cidrs", "127.0.0.1/32")
    assert _webhook_source_allowed(_request("8.8.8.8", {"X-Forwarded-For": "185.71.76.9"})) is False
    assert _webhook_source_allowed(_request("8.8.8.8", {"X-Real-IP": "77.75.156.11"})) is False


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
        if provider_payment_id not in self.remote:
            from app.services.yookassa_client import YooKassaError
            raise YooKassaError("provider payment not found")
        return self.remote[provider_payment_id]


def _remote(payment: Payment, owner_id: str, **overrides) -> dict:
    # Mirror the client metadata contract (type is enforced by _payment_matches).
    key = payment.idempotence_key or ""
    if key.startswith("rebill-"):
        charge_type = "recurrent"
    elif key.startswith("init-"):
        charge_type = "initial_recurrent"
    elif key.startswith("purchase-"):
        charge_type = "one_time"
    else:
        charge_type = None
    metadata = {
        "user_id": str(payment.user_id),
        "owner_id": owner_id,
        "product_slug": payment.product_slug,
    }
    if charge_type:
        metadata["type"] = charge_type
    remote = {
        "provider_payment_id": payment.provider_payment_id,
        "status": "succeeded",
        "paid": True,
        "amount_value": f"{payment.amount // 100}.{payment.amount % 100:02d}",
        "currency": payment.currency,
        "metadata": metadata,
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
async def test_webhook_provider_get_failure_is_retryable_502(
    async_client: AsyncClient, db_session, monkeypatch
) -> None:
    """Provider GET failure on the webhook is a STABLE retryable 502 — never
    a raw 500, never a false 200 ack, never provider text."""
    from app.services.yookassa_client import YooKassaError

    monkeypatch.setattr(settings, "yookassa_enabled", True)
    monkeypatch.setattr("app.api.payment._webhook_source_allowed", lambda request: True)
    remote: dict = {}
    monkeypatch.setattr(
        "app.services.billing_service.get_yookassa_client",
        lambda: FakeClient(remote),
    )
    user, payment, subscription_id = await _make_pending_payment(db_session, 900024)

    class FailingClient:
        async def get_payment(self, provider_payment_id: str) -> dict:
            raise YooKassaError("yookassa transport error: raw internal text with 10.0.0.1")

    # The provider starts failing only NOW (after a clean local reservation).
    monkeypatch.setattr(
        "app.services.billing_service.get_yookassa_client",
        lambda: FailingClient(),
    )
    r = await async_client.post(
        "/api/payment/webhook/yookassa",
        json={"type": "notification", "event": "payment.succeeded", "object": {"id": payment.provider_payment_id}},
    )
    assert r.status_code == 502
    assert r.json()["detail"]["code"] == "PROVIDER_UNAVAILABLE"
    assert "10.0.0.1" not in r.text
    await db_session.refresh(payment)
    assert payment.status == "pending"  # no fulfillment, no state change
    assert (await db_session.execute(select(AccessLedger))).scalars().all() == []


@pytest.mark.asyncio
async def test_webhook_unknown_payment_is_retryable(
    async_client: AsyncClient, db_session, monkeypatch
) -> None:
    """Early webhook before the local commit: unknown_payment is a TRANSIENT
    gap -> 500, so YooKassa redelivers (up to 24h) instead of the grant being
    silently lost behind a false 200 ack."""
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
    assert r.status_code == 500


@pytest.mark.asyncio
async def test_webhook_transient_owner_gap_retried_then_acked(
    async_client: AsyncClient, db_session, monkeypatch
) -> None:
    """Transient owner gap -> 500 (YooKassa redelivers); after the gap is
    repaired the redelivery is acked 200 and fulfills exactly once."""
    monkeypatch.setattr(settings, "yookassa_enabled", True)
    monkeypatch.setattr("app.api.payment._webhook_source_allowed", lambda request: True)
    remote: dict = {}
    monkeypatch.setattr(
        "app.services.billing_service.get_yookassa_client",
        lambda: FakeClient(remote),
    )

    await seed_products(db_session)
    user = User(id=uuid.uuid4(), tg_user_id=900022)
    db_session.add(user)
    await db_session.commit()
    service = BillingService(db_session)
    started = await service.start_purchase(user.id, "horary_1")
    payment = (await db_session.execute(select(Payment))).scalar_one()
    purchase = (await db_session.execute(select(Purchase))).scalar_one()
    purchase.payment_id = None  # transient local gap
    await db_session.commit()

    remote[payment.provider_payment_id] = _remote(payment, str(started["purchase_id"]))
    body = {"type": "notification", "event": "payment.succeeded", "object": {"id": payment.provider_payment_id}}
    r = await async_client.post("/api/payment/webhook/yookassa", json=body)
    assert r.status_code == 500
    assert (await db_session.execute(select(HoraryCredit))).scalars().all() == []

    purchase.payment_id = payment.id  # gap repaired before the redelivery
    await db_session.commit()
    r = await async_client.post("/api/payment/webhook/yookassa", json=body)
    assert r.status_code == 200
    assert (await db_session.execute(select(HoraryCredit))).scalar_one().amount == 1


@pytest.mark.asyncio
async def test_webhook_subscription_inactive_is_retryable(
    async_client: AsyncClient, db_session, monkeypatch
) -> None:
    """Verified money against an inactive subscription is NOT a terminal
    success: 500, so the operator reconciles/refunds inside YooKassa's 24h
    redelivery window instead of the grant being lost behind a false 200."""
    monkeypatch.setattr(settings, "yookassa_enabled", True)
    monkeypatch.setattr("app.api.payment._webhook_source_allowed", lambda request: True)
    remote: dict = {}
    monkeypatch.setattr(
        "app.services.billing_service.get_yookassa_client",
        lambda: FakeClient(remote),
    )
    user, payment, subscription_id = await _make_pending_payment(db_session, 900023)
    sub = (await db_session.execute(select(Subscription))).scalar_one()
    sub.status = "canceled"  # legacy canceled initial start
    await db_session.commit()

    remote[payment.provider_payment_id] = _remote(payment, subscription_id)
    r = await async_client.post(
        "/api/payment/webhook/yookassa",
        json={"type": "notification", "event": "payment.succeeded", "object": {"id": payment.provider_payment_id}},
    )
    assert r.status_code == 500
    assert (await db_session.execute(select(AccessLedger))).scalars().all() == []


@pytest.mark.asyncio
async def test_webhook_malformed_paid_scalar_is_retryable_502_no_grant(
    async_client: AsyncClient, db_session, monkeypatch
) -> None:
    """Valid identity but malformed provider scalar (paid as a STRING): the
    strict client contract rejects it, the endpoint answers a retryable 502,
    and NOTHING is granted (payment pending, ledger empty)."""
    import httpx
    from app.services.yookassa_client import YooKassaClient

    monkeypatch.setattr(settings, "yookassa_enabled", True)
    monkeypatch.setattr("app.api.payment._webhook_source_allowed", lambda request: True)
    monkeypatch.setattr(
        "app.services.billing_service.get_yookassa_client",
        lambda: FakeClient({}),
    )
    user, payment, subscription_id = await _make_pending_payment(db_session, 900025)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": payment.provider_payment_id,
                "status": "succeeded",
                "paid": "false",  # malformed scalar: must be a real bool
                "amount": {"value": "99.00", "currency": "RUB"},
                "metadata": {
                    "user_id": str(payment.user_id),
                    "owner_id": subscription_id,
                    "product_slug": "subscription_month",
                    "type": "initial_recurrent",
                },
            },
        )

    strict_client = YooKassaClient("shop-1", "secret-1", transport=httpx.MockTransport(handler))
    monkeypatch.setattr(
        "app.services.billing_service.get_yookassa_client",
        lambda: strict_client,
    )
    r = await async_client.post(
        "/api/payment/webhook/yookassa",
        json={"type": "notification", "event": "payment.succeeded", "object": {"id": payment.provider_payment_id}},
    )
    assert r.status_code == 502
    assert r.json()["detail"]["code"] == "PROVIDER_UNAVAILABLE"
    await db_session.refresh(payment)
    assert payment.status == "pending"
    assert (await db_session.execute(select(AccessLedger))).scalars().all() == []
