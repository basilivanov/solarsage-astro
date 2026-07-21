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

import inspect
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.db.models import (
    AccessLedger,
    HoraryCredit,
    Payment,
    Product,
    Purchase,
    Subscription,
    User,
)
from app.services.billing_service import BillingService
from app.services.product_catalog import seed_products
from app.services.yookassa_client import YooKassaClient, YooKassaError


class FakeYooKassaClient:
    """In-test provider fake: records create calls, serves get_payment fakes.

    Signatures mirror YooKassaClient exactly (keyword-only, no **kwargs): a
    misspelled argument at a call site (e.g. ``amount_kopeks=``) raises
    TypeError here instead of being silently swallowed by the fake."""

    def __init__(self, remote: dict | None = None):
        self.calls: list[tuple[str, dict]] = []
        self.remote = remote or {}
        self.next_id = 0
        # >0: the next N recurrent create calls raise YooKassaError BEFORE
        # recording — an injected transport failure with unknown outcome.
        self.fail_recurrent_times = 0

    def _new_id(self) -> str:
        self.next_id += 1
        return f"prov-{self.next_id:04d}"

    async def create_initial_payment(
        self,
        *,
        user_id: uuid.UUID,
        owner_id: uuid.UUID,
        amount_kopecks: int,
        currency: str,
        description: str,
        return_url: str,
        product_slug: str,
        idempotence_key: str,
    ) -> dict:
        self.calls.append(("initial", {
            "user_id": user_id,
            "owner_id": owner_id,
            "amount_kopecks": amount_kopecks,
            "currency": currency,
            "description": description,
            "return_url": return_url,
            "product_slug": product_slug,
            "idempotence_key": idempotence_key,
        }))
        return {"provider_payment_id": self._new_id(), "confirmation_url": "https://pay.example/init", "status": "pending"}

    async def create_one_time_payment(
        self,
        *,
        user_id: uuid.UUID,
        owner_id: uuid.UUID,
        amount_kopecks: int,
        currency: str,
        description: str,
        return_url: str,
        product_slug: str,
        idempotence_key: str,
    ) -> dict:
        self.calls.append(("one_time", {
            "user_id": user_id,
            "owner_id": owner_id,
            "amount_kopecks": amount_kopecks,
            "currency": currency,
            "description": description,
            "return_url": return_url,
            "product_slug": product_slug,
            "idempotence_key": idempotence_key,
        }))
        return {"provider_payment_id": self._new_id(), "confirmation_url": "https://pay.example/once", "status": "pending"}

    async def create_recurrent_payment(
        self,
        *,
        user_id: uuid.UUID,
        owner_id: uuid.UUID,
        payment_method_id: str,
        amount_kopecks: int,
        currency: str,
        description: str,
        product_slug: str,
        period_label: str,
        idempotence_key: str,
    ) -> dict:
        if self.fail_recurrent_times > 0:
            self.fail_recurrent_times -= 1
            raise YooKassaError("injected transport failure (unknown outcome)")
        self.calls.append(("rebill", {
            "user_id": user_id,
            "owner_id": owner_id,
            "payment_method_id": payment_method_id,
            "amount_kopecks": amount_kopecks,
            "currency": currency,
            "description": description,
            "product_slug": product_slug,
            "period_label": period_label,
            "idempotence_key": idempotence_key,
        }))
        return {"provider_payment_id": self._new_id(), "status": "pending"}

    async def get_payment(self, provider_payment_id: str) -> dict:
        return self.remote[provider_payment_id]


def test_fake_client_mirrors_real_provider_signatures() -> None:
    """Guard against contract drift: the fake must expose the SAME typed
    keyword-only parameters as YooKassaClient, so a typo'd kwarg at any call
    site (e.g. amount_kopeks) fails with TypeError instead of passing through
    a **kwargs fake. Also proves no VAR_KEYWORD (**kwargs) crept back in."""
    for name in (
        "create_initial_payment",
        "create_one_time_payment",
        "create_recurrent_payment",
        "get_payment",
    ):
        real = inspect.signature(getattr(YooKassaClient, name))
        fake = inspect.signature(getattr(FakeYooKassaClient, name))
        assert list(fake.parameters) == list(real.parameters), name
        assert all(
            p.kind is not inspect.Parameter.VAR_KEYWORD for p in fake.parameters.values()
        ), name


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


