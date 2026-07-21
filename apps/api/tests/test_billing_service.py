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
from datetime import UTC, date, datetime, timedelta

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

    # The reservation is durably committed despite the failed POST — and so
    # is the first-attempt anchor that bounds the 24h dedupe window.
    subs = (await db_session.execute(select(Subscription))).scalars().all()
    payments = (await db_session.execute(select(Payment))).scalars().all()
    assert len(subs) == 1
    assert len(payments) == 1
    assert payments[0].status == "pending"
    assert payments[0].provider_payment_id is None
    assert payments[0].first_attempt_at is not None
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
    assert keys[1] == f"{first_key}-a1"
    rebill_calls = [c for c in fake_client.calls if c[0] == "rebill"]
    assert len(rebill_calls) == 2
    assert rebill_calls[1][1]["idempotence_key"] != first_key


@pytest.mark.asyncio
async def test_rebill_attempt_key_tenth_attempt_no_collision(db_session) -> None:
    """Regression: with a 54-char base the old [:64] truncation collapsed
    -attempt-10 into -attempt-1 (a DEAD key -> double-charge risk). The
    compact suffix keeps the 10th fresh key distinct and <=64."""
    await seed_products(db_session)
    user = await _user(db_session, 900042)
    sub = Subscription(
        user_id=user.id,
        product_slug="subscription_month",
        status="past_due",
        price_kopecks=9900,
        currency="RUB",
        payment_method_id="pm-saved-1",
        current_period_start=datetime.now(UTC) - timedelta(days=29),
        current_period_end=datetime.now(UTC),
        next_charge_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(sub)
    await db_session.commit()

    label = sub.current_period_end.date().isoformat()
    base = f"rebill-{sub.id}-{label}"
    assert len(base) == 54  # the truncation boundary of the old scheme
    # The old scheme really collided: prove it before proving the fix.
    assert f"{base}-attempt-10"[:64] == f"{base}-attempt-1"

    existing: list[str] = []
    for n in range(1, 10):
        key = f"{base}-a{n}"
        existing.append(key)
        db_session.add(
            Payment(
                user_id=user.id,
                amount=9900,
                currency="RUB",
                status="canceled",
                provider="yookassa",
                product_slug="subscription_month",
                idempotence_key=key,
                subscription_id=sub.id,
            )
        )
    await db_session.commit()

    service = BillingService(db_session)
    key10 = await service._next_rebill_attempt_key(sub, label)
    assert len(key10) <= 64
    assert key10 == f"{base}-a10"
    assert key10 not in existing
    assert key10 != f"{base}-attempt-10"[:64]


@pytest.mark.asyncio
async def test_rebill_cycle_reuses_live_attempt_until_known_canceled(db_session, fake_client, monkeypatch) -> None:
    """Anti-double-charge cycle resolution: base canceled -> next run creates
    exactly ONE fresh attempt + ONE provider call; a second cron run BEFORE
    the webhook reuses that live attempt (no new row, no provider call);
    known-cancel of the fresh attempt then allows exactly the NEXT unique
    key. All keys <=64 and unique."""
    monkeypatch.setattr(settings, "yookassa_recurrent_enabled", True)
    _, sub = await _make_due_subscription(db_session, 900043)
    service = BillingService(db_session)

    # Run 1: base cycle payment charged.
    assert await service.rebill_due_subscriptions() == 1
    base_payment = (await db_session.execute(select(Payment))).scalar_one()
    base_key = base_payment.idempotence_key

    # Webhook: base canceled (e.g. card declined) -> sub past_due.
    fake_client.remote[base_payment.provider_payment_id] = _remote_for(
        base_payment, str(sub.id), status="canceled", paid=False
    )
    assert (await service.verify_and_process_webhook(base_payment.provider_payment_id))["reason"] == "canceled"

    # Run 2: exactly ONE fresh attempt and ONE provider call.
    await db_session.refresh(sub)
    sub.next_charge_at = datetime.now(UTC) - timedelta(hours=1)
    await db_session.commit()
    assert await service.rebill_due_subscriptions() == 1
    payments = (await db_session.execute(select(Payment))).scalars().all()
    assert len(payments) == 2
    attempt1 = next(p for p in payments if p.idempotence_key != base_key)
    assert attempt1.idempotence_key == f"{base_key}-a1"
    assert attempt1.provider_payment_id is not None
    rebill_calls = [c for c in fake_client.calls if c[0] == "rebill"]
    assert len(rebill_calls) == 2

    # Run 3 BEFORE the webhook: the live attempt is reused — no new row, no
    # provider call, no charge.
    assert await service.rebill_due_subscriptions() == 0
    payments = (await db_session.execute(select(Payment))).scalars().all()
    assert len(payments) == 2
    assert len([c for c in fake_client.calls if c[0] == "rebill"]) == 2

    # Known-cancel the fresh attempt: the next run allows exactly the NEXT
    # unique key, nothing else.
    fake_client.remote[attempt1.provider_payment_id] = _remote_for(
        attempt1, str(sub.id), status="canceled", paid=False
    )
    assert (await service.verify_and_process_webhook(attempt1.provider_payment_id))["reason"] == "canceled"
    await db_session.refresh(sub)
    sub.next_charge_at = datetime.now(UTC) - timedelta(hours=1)
    await db_session.commit()
    assert await service.rebill_due_subscriptions() == 1
    payments = (await db_session.execute(select(Payment))).scalars().all()
    assert len(payments) == 3
    keys = [p.idempotence_key for p in payments]
    assert len(set(keys)) == 3
    assert all(len(k) <= 64 for k in keys)
    assert f"{base_key}-a2" in keys
    assert len([c for c in fake_client.calls if c[0] == "rebill"]) == 3


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


# ---- In-flight renewal succeeding after a user cancel ----

@pytest.mark.asyncio
async def test_inflight_rebill_fulfilled_after_cancel_keeps_canceled(db_session, fake_client, monkeypatch) -> None:
    """An in-flight renewal that succeeds AFTER the user's cancel must honor
    the paid period exactly once (the money never vanishes) while the
    subscription stays canceled with next_charge_at NULL — never resurrected,
    never re-charged. Duplicate webhook stays idempotent."""
    monkeypatch.setattr(settings, "yookassa_recurrent_enabled", True)
    await seed_products(db_session)
    user = await _user(db_session, 900044)
    service = BillingService(db_session)

    # Activate: initial payment fulfilled -> active with a paid period.
    started = await service.start_subscription(user.id, "subscription_month")
    first_payment = (await db_session.execute(select(Payment))).scalar_one()
    fake_client.remote[first_payment.provider_payment_id] = _remote_for(
        first_payment, str(started["subscription_id"])
    )
    await service.verify_and_process_webhook(first_payment.provider_payment_id)
    sub = (await db_session.execute(select(Subscription))).scalar_one()
    first_end = sub.current_period_end

    # Renewal becomes due and is charged (in-flight at the provider).
    sub.next_charge_at = datetime.now(UTC) - timedelta(hours=1)
    await db_session.commit()
    assert await service.rebill_due_subscriptions() == 1
    renewal = (
        await db_session.execute(select(Payment).where(Payment.idempotence_key.like("rebill-%")))
    ).scalar_one()

    # The user cancels BEFORE the provider confirms the renewal.
    canceled = await service.cancel_subscription(user.id, "user_request")
    assert canceled["status"] == "canceled"

    # The in-flight renewal succeeds: fulfill the paid period exactly once.
    fake_client.remote[renewal.provider_payment_id] = _remote_for(renewal, str(sub.id))
    result = await service.verify_and_process_webhook(renewal.provider_payment_id)
    assert result["processed"] is True
    await db_session.refresh(sub)
    assert sub.status == "canceled"
    assert sub.next_charge_at is None
    assert sub.current_period_end == first_end + timedelta(days=30)
    # AccessLedger.id is a UUID — order by start_date, never by id.
    ledgers = (await db_session.execute(select(AccessLedger).order_by(AccessLedger.start_date))).scalars().all()
    assert len(ledgers) == 2
    # The renewal ledger covers the EXTENDED period (start at the prior
    # period end, which is still in the future), not blindly today.
    assert ledgers[0].start_date == datetime.now(UTC).date()
    assert ledgers[1].start_date == first_end.date()
    assert ledgers[1].end_date == first_end.date() + timedelta(days=29)

    # Duplicate delivery: idempotent — no second extension.
    again = await service.verify_and_process_webhook(renewal.provider_payment_id)
    assert again["reason"] == "already_fulfilled"
    await db_session.refresh(sub)
    assert sub.status == "canceled"
    assert sub.next_charge_at is None
    assert sub.current_period_end == first_end + timedelta(days=30)
    assert len((await db_session.execute(select(AccessLedger))).scalars().all()) == 2


@pytest.mark.asyncio
async def test_canceled_initial_payment_not_resurrected(db_session, fake_client) -> None:
    """An initial payment linked to a canceled (never-active) start must NOT
    activate anything: subscription_inactive, payment stays pending, no
    access ledger. Only paid renewals are honored after a cancel."""
    await seed_products(db_session)
    user = await _user(db_session, 900045)
    service = BillingService(db_session)

    started = await service.start_subscription(user.id, "subscription_month")
    payment = (await db_session.execute(select(Payment))).scalar_one()
    sub = (await db_session.execute(select(Subscription))).scalar_one()
    sub.status = "canceled"  # legacy/manual state: never activated
    await db_session.commit()

    fake_client.remote[payment.provider_payment_id] = _remote_for(payment, str(started["subscription_id"]))
    result = await service.verify_and_process_webhook(payment.provider_payment_id)
    assert result == {"processed": False, "reason": "subscription_inactive"}
    await db_session.refresh(sub)
    assert sub.status == "canceled"
    await db_session.refresh(payment)
    assert payment.status == "pending"
    assert (await db_session.execute(select(AccessLedger))).scalars().all() == []


# ---- One-time retry after a known-canceled attempt ----

@pytest.mark.asyncio
async def test_one_time_retry_after_cancel_fulfills_fresh_attempt(db_session, fake_client) -> None:
    """Regression: the fresh attempt key is purchase-<uuid>-attempt-N, but the
    provider metadata always carries the PLAIN purchase UUID. The owner
    invariant must strip the exact -attempt-N suffix — otherwise every
    verified retry is a permanent mismatch (money without grant)."""
    await seed_products(db_session)
    user = await _user(db_session, 900046)
    service = BillingService(db_session)

    started = await service.start_purchase(user.id, "horary_1")
    base_payment = (await db_session.execute(select(Payment))).scalar_one()
    fake_client.remote[base_payment.provider_payment_id] = _remote_for(
        base_payment, str(started["purchase_id"]), status="canceled", paid=False
    )
    assert (await service.verify_and_process_webhook(base_payment.provider_payment_id))["reason"] == "canceled"

    # Retry of the same purchase: FRESH attempt payment, same linked purchase.
    retried = await service.start_purchase(user.id, "horary_1")
    assert retried["status"] == "pending"
    assert retried["purchase_id"] == started["purchase_id"]
    payments = (await db_session.execute(select(Payment))).scalars().all()
    assert len(payments) == 2
    fresh = next(p for p in payments if p.id != base_payment.id)
    assert fresh.idempotence_key == f"purchase-{started['purchase_id']}-attempt-1"
    purchase = (await db_session.execute(select(Purchase))).scalar_one()
    assert purchase.payment_id == fresh.id

    # Verified succeeded webhook on the fresh attempt fulfills exactly once.
    fake_client.remote[fresh.provider_payment_id] = _remote_for(fresh, str(started["purchase_id"]))
    result = await service.verify_and_process_webhook(fresh.provider_payment_id)
    assert result["processed"] is True
    credit = (await db_session.execute(select(HoraryCredit))).scalar_one()
    assert credit.amount == 1
    assert credit.source == "paid"

    again = await service.verify_and_process_webhook(fresh.provider_payment_id)
    assert again["reason"] == "already_fulfilled"
    assert len((await db_session.execute(select(HoraryCredit))).scalars().all()) == 1


@pytest.mark.asyncio
async def test_natal_retry_after_cancel_fulfills_entitlement(db_session, fake_client, monkeypatch) -> None:
    """Same retry-owner path for the natal entitlement: canceled base -> fresh
    attempt -> fulfilled entitlement bound to the CURRENT context hash."""
    from datetime import date as Date, time as dtime
    from decimal import Decimal

    from app.db.models import UserProfile
    from app.services.natal_context_service import NatalContextService

    monkeypatch.setattr(settings, "natal_report_enabled", True)
    await seed_products(db_session)
    user = await _user(db_session, 900047)
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
    base_payment = (await db_session.execute(select(Payment))).scalar_one()
    fake_client.remote[base_payment.provider_payment_id] = _remote_for(
        base_payment, str(started["purchase_id"]), status="canceled", paid=False
    )
    await service.verify_and_process_webhook(base_payment.provider_payment_id)

    retried = await service.start_purchase(user.id, "natal_full_report")
    assert retried["status"] == "pending"  # not yet entitled
    fresh = (
        await db_session.execute(select(Payment).where(Payment.id != base_payment.id))
    ).scalar_one()
    fake_client.remote[fresh.provider_payment_id] = _remote_for(fresh, str(started["purchase_id"]))
    result = await service.verify_and_process_webhook(fresh.provider_payment_id)
    assert result["processed"] is True
    assert await service.has_natal_entitlement(user.id, real_hash) is True

    entitled_again = await service.start_purchase(user.id, "natal_full_report")
    assert entitled_again["status"] == "already_entitled"


# ---- Renewal ledger covers the EXTENDED period ----

@pytest.mark.asyncio
async def test_renewal_ledger_covers_extended_period(db_session, fake_client, monkeypatch) -> None:
    """Renewal extends current_period_end FROM the prior base_end; the access
    ledger must cover that same extended period (start = max(today, prior
    base_end)), not blindly today — asserted on DATES, not just row count."""
    monkeypatch.setattr(settings, "yookassa_recurrent_enabled", True)
    _, sub = await _make_due_subscription(db_session, 900048)
    # Prior period still has 10 days left (future base_end).
    sub.current_period_end = datetime.now(UTC) + timedelta(days=10)
    await db_session.commit()
    await db_session.refresh(sub)
    base_end = sub.current_period_end  # DB-normalized (tz-naive on SQLite)
    service = BillingService(db_session)

    assert await service.rebill_due_subscriptions() == 1
    renewal = (await db_session.execute(select(Payment))).scalar_one()
    fake_client.remote[renewal.provider_payment_id] = _remote_for(renewal, str(sub.id))
    result = await service.verify_and_process_webhook(renewal.provider_payment_id)
    assert result["processed"] is True

    await db_session.refresh(sub)
    assert sub.current_period_end == base_end + timedelta(days=30)
    ledger = (await db_session.execute(select(AccessLedger))).scalar_one()
    assert ledger.start_date == base_end.date()
    assert ledger.end_date == base_end.date() + timedelta(days=29)


# ---- Non-renewing lifecycle fail-safe (initial success without saved method) ----

@pytest.mark.asyncio
async def test_initial_success_without_saved_method_expires_and_new_start_works(db_session, fake_client) -> None:
    """Regression: an initial payment may succeed with payment_method_saved=
    false. The paid period is fully honored, but the subscription must expire
    at period end — otherwise it stays live forever and the one-live guard
    deadlocks any new start. No charge is ever attempted for it."""
    await seed_products(db_session)
    user = await _user(db_session, 900049)
    service = BillingService(db_session)

    started = await service.start_subscription(user.id, "subscription_month")
    payment = (await db_session.execute(select(Payment))).scalar_one()
    fake_client.remote[payment.provider_payment_id] = _remote_for(
        payment,
        str(started["subscription_id"]),
        payment_method_saved=False,
        payment_method_id=None,
    )
    result = await service.verify_and_process_webhook(payment.provider_payment_id)
    assert result["processed"] is True

    sub = (await db_session.execute(select(Subscription))).scalar_one()
    assert sub.status == "active"
    assert sub.payment_method_id is None  # cannot ever renew
    assert len((await db_session.execute(select(AccessLedger))).scalars().all()) == 1

    # The paid period ends.
    sub.current_period_end = datetime.now(UTC) - timedelta(hours=1)
    await db_session.commit()

    # Honest read: expired, and the paid ledger is preserved.
    status = await service.get_subscription_status(user.id)
    assert status["status"] == "expired"
    await db_session.refresh(sub)
    assert sub.status == "expired"
    assert sub.next_charge_at is None
    assert len((await db_session.execute(select(AccessLedger))).scalars().all()) == 1

    # No deadlock: a new start works immediately after expiry.
    new_started = await service.start_subscription(user.id, "subscription_month")
    assert new_started["status"] == "pending"
    subs = (await db_session.execute(select(Subscription))).scalars().all()
    assert len(subs) == 2
    assert sorted(s.status for s in subs) == ["expired", "pending"]


@pytest.mark.asyncio
async def test_expire_never_touches_renewing_or_past_due(db_session, fake_client, monkeypatch) -> None:
    """The fail-safe is strictly for non-renewing subs: an active sub WITH a
    saved method renews via rebill (never expired here), and a past_due retry
    is left alone."""
    monkeypatch.setattr(settings, "yookassa_recurrent_enabled", True)
    _, sub = await _make_due_subscription(db_session, 900050)  # has pm-saved-1
    service = BillingService(db_session)

    status = await service.get_subscription_status(sub.user_id)
    assert status["status"] == "active"  # renewing sub is NOT expired

    sub.status = "past_due"
    await db_session.commit()
    status = await service.get_subscription_status(sub.user_id)
    assert status["status"] == "past_due"  # retry flow untouched


@pytest.mark.asyncio
async def test_rebill_job_expires_non_renewing_without_charging(db_session, fake_client, monkeypatch) -> None:
    """The canonical job expires non-renewing subs with zero provider calls,
    and the transition does not depend on the recurrent kill-switch."""
    monkeypatch.setattr(settings, "yookassa_recurrent_enabled", True)
    await seed_products(db_session)
    user = await _user(db_session, 900051)
    sub = Subscription(
        user_id=user.id,
        product_slug="subscription_month",
        status="active",
        price_kopecks=9900,
        currency="RUB",
        payment_method_id=None,
        current_period_start=datetime.now(UTC) - timedelta(days=31),
        current_period_end=datetime.now(UTC) - timedelta(days=1),
        next_charge_at=datetime.now(UTC) - timedelta(days=1),
    )
    db_session.add(sub)
    await db_session.commit()

    service = BillingService(db_session)
    attempts = await service.rebill_due_subscriptions()
    assert attempts == 0
    assert fake_client.calls == []  # no charge attempt, ever
    await db_session.refresh(sub)
    assert sub.status == "expired"
    assert sub.next_charge_at is None


@pytest.mark.asyncio
async def test_expiry_runs_even_with_recurrent_kill_switch_off(db_session, fake_client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "yookassa_recurrent_enabled", False)
    await seed_products(db_session)
    user = await _user(db_session, 900052)
    db_session.add(
        Subscription(
            user_id=user.id,
            product_slug="subscription_month",
            status="active",
            price_kopecks=9900,
            currency="RUB",
            payment_method_id=None,
            current_period_start=datetime.now(UTC) - timedelta(days=31),
            current_period_end=datetime.now(UTC) - timedelta(days=1),
            next_charge_at=datetime.now(UTC) - timedelta(days=1),
        )
    )
    await db_session.commit()

    service = BillingService(db_session)
    assert await service.rebill_due_subscriptions() == 0  # kill-switch: zero charges
    assert fake_client.calls == []
    sub = (await db_session.execute(select(Subscription))).scalar_one()
    assert sub.status == "expired"  # lifecycle hygiene is NOT gated by charging


# ---- 24h dedupe window for START flows (initial + one-time) ----

@pytest.mark.asyncio
async def test_start_subscription_after_window_no_second_charge(db_session, fake_client) -> None:
    """Past the 24h dedupe window the first attempt's outcome is unknowable
    and the provider no longer dedupes the key: NO provider POST, stable
    domain error, pending owner/payment stay observable for reconciliation."""
    await seed_products(db_session)
    user = await _user(db_session, 900053)
    service = BillingService(db_session)

    calls: list[dict] = []

    async def failing_initial(**kwargs):
        calls.append(kwargs)
        raise YooKassaError("timeout")

    fake_client.create_initial_payment = failing_initial
    with pytest.raises(YooKassaError):
        await service.start_subscription(user.id, "subscription_month")
    payment = (await db_session.execute(select(Payment))).scalar_one()
    assert payment.first_attempt_at is not None  # durable anchor despite failure

    # The first attempt happened >24h ago: the dedupe window has expired.
    payment.first_attempt_at = datetime.now(UTC) - timedelta(hours=25)
    await db_session.commit()

    with pytest.raises(ValueError, match="PAYMENT_NEEDS_RECONCILIATION"):
        await service.start_subscription(user.id, "subscription_month")
    assert len(calls) == 1  # ZERO provider calls after the window

    await db_session.refresh(payment)
    assert payment.status == "pending"  # observable for reconciliation
    sub = (await db_session.execute(select(Subscription))).scalar_one()
    assert sub.status == "pending"


@pytest.mark.asyncio
async def test_start_purchase_retry_inside_window_reuses_key(db_session, fake_client) -> None:
    """One-time mirror of the subscription timeout contract: failed first
    attempt leaves the durable reservation + anchor; retry inside 24h uses
    the SAME key (provider dedupes) and links the same purchase."""
    await seed_products(db_session)
    user = await _user(db_session, 900054)
    service = BillingService(db_session)

    attempts: list[dict] = []
    original = fake_client.create_one_time_payment

    async def fail_once(**kwargs):
        attempts.append(kwargs)
        if len(attempts) == 1:
            raise YooKassaError("timeout")
        return await original(**kwargs)

    fake_client.create_one_time_payment = fail_once
    with pytest.raises(YooKassaError):
        await service.start_purchase(user.id, "horary_1")
    payment = (await db_session.execute(select(Payment))).scalar_one()
    assert payment.status == "pending"
    assert payment.first_attempt_at is not None
    stable_key = payment.idempotence_key

    result = await service.start_purchase(user.id, "horary_1")
    assert result["status"] == "pending"
    assert len(attempts) == 2
    assert {a["idempotence_key"] for a in attempts} == {stable_key}

    payments = (await db_session.execute(select(Payment))).scalars().all()
    assert len(payments) == 1  # retry never creates a second local payment
    purchase = (await db_session.execute(select(Purchase))).scalar_one()
    assert purchase.payment_id == payment.id


@pytest.mark.asyncio
async def test_start_purchase_after_window_no_second_charge(db_session, fake_client) -> None:
    await seed_products(db_session)
    user = await _user(db_session, 900055)
    service = BillingService(db_session)

    calls: list[dict] = []

    async def failing_one_time(**kwargs):
        calls.append(kwargs)
        raise YooKassaError("timeout")

    fake_client.create_one_time_payment = failing_one_time
    with pytest.raises(YooKassaError):
        await service.start_purchase(user.id, "horary_1")
    payment = (await db_session.execute(select(Payment))).scalar_one()
    assert payment.first_attempt_at is not None

    payment.first_attempt_at = datetime.now(UTC) - timedelta(hours=25)
    await db_session.commit()

    with pytest.raises(ValueError, match="PAYMENT_NEEDS_RECONCILIATION"):
        await service.start_purchase(user.id, "horary_1")
    assert len(calls) == 1  # ZERO provider calls after the window

    await db_session.refresh(payment)
    assert payment.status == "pending"
    purchase = (await db_session.execute(select(Purchase))).scalar_one()
    assert purchase.status == "pending"


def test_payment_needs_reconciliation_maps_to_409() -> None:
    """Stable API contract for the expired-window domain error."""
    from app.api.payment import _domain_error

    exc = _domain_error(ValueError("PAYMENT_NEEDS_RECONCILIATION"))
    assert exc.status_code == 409
    assert exc.detail["code"] == "PAYMENT_NEEDS_RECONCILIATION"


# ---- Deferred initial paid period (bonus days first) ----

@pytest.mark.asyncio
async def test_initial_fulfill_defers_paid_period_after_existing_access(db_session, fake_client) -> None:
    """The AccessCard promise "сначала бонусные дни": with an active referral
    bonus (and a leftover paid ledger), the paid 30-day period must start the
    day AFTER the latest existing access end — no overlap (no lost days), no
    gap — and current_period_*/next_charge_at shift with the same deferral
    (period end exclusive vs ledger inclusive)."""
    await seed_products(db_session)
    user = await _user(db_session, 900056)
    today = date.today()
    db_session.add(
        AccessLedger(
            user_id=user.id, entry_type="referral_bonus", days_granted=14,
            start_date=today - timedelta(days=3), end_date=today + timedelta(days=11),
        )
    )
    db_session.add(
        AccessLedger(
            user_id=user.id, entry_type="subscription", days_granted=30,
            start_date=today - timedelta(days=25), end_date=today + timedelta(days=5),
        )
    )
    await db_session.commit()
    service = BillingService(db_session)

    started = await service.start_subscription(user.id, "subscription_month")
    payment = (await db_session.execute(select(Payment))).scalar_one()
    fake_client.remote[payment.provider_payment_id] = _remote_for(payment, str(started["subscription_id"]))
    result = await service.verify_and_process_webhook(payment.provider_payment_id)
    assert result["processed"] is True

    expected_start = today + timedelta(days=12)  # latest end (+11d) + 1 day
    ledgers = (
        await db_session.execute(select(AccessLedger).order_by(AccessLedger.start_date))
    ).scalars().all()
    assert len(ledgers) == 3
    paid = ledgers[-1]
    assert paid.entry_type == "subscription"
    assert paid.start_date == expected_start
    assert paid.end_date == expected_start + timedelta(days=29)  # full 30 days, inclusive

    sub = (await db_session.execute(select(Subscription))).scalar_one()
    assert sub.current_period_start.date() == expected_start
    assert sub.current_period_end.date() == expected_start + timedelta(days=30)
    assert sub.next_charge_at == sub.current_period_end  # charge at paid period end

    # No overlap with any existing access day: previous latest end + 1 == start.
    assert paid.start_date == today + timedelta(days=11) + timedelta(days=1)


@pytest.mark.asyncio
async def test_initial_fulfill_without_prior_access_starts_today(db_session, fake_client) -> None:
    """No existing access: the initial paid period starts today (no deferral)."""
    await seed_products(db_session)
    user = await _user(db_session, 900057)
    service = BillingService(db_session)

    started = await service.start_subscription(user.id, "subscription_month")
    payment = (await db_session.execute(select(Payment))).scalar_one()
    fake_client.remote[payment.provider_payment_id] = _remote_for(payment, str(started["subscription_id"]))
    await service.verify_and_process_webhook(payment.provider_payment_id)

    today = date.today()
    paid = (await db_session.execute(select(AccessLedger))).scalar_one()
    assert paid.start_date == today
    assert paid.end_date == today + timedelta(days=29)
    sub = (await db_session.execute(select(Subscription))).scalar_one()
    assert sub.current_period_end.date() == today + timedelta(days=30)
    assert sub.next_charge_at == sub.current_period_end
