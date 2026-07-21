# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_BILLING_SERVICE — billing service unit tests.
# ROLE: Proves provider create mapping/idempotency, cancel semantics, the
#       recurrent kill-switch, verified-webhook fulfillment for
#       subscription/horary/natal and duplicate-grant idempotency — all with
#       a mocked provider (never a live charge).
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-BILLING-SERVICE
# purpose: Directed unit tests for BillingService with a fake YooKassa client.
# owns:
#   - apps/api/tests/test_billing_service.py
# inputs: test DB session, monkeypatched provider client.
# outputs: assertions on rows and call logs.
# dependencies: BillingService, product_catalog.seed_products.
# side_effects: test DB rows only.
# emitted_logs: none.
# invariants:
#   - No live provider calls; all network is the in-test fake.
#   - Duplicate start/webhook never double-grants.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-BILLING-SERVICE

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.db.models import (
    AccessLedger,
    HoraryCredit,
    Payment,
    Purchase,
    Subscription,
    User,
)
from app.services.billing_service import BillingService
from app.services.product_catalog import seed_products


class FakeYooKassaClient:
    """In-test provider fake: records create calls, serves get_payment fakes."""

    def __init__(self, remote: dict | None = None):
        self.calls: list[tuple[str, dict]] = []
        self.remote = remote or {}
        self.next_id = 0

    def _new_id(self) -> str:
        self.next_id += 1
        return f"prov-{self.next_id:04d}"

    async def create_initial_payment(self, **kwargs):
        self.calls.append(("initial", kwargs))
        return {"provider_payment_id": self._new_id(), "confirmation_url": "https://pay.example/init", "status": "pending"}

    async def create_one_time_payment(self, **kwargs):
        self.calls.append(("one_time", kwargs))
        return {"provider_payment_id": self._new_id(), "confirmation_url": "https://pay.example/once", "status": "pending"}

    async def create_recurrent_payment(self, **kwargs):
        self.calls.append(("rebill", kwargs))
        return {"provider_payment_id": self._new_id(), "status": "pending"}

    async def get_payment(self, provider_payment_id: str) -> dict:
        return self.remote[provider_payment_id]


def _remote_for(payment: Payment, owner_id: str, **overrides) -> dict:
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
        "payment_method_id": "pm-saved-1",
        "payment_method_saved": True,
    }
    remote.update(overrides)
    return remote


async def _user(db_session, tg: int) -> User:
    user = User(id=uuid.uuid4(), tg_user_id=tg)
    db_session.add(user)
    await db_session.commit()
    return user


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeYooKassaClient()
    monkeypatch.setattr("app.services.billing_service.get_yookassa_client", lambda: client)
    monkeypatch.setattr(settings, "yookassa_enabled", True)
    monkeypatch.setattr(settings, "yookassa_return_url", "https://app.example/return")
    return client


# ---- start_subscription: provider mapping + idempotency ----

@pytest.mark.asyncio
async def test_start_subscription_maps_initial_recurrent_payment(db_session, fake_client) -> None:
    await seed_products(db_session)
    user = await _user(db_session, 900001)
    service = BillingService(db_session)

    result = await service.start_subscription(user.id, "subscription_month")

    kind, kwargs = fake_client.calls[0]
    assert kind == "initial"
    assert kwargs["amount_kopecks"] == 9900
    assert kwargs["currency"] == "RUB"
    assert kwargs["return_url"] == "https://app.example/return"
    assert kwargs["product_slug"] == "subscription_month"
    assert str(kwargs["owner_id"]) == str(result["subscription_id"])
    assert kwargs["idempotence_key"] == f"init-{result['subscription_id']}-first"
    assert len(kwargs["idempotence_key"]) <= 64
    assert result["confirmation_url"] == "https://pay.example/init"


@pytest.mark.asyncio
async def test_start_subscription_repeat_reuses_pending(db_session, fake_client) -> None:
    await seed_products(db_session)
    user = await _user(db_session, 900002)
    service = BillingService(db_session)

    first = await service.start_subscription(user.id, "subscription_month")
    second = await service.start_subscription(user.id, "subscription_month")

    assert second["status"] == "pending"
    assert second["subscription_id"] == first["subscription_id"]
    assert second["provider_payment_id"] == first["provider_payment_id"]
    assert len(fake_client.calls) == 1  # no duplicate provider payment

    subs = (await db_session.execute(select(Subscription))).scalars().all()
    payments = (await db_session.execute(select(Payment))).scalars().all()
    assert len(subs) == 1
    assert len(payments) == 1