async def _make_due_subscription(db_session, tg: int, *, status: str = "active") -> tuple[User, Subscription]:
    """An active/past_due subscription due for renewal RIGHT NOW."""
    await seed_products(db_session)
    user = await _user(db_session, tg)
    sub = Subscription(
        user_id=user.id,
        product_slug="subscription_month",
        status=status,
        price_kopecks=9900,
        currency="RUB",
        payment_method_id="pm-saved-1",
        current_period_start=datetime.now(UTC) - timedelta(days=29),
        current_period_end=datetime.now(UTC),
        next_charge_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(sub)
    await db_session.commit()
    return user, sub


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


# ---- start_purchase: idempotency ----

@pytest.mark.asyncio
async def test_start_purchase_repeat_reuses_pending(db_session, fake_client) -> None:
    """Retry of start_purchase with an existing pending payment must NOT call
    the provider again and must return the SAME payment/confirmation (this
    path previously dereferenced an unbound `result`)."""
    await seed_products(db_session)
    user = await _user(db_session, 900017)
    service = BillingService(db_session)

    first = await service.start_purchase(user.id, "horary_3")
    second = await service.start_purchase(user.id, "horary_3")

    assert second["status"] == "pending"
    assert second["purchase_id"] == first["purchase_id"]
    assert second["provider_payment_id"] == first["provider_payment_id"]
    assert second["confirmation_url"] == first["confirmation_url"]
    assert len(fake_client.calls) == 1  # no duplicate provider payment

    purchases = (await db_session.execute(select(Purchase))).scalars().all()
    payments = (await db_session.execute(select(Payment))).scalars().all()
    assert len(purchases) == 1
    assert len(payments) == 1


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
async def test_live_unique_index_blocks_concurrent_pending_rows(db_session) -> None:
    """DB-level concurrency guard: two live subscriptions for the same user
    violate the one-live-per-user partial unique index."""
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


@pytest.mark.asyncio
async def test_live_unique_index_blocks_two_live_rows_across_plans(db_session) -> None:
    """The guard is per USER, not per product: pending month + active year
    must also violate the index (two charge owners are impossible)."""
    from sqlalchemy.exc import IntegrityError as SQLIntegrityError

    user = await _user(db_session, 900031)
    db_session.add(
        Subscription(user_id=user.id, product_slug="subscription_month", status="pending", price_kopecks=9900, currency="RUB")
    )
    await db_session.commit()
    db_session.add(
        Subscription(user_id=user.id, product_slug="subscription_year", status="active", price_kopecks=99900, currency="RUB")
    )
    with pytest.raises(SQLIntegrityError):
        await db_session.commit()


class TimeoutThenSuccessClient(FakeYooKassaClient):
    """First create call times out; the retry succeeds."""

    def __init__(self):
        super().__init__()
        self.initial_calls = 0

    async def create_initial_payment(
        self,
        *,
        user_id: uuid.UUID,
        owner_id: uuid.UUID,
        amount_kopecks: int,
        currency: str,
        description: str,
        return_url: str,
        product_slug: str,
        idempotence_key: str,
    ) -> dict:
        self.initial_calls += 1
        self.calls.append(("initial", {
            "user_id": user_id,
            "owner_id": owner_id,
            "amount_kopecks": amount_kopecks,
            "currency": currency,
            "description": description,
            "return_url": return_url,
            "product_slug": product_slug,
            "idempotence_key": idempotence_key,
        }))
        if self.initial_calls == 1:
            raise YooKassaError("yookassa transport error: timeout")
        return {
            "provider_payment_id": f"prov-{len(self.calls):04d}",
            "confirmation_url": "https://pay.example/init",
            "status": "pending",
        }


@pytest.mark.asyncio
async def test_provider_timeout_retry_reuses_same_key_and_owner(db_session, monkeypatch) -> None:
    """Timeout/unknown outcome: reservation stays committed; retry reconciles
    with the SAME idempotence key — no second local owner, no second charge."""
    client = TimeoutThenSuccessClient()
    monkeypatch.setattr("app.services.billing_service.get_yookassa_client", lambda: client)
    monkeypatch.setattr(settings, "yookassa_enabled", True)
    monkeypatch.setattr(settings, "yookassa_return_url", "https://app.example/return")
    await seed_products(db_session)
    user = await _user(db_session, 900016)

    service = BillingService(db_session)
    with pytest.raises(YooKassaError):
        await service.start_subscription(user.id, "subscription_month")

    # The reservation is durably committed despite the failed POST.
    subs = (await db_session.execute(select(Subscription))).scalars().all()
    payments = (await db_session.execute(select(Payment))).scalars().all()
    assert len(subs) == 1
    assert len(payments) == 1
    assert payments[0].status == "pending"
    assert payments[0].provider_payment_id is None
    stable_key = payments[0].idempotence_key

    # A FRESH service instance (new request) sees the same committed state.
    service_retry = BillingService(db_session)
    result = await service_retry.start_subscription(user.id, "subscription_month")

    subs = (await db_session.execute(select(Subscription))).scalars().all()
    payments = (await db_session.execute(select(Payment))).scalars().all()
    assert len(subs) == 1, "retry must never create a second local owner"
    assert len(payments) == 1, "retry must never create a second local payment"
    assert payments[0].idempotence_key == stable_key
    assert payments[0].provider_payment_id is not None
    assert result["confirmation_url"] == "https://pay.example/init"

    # Both provider calls used the SAME idempotence key (dedupe contract).
    assert len(client.calls) == 2
    keys = {kwargs["idempotence_key"] for _kind, kwargs in client.calls}
    assert keys == {stable_key}


# ---- Webhook race: owner link is durable BEFORE the provider create ----

@pytest.mark.asyncio
async def test_purchase_payment_link_durable_before_provider_create(db_session, fake_client) -> None:
    """Regression: purchase.payment_id must be COMMITTED before the provider
    create returns, so a webhook arriving mid-charge resolves the owner
    through the FK. The fake checks the link INSIDE the create call itself —
    with the old post-POST linking this records False."""
    await seed_products(db_session)
    user = await _user(db_session, 900040)
    service = BillingService(db_session)

    original_create = fake_client.create_one_time_payment
    link_state_at_create: list[bool] = []

    async def create_and_check_link(**kwargs):
        purchase = (await db_session.execute(select(Purchase))).scalar_one()
        payment = (await db_session.execute(select(Payment))).scalar_one()
        link_state_at_create.append(purchase.payment_id == payment.id)
        return await original_create(**kwargs)

    fake_client.create_one_time_payment = create_and_check_link
    started = await service.start_purchase(user.id, "horary_1")
    assert link_state_at_create == [True]

    # The immediate webhook then fulfills normally (link was already there).
    payment = (await db_session.execute(select(Payment))).scalar_one()
    fake_client.remote[payment.provider_payment_id] = _remote_for(payment, str(started["purchase_id"]))
    result = await service.verify_and_process_webhook(payment.provider_payment_id)
    assert result["processed"] is True


# ---- One live subscription per user (service guard) ----

@pytest.mark.asyncio
async def test_cross_plan_start_blocked_by_live_pending(db_session, fake_client) -> None:
    await seed_products(db_session)
    user = await _user(db_session, 900032)
    service = BillingService(db_session)

    await service.start_subscription(user.id, "subscription_month")
    with pytest.raises(ValueError, match="LIVE_SUBSCRIPTION_EXISTS"):
        await service.start_subscription(user.id, "subscription_year")

    assert len(fake_client.calls) == 1  # no second provider payment
    subs = (await db_session.execute(select(Subscription))).scalars().all()
    assert len(subs) == 1


@pytest.mark.asyncio
async def test_past_due_subscription_blocks_new_start(db_session, fake_client) -> None:
    await seed_products(db_session)
    user = await _user(db_session, 900033)
    service = BillingService(db_session)

    await service.start_subscription(user.id, "subscription_month")
    sub = (await db_session.execute(select(Subscription))).scalar_one()
    sub.status = "past_due"
    sub.next_charge_at = datetime.now(UTC) + timedelta(days=1)
    await db_session.commit()

    with pytest.raises(ValueError, match="LIVE_SUBSCRIPTION_EXISTS"):
        await service.start_subscription(user.id, "subscription_year")
    with pytest.raises(ValueError, match="LIVE_SUBSCRIPTION_EXISTS"):
        await service.start_subscription(user.id, "subscription_month")


@pytest.mark.asyncio
async def test_cancel_past_due_keeps_paid_period(db_session, fake_client) -> None:
    """Cancel must work on past_due (not only active) and never revoke the
    already-paid access ledger."""
    await seed_products(db_session)
    user = await _user(db_session, 900034)
    service = BillingService(db_session)

    started = await service.start_subscription(user.id, "subscription_month")
    payment = (await db_session.execute(select(Payment))).scalar_one()
    fake_client.remote[payment.provider_payment_id] = _remote_for(payment, str(started["subscription_id"]))
    await service.verify_and_process_webhook(payment.provider_payment_id)

    sub = (await db_session.execute(select(Subscription))).scalar_one()
    sub.status = "past_due"
    sub.next_charge_at = datetime.now(UTC) + timedelta(days=1)
    await db_session.commit()

    result = await service.cancel_subscription(user.id, "too_expensive")
    assert result["status"] == "canceled"
    await db_session.refresh(sub)
    assert sub.status == "canceled"
    assert sub.next_charge_at is None  # no further rebill attempts
    ledger = (await db_session.execute(select(AccessLedger))).scalars().all()
    assert len(ledger) == 1  # paid period untouched


@pytest.mark.asyncio
async def test_cancel_pending_rejected_without_provider_cancel(db_session, fake_client) -> None:
    """NO local cancel of a pending start: without a provider cancel API the
    confirmation URL stays payable and the user could pay into an abandoned
    owner. Cancel is an explicit domain reject; the pending start keeps the
    reuse path, and a plan switch stays the 409 on start."""
    await seed_products(db_session)
    user = await _user(db_session, 900035)
    service = BillingService(db_session)

    await service.start_subscription(user.id, "subscription_month")
    with pytest.raises(ValueError, match="PENDING_SUBSCRIPTION_NOT_CANCELABLE"):
        await service.cancel_subscription(user.id, None)

    sub = (await db_session.execute(select(Subscription))).scalar_one()
    assert sub.status == "pending"  # no silent abandonment
    payment = (await db_session.execute(select(Payment))).scalar_one()
    assert payment.status == "pending"

    # Same-plan start still reuses the pending start; cross-plan stays 409.
    again = await service.start_subscription(user.id, "subscription_month")
    assert again["status"] == "pending"
    assert len(fake_client.calls) == 1
    with pytest.raises(ValueError, match="LIVE_SUBSCRIPTION_EXISTS"):
        await service.start_subscription(user.id, "subscription_year")


# ---- Rebill: 24h dedupe window + known-canceled fresh key ----

@pytest.mark.asyncio
async def test_rebill_retry_within_24h_reuses_same_key(db_session, fake_client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "yookassa_recurrent_enabled", True)
    _, sub = await _make_due_subscription(db_session, 900036)
    service = BillingService(db_session)

    fake_client.fail_recurrent_times = 1  # first attempt: unknown outcome
    assert await service.rebill_due_subscriptions() == 0
    payment = (await db_session.execute(select(Payment))).scalar_one()
    assert payment.status == "pending"
    assert payment.provider_payment_id is None
    assert payment.first_attempt_at is not None
    await db_session.refresh(sub)
    assert sub.status == "past_due"

    # Retry INSIDE the dedupe window: SAME key, provider dedupes the charge.
    sub.next_charge_at = datetime.now(UTC) - timedelta(hours=1)
    await db_session.commit()
    assert await service.rebill_due_subscriptions() == 1
    rebill_calls = [c for c in fake_client.calls if c[0] == "rebill"]
    assert len(rebill_calls) == 1
    assert rebill_calls[0][1]["idempotence_key"] == payment.idempotence_key
    await db_session.refresh(payment)
    assert payment.provider_payment_id is not None


@pytest.mark.asyncio
async def test_rebill_after_24h_window_no_second_charge(db_session, fake_client, monkeypatch) -> None:
    """YooKassa dedupes an Idempotence-Key only for 24h. Past the window the
    ambiguous payment is NEVER auto-charged again: no provider call, payment
    stays pending for manual reconciliation, subscription past_due."""
    monkeypatch.setattr(settings, "yookassa_recurrent_enabled", True)
    _, sub = await _make_due_subscription(db_session, 900037)
    service = BillingService(db_session)

    fake_client.fail_recurrent_times = 1
    assert await service.rebill_due_subscriptions() == 0
    payment = (await db_session.execute(select(Payment))).scalar_one()

    # The first attempt happened >24h ago: the dedupe window has expired.
    payment.first_attempt_at = datetime.now(UTC) - timedelta(hours=25)
    await db_session.refresh(sub)
    sub.next_charge_at = datetime.now(UTC) - timedelta(hours=1)
    await db_session.commit()

    calls_before = list(fake_client.calls)
    assert await service.rebill_due_subscriptions() == 0
    assert fake_client.calls == calls_before  # NO second charge
    await db_session.refresh(payment)
    assert payment.status == "pending"
    assert payment.provider_payment_id is None
    await db_session.refresh(sub)
    assert sub.status == "past_due"


@pytest.mark.asyncio
async def test_rebill_known_canceled_gets_fresh_attempt_key(db_session, fake_client, monkeypatch) -> None:
    """A KNOWN canceled renewal must not block its cycle key forever: the
    webhook demotes the subscription to past_due and the next rebill run
    charges the SAME cycle on a fresh -attempt-N key (dead key never reused)."""
    monkeypatch.setattr(settings, "yookassa_recurrent_enabled", True)
    _, sub = await _make_due_subscription(db_session, 900038)
    service = BillingService(db_session)

    assert await service.rebill_due_subscriptions() == 1
    first_payment = (await db_session.execute(select(Payment))).scalar_one()
    first_key = first_payment.idempotence_key

    # Provider reports the renewal canceled (e.g. card declined).
    fake_client.remote[first_payment.provider_payment_id] = _remote_for(
        first_payment, str(sub.id), status="canceled", paid=False
    )
    result = await service.verify_and_process_webhook(first_payment.provider_payment_id)
    assert result["reason"] == "canceled"
    await db_session.refresh(sub)
    assert sub.status == "past_due"

    sub.next_charge_at = datetime.now(UTC) - timedelta(hours=1)
    await db_session.commit()
    assert await service.rebill_due_subscriptions() == 1

    payments = (await db_session.execute(select(Payment))).scalars().all()
    assert len(payments) == 2
    keys = sorted(p.idempotence_key for p in payments)
    assert keys[0] == first_key
    assert keys[1].startswith(f"{first_key}-attempt-")
    rebill_calls = [c for c in fake_client.calls if c[0] == "rebill"]
    assert len(rebill_calls) == 2
    assert rebill_calls[1][1]["idempotence_key"] != first_key


# ---- Fulfillment safety: no is_active filter, recoverable owner gaps ----

@pytest.mark.asyncio
async def test_webhook_fulfills_despite_deactivated_product(db_session, fake_client) -> None:
    """Deactivating a product stops NEW sales but must never strand an
    already-accepted payment: fulfillment reads the catalog row WITHOUT the
    is_active sales filter (amount verified against the payment snapshot)."""
    await seed_products(db_session)
    user = await _user(db_session, 900039)
    service = BillingService(db_session)

    started = await service.start_purchase(user.id, "horary_3")
    payment = (await db_session.execute(select(Payment))).scalar_one()
    product = (await db_session.execute(select(Product).where(Product.slug == "horary_3"))).scalar_one()
    product.is_active = False  # operator deactivates AFTER the payment started
    await db_session.commit()

    fake_client.remote[payment.provider_payment_id] = _remote_for(payment, str(started["purchase_id"]))
    result = await service.verify_and_process_webhook(payment.provider_payment_id)
    assert result["processed"] is True
    credit = (await db_session.execute(select(HoraryCredit))).scalar_one()
    assert credit.amount == 3


@pytest.mark.asyncio
async def test_webhook_missing_owner_is_recoverable(db_session, fake_client) -> None:
    """A missing owner link must NOT become succeeded-without-grant: the
    payment stays pending (observable/recoverable), and after the link is
    repaired a later webhook fulfills exactly once."""
    await seed_products(db_session)
    user = await _user(db_session, 900041)
    service = BillingService(db_session)

    started = await service.start_purchase(user.id, "horary_1")
    payment = (await db_session.execute(select(Payment))).scalar_one()
    purchase = (await db_session.execute(select(Purchase))).scalar_one()
    purchase.payment_id = None  # damaged/missing link
    await db_session.commit()

    fake_client.remote[payment.provider_payment_id] = _remote_for(payment, str(started["purchase_id"]))
    result = await service.verify_and_process_webhook(payment.provider_payment_id)
    assert result == {"processed": False, "reason": "owner_missing"}
    await db_session.refresh(payment)
    assert payment.status == "pending"
    assert (await db_session.execute(select(HoraryCredit))).scalars().all() == []

    purchase.payment_id = payment.id  # operator repairs the link
    await db_session.commit()
    result = await service.verify_and_process_webhook(payment.provider_payment_id)
    assert result["processed"] is True
    assert (await db_session.execute(select(HoraryCredit))).scalar_one().amount == 1


# ---- Charge boundary invariant: never mask a broken reservation ----

@pytest.mark.asyncio
async def test_missing_idempotence_key_fails_closed(db_session) -> None:
    """No silent `or attempt_key` masking: a reserved payment without its key
    raises BEFORE any provider call (fail closed + system.error log)."""
    payment = Payment(
        user_id=uuid.uuid4(),
        amount=100,
        currency="RUB",
        status="pending",
        provider="yookassa",
        idempotence_key=None,
    )
    with pytest.raises(RuntimeError, match="PAYMENT_INVARIANT_VIOLATION"):
        BillingService._require_idempotence_key(payment)
