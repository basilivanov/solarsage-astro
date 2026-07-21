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
#   billing.rebill_skipped, billing.rebill_started, billing.webhook_rejected,
#   billing.fulfillment_blocked, system.error
# invariants:
#   - No parallel access/quota ledgers: subscription access goes ONLY through
#     AccessService.grant_subscription; horary quota ONLY via HoraryCredit
#     source="paid"; natal entitlement ONLY via Purchase(context_hash).
#   - Idempotent everywhere: duplicate start reuses the pending row;
#     duplicate webhook/fulfill grants nothing twice; unique
#     idempotence_key/provider_payment_id enforced by DB constraints.
#   - At most ONE live (pending/active/past_due) subscription per user,
#     enforced by the uq_subscriptions_one_live_per_user partial unique index
#     and by the service guard (reuse pending-same-plan, else domain 409).
#   - A payment is marked succeeded ONLY when its fulfillment target
#     (product row without the is_active sales filter + owner row) exists;
#     otherwise it stays pending and observable (billing.fulfillment_blocked)
#     so a later webhook/reconciliation can still grant. An in-flight renewal
#     that succeeds AFTER a user cancel fulfills exactly the paid period once
#     (status stays canceled, next_charge_at NULL); an initial payment of a
#     canceled start is never resurrected.
#   - Same-key provider retries happen only inside the 24h YooKassa
#     Idempotence-Key dedupe window anchored by payments.first_attempt_at;
#     past the window an ambiguous rebill is NEVER auto-charged again.
#   - A rebill cycle always resolves its LATEST attempt first: a live
#     (non-canceled) latest attempt is reused/skipped, never re-charged; a
#     fresh -a<N> key is reserved ONLY when the latest attempt is known
#     canceled (dead keys are never reused for a charge).
#   - YOOKASSA_ENABLED=false => all start/status paths fail 503 upstream.
#   - YOOKASSA_RECURRENT_ENABLED=false => rebill performs zero charges.
#   - Cancel never revokes the already-paid period; cancel applies only to
#     active/past_due. A pending (unpaid) start is never silently abandoned
#     (no provider cancel call exists, so its confirmation URL would stay
#     payable) — plan switch is the explicit 409, not local cancel.
#   - A reserved payment without idempotence_key is corrupted state: fail
#     closed (RuntimeError), never charge on a silently substituted key.
#   - No secrets, shop keys or raw provider payloads in logs.
# failure_policy: ValueError on domain violations (unknown product, wrong
#   state, LIVE_SUBSCRIPTION_EXISTS); RuntimeError on reservation invariant
#   violations; YooKassaError on provider failure; webhook mismatches are
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

