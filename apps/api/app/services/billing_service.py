# ############################################################################
# AI_HEADER: MODULE_BILLING_SERVICE — subscription/purchase business logic.
# ROLE: Start subscriptions and one-time purchases, fulfill them after a
#       verified webhook, cancel subscriptions without revoking paid periods,
#       and rebill due subscriptions behind the recurrent kill-switch.
# DEPENDENCIES: AsyncSession, YooKassaClient, AccessService, HoraryCredit
# GRACE_ANCHORS: [BILLING_PRODUCTS, BILLING_START, BILLING_FULFILL, BILLING_REBILL]
# ############################################################################

# START_MODULE_CONTRACT: M-BILLING-SERVICE
# purpose: All billing business logic: catalog reads, subscription/purchase
#   start with provider idempotency, webhook-driven fulfillment with strict
#   provider verification, cancel-without-revoke, recurrent rebill.
# owns:
#   - apps/api/app/services/billing_service.py
# inputs: user ids, product slugs, provider payment ids.
# outputs: catalog lists, start payloads (confirmation url), status dicts,
#   fulfillment results.
# dependencies: AsyncSession, get_yookassa_client, AccessService,
#   NatalContextService (profile hash for the natal entitlement).
# side_effects: creates/updates Payment/Subscription/Purchase/AccessLedger/
#   HoraryCredit rows; calls the YooKassa API via the client.
# emitted_logs: billing.subscription_started, billing.purchase_started,
#   billing.payment_fulfilled, billing.subscription_canceled,
#   billing.rebill_skipped, billing.rebill_started, system.error
# invariants:
#   - No parallel access/quota ledgers: subscription access goes ONLY through
#     AccessService.grant_subscription; horary quota ONLY via HoraryCredit
#     source="paid"; natal entitlement ONLY via Purchase(context_hash).
#   - Idempotent everywhere: duplicate start reuses the pending row;
#     duplicate webhook/fulfill grants nothing twice; unique
#     idempotence_key/provider_payment_id enforced by DB constraints.
#   - YOOKASSA_ENABLED=false => all start/status paths fail 503 upstream.
#   - YOOKASSA_RECURRENT_ENABLED=false => rebill performs zero charges.
#   - Cancel never revokes the already-paid period.
#   - No secrets, shop keys or raw provider payloads in logs.
# failure_policy: ValueError on domain violations (unknown product, wrong
#   state); YooKassaError on provider failure; webhook mismatches are
#   rejected silently (no state change) with a warning log.
# END_MODULE_CONTRACT: M-BILLING-SERVICE

# START_MODULE_MAP: M-BILLING-SERVICE
# public_entrypoints:
#   - BillingService.get_products
#   - BillingService.start_subscription
#   - BillingService.start_purchase
#   - BillingService.get_subscription_status
#   - BillingService.cancel_subscription
#   - BillingService.verify_and_process_webhook
#   - BillingService.rebill_due_subscriptions
#   - BillingService.has_natal_entitlement
# semantic_blocks:
#   - BILLING_PRODUCTS: catalog reads (products table seeded from CATALOG)
#   - BILLING_START: subscription/purchase creation with provider idempotency
#   - BILLING_FULFILL: verified webhook processing + product fulfillment
#   - BILLING_REBILL: recurrent charging behind the kill-switch
# owned_tests:
#   - apps/api/tests/test_billing_products.py
#   - apps/api/tests/test_billing_service.py
#   - apps/api/tests/test_billing_webhook.py
# END_MODULE_MAP: M-BILLING-SERVICE

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import log_event
from app.db.models import (
    AccessLedger,
    HoraryCredit,
    Payment,
    Product,
    Purchase,
    Subscription,
)
from app.services.access_service import AccessService
from app.services.yookassa_client import get_yookassa_client


def _kopecks_str(kopecks: int) -> str:
    return f"{kopecks // 100}.{kopecks % 100:02d}"


class BillingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # START_BLOCK: BILLING_PRODUCTS
    async def get_products(self) -> list[Product]:
        result = await self.db.execute(
            select(Product).where(Product.is_active.is_(True)).order_by(Product.price_kopecks)
        )
        return list(result.scalars().all())

    async def _get_product(self, slug: str) -> Product | None:
        result = await self.db.execute(
            select(Product).where(Product.slug == slug, Product.is_active.is_(True))
        )
        return result.scalar_one_or_none()
    # END_BLOCK: BILLING_PRODUCTS

    # START_BLOCK: BILLING_START
    async def start_subscription(self, user_id: uuid.UUID, product_slug: str) -> dict:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.start_subscription
        # purpose: Create the initial recurrent payment for a subscription.
        #   Idempotent: an already-active subscription returns
        #   {"status": "already_active"}; a pending one is reused, never
        #   duplicated.
        # inputs: user_id, product_slug (subscription_month|subscription_year).
        # returns: dict with subscription_id, product_slug,
        #   provider_payment_id, confirmation_url, status.
        # side_effects: inserts Subscription + Payment rows; POST to YooKassa
        #   with save_payment_method=true, merchant_customer_id, capture=true.
        # error_behavior: ValueError on unknown/wrong product; YooKassaError
        #   on provider failure.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.start_subscription
        product = await self._get_product(product_slug)
        if product is None or product.product_type != "subscription_recurrent":
            raise ValueError("PRODUCT_NOT_FOUND")

        active = await self._get_active_subscription(user_id)
        if active is not None:
            return {"status": "already_active", "subscription_id": active.id}

        pending = await self._get_pending_subscription(user_id, product_slug)
        if pending is not None:
            payment = await self._get_pending_payment_for(
                user_id, product_slug, f"init-{pending.id}-first"
            )
            if payment is not None:
                return {
                    "subscription_id": pending.id,
                    "product_slug": product_slug,
                    "provider_payment_id": payment.provider_payment_id,
                    "confirmation_url": payment.confirmation_url,
                    "status": "pending",
                }

        subscription = Subscription(
            user_id=user_id,
            product_slug=product_slug,
            status="pending",
            price_kopecks=product.price_kopecks,
            currency=product.currency,
        )
        self.db.add(subscription)
        await self.db.flush()

        client = get_yookassa_client()
        result = await client.create_initial_payment(
            user_id=user_id,
            owner_id=subscription.id,
            amount_kopecks=product.price_kopecks,
            currency=product.currency,
            description=product.name,
            return_url=settings.yookassa_return_url,
            product_slug=product_slug,
            idempotence_key=f"init-{subscription.id}-first",
        )

        payment = Payment(
            user_id=user_id,
            amount=product.price_kopecks,
            currency=product.currency,
            status="pending",
            provider="yookassa",
            description=product.name,
            product_slug=product_slug,
            provider_payment_id=result["provider_payment_id"],
            idempotence_key=f"init-{subscription.id}-first",
            confirmation_url=result.get("confirmation_url"),
        )
        self.db.add(payment)
        await self.db.commit()
        log_event("billing.subscription_started", msg="subscription started", payload={"payment_id": payment.id})

        return {
            "subscription_id": subscription.id,
            "product_slug": product_slug,
            "provider_payment_id": result["provider_payment_id"],
            "confirmation_url": result.get("confirmation_url"),
            "status": result["status"],
        }

    async def start_purchase(self, user_id: uuid.UUID, product_slug: str) -> dict:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.start_purchase
        # purpose: Create a one-time payment (horary pack or natal report
        #   entitlement). Idempotent per pending purchase; natal entitlement
        #   is bound to the CURRENT natal context hash and an existing
        #   succeeded entitlement returns {"status": "already_entitled"}.
        # inputs: user_id, product_slug (natal_full_report | horary_*).
        # returns: dict with purchase_id, product_slug, provider_payment_id,
        #   confirmation_url, status.
        # side_effects: inserts Purchase + Payment rows; POST to YooKassa
        #   with capture=true.
        # error_behavior: ValueError on unknown/inactive product (synastry is
        #   fail-closed) or missing natal context; YooKassaError upstream.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.start_purchase
        product = await self._get_product(product_slug)
        if product is None or product.product_type != "one_time":
            raise ValueError("PRODUCT_NOT_FOUND")

        context_hash: str | None = None
        if product_slug == "natal_full_report":
            context_hash = await self._current_natal_context_hash(user_id)
            if context_hash is None:
                raise ValueError("NATAL_CONTEXT_MISSING")
            entitled = await self.has_natal_entitlement(user_id, context_hash)
            if entitled:
                return {"status": "already_entitled"}

        pending = await self._get_pending_purchase(user_id, product_slug, context_hash)
        if pending is not None:
            payment = await self._get_pending_payment_for(
                user_id, product_slug, f"purchase-{pending.id}"
            )
            if payment is not None:
                return {
                    "purchase_id": pending.id,
                    "product_slug": product_slug,
                    "provider_payment_id": payment.provider_payment_id,
                    "confirmation_url": payment.confirmation_url,
                    "status": "pending",
                }

        purchase = Purchase(
            user_id=user_id,
            product_slug=product_slug,
            status="pending",
            horary_quota_added=product.horary_quota,
            context_hash=context_hash,
        )
        self.db.add(purchase)
        await self.db.flush()

        client = get_yookassa_client()
        result = await client.create_one_time_payment(
            user_id=user_id,
            owner_id=purchase.id,
            amount_kopecks=product.price_kopecks,
            currency=product.currency,
            description=product.name,
            return_url=settings.yookassa_return_url,
            product_slug=product_slug,
            idempotence_key=f"purchase-{purchase.id}",
        )

        payment = Payment(
            user_id=user_id,
            amount=product.price_kopecks,
            currency=product.currency,
            status="pending",
            provider="yookassa",
            description=product.name,
            product_slug=product_slug,
            provider_payment_id=result["provider_payment_id"],
            idempotence_key=f"purchase-{purchase.id}",
            confirmation_url=result.get("confirmation_url"),
        )
        self.db.add(payment)
        await self.db.flush()
        purchase.payment_id = payment.id
        await self.db.commit()
        log_event("billing.purchase_started", msg="purchase started", payload={"payment_id": payment.id})

        return {
            "purchase_id": purchase.id,
            "product_slug": product_slug,
            "provider_payment_id": result["provider_payment_id"],
            "confirmation_url": result.get("confirmation_url"),
            "status": result["status"],
        }
    # END_BLOCK: BILLING_START

    async def get_subscription_status(self, user_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
        )
        subscription = result.scalars().first()
        access = await self._access_summary(user_id)
        if subscription is None:
            return {
                "subscription_id": None,
                "product_slug": None,
                "status": "none",
                "price_kopecks": None,
                "currency": None,
                "current_period_end": None,
                "next_charge_at": None,
                **access,
            }
        return {
            "subscription_id": subscription.id,
            "product_slug": subscription.product_slug,
            "status": subscription.status,
            "price_kopecks": subscription.price_kopecks,
            "currency": subscription.currency,
            "current_period_end": (
                subscription.current_period_end.date().isoformat()
                if subscription.current_period_end else None
            ),
            "next_charge_at": (
                subscription.next_charge_at.isoformat()
                if subscription.next_charge_at else None
            ),
            **access,
        }

    async def cancel_subscription(self, user_id: uuid.UUID, reason: str | None) -> dict:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.cancel_subscription
        # purpose: Cancel an active subscription. The already-paid period is
        #   NEVER revoked — access stays until the ledger end date.
        # inputs: user_id, reason.
        # returns: {"subscription_id": id|None, "status": "canceled"|"no_active_subscription"}
        # side_effects: updates Subscription.status to canceled.
        # error_behavior: none raised for missing subscription.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.cancel_subscription
        subscription = await self._get_active_subscription(user_id)
        if subscription is None:
            return {"subscription_id": None, "status": "no_active_subscription"}
        subscription.status = "canceled"
        subscription.canceled_at = datetime.now(UTC)
        subscription.cancellation_reason = reason or "user_request"
        await self.db.commit()
        log_event("billing.subscription_canceled", msg="subscription canceled")
        return {"subscription_id": subscription.id, "status": "canceled"}

    # START_BLOCK: BILLING_FULFILL
    async def verify_and_process_webhook(self, provider_payment_id: str) -> dict:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.verify_and_process_webhook
        # purpose: Mandatory second webhook verification step: authenticated
        #   provider GET by id, strict comparison (status, paid, amount,
        #   currency, shop metadata vs the LOCAL payment), then idempotent
        #   fulfillment. The webhook payload itself is NEVER trusted.
        # inputs: provider_payment_id from the webhook envelope.
        # returns: {"processed": bool, "reason": str}
        # side_effects: fulfills Payment/Subscription/Purchase/AccessLedger/
        #   HoraryCredit exactly once.
        # error_behavior: mismatches are rejected without state change;
        #   provider errors propagate as YooKassaError.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.verify_and_process_webhook
        result = await self.db.execute(
            select(Payment).where(Payment.provider_payment_id == provider_payment_id)
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            log_event("billing.webhook_rejected", msg="unknown provider payment", level="warning")
            return {"processed": False, "reason": "unknown_payment"}

        if payment.status == "succeeded":
            return {"processed": False, "reason": "already_fulfilled"}

        client = get_yookassa_client()
        remote = await client.get_payment(provider_payment_id)

        if remote["status"] == "canceled":
            payment.status = "canceled"
            payment.canceled_at = datetime.now(UTC)
            await self.db.commit()
            return {"processed": False, "reason": "canceled"}

        if remote["status"] != "succeeded":
            return {"processed": False, "reason": f"provider_status_{remote['status']}"}

        if not self._payment_matches(payment, remote):
            log_event("billing.webhook_rejected", msg="webhook/provider mismatch", level="warning")
            return {"processed": False, "reason": "mismatch"}

        payment.status = "succeeded"
        payment.completed_at = datetime.now(UTC)
        payment.payment_method_saved = remote["payment_method_saved"]
        if remote["payment_method_saved"] and remote["payment_method_id"]:
            payment.payment_method_id = remote["payment_method_id"]

        product = await self._get_product(payment.product_slug) if payment.product_slug else None
        if product is None:
            await self.db.commit()
            return {"processed": False, "reason": "product_not_found"}

        if product.product_type == "subscription_recurrent":
            await self._fulfill_subscription(payment, product, remote)
        elif product.product_type == "one_time":
            await self._fulfill_one_time(payment, product, remote)

        await self.db.commit()
        log_event("billing.payment_fulfilled", msg="payment fulfilled", payload={"payment_id": payment.id})
        return {"processed": True, "reason": "fulfilled"}

    def _payment_matches(self, payment: Payment, remote: dict) -> bool:
        if not remote["paid"]:
            return False
        if remote["amount_value"] != _kopecks_str(payment.amount):
            return False
        if remote["currency"] != payment.currency:
            return False
        metadata = remote["metadata"]
        if str(metadata.get("user_id")) != str(payment.user_id):
            return False
        if metadata.get("product_slug") != payment.product_slug:
            return False
        if str(metadata.get("owner_id")) != self._expected_owner_id(payment):
            return False
        return True

    def _expected_owner_id(self, payment: Payment) -> str:
        key = payment.idempotence_key or ""
        if key.startswith("init-") and key.endswith("-first"):
            return key[len("init-"):-len("-first")]
        if key.startswith("purchase-"):
            return key[len("purchase-"):]
        if key.startswith("rebill-"):
            return key[len("rebill-"):].rsplit("-", 1)[0]
        return ""

    async def _fulfill_subscription(self, payment: Payment, product: Product, remote: dict) -> None:
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.user_id == payment.user_id,
                Subscription.status.in_(["pending", "past_due"]),
                Subscription.product_slug == product.slug,
            ).order_by(Subscription.created_at.desc())
        )
        subscription = result.scalars().first()
        days = product.period_days or 30
        now = datetime.now(UTC)
        if subscription is not None:
            subscription.status = "active"
            subscription.current_period_start = now
            subscription.current_period_end = now + timedelta(days=days)
            subscription.next_charge_at = now + timedelta(days=days)
            if remote["payment_method_saved"] and remote["payment_method_id"]:
                subscription.payment_method_id = remote["payment_method_id"]
        access = AccessService(self.db)
        await access.grant_subscription(user_id=payment.user_id, start_date=date.today(), days=days)

    async def _fulfill_one_time(self, payment: Payment, product: Product, remote: dict) -> None:
        result = await self.db.execute(
            select(Purchase).where(Purchase.payment_id == payment.id)
        )
        purchase = result.scalar_one_or_none()
        if purchase is None:
            return

        if product.horary_quota:
            credit = HoraryCredit(
                user_id=payment.user_id,
                source="paid",
                amount=product.horary_quota,
                used_amount=0,
            )
            self.db.add(credit)
            purchase.horary_quota_added = product.horary_quota
            purchase.status = "consumed"
        elif product.slug == "natal_full_report":
            purchase.status = "delivered"
        else:
            purchase.status = "succeeded"
    # END_BLOCK: BILLING_FULFILL

    # START_BLOCK: BILLING_REBILL
    async def rebill_due_subscriptions(self) -> int:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.rebill_due_subscriptions
        # purpose: Charge all due subscriptions with their saved
        #   payment_method_id. Hard kill-switch: when
        #   YOOKASSA_RECURRENT_ENABLED=false performs ZERO charges.
        # inputs: none (scans due subscriptions).
        # returns: number of rebill attempts made.
        # side_effects: POST /payments per due subscription; marks failures
        #   past_due with next_charge_at +1 day.
        # error_behavior: provider failures demote to past_due, never raise.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.rebill_due_subscriptions
        if not settings.yookassa_recurrent_enabled:
            log_event("billing.rebill_skipped", msg="recurrent disabled by kill-switch")
            return 0

        now = datetime.now(UTC)
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.status.in_(["active", "past_due"]),
                Subscription.next_charge_at.is_not(None),
                Subscription.next_charge_at <= now,
                Subscription.payment_method_id.is_not(None),
            )
        )
        due = result.scalars().all()
        client = get_yookassa_client()
        attempts = 0
        for sub in due:
            period_label = (sub.next_charge_at or now).date().isoformat()
            idempotence_key = f"rebill-{sub.id}-{period_label}"[:64]
            # next_charge_at filter guarantees a saved method id.
            payment_method_id = sub.payment_method_id
            if not payment_method_id:
                continue
            try:
                result_payment = await client.create_recurrent_payment(
                    user_id=sub.user_id,
                    owner_id=sub.id,
                    payment_method_id=payment_method_id,
                    amount_kopecks=sub.price_kopecks,
                    currency=sub.currency,
                    description="Подписка SolarSage — автопродление",
                    product_slug=sub.product_slug,
                    period_label=period_label,
                    idempotence_key=idempotence_key,
                )
                payment = Payment(
                    user_id=sub.user_id,
                    amount=sub.price_kopecks,
                    currency=sub.currency,
                    status="pending",
                    provider="yookassa",
                    description="Автопродление подписки",
                    product_slug=sub.product_slug,
                    provider_payment_id=result_payment["provider_payment_id"],
                    idempotence_key=idempotence_key,
                )
                self.db.add(payment)
                sub.next_charge_at = now + timedelta(days=1)
                attempts += 1
                log_event("billing.rebill_started", msg="rebill started")
            except Exception:
                sub.status = "past_due"
                sub.next_charge_at = now + timedelta(days=1)
                log_event("system.error", msg="rebill failed", level="error")
        await self.db.commit()
        return attempts
    # END_BLOCK: BILLING_REBILL

    # ---- Natal entitlement ----

    async def has_natal_entitlement(self, user_id: uuid.UUID, context_hash: str) -> bool:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.has_natal_entitlement
        # purpose: Check whether the user owns a fulfilled natal report
        #   entitlement for the CURRENT natal context hash. Repeat generation
        #   of an already-purchased report requires no new payment.
        # inputs: user_id, context_hash (current natal profile hash).
        # returns: True when a delivered natal_full_report purchase exists.
        # side_effects: none.
        # error_behavior: none.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.has_natal_entitlement
        result = await self.db.execute(
            select(Purchase).where(
                Purchase.user_id == user_id,
                Purchase.product_slug == "natal_full_report",
                Purchase.context_hash == context_hash,
                Purchase.status.in_(["succeeded", "delivered"]),
            )
        )
        return result.scalar_one_or_none() is not None

    # ---- Helpers ----

    async def _get_active_subscription(self, user_id: uuid.UUID) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.status == "active",
            )
        )
        return result.scalar_one_or_none()

    async def _get_pending_subscription(self, user_id: uuid.UUID, product_slug: str) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.product_slug == product_slug,
                Subscription.status == "pending",
            ).order_by(Subscription.created_at.desc())
        )
        return result.scalars().first()

    async def _get_pending_purchase(
        self, user_id: uuid.UUID, product_slug: str, context_hash: str | None
    ) -> Purchase | None:
        result = await self.db.execute(
            select(Purchase).where(
                Purchase.user_id == user_id,
                Purchase.product_slug == product_slug,
                Purchase.context_hash.is_(context_hash) if context_hash is None else Purchase.context_hash == context_hash,
                Purchase.status == "pending",
            ).order_by(Purchase.created_at.desc())
        )
        return result.scalars().first()

    async def _get_pending_payment_for(
        self, user_id: uuid.UUID, product_slug: str, idempotence_key: str
    ) -> Payment | None:
        result = await self.db.execute(
            select(Payment).where(
                Payment.user_id == user_id,
                Payment.product_slug == product_slug,
                Payment.idempotence_key == idempotence_key,
                Payment.status == "pending",
            )
        )
        return result.scalar_one_or_none()

    async def _current_natal_context_hash(self, user_id: uuid.UUID) -> str | None:
        from app.services.natal_context_service import NatalContextService

        service = NatalContextService(self.db)
        context = await service.get_or_build_natal_context(user_id)
        return getattr(context, "profile_hash", None)

    async def _access_summary(self, user_id: uuid.UUID) -> dict:
        today = date.today()
        result = await self.db.execute(
            select(AccessLedger).where(
                AccessLedger.user_id == user_id,
                AccessLedger.start_date <= today,
                AccessLedger.end_date >= today,
            ).order_by(AccessLedger.end_date.desc())
        )
        entry = result.scalars().first()
        return {
            "has_access": entry is not None,
            "access_until": entry.end_date.isoformat() if entry else None,
        }