@pytest.mark.asyncio
async def test_start_subscription_when_already_active(db_session, fake_client) -> None:
    await seed_products(db_session)
    user = await _user(db_session, 900003)
    service = BillingService(db_session)
    remote_payment_id = None

    started = await service.start_subscription(user.id, "subscription_month")
    payment = (await db_session.execute(select(Payment))).scalar_one()
    remote_payment_id = payment.provider_payment_id
    fake_client.remote[remote_payment_id] = _remote_for(payment, str(started["subscription_id"]))
    await service.verify_and_process_webhook(remote_payment_id)

    result = await service.start_subscription(user.id, "subscription_year")
    assert result["status"] == "already_active"
    assert len(fake_client.calls) == 1


# ---- Fulfillment: subscription ----

@pytest.mark.asyncio
async def test_webhook_fulfill_subscription_grants_access_and_method(db_session, fake_client) -> None:
    await seed_products(db_session)
    user = await _user(db_session, 900004)
    service = BillingService(db_session)

    started = await service.start_subscription(user.id, "subscription_year")
    payment = (await db_session.execute(select(Payment))).scalar_one()
    fake_client.remote[payment.provider_payment_id] = _remote_for(payment, str(started["subscription_id"]))

    result = await service.verify_and_process_webhook(payment.provider_payment_id)

    assert result["processed"] is True
    sub = (await db_session.execute(select(Subscription))).scalar_one()
    assert sub.status == "active"
    assert sub.payment_method_id == "pm-saved-1"
    assert sub.current_period_end is not None

    ledger = (await db_session.execute(select(AccessLedger))).scalars().all()
    assert len(ledger) == 1
    assert ledger[0].entry_type == "subscription"
    assert ledger[0].days_granted == 365

    # Duplicate webhook: no double grant.
    again = await service.verify_and_process_webhook(payment.provider_payment_id)
    assert again["reason"] == "already_fulfilled"
    ledger = (await db_session.execute(select(AccessLedger))).scalars().all()
    assert len(ledger) == 1


# ---- Fulfillment: horary ----

@pytest.mark.asyncio
async def test_webhook_fulfill_horary_creates_paid_credit(db_session, fake_client) -> None:
    await seed_products(db_session)
    user = await _user(db_session, 900005)
    service = BillingService(db_session)

    started = await service.start_purchase(user.id, "horary_3")
    payment = (await db_session.execute(select(Payment))).scalar_one()
    fake_client.remote[payment.provider_payment_id] = _remote_for(payment, str(started["purchase_id"]))

    result = await service.verify_and_process_webhook(payment.provider_payment_id)

    assert result["processed"] is True
    credit = (await db_session.execute(select(HoraryCredit))).scalar_one()
    assert credit.source == "paid"
    assert credit.amount == 3
    assert credit.used_amount == 0
    purchase = (await db_session.execute(select(Purchase))).scalar_one()
    assert purchase.status == "consumed"

    again = await service.verify_and_process_webhook(payment.provider_payment_id)
    assert again["reason"] == "already_fulfilled"
    credits = (await db_session.execute(select(HoraryCredit))).scalars().all()
    assert len(credits) == 1


# ---- Fulfillment: natal entitlement ----

@pytest.mark.asyncio
async def test_webhook_fulfill_natal_delivers_entitlement(db_session, fake_client, monkeypatch) -> None:
    from app.db.models import UserProfile
    from app.services.natal_context_service import NatalContextService
    from decimal import Decimal
    from datetime import date as Date, time as dtime

    monkeypatch.setattr(settings, "natal_report_enabled", True)
    await seed_products(db_session)
    user = await _user(db_session, 900006)
    db_session.add(
        UserProfile(
            user_id=user.id, first_name="Nat", gender="female",
            birthday=Date(1993, 1, 7), birth_time=dtime(10, 33),
            birth_city="Chirchiq", birth_lat=Decimal("41.46890"),
            birth_lon=Decimal("69.58220"), birth_tz="Asia/Tashkent",
            is_onboarded=True,
        )
    )
    await db_session.commit()
    real_hash = NatalContextService.compute_profile_hash(
        (await db_session.execute(select(UserProfile).where(UserProfile.user_id == user.id))).scalar_one()
    )
    service = BillingService(db_session)

    started = await service.start_purchase(user.id, "natal_full_report")
    assert started["status"] == "pending"
    payment = (await db_session.execute(select(Payment))).scalar_one()
    fake_client.remote[payment.provider_payment_id] = _remote_for(payment, str(started["purchase_id"]))

    result = await service.verify_and_process_webhook(payment.provider_payment_id)
    assert result["processed"] is True

    assert await service.has_natal_entitlement(user.id, real_hash) is True
    assert await service.has_natal_entitlement(user.id, "other-hash") is False

    again = await service.verify_and_process_webhook(payment.provider_payment_id)
    assert again["reason"] == "already_fulfilled"

    entitled_again = await service.start_purchase(user.id, "natal_full_report")
    assert entitled_again["status"] == "already_entitled"
    assert len(fake_client.calls) == 1