from sqlalchemy import or_, select
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
from app.services.yookassa_client import YooKassaError, get_yookassa_client


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
        products = list(result.scalars().all())
        # Never advertise a 501 feature: the natal report is hidden while its
        # generation flag is off.
        if not settings.natal_report_enabled:
            products = [p for p in products if p.slug != "natal_full_report"]
        return products

    async def _get_product(self, slug: str) -> Product | None:
        result = await self.db.execute(
            select(Product).where(Product.slug == slug, Product.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def _get_product_any(self, slug: str) -> Product | None:
        # Fulfillment path ONLY: no is_active sales filter. Deactivating a
        # product stops NEW sales but must never strand an already-accepted
        # payment (amount/currency are verified against the payment snapshot).
        result = await self.db.execute(select(Product).where(Product.slug == slug))
        return result.scalar_one_or_none()
    # END_BLOCK: BILLING_PRODUCTS

    # START_BLOCK: BILLING_START
    async def start_subscription(self, user_id: uuid.UUID, product_slug: str) -> dict:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.start_subscription
        # purpose: Create the initial recurrent payment for a subscription.
        #   Durable-first: the owner Subscription AND the pending Payment with
        #   a stable idempotence_key are COMMITTED before the external
        #   provider POST. A timeout/unknown outcome leaves the pending rows;
        #   any retry reuses the SAME key (YooKassa dedupes) and reconciles
        #   instead of charging twice.
        # inputs: user_id, product_slug (subscription_month|subscription_year).
        # returns: dict with subscription_id, product_slug,
        #   provider_payment_id, confirmation_url, status.
        # side_effects: commits Subscription + Payment reservations; POST to
        #   YooKassa with save_payment_method=true, merchant_customer_id,
        #   capture=true.
        # error_behavior: ValueError on unknown/wrong product or when another
        #   live subscription exists (LIVE_SUBSCRIPTION_EXISTS -> 409);
        #   RuntimeError on a broken reservation (missing idempotence key);
        #   YooKassaError on provider failure (reservation stays pending).
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.start_subscription
        product = await self._get_product(product_slug)
        if product is None or product.product_type != "subscription_recurrent":
            raise ValueError("PRODUCT_NOT_FOUND")

        live = await self._get_live_subscription(user_id)
        if live is not None:
            if live.status == "active":
                return {"status": "already_active", "subscription_id": live.id}
            if live.status == "pending" and live.product_slug == product_slug:
                subscription = live
            else:
                # past_due OR a pending start for a DIFFERENT plan: exactly
                # one live subscription per user — never a second charge owner.
                raise ValueError("LIVE_SUBSCRIPTION_EXISTS")
        else:
            subscription = await self._reserve_subscription(user_id, product)
        attempt_key = await self._next_attempt_key(subscription.id, product_slug)
        payment = await self._reserve_payment(
            user_id=user_id,
            product=product,
            idempotence_key=attempt_key,
            subscription_id=subscription.id,
        )
        if payment.status == "canceled":
            # Previous attempt was canceled at the provider: move to a fresh
            # attempt key (never reuses a dead idempotence key).
            payment = await self._reserve_payment(
                user_id=user_id,
                product=product,
                idempotence_key=await self._next_attempt_key(subscription.id, product_slug, force_new=True),
                subscription_id=subscription.id,
            )

        if payment.provider_payment_id is None:
            # First external attempt (or reconciliation after a timeout): the
            # SAME idempotence key makes YooKassa dedupe the charge, so a
            # retry merges into the existing payment instead of doubling it.
            client = get_yookassa_client()
            result = await client.create_initial_payment(
                user_id=user_id,
                owner_id=subscription.id,
                amount_kopecks=product.price_kopecks,
                currency=product.currency,
                description=product.name,
                return_url=settings.yookassa_return_url,
                product_slug=product_slug,
                idempotence_key=self._require_idempotence_key(payment),
            )
            payment.provider_payment_id = result["provider_payment_id"]
            payment.confirmation_url = result.get("confirmation_url")
            await self.db.commit()

        log_event("billing.subscription_started", msg="subscription started", payload={"payment_id": payment.id})

        return {
            "subscription_id": subscription.id,
            "product_slug": product_slug,
            "provider_payment_id": payment.provider_payment_id,
            "confirmation_url": payment.confirmation_url,
            "status": "pending",
        }

    async def start_purchase(self, user_id: uuid.UUID, product_slug: str) -> dict:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.start_purchase
        # purpose: Create a one-time payment (horary pack or natal report
        #   entitlement). Idempotent per pending purchase; natal entitlement
        #   is bound to the CURRENT natal context hash and an existing
        #   succeeded entitlement returns {"status": "already_entitled"}.
        #   Durable-first: the Purchase AND its payment_id link are COMMITTED
        #   BEFORE the external POST, so a webhook arriving while the provider
        #   processes the charge already resolves the owner (no lost grant).
        # inputs: user_id, product_slug (natal_full_report | horary_*).
        # returns: dict with purchase_id, product_slug, provider_payment_id,
        #   confirmation_url, status.
        # side_effects: commits Purchase + Payment reservation and the
        #   purchase.payment_id link; POST to YooKassa with capture=true.
        # error_behavior: ValueError on unknown/inactive product (synastry is
        #   fail-closed) or missing natal context; RuntimeError on a broken
        #   reservation (missing idempotence key); YooKassaError upstream.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.start_purchase
        product = await self._get_product(product_slug)
        if product is None or product.product_type != "one_time":
            raise ValueError("PRODUCT_NOT_FOUND")
        # Fail closed: never sell a 501 feature.
        if product_slug == "natal_full_report" and not settings.natal_report_enabled:
            raise ValueError("PRODUCT_NOT_FOUND")

        context_hash = ""
        if product_slug == "natal_full_report":
            natal_hash = await self._current_natal_context_hash(user_id)
            if natal_hash is None:
                raise ValueError("NATAL_CONTEXT_MISSING")
            context_hash = natal_hash
            entitled = await self.has_natal_entitlement(user_id, context_hash)
            if entitled:
                return {"status": "already_entitled"}

        purchase = await self._reserve_purchase(user_id, product, context_hash)
        attempt_key = await self._next_attempt_key(purchase.id, product_slug, prefix="purchase")
        payment = await self._reserve_payment(
            user_id=user_id,
            product=product,
            idempotence_key=attempt_key,
        )
        if payment.status == "canceled":
            payment = await self._reserve_payment(
                user_id=user_id,
                product=product,
                idempotence_key=await self._next_attempt_key(purchase.id, product_slug, prefix="purchase", force_new=True),
            )

        if purchase.payment_id != payment.id:
            # The owner link MUST be durable BEFORE the external POST: a
            # webhook can arrive while the provider is still processing the
            # charge, and _fulfill_one_time resolves the purchase strictly
            # through this FK. Linking only after the POST loses that webhook
            # behind the already_fulfilled early-return.
            purchase.payment_id = payment.id
            await self.db.commit()

        if payment.provider_payment_id is None:
            client = get_yookassa_client()
            result = await client.create_one_time_payment(
                user_id=user_id,
                owner_id=purchase.id,
                amount_kopecks=product.price_kopecks,
                currency=product.currency,
                description=product.name,
                return_url=settings.yookassa_return_url,
                product_slug=product_slug,
                idempotence_key=self._require_idempotence_key(payment),
            )
            payment.provider_payment_id = result["provider_payment_id"]
            payment.confirmation_url = result.get("confirmation_url")
            await self.db.commit()

        log_event("billing.purchase_started", msg="purchase started", payload={"payment_id": payment.id})

        return {
            "purchase_id": purchase.id,
            "product_slug": product_slug,
            "provider_payment_id": payment.provider_payment_id,
            "confirmation_url": payment.confirmation_url,
            "status": "pending",
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
        # purpose: Cancel the user's PAYING subscription (active/past_due).
        #   The already-paid period is NEVER revoked — access stays until the
        #   ledger end date. A PENDING (unpaid) start is NOT locally
        #   cancelable: without a provider cancel call its confirmation URL
        #   stays payable and the user could pay into an abandoned owner, so
        #   cancel is rejected explicitly and a plan switch stays the domain
        #   409 on start (LIVE_SUBSCRIPTION_EXISTS), never silent abandonment.
        # inputs: user_id, reason.
        # returns: {"subscription_id": id|None, "status": "canceled"|"no_active_subscription"}
        # side_effects: updates Subscription.status to canceled and clears
        #   next_charge_at (no further rebill attempts).
        # error_behavior: ValueError PENDING_SUBSCRIPTION_NOT_CANCELABLE when
        #   only a pending start exists (-> API 409).
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.cancel_subscription
        subscription = await self._get_live_subscription(user_id)
        if subscription is None:
            return {"subscription_id": None, "status": "no_active_subscription"}
        if subscription.status == "pending":
            raise ValueError("PENDING_SUBSCRIPTION_NOT_CANCELABLE")
        subscription.status = "canceled"
        subscription.canceled_at = datetime.now(UTC)
        subscription.cancellation_reason = reason or "user_request"
        subscription.next_charge_at = None
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
        #   provider errors propagate as YooKassaError; a missing/deactivated
        #   fulfillment target (product row, owner row, inactive subscription)
        #   leaves the payment PENDING with billing.fulfillment_blocked so the
        #   grant stays recoverable, and a canceled renewal demotes an active
        #   subscription to past_due for a fresh-key retry.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.verify_and_process_webhook
        result = await self.db.execute(
            select(Payment)
            .where(Payment.provider_payment_id == provider_payment_id)
            .with_for_update()
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
            # A canceled RENEWAL demotes an active subscription to past_due so
            # the rebill loop retries the cycle on a FRESH attempt key. An
            # INITIAL payment (subscription still pending) leaves the
            # subscription pending — the start flow rekeys it on the user's
            # next attempt instead of deadlocking the one-live slot.
            if payment.subscription_id is not None:
                linked = await self.db.execute(
                    select(Subscription).where(Subscription.id == payment.subscription_id)
                )
                sub = linked.scalar_one_or_none()
                if sub is not None and sub.status == "active":
                    sub.status = "past_due"
                    sub.next_charge_at = datetime.now(UTC) + timedelta(days=1)
            await self.db.commit()
            return {"processed": False, "reason": "canceled"}

        if remote["status"] != "succeeded":
            return {"processed": False, "reason": f"provider_status_{remote['status']}"}

        if not self._payment_matches(payment, remote):
            log_event("billing.webhook_rejected", msg="webhook/provider mismatch", level="warning")
            return {"processed": False, "reason": "mismatch"}

        # Fulfillment target gate BEFORE marking succeeded: the payment is
        # marked succeeded ONLY when the grant can actually happen. A missing
        # product row (lookup has NO is_active sales filter here) or a missing
        # owner leaves the payment pending and observable, so a later webhook
        # or manual reconciliation can still fulfill — never lost behind the
        # already_fulfilled early-return.
        product = await self._get_product_any(payment.product_slug) if payment.product_slug else None
        if product is None:
            log_event(
                "billing.fulfillment_blocked",
                msg="payment product row missing",
                level="error",
                payload={"payment_id": payment.id},
            )
            return {"processed": False, "reason": "product_missing"}
        block_reason = await self._fulfillment_block_reason(payment, product)
        if block_reason is not None:
            log_event(
                "billing.fulfillment_blocked",
                msg=block_reason,
                level="error",
                payload={"payment_id": payment.id},
            )
            return {"processed": False, "reason": block_reason}

        payment.status = "succeeded"
        payment.completed_at = datetime.now(UTC)
        payment.payment_method_saved = remote["payment_method_saved"]
        if remote["payment_method_saved"] and remote["payment_method_id"]:
            payment.payment_method_id = remote["payment_method_id"]

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
        # Strict owner check: subscription payments are linked by FK; purchase
        # payments by the purchase key prefix.
        owner = str(metadata.get("owner_id"))
        if payment.subscription_id is not None:
            return owner == str(payment.subscription_id)
        return owner == self._expected_purchase_owner_id(payment)

    @staticmethod
    def _expected_purchase_owner_id(payment: Payment) -> str:
        key = payment.idempotence_key or ""
        if key.startswith("purchase-"):
            return key[len("purchase-"):]
        return ""

    @staticmethod
    def _is_paid_canceled_renewal(payment: Payment, subscription: Subscription) -> bool:
        # An IN-FLIGHT renewal (rebill- key) of a subscription that was active
        # (has a paid period) and was then canceled: the money was taken for
        # the next period before the cancel landed, so the paid period must
        # be honored — WITHOUT resurrecting the subscription.
        return (
            subscription.status == "canceled"
            and (payment.idempotence_key or "").startswith("rebill-")
            and subscription.current_period_end is not None
        )

    async def _fulfillment_block_reason(self, payment: Payment, product: Product) -> str | None:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._fulfillment_block_reason
        # purpose: Decide whether a verified succeeded payment can be granted
        #   RIGHT NOW. Any gap returns a stable reason string and the caller
        #   keeps the payment pending (recoverable + observable).
        # inputs: payment (locked row), product (unfiltered catalog row).
        # returns: None when fulfillment may proceed, else one of
        #   owner_missing | subscription_inactive | unknown_product_type.
        #   A paid in-flight renewal of a canceled subscription is NOT a gap:
        #   it fulfills the paid period while the subscription stays canceled.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._fulfillment_block_reason
        if product.product_type == "subscription_recurrent":
            if payment.subscription_id is None:
                return "owner_missing"
            result = await self.db.execute(
                select(Subscription).where(Subscription.id == payment.subscription_id)
            )
            subscription = result.scalar_one_or_none()
            if subscription is None:
                return "owner_missing"
            if subscription.status in ("pending", "past_due", "active"):
                return None
            if self._is_paid_canceled_renewal(payment, subscription):
                return None
            # canceled initial payment / expired: never resurrect via webhook.
            return "subscription_inactive"
        if product.product_type == "one_time":
            result = await self.db.execute(
                select(Purchase).where(Purchase.payment_id == payment.id)
            )
            purchase = result.scalar_one_or_none()
            return None if purchase is not None else "owner_missing"
        return "unknown_product_type"

    async def _fulfill_subscription(self, payment: Payment, product: Product, remote: dict) -> None:
        # Strict owner: the payment is FK-linked to exactly one subscription.
        if payment.subscription_id is None:
            log_event("billing.webhook_rejected", msg="subscription payment without owner link", level="warning")
            return
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.id == payment.subscription_id)
            .with_for_update()
        )
        subscription = result.scalar_one_or_none()
        if subscription is None:
            return

        days = product.period_days or 30
        now = datetime.now(UTC)
        if subscription.status in ("pending", "past_due"):
            # First activation: a new period starts now.
            subscription.status = "active"
            subscription.current_period_start = now
            subscription.current_period_end = now + timedelta(days=days)
            subscription.next_charge_at = now + timedelta(days=days)
        elif subscription.status == "active":
            # Renewal: extend strictly FROM the current period end, so a
            # renewal payment can never shorten or duplicate a period.
            base_end = subscription.current_period_end or now
            subscription.current_period_end = base_end + timedelta(days=days)
            subscription.next_charge_at = base_end + timedelta(days=days)
        elif self._is_paid_canceled_renewal(payment, subscription):
            # In-flight renewal that succeeded AFTER the user's cancel: honor
            # exactly the paid period (extend access from the paid period
            # end) but NEVER resurrect — status stays canceled and
            # next_charge_at stays NULL, so no future charge can happen.
            base_end = subscription.current_period_end or now
            subscription.current_period_end = base_end + timedelta(days=days)
            subscription.next_charge_at = None
        else:
            # canceled initial payment / expired: never resurrect via webhook.
            log_event("billing.webhook_rejected", msg="webhook for inactive subscription", level="warning")
            return

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
    # YooKassa guarantees Idempotence-Key dedupe only for 24h after the first
    # attempt. Same-key retries are allowed strictly inside this window.
    _REBILL_KEY_DEDUPE_WINDOW = timedelta(hours=24)

    async def rebill_due_subscriptions(self) -> int:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.rebill_due_subscriptions
        # purpose: Charge all due subscriptions with their saved
        #   payment_method_id. Hard kill-switch: when
        #   YOOKASSA_RECURRENT_ENABLED=false performs ZERO charges.
        # inputs: none (scans due subscriptions).
        # returns: number of rebill attempts made.
        # side_effects: POST /payments per due subscription; marks failures
        #   past_due with next_charge_at +1 day; anchors first_attempt_at.
        # error_behavior: provider failures demote to past_due, never raise.
        #   The cycle resolves its LATEST attempt: a live latest attempt is
        #   reused/skipped (no second charge before the webhook), a
        #   known-canceled latest attempt is retried on a FRESH -a<N> key.
        #   An ambiguous payment whose 24h dedupe window expired is NEVER
        #   auto-charged again — it stays pending for manual reconciliation
        #   (system.error log), subscription past_due.
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
            payment_method_id = sub.payment_method_id
            if not payment_method_id:
                continue
            # Stable per-cycle label: retries of the SAME rebill keep the same
            # idempotence key even when next_charge_at is pushed forward.
            cycle_end = sub.current_period_end or sub.next_charge_at or now
            period_label = cycle_end.date().isoformat()
            idempotence_key = f"rebill-{sub.id}-{period_label}"[:64]
            # Resolve the LATEST payment of this cycle first: a live
            # (non-canceled) attempt is always reused/skipped, so a second
            # cron run before the webhook can never start -a2 and double
            # charge. A fresh key is reserved ONLY when the latest attempt
            # of the cycle is KNOWN canceled.
            payment = await self._latest_cycle_payment(sub, period_label)
            if payment is None:
                # Durable reservation BEFORE the external POST; a prior
                # attempt that died after charging reconciles through this
                # same key.
                payment = await self._reserve_rebill_payment(sub, idempotence_key)
            elif payment.status == "canceled":
                # KNOWN dead latest attempt: the cycle continues on a FRESH
                # key (dead keys are never reused for a charge).
                idempotence_key = await self._next_rebill_attempt_key(sub, period_label)
                payment = await self._reserve_rebill_payment(sub, idempotence_key)

            if payment.provider_payment_id is not None:
                # Created at the provider; the webhook drives fulfillment.
                continue

            first_attempt_at = payment.first_attempt_at
            # SQLite returns tz-naive datetimes; Postgres returns aware ones.
            if first_attempt_at is not None and first_attempt_at.tzinfo is None:
                first_attempt_at = first_attempt_at.replace(tzinfo=UTC)
            if (
                first_attempt_at is not None
                and now - first_attempt_at >= self._REBILL_KEY_DEDUPE_WINDOW
            ):
                # Past the dedupe window the first attempt's outcome is
                # unknowable client-side and the provider no longer dedupes
                # the key: NEVER auto-charge again — manual reconciliation.
                sub.status = "past_due"
                sub.next_charge_at = now + timedelta(days=1)
                await self.db.commit()
                log_event(
                    "system.error",
                    msg="rebill needs manual reconciliation: idempotence window expired",
                    level="error",
                    payload={"subscription_id": str(sub.id)},
                )
                continue

            if payment.first_attempt_at is None:
                # Durable attempt anchor BEFORE the POST: the 24h window is
                # computed from the committed row, not from process memory.
                payment.first_attempt_at = now
                await self.db.commit()
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
            except YooKassaError:
                # Unknown outcome: demote and retry next cycle with the SAME
                # key inside the dedupe window, never a fresh charge.
                sub.status = "past_due"
                sub.next_charge_at = now + timedelta(days=1)
                await self.db.commit()
                log_event("system.error", msg="rebill provider failure", level="error")
                continue
            payment.provider_payment_id = result_payment["provider_payment_id"]
            if result_payment.get("status") == "canceled":
                # Canceled AT CREATE: mark immediately so the next run moves
                # to a fresh attempt key instead of blocking the cycle.
                payment.status = "canceled"
                payment.canceled_at = datetime.now(UTC)
                sub.status = "past_due"
                sub.next_charge_at = now + timedelta(days=1)
                await self.db.commit()
                log_event("billing.webhook_rejected", msg="rebill canceled at create", level="warning")
                continue
            await self.db.commit()
            attempts += 1
            log_event("billing.rebill_started", msg="rebill started")
        await self.db.commit()
        return attempts

    async def _latest_cycle_payment(self, sub: Subscription, period_label: str) -> Payment | None:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._latest_cycle_payment
        # purpose: Return the LATEST reserved payment of one rebill cycle —
        #   the base key or any -a<N> attempt (payments.id is monotonic with
        #   reservation order). This is the anti-double-charge selector: the
        #   caller reuses/skips a live latest attempt and reserves a fresh
        #   key ONLY when this latest one is known canceled.
        # inputs: sub (due subscription), period_label (cycle label).
        # returns: newest cycle Payment or None when the cycle never started.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._latest_cycle_payment
        base = f"rebill-{sub.id}-{period_label}"
        result = await self.db.execute(
            select(Payment)
            .where(
                Payment.subscription_id == sub.id,
                or_(
                    Payment.idempotence_key == base,
                    Payment.idempotence_key.like(f"{base}-a%"),
                ),
            )
            .order_by(Payment.id.desc())
        )
        return result.scalars().first()

    async def _reserve_rebill_payment(self, sub: Subscription, idempotence_key: str) -> Payment:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._reserve_rebill_payment
        # purpose: Durable get-or-create of the renewal Payment with a stable
        #   idempotence key (amount/description from the subscription),
        #   committed BEFORE any external POST — same contract as
        #   _reserve_payment, specialised for renewal charges.
        # inputs: sub (due subscription), idempotence_key (cycle/attempt key).
        # returns: the pending Payment row (committed).
        # side_effects: commits the reservation; a concurrent collision on the
        #   unique idempotence_key is converted to the reuse path.
        # error_behavior: re-raises if the row cannot be reserved or reused.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._reserve_rebill_payment
        from sqlalchemy.exc import IntegrityError as SQLIntegrityError

        existing = await self._get_payment_by_idempotence_key(idempotence_key)
        if existing is not None:
            return existing
        payment = Payment(
            user_id=sub.user_id,
            amount=sub.price_kopecks,
            currency=sub.currency,
            status="pending",
            provider="yookassa",
            description="Автопродление подписки",
            product_slug=sub.product_slug,
            idempotence_key=idempotence_key,
            subscription_id=sub.id,
        )
        self.db.add(payment)
        try:
            await self.db.commit()
        except SQLIntegrityError:
            await self.db.rollback()
            existing = await self._get_payment_by_idempotence_key(idempotence_key)
            if existing is None:
                raise
            return existing
        return payment

    async def _next_rebill_attempt_key(self, sub: Subscription, period_label: str) -> str:
        # Fresh key for the SAME cycle after a KNOWN canceled attempt:
        # rebill-<sub>-<period_label>-a<N> (N counts prior attempts), so a
        # dead idempotence key is never reused for a fresh charge. The
        # compact -a<N> suffix keeps multi-digit N inside the 64-char column
        # WITHOUT truncation — the old [:64] silently collapsed -attempt-10
        # into -attempt-1. Overflow fails closed instead of colliding.
        from sqlalchemy import func

        base = f"rebill-{sub.id}-{period_label}"
        result = await self.db.execute(
            select(func.count(Payment.id)).where(Payment.idempotence_key.like(f"{base}-a%"))
        )
        attempt = (result.scalar_one() or 0) + 1
        key = f"{base}-a{attempt}"
        if len(key) > 64:
            log_event(
                "system.error",
                msg="rebill attempt key overflow",
                level="error",
                payload={"subscription_id": str(sub.id)},
            )
            raise RuntimeError("REBILL_KEY_OVERFLOW")
        return key
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

    async def _get_live_subscription(self, user_id: uuid.UUID) -> Subscription | None:
        # LIVE = pending | active | past_due. The partial unique index
        # uq_subscriptions_one_live_per_user guarantees at most one such row.
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.status.in_(["pending", "active", "past_due"]),
            ).order_by(Subscription.created_at.desc())
        )
        return result.scalars().first()

    @staticmethod
    def _require_idempotence_key(payment: Payment) -> str:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._require_idempotence_key
        # purpose: Fail-closed guard at the charge boundary. A reserved
        #   payment row without its idempotence key is corrupted state; the
        #   old `payment.idempotence_key or attempt_key` silently masked it
        #   and could charge on a key the row never persisted.
        # inputs: payment (reserved row about to be charged).
        # returns: the persisted idempotence key.
        # side_effects: system.error log on violation.
        # error_behavior: raises RuntimeError PAYMENT_INVARIANT_VIOLATION —
        #   no provider call happens on a broken reservation.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._require_idempotence_key
        if payment.idempotence_key is None:
            log_event(
                "system.error",
                msg="payment reservation missing idempotence_key",
                level="error",
                payload={"payment_id": payment.id},
            )
            raise RuntimeError("PAYMENT_INVARIANT_VIOLATION")
        return payment.idempotence_key

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
        self, user_id: uuid.UUID, product_slug: str, context_hash: str
    ) -> Purchase | None:
        result = await self.db.execute(
            select(Purchase).where(
                Purchase.user_id == user_id,
                Purchase.product_slug == product_slug,
                Purchase.context_hash == context_hash,
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

    async def _get_payment_by_idempotence_key(self, idempotence_key: str) -> Payment | None:
        result = await self.db.execute(
            select(Payment).where(Payment.idempotence_key == idempotence_key)
        )
        return result.scalar_one_or_none()

    # ---- Durable reservations (commit BEFORE any external provider POST) ----

    async def _reserve_subscription(self, user_id: uuid.UUID, product: Product) -> Subscription:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._reserve_subscription
        # purpose: Get-or-create the pending Subscription and COMMIT it, so
        #   the owner exists durably before any external charge attempt. A
        #   concurrent start collides on the partial unique index and is
        #   converted to the same reuse path.
        # inputs: user_id, product (subscription product).
        # returns: the pending Subscription row (committed).
        # side_effects: commits the reservation.
        # error_behavior: re-raises if the row cannot be reserved or reused.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._reserve_subscription
        from sqlalchemy.exc import IntegrityError as SQLIntegrityError

        pending = await self._get_pending_subscription(user_id, product.slug)
        if pending is not None:
            return pending
        subscription = Subscription(
            user_id=user_id,
            product_slug=product.slug,
            status="pending",
            price_kopecks=product.price_kopecks,
            currency=product.currency,
        )
        self.db.add(subscription)
        try:
            await self.db.commit()
        except SQLIntegrityError:
            # Collided with the one-live-per-user index: reuse the pending row
            # for the SAME plan; any other live row is a domain conflict.
            await self.db.rollback()
            live = await self._get_live_subscription(user_id)
            if live is not None and live.status == "pending" and live.product_slug == product.slug:
                return live
            if live is not None:
                raise ValueError("LIVE_SUBSCRIPTION_EXISTS")
            raise
        return subscription

    async def _reserve_purchase(
        self, user_id: uuid.UUID, product: Product, context_hash: str
    ) -> Purchase:
        # Same durable get-or-create contract for one-time purchases.
        from sqlalchemy.exc import IntegrityError as SQLIntegrityError

        pending = await self._get_pending_purchase(user_id, product.slug, context_hash)
        if pending is not None:
            return pending
        purchase = Purchase(
            user_id=user_id,
            product_slug=product.slug,
            status="pending",
            horary_quota_added=product.horary_quota,
            context_hash=context_hash,
        )
        self.db.add(purchase)
        try:
            await self.db.commit()
        except SQLIntegrityError:
            await self.db.rollback()
            pending = await self._get_pending_purchase(user_id, product.slug, context_hash)
            if pending is None:
                raise
            return pending
        return purchase

    async def _reserve_payment(
        self,
        *,
        user_id: uuid.UUID,
        product: Product,
        idempotence_key: str,
        subscription_id: uuid.UUID | None = None,
    ) -> Payment:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._reserve_payment
        # purpose: Get-or-create the pending Payment with a STABLE
        #   idempotence_key and COMMIT it before the external POST. Timeout
        #   or unknown provider outcome leaves this row pending; every retry
        #   reuses the same key (provider dedupe) instead of a new charge.
        # inputs: user_id, product, idempotence_key, optional subscription link.
        # returns: the pending Payment row (committed).
        # side_effects: commits the reservation.
        # error_behavior: re-raises if the row cannot be reserved or reused.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._reserve_payment
        from sqlalchemy.exc import IntegrityError as SQLIntegrityError

        existing = await self._get_payment_by_idempotence_key(idempotence_key)
        if existing is not None:
            return existing
        payment = Payment(
            user_id=user_id,
            amount=product.price_kopecks,
            currency=product.currency,
            status="pending",
            provider="yookassa",
            description=product.name,
            product_slug=product.slug,
            idempotence_key=idempotence_key,
            subscription_id=subscription_id,
        )
        self.db.add(payment)
        try:
            await self.db.commit()
        except SQLIntegrityError:
            await self.db.rollback()
            existing = await self._get_payment_by_idempotence_key(idempotence_key)
            if existing is None:
                raise
            return existing
        return payment

    async def _next_attempt_key(
        self, owner_id: uuid.UUID, product_slug: str, *, prefix: str = "init", force_new: bool = False
    ) -> str:
        # Attempt keys are stable per pending owner: init-<owner>-first (or
        # purchase-<owner>). After a canceled attempt, a NEW suffix is used so
        # a dead idempotence key is never reused for a fresh charge.
        from sqlalchemy import func

        if not force_new:
            return f"{prefix}-{owner_id}-first" if prefix == "init" else f"purchase-{owner_id}"
        result = await self.db.execute(
            select(func.count(Payment.id)).where(
                Payment.user_id == (await self._owner_user_id(owner_id, prefix)),
                Payment.product_slug == product_slug,
                Payment.idempotence_key.like(f"{prefix}-{owner_id}-attempt-%" if prefix == "init" else f"purchase-{owner_id}-attempt-%"),
            )
        )
        attempt = (result.scalar_one() or 0) + 1
        return f"{prefix}-{owner_id}-attempt-{attempt}" if prefix == "init" else f"purchase-{owner_id}-attempt-{attempt}"

    async def _owner_user_id(self, owner_id: uuid.UUID, prefix: str) -> uuid.UUID:
        if prefix == "init":
            result = await self.db.execute(select(Subscription.user_id).where(Subscription.id == owner_id))
        else:
            result = await self.db.execute(select(Purchase.user_id).where(Purchase.id == owner_id))
        return result.scalar_one()

    async def _current_natal_context_hash(self, user_id: uuid.UUID) -> str | None:
        # Compute the entitlement hash from the REAL current profile — the
        # same deterministic input the generation gate uses. The previous
        # getattr(NatalContextData, "profile_hash") always returned None.
        from app.db.models import UserProfile
        from app.services.natal_context_service import NatalContextService

        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            return None
        return NatalContextService.compute_profile_hash(profile)

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