@pytest.mark.asyncio
async def test_natal_context_hash_computed_from_real_profile(db_session) -> None:
    """Regression: entitlement hash must equal compute_profile_hash(profile),
    never getattr(context, 'profile_hash') (the old always-None bug)."""
    from app.db.models import UserProfile
    from app.services.natal_context_service import NatalContextService
    from decimal import Decimal
    from datetime import date as Date, time as dtime

    user = await _user(db_session, 900012)
    profile = UserProfile(
        user_id=user.id, first_name="Hash", gender="male",
        birthday=Date(1990, 5, 20), birth_time=dtime(6, 15),
        birth_city="Moscow", birth_lat=Decimal("55.7558"),
        birth_lon=Decimal("37.6173"), birth_tz="Europe/Moscow",
        is_onboarded=True,
    )
    db_session.add(profile)
    await db_session.commit()

    service = BillingService(db_session)
    computed = await service._current_natal_context_hash(user.id)
    expected = NatalContextService.compute_profile_hash(profile)
    assert computed is not None
    assert computed == expected


@pytest.mark.asyncio
async def test_natal_product_not_sold_when_report_disabled(db_session, fake_client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "natal_report_enabled", False)
    await seed_products(db_session)
    user = await _user(db_session, 900013)
    service = BillingService(db_session)

    products = await service.get_products()
    assert "natal_full_report" not in [p.slug for p in products]

    with pytest.raises(ValueError, match="PRODUCT_NOT_FOUND"):
        await service.start_purchase(user.id, "natal_full_report")
    assert fake_client.calls == []


# ---- Webhook rejections (service level) ----

@pytest.mark.asyncio
async def test_webhook_rejects_amount_mismatch(db_session, fake_client) -> None:
    await seed_products(db_session)
    user = await _user(db_session, 900007)
    service = BillingService(db_session)
    started = await service.start_subscription(user.id, "subscription_month")
    payment = (await db_session.execute(select(Payment))).scalar_one()
    fake_client.remote[payment.provider_payment_id] = _remote_for(
        payment, str(started["subscription_id"]), amount_value="0.01"
    )

    result = await service.verify_and_process_webhook(payment.provider_payment_id)
    assert result["reason"] == "mismatch"
    assert (await db_session.execute(select(Payment))).scalar_one().status == "pending"
    assert (await db_session.execute(select(AccessLedger))).scalars().all() == []


@pytest.mark.asyncio
async def test_webhook_rejects_not_succeeded_and_forged_metadata(db_session, fake_client) -> None:
    await seed_products(db_session)
    user = await _user(db_session, 900008)
    service = BillingService(db_session)
    started = await service.start_purchase(user.id, "horary_1")
    payment = (await db_session.execute(select(Payment))).scalar_one()

    fake_client.remote[payment.provider_payment_id] = _remote_for(
        payment, str(started["purchase_id"]), status="waiting_for_capture", paid=False
    )
    result = await service.verify_and_process_webhook(payment.provider_payment_id)
    assert result["reason"] == "provider_status_waiting_for_capture"

    fake_client.remote[payment.provider_payment_id] = _remote_for(
        payment, "00000000-0000-0000-0000-000000000000"
    )
    result = await service.verify_and_process_webhook(payment.provider_payment_id)
    assert result["reason"] == "mismatch"
    assert (await db_session.execute(select(HoraryCredit))).scalars().all() == []


# ---- Cancel: never revokes the paid period ----

@pytest.mark.asyncio
async def test_cancel_keeps_paid_period(db_session, fake_client) -> None:
    await seed_products(db_session)
    user = await _user(db_session, 900009)
    service = BillingService(db_session)

    started = await service.start_subscription(user.id, "subscription_month")
    payment = (await db_session.execute(select(Payment))).scalar_one()
    fake_client.remote[payment.provider_payment_id] = _remote_for(payment, str(started["subscription_id"]))
    await service.verify_and_process_webhook(payment.provider_payment_id)

    result = await service.cancel_subscription(user.id, "not needed")
    assert result["status"] == "canceled"
    ledger = (await db_session.execute(select(AccessLedger))).scalars().all()
    assert len(ledger) == 1  # paid period preserved, nothing revoked

    status = await service.get_subscription_status(user.id)
    assert status["status"] == "canceled"
    assert status["has_access"] is True


# ---- Rebill kill-switch ----

@pytest.mark.asyncio
async def test_rebill_disabled_by_kill_switch(db_session, fake_client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "yookassa_recurrent_enabled", False)
    await seed_products(db_session)
    user = await _user(db_session, 900010)
    db_session.add(
        Subscription(
            user_id=user.id,
            product_slug="subscription_month",
            status="active",
            price_kopecks=9900,
            currency="RUB",
            payment_method_id="pm-saved-1",
            next_charge_at=datetime.now(UTC) - timedelta(hours=1),
        )
    )
    await db_session.commit()

    service = BillingService(db_session)
    attempts = await service.rebill_due_subscriptions()
    assert attempts == 0
    assert fake_client.calls == []


@pytest.mark.asyncio
async def test_rebill_charges_saved_method_with_stable_key(db_session, fake_client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "yookassa_recurrent_enabled", True)
    await seed_products(db_session)
    user = await _user(db_session, 900011)
    db_session.add(
        Subscription(
            user_id=user.id,
            product_slug="subscription_month",
            status="active",
            price_kopecks=9900,
            currency="RUB",
            payment_method_id="pm-saved-1",
            current_period_start=datetime.now(UTC) - timedelta(days=29),
            current_period_end=datetime.now(UTC),
            next_charge_at=datetime.now(UTC) - timedelta(hours=1),
        )
    )
    await db_session.commit()

    service = BillingService(db_session)
    attempts = await service.rebill_due_subscriptions()
    assert attempts == 1
    kind, kwargs = fake_client.calls[0]
    assert kind == "rebill"
    assert kwargs["payment_method_id"] == "pm-saved-1"
    assert kwargs["amount_kopecks"] == 9900
    assert kwargs["idempotence_key"].startswith("rebill-")
    assert len(kwargs["idempotence_key"]) <= 64
    payment = (await db_session.execute(select(Payment))).scalar_one()
    assert payment.subscription_id == kwargs["owner_id"] or str(payment.subscription_id) == str(kwargs["owner_id"])


@pytest.mark.asyncio
async def test_renewal_webhook_extends_active_period(db_session, fake_client, monkeypatch) -> None:
    """Renewal fulfillment must extend from current period end, and a
    duplicate renewal webhook must not create a duplicate ledger."""
    monkeypatch.setattr(settings, "yookassa_recurrent_enabled", True)
    await seed_products(db_session)
    user = await _user(db_session, 900014)
    service = BillingService(db_session)

    started = await service.start_subscription(user.id, "subscription_month")
    first_payment = (await db_session.execute(select(Payment))).scalar_one()
    fake_client.remote[first_payment.provider_payment_id] = _remote_for(
        first_payment, str(started["subscription_id"])
    )
    await service.verify_and_process_webhook(first_payment.provider_payment_id)

    sub = (await db_session.execute(select(Subscription))).scalar_one()
    first_end = sub.current_period_end

    # Make the subscription due for renewal (period boundary reached).
    sub.next_charge_at = datetime.now(UTC) - timedelta(hours=1)
    await db_session.commit()

    attempts = await service.rebill_due_subscriptions()
    assert attempts == 1
    renewal_payment = (
        await db_session.execute(
            select(Payment).where(Payment.idempotence_key.like("rebill-%"))
        )
    ).scalar_one()
    fake_client.remote[renewal_payment.provider_payment_id] = _remote_for(
        renewal_payment, str(started["subscription_id"])
    )

    result = await service.verify_and_process_webhook(renewal_payment.provider_payment_id)
    assert result["processed"] is True

    sub = (await db_session.execute(select(Subscription))).scalar_one()
    assert sub.status == "active"
    assert sub.current_period_end > first_end
    # Extended by exactly one period from the previous end.
    assert (sub.current_period_end - first_end).days in (29, 30)

    ledgers = (await db_session.execute(select(AccessLedger))).scalars().all()
    assert len(ledgers) == 2  # one per paid period, exactly

    # Duplicate renewal webhook: no third ledger.
    again = await service.verify_and_process_webhook(renewal_payment.provider_payment_id)
    assert again["reason"] == "already_fulfilled"
    ledgers = (await db_session.execute(select(AccessLedger))).scalars().all()
    assert len(ledgers) == 2


@pytest.mark.asyncio
async def test_pending_unique_index_blocks_concurrent_start_rows(db_session) -> None:
    """DB-level concurrency guard: two pending subscriptions for the same
    user+product violate the partial unique index."""
    from sqlalchemy.exc import IntegrityError as SQLIntegrityError

    user = await _user(db_session, 900015)
    db_session.add(
        Subscription(user_id=user.id, product_slug="subscription_month", status="pending", price_kopecks=9900, currency="RUB")
    )
    await db_session.commit()
    db_session.add(
        Subscription(user_id=user.id, product_slug="subscription_month", status="pending", price_kopecks=9900, currency="RUB")
    )
    with pytest.raises(SQLIntegrityError):
        await db_session.commit()
