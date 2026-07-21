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
#   billing.payment_fulfilled, billing.payment_reconciled,
#   billing.subscription_canceled,
#   billing.subscription_expired,
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
#   - Initial activation defers the paid period AFTER the latest existing
#     access end (referral bonus or leftover paid): bonus days are consumed
#     first, the paid ledger starts the next day with no overlap and no gap,
#     and current_period_*/next_charge_at shift with the same deferral. A
#     non-renewing initial (payment_method_saved=false) carries
#     next_charge_at=NULL from the start.
#   - An unknown provider payment id is reconciled ONLY via authenticated
#     GET + exact durable owner match (subscription FK or Purchase link) —
#     never from the webhook body, never via broad search; no exact
#     candidate means no bind and no grant.
#   - A provider-canceled INITIAL payment closes its pending subscription
#     terminally (a new start of any plan is then free); a canceled renewal
#     demotes to past_due and retries on a fresh attempt key.
#   - Same-key provider retries happen only inside the 24h YooKassa
#     Idempotence-Key dedupe window anchored by payments.first_attempt_at
#     (committed BEFORE the POST in every charge path: initial, one-time,
#     rebill); past the window an ambiguous payment is NEVER auto-charged
#     again — start flows fail with PAYMENT_NEEDS_RECONCILIATION (API 409),
#     rebill skips charging, and the owner/payment stays observable.
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
#   - A non-renewing subscription (initial success without a saved payment
#     method) expires automatically at period end: the paid period is
#     preserved, no charge is attempted, and the one-live slot frees for a
#     new start. Expiry never depends on a charge attempt or the recurrent
#     kill-switch; renewing subscriptions and past_due retries are untouched.
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
#   - BillingService.get_purchase_status
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

import re
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
        #   ValueError PAYMENT_NEEDS_RECONCILIATION when the 24h dedupe window
        #   of the first attempt expired (-> 409, no provider POST);
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
            # retry merges into the existing payment instead of doubling it —
            # but ONLY inside the provider's 24h dedupe window.
            self._assert_within_dedupe_window(payment)
            if payment.first_attempt_at is None:
                # Durable attempt anchor COMMITTED before the external POST:
                # the dedupe window is computed from the row, not from
                # process memory, even when the POST outcome stays unknown.
                payment.first_attempt_at = datetime.now(UTC)
                await self.db.commit()
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
        #   fail-closed) or missing natal context; ValueError
        #   PAYMENT_NEEDS_RECONCILIATION when the 24h dedupe window expired
        #   (-> 409, no provider POST); RuntimeError on a broken reservation
        #   (missing idempotence key); YooKassaError upstream.
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
            # Same dedupe-window contract as the subscription start: retry
            # with the SAME key only inside 24h; past it, fail closed with a
            # domain error and leave the pending owner/payment observable.
            self._assert_within_dedupe_window(payment)
            if payment.first_attempt_at is None:
                payment.first_attempt_at = datetime.now(UTC)
                await self.db.commit()
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
        # Honest read: expire a non-renewing subscription whose period ended
        # before reporting, so the UI never shows a dead sub as active.
        await self._expire_non_renewing(user_id)
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
                "renewing": False,
                "cancelable": False,
                **access,
            }
        # Backend state machine, never UI-derived:
        # renewing = live (active/past_due) with a saved method AND a
        # scheduled next charge; cancelable = a real recurring enrollment
        # exists that the cancel endpoint meaningfully cancels.
        live = subscription.status in ("active", "past_due")
        has_method = subscription.payment_method_id is not None
        renewing = live and has_method and subscription.next_charge_at is not None
        cancelable = live and has_method
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
            "renewing": renewing,
            "cancelable": cancelable,
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

    async def get_purchase_status(self, user_id: uuid.UUID, purchase_id: uuid.UUID) -> dict:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.get_purchase_status
        # purpose: Owner-only authenticated status read for the purchase
        #   polling flow. Answers strictly from LOCAL rows — never calls the
        #   provider (webhook is the only fulfillment driver).
        # inputs: user_id (session), purchase_id.
        # returns: dict with purchase_id, product_slug, status
        #   (pending|succeeded|consumed|delivered|canceled),
        #   provider_payment_id, confirmation_url (only while pending).
        # side_effects: none.
        # error_behavior: ValueError PURCHASE_NOT_FOUND for an unknown OR
        #   foreign purchase id (no existence leak across users).
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.get_purchase_status
        result = await self.db.execute(select(Purchase).where(Purchase.id == purchase_id))
        purchase = result.scalar_one_or_none()
        if purchase is None or purchase.user_id != user_id:
            raise ValueError("PURCHASE_NOT_FOUND")

        status = purchase.status
        provider_payment_id = None
        confirmation_url = None
        if purchase.payment_id is not None:
            payment_result = await self.db.execute(
                select(Payment).where(Payment.id == purchase.payment_id)
            )
            payment = payment_result.scalar_one_or_none()
            if payment is not None:
                provider_payment_id = payment.provider_payment_id
                if payment.status == "canceled" and purchase.status == "pending":
                    status = "canceled"
                if purchase.status == "pending" and payment.status == "pending":
                    confirmation_url = payment.confirmation_url
        return {
            "purchase_id": purchase.id,
            "product_slug": purchase.product_slug,
            "status": status,
            "provider_payment_id": provider_payment_id,
            "confirmation_url": confirmation_url,
        }

    # START_BLOCK: BILLING_FULFILL
    async def verify_and_process_webhook(self, provider_payment_id: str) -> dict:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.verify_and_process_webhook
        # purpose: Mandatory second webhook verification step: authenticated
        #   provider GET by id, strict comparison (status, paid, amount,
        #   currency, shop metadata vs the LOCAL payment), then idempotent
        #   fulfillment. The webhook payload itself is NEVER trusted. An
        #   unknown provider id first goes through fail-closed
        #   self-reconciliation (authenticated GET + exact durable owner
        #   match) so a charge with an unknown create outcome still grants
        #   exactly once; no exact candidate means no bind and no grant.
        # inputs: provider_payment_id from the webhook envelope.
        # returns: {"processed": bool, "reason": str}
        # side_effects: fulfills Payment/Subscription/Purchase/AccessLedger/
        #   HoraryCredit exactly once.
        # error_behavior: mismatches are rejected WITHOUT any state change —
        #   strict identity (provider id/amount/currency/user/product/owner/
        #   charge kind/period) is enforced BEFORE canceled or succeeded
        #   handling; provider errors propagate as YooKassaError; a
        #   missing/deactivated fulfillment target (product row, owner row,
        #   inactive subscription) leaves the payment PENDING with
        #   billing.fulfillment_blocked so the grant stays recoverable, and a
        #   canceled renewal demotes an active subscription to past_due for a
        #   fresh-key retry.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.verify_and_process_webhook
        result = await self.db.execute(
            select(Payment)
            .where(Payment.provider_payment_id == provider_payment_id)
            .with_for_update()
        )
        payment = result.scalar_one_or_none()
        client = get_yookassa_client()
        bound_here = False
        if payment is None:
            # Fail-closed self-reconciliation: a local durable payment may be
            # unbound (unknown create outcome). Bind ONLY after an
            # authenticated provider GET and an exact owner match — never by
            # the webhook payload, never by a broad search.
            outcome = await self._reconcile_unknown_payment(client, provider_payment_id)
            if outcome is None:
                # False-unknown race: a concurrent binder may have committed
                # BETWEEN the initial SELECT and the candidate lookup. One
                # fresh locked re-read by provider id decides by ACTUAL
                # state — never answer a false unknown for a row that now
                # exists.
                payment = await self._reread_by_provider_id(provider_payment_id)
                if payment is None:
                    log_event("billing.webhook_rejected", msg="unknown provider payment", level="warning")
                    return {"processed": False, "reason": "unknown_payment"}
            else:
                payment, bound_here = outcome

        def _abort_uncommitted() -> None:
            # A binding that never reached a durable commit must not linger
            # even in-memory (shared-session safety); the row was never
            # committed, so clearing mirrors the DB exactly.
            if bound_here:
                payment.provider_payment_id = None

        if payment.status == "succeeded":
            return {"processed": False, "reason": "already_fulfilled"}

        remote = await client.get_payment(provider_payment_id)

        # STRICT identity BEFORE any local mutation: provider id + amount +
        # currency + user/product + exact owner + charge kind (+ recurrent
        # period). A canceled/pending remote with a forged identity must
        # change NOTHING (no canceled marks, no reconcile commit).
        if not self._identity_matches(payment, remote):
            _abort_uncommitted()
            log_event("billing.webhook_rejected", msg="webhook/provider identity mismatch", level="warning")
            return {"processed": False, "reason": "mismatch"}

        if remote["status"] == "canceled":
            payment.status = "canceled"
            payment.canceled_at = datetime.now(UTC)
            # A canceled RENEWAL demotes an active subscription to past_due so
            # the rebill loop retries the cycle on a FRESH attempt key. A
            # provider-authoritative canceled INITIAL payment (subscription
            # still pending) closes the pending owner TERMINALLY: otherwise
            # the one-live index would block any future plan forever. Its dead
            # key is never reused — a new start creates a fresh owner+key.
            if payment.subscription_id is not None:
                linked = await self.db.execute(
                    select(Subscription).where(Subscription.id == payment.subscription_id)
                )
                sub = linked.scalar_one_or_none()
                if sub is not None and sub.status == "active":
                    sub.status = "past_due"
                    sub.next_charge_at = datetime.now(UTC) + timedelta(days=1)
                elif (
                    sub is not None
                    and sub.status == "pending"
                    and (payment.idempotence_key or "").startswith("init-")
                ):
                    sub.status = "canceled"
                    sub.canceled_at = datetime.now(UTC)
                    sub.cancellation_reason = "provider_canceled"
                    sub.next_charge_at = None
            await self.db.commit()
            if bound_here:
                # Durable canceled bind committed: the reconciliation event
                # is truthful only NOW (never on rollback/abort paths).
                log_event(
                    "billing.payment_reconciled",
                    msg="reconciled unknown provider payment (canceled)",
                    payload={"payment_id": payment.id},
                )
            return {"processed": False, "reason": "canceled"}

        if remote["status"] != "succeeded":
            _abort_uncommitted()
            return {"processed": False, "reason": f"provider_status_{remote['status']}"}

        if not remote["paid"]:
            _abort_uncommitted()
            log_event("billing.webhook_rejected", msg="webhook/provider paid flag mismatch", level="warning")
            return {"processed": False, "reason": "mismatch"}

        # Fulfillment target gate BEFORE marking succeeded: the payment is
        # marked succeeded ONLY when the grant can actually happen. A missing
        # product row (lookup has NO is_active sales filter here) or a missing
        # owner leaves the payment pending and observable, so a later webhook
        # or manual reconciliation can still fulfill — never lost behind the
        # already_fulfilled early-return.
        product = await self._get_product_any(payment.product_slug) if payment.product_slug else None
        if product is None:
            _abort_uncommitted()
            log_event(
                "billing.fulfillment_blocked",
                msg="payment product row missing",
                level="error",
                payload={"payment_id": payment.id},
            )
            return {"processed": False, "reason": "product_missing"}
        block_reason = await self._fulfillment_block_reason(payment, product)
        if block_reason is not None:
            _abort_uncommitted()
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
        if bound_here:
            # The reconciliation event is emitted ONLY after the durable
            # commit of binding+verification+fulfillment — never before.
            log_event(
                "billing.payment_reconciled",
                msg="reconciled unknown provider payment",
                payload={"payment_id": payment.id},
            )
        log_event("billing.payment_fulfilled", msg="payment fulfilled", payload={"payment_id": payment.id})
        return {"processed": True, "reason": "fulfilled"}

    async def _reread_by_provider_id(self, provider_payment_id: str) -> Payment | None:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._reread_by_provider_id
        # purpose: The false-unknown guard: one fresh LOCKED re-read by
        #   provider_payment_id after reconciliation found no candidate. A
        #   concurrent binder's committed row is seen in its ACTUAL state
        #   (never a stale identity-map snapshot); the caller continues by
        #   that state (already_fulfilled or normal verification) instead of
        #   a false unknown_payment.
        # inputs: provider_payment_id from the webhook.
        # returns: the fresh locked Payment or None when it truly does not
        #   exist locally.
        # side_effects: locked refresh read only; no mutation.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._reread_by_provider_id
        result = await self.db.execute(
            select(Payment)
            .where(Payment.provider_payment_id == provider_payment_id)
            .with_for_update()
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            return None
        await self.db.refresh(payment, with_for_update=True)
        return payment

    async def _reconcile_unknown_payment(self, client, provider_payment_id: str) -> tuple[Payment, bool] | None:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._reconcile_unknown_payment
        # purpose: Recover from a CHARGE-WITHOUT-GRANT window: the provider
        #   created/captured a payment whose create response we never saw
        #   (unknown outcome, local provider_payment_id NULL) and the user
        #   did NOT retry start. The webhook alone can now link it.
        #   Verification order: authenticated provider GET first (its id must
        #   equal the requested one); then match remote metadata + amount +
        #   currency + exact durable owner (Payment.subscription_id for
        #   subscriptions, Purchase.payment_id for one-time) + exact charge
        #   kind (init -> initial_recurrent, rebill -> recurrent with the
        #   exact cycle period, purchase -> one_time) against pending UNBOUND
        #   local payments; bind ONLY on EXACTLY ONE exact candidate.
        #   ATOMICITY: the binding is NOT committed here — it commits
        #   together with verification + fulfillment in the caller's single
        #   transaction under this Payment row lock, so a crash stays safely
        #   retryable and a concurrent binder reads the ACTUAL state after
        #   its lock wait (bound+succeeded -> already_fulfilled, never a
        #   false unknown, never a double grant).
        # inputs: provider client, provider_payment_id from the webhook.
        # returns: (payment, bound_here) to continue with (bound in-memory,
        #   uncommitted) or None when the exact candidate is absent/mismatched.
        # side_effects: provider GET; SELECT ... FOR UPDATE on the candidate.
        # error_behavior: any mismatch/ambiguity -> None (no state change);
        #   a provider GET failure (e.g. truly unknown id) also -> None.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._reconcile_unknown_payment
        try:
            remote = await client.get_payment(provider_payment_id)
        except YooKassaError:
            return None
        # Strict remote identity: the authenticated GET must answer for the
        # EXACT id we asked about.
        if remote.get("provider_payment_id") != provider_payment_id:
            return None
        metadata = remote.get("metadata") or {}
        remote_user = metadata.get("user_id")
        remote_owner = metadata.get("owner_id")
        remote_slug = metadata.get("product_slug")
        remote_type = metadata.get("type")
        if not remote_user or not remote_owner or not remote_slug:
            return None
        try:
            remote_user_uuid = uuid.UUID(str(remote_user))
        except (ValueError, AttributeError, TypeError):
            return None

        result = await self.db.execute(
            select(Payment).where(
                Payment.user_id == remote_user_uuid,
                Payment.product_slug == remote_slug,
                Payment.status == "pending",
                Payment.provider_payment_id.is_(None),
            )
        )
        candidates = []
        for candidate in result.scalars().all():
            if remote["amount_value"] != _kopecks_str(candidate.amount):
                continue
            if remote["currency"] != candidate.currency:
                continue
            # Exact charge-kind identity from the LOCAL key.
            expected_type = self._expected_charge_type(candidate)
            if expected_type is None or remote_type != expected_type:
                continue
            if expected_type == "recurrent" and metadata.get("period") != self._rebill_cycle_label(candidate):
                continue
            if candidate.subscription_id is not None:
                # Subscription charge: owner is the durable FK link.
                if str(candidate.subscription_id) != str(remote_owner):
                    continue
            else:
                # One-time charge: owner is the Purchase linked by payment_id.
                purchase_result = await self.db.execute(
                    select(Purchase).where(Purchase.payment_id == candidate.id)
                )
                purchase = purchase_result.scalar_one_or_none()
                if purchase is None or str(purchase.id) != str(remote_owner):
                    continue
            candidates.append(candidate)

        if len(candidates) != 1:
            return None

        # Lock the row and re-verify its ACTUAL state after any lock wait.
        return await self._lock_candidate_for_bind(candidates[0].id, provider_payment_id)

    async def _lock_candidate_for_bind(self, candidate_id: int, provider_payment_id: str) -> tuple[Payment, bool] | None:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._lock_candidate_for_bind
        # purpose: The ONLY binding boundary for self-reconciliation. After
        #   SELECT ... FOR UPDATE the row is REFRESHED under the same lock —
        #   the identity map can hold a stale unbound snapshot taken before a
        #   concurrent binder committed. Decision strictly by actual state:
        #   same id -> concurrent binder, return for the already_fulfilled
        #   path; foreign id/non-pending -> reject; unbound pending -> bind.
        # inputs: candidate Payment.id, provider_payment_id to bind.
        # returns: (payment, bound_here) or None on reject.
        # side_effects: locked refresh read; in-memory bind (NO commit).
        # error_behavior: None on any non-exact state.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._lock_candidate_for_bind
        locked = await self.db.execute(
            select(Payment).where(Payment.id == candidate_id).with_for_update()
        )
        payment = locked.scalar_one_or_none()
        if payment is None:
            return None
        await self.db.refresh(payment, with_for_update=True)
        if payment.provider_payment_id == provider_payment_id:
            # A concurrent binder already linked it: continue by ACTUAL state
            # (the caller's succeeded check yields already_fulfilled).
            return (payment, False)
        if payment.provider_payment_id is not None or payment.status != "pending":
            return None
        # Bind WITHOUT committing: the caller's final commit covers
        # binding + verification + fulfillment atomically.
        payment.provider_payment_id = provider_payment_id
        return (payment, True)

    @staticmethod
    def _expected_charge_type(payment: Payment) -> str | None:
        # Charge-kind contract from the local idempotence key:
        # init-* -> initial_recurrent, rebill-* -> recurrent, purchase-* -> one_time.
        key = payment.idempotence_key or ""
        if key.startswith("rebill-"):
            return "recurrent"
        if key.startswith("init-"):
            return "initial_recurrent"
        if key.startswith("purchase-"):
            return "one_time"
        return None

    @staticmethod
    def _rebill_cycle_label(payment: Payment) -> str | None:
        # The cycle label embedded in a rebill key: rebill-<sub>-<label>[-a<N>].
        key = payment.idempotence_key or ""
        base = f"rebill-{payment.subscription_id}-"
        if not key.startswith(base):
            return None
        return re.sub(r"-a\d+$", "", key[len(base):])

    def _identity_matches(self, payment: Payment, remote: dict) -> bool:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._identity_matches
        # purpose: The strict remote-vs-local identity check, INDEPENDENT of
        #   the paid flag: provider id + amount/currency + user/product +
        #   exact owner + charge kind (init -> initial_recurrent, rebill ->
        #   recurrent with the exact cycle period, purchase -> one_time).
        #   Runs BEFORE any local mutation (canceled handling included).
        # inputs: payment (locked local row), remote (authenticated GET dict).
        # returns: True only on exact identity; any mismatch means the caller
        #   must not change state at all.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._identity_matches
        if remote.get("provider_payment_id") != payment.provider_payment_id:
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
        expected_type = self._expected_charge_type(payment)
        if expected_type is None or metadata.get("type") != expected_type:
            return False
        if expected_type == "recurrent" and metadata.get("period") != self._rebill_cycle_label(payment):
            return False
        # Strict owner check: subscription payments are linked by FK; purchase
        # payments by the purchase key prefix.
        owner = str(metadata.get("owner_id"))
        if payment.subscription_id is not None:
            return owner == str(payment.subscription_id)
        return owner == self._expected_purchase_owner_id(payment)

    def _payment_matches(self, payment: Payment, remote: dict) -> bool:
        # Succeeded-path matcher: the strict identity plus the paid flag.
        return bool(remote["paid"]) and self._identity_matches(payment, remote)

    @staticmethod
    def _expected_purchase_owner_id(payment: Payment) -> str:
        # Owner is encoded in the idempotence key: purchase-<uuid> with an
        # optional exact -attempt-<N> retry suffix. Only the exact suffix is
        # stripped — the provider metadata always carries the PLAIN purchase
        # UUID, so a fresh payment after a known-canceled attempt must
        # resolve to the same owner (the old raw strip returned
        # <uuid>-attempt-1 -> permanent mismatch -> money without grant).
        key = payment.idempotence_key or ""
        if not key.startswith("purchase-"):
            return ""
        return re.sub(r"-attempt-\d+$", "", key[len("purchase-"):])

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
        # Whether THIS payment can ever renew: only a saved method allows a
        # future charge. A non-renewing initial must carry next_charge_at=NULL
        # from the start (the UI's auto-renew flag derives from it) while
        # current_period_end and the paid ledger are fully honored; expiry at
        # period end is handled by _expire_non_renewing.
        renewing = bool(remote["payment_method_saved"] and remote["payment_method_id"])
        # All ledger dates derive from the SAME UTC clock as the period
        # timestamps — date.today() (local TZ) would diverge from
        # current_period_end around local midnight and shift the paid window.
        grant_start = now.date()
        if subscription.status in ("pending", "past_due"):
            # First activation: bonus/referral days and any leftover paid
            # access are consumed FIRST (the AccessCard promise). The paid
            # period starts right after the LATEST existing access end — no
            # overlap (no lost days), no gap. current_period_* and
            # next_charge_at shift with the same deferral; the ledger end
            # (inclusive) is the day before current_period_end (exclusive).
            latest_end = await self._latest_access_end_date(payment.user_id)
            defer_days = 0
            if latest_end is not None and latest_end >= now.date():
                defer_days = (latest_end - now.date()).days + 1
            subscription.status = "active"
            subscription.current_period_start = now + timedelta(days=defer_days)
            subscription.current_period_end = now + timedelta(days=defer_days + days)
            subscription.next_charge_at = (
                now + timedelta(days=defer_days + days) if renewing else None
            )
            grant_start = now.date() + timedelta(days=defer_days)
        elif subscription.status == "active":
            # Renewal: extend strictly FROM the current period end, so a
            # renewal payment can never shorten or duplicate a period. The
            # ledger must cover the EXTENDED period: when the prior period
            # end is still in the future the grant starts there, not today.
            base_end = subscription.current_period_end or now
            subscription.current_period_end = base_end + timedelta(days=days)
            subscription.next_charge_at = base_end + timedelta(days=days)
            grant_start = max(now.date(), base_end.date())
        elif self._is_paid_canceled_renewal(payment, subscription):
            # In-flight renewal that succeeded AFTER the user's cancel: honor
            # exactly the paid period (extend access from the paid period
            # end) but NEVER resurrect — status stays canceled and
            # next_charge_at stays NULL, so no future charge can happen.
            base_end = subscription.current_period_end or now
            subscription.current_period_end = base_end + timedelta(days=days)
            subscription.next_charge_at = None
            grant_start = max(now.date(), base_end.date())
        else:
            # canceled initial payment / expired: never resurrect via webhook.
            log_event("billing.webhook_rejected", msg="webhook for inactive subscription", level="warning")
            return

        if remote["payment_method_saved"] and remote["payment_method_id"]:
            subscription.payment_method_id = remote["payment_method_id"]

        access = AccessService(self.db)
        # Non-committing grant: THIS service owns the single final commit
        # (binding + succeeded + subscription + ledger in one transaction).
        await access.grant_subscription(user_id=payment.user_id, start_date=grant_start, days=days, commit=False)

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
    # attempt. Same-key retries are allowed strictly inside this window —
    # for rebill AND for initial/one-time start charges alike.
    _KEY_DEDUPE_WINDOW = timedelta(hours=24)
    # Unknown-outcome retry cadence: strictly INSIDE the dedupe window so a
    # real same-key retry actually happens (a +1 day reschedule would land on
    #/past the 24h boundary and make every first failure terminal).
    _REBILL_RETRY_INTERVAL = timedelta(hours=1)

    async def rebill_due_subscriptions(self) -> int:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.rebill_due_subscriptions
        # purpose: Charge all due subscriptions with their saved
        #   payment_method_id. Hard kill-switch: when
        #   YOOKASSA_RECURRENT_ENABLED=false performs ZERO charges.
        # inputs: none (scans due subscriptions).
        # returns: number of rebill attempts made.
        # side_effects: POST /payments per due subscription; marks failures
        #   past_due with a bounded retry interval strictly inside the dedupe
        #   window; anchors first_attempt_at; re-verifies the due subscription
        #   under a row lock immediately before every charge.
        # error_behavior: provider failures demote to past_due, never raise.
        #   The cycle resolves its LATEST attempt: a live latest attempt is
        #   reused/skipped (no second charge before the webhook), a
        #   known-canceled latest attempt is retried on a FRESH -a<N> key.
        #   An ambiguous payment whose 24h dedupe window expired is NEVER
        #   auto-charged again — it stays pending for manual reconciliation
        #   (system.error log), subscription past_due.
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE.rebill_due_subscriptions
        # Lifecycle hygiene first and INDEPENDENT of charging: non-renewing
        # subscriptions (no saved method) whose paid period ended become
        # expired even when the recurrent kill-switch is off — expiry never
        # depends on a charge attempt.
        await self._expire_non_renewing()
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
                and now - first_attempt_at >= self._KEY_DEDUPE_WINDOW
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
            # Stale-due race guard at the charge boundary: re-read the due
            # subscription under a row lock right before the provider POST.
            # A cancel committed BEFORE this claim means zero provider calls;
            # a cancel committed after it leaves the payment in-flight and
            # the paid-after-cancel rule honors it honestly.
            locked_sub_result = await self.db.execute(
                select(Subscription).where(Subscription.id == sub.id).with_for_update()
            )
            locked_sub = locked_sub_result.scalar_one_or_none()
            if locked_sub is None:
                # End the transaction WITHOUT expiring the due-list rows
                # (Session.rollback would expire them all and break the job
                # with MissingGreenlet on the next user's attribute access).
                await self.db.commit()
                continue
            # Fresh locked read: production sessions run expire_on_commit=
            # False, so a plain select can serve a STALE row from the
            # identity map. refresh(with_for_update) forces the real state.
            await self.db.refresh(locked_sub, with_for_update=True)
            next_charge_at = locked_sub.next_charge_at
            if next_charge_at is not None and next_charge_at.tzinfo is None:
                next_charge_at = next_charge_at.replace(tzinfo=UTC)
            if (
                locked_sub.status not in ("active", "past_due")
                or next_charge_at is None
                or next_charge_at > now
                or not locked_sub.payment_method_id
            ):
                # Release the row lock NOW (commit ends the tx but keeps ORM
                # rows usable for the remaining due users); never hold it
                # across other users.
                await self.db.commit()
                continue
            sub = locked_sub
            payment_method_id = locked_sub.payment_method_id
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
                # Unknown outcome: demote and retry on a bounded interval
                # STRICTLY INSIDE the dedupe window with the SAME key, never
                # a fresh charge.
                sub.status = "past_due"
                sub.next_charge_at = now + self._REBILL_RETRY_INTERVAL
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
        # Fail-safe first: a non-renewing active subscription whose paid
        # period has ended is expired here, so it can never deadlock a new
        # start behind the one-live guard.
        await self._expire_non_renewing(user_id)
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.status.in_(["pending", "active", "past_due"]),
            ).order_by(Subscription.created_at.desc())
        )
        return result.scalars().first()

    async def _latest_access_end_date(self, user_id: uuid.UUID) -> date | None:
        # Latest access end across ALL ledger types (referral bonus and paid
        # alike): the anchor for the deferred initial paid period.
        result = await self.db.execute(
            select(AccessLedger.end_date)
            .where(AccessLedger.user_id == user_id)
            .order_by(AccessLedger.end_date.desc())
        )
        return result.scalars().first()

    async def _expire_non_renewing(self, user_id: uuid.UUID | None = None) -> int:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._expire_non_renewing
        # purpose: Lifecycle fail-safe for subscriptions that CANNOT renew
        #   (initial payment succeeded with payment_method_saved=false, so no
        #   payment_method_id). When their paid period ends they transition
        #   active -> expired — the paid period (access ledger) is fully
        #   preserved, no charge is ever attempted, and the one-live slot
        #   frees up for a new start. Renewing subscriptions (saved method)
        #   and past_due retries are NEVER touched here; the transition does
        #   not depend on the recurrent kill-switch or any charge attempt.
        # inputs: optional user_id to scope the sweep (read paths), else all.
        # returns: number of subscriptions expired in this sweep.
        # side_effects: status/next_charge_at update + commit, expiry log.
        # error_behavior: none (idempotent no-op when nothing is due).
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._expire_non_renewing
        now = datetime.now(UTC)
        stmt = select(Subscription).where(
            Subscription.status == "active",
            Subscription.payment_method_id.is_(None),
            Subscription.current_period_end.is_not(None),
            Subscription.current_period_end <= now,
        )
        if user_id is not None:
            stmt = stmt.where(Subscription.user_id == user_id)
        result = await self.db.execute(stmt)
        rows = list(result.scalars().all())
        for sub in rows:
            sub.status = "expired"
            sub.next_charge_at = None
            log_event(
                "billing.subscription_expired",
                msg="non-renewing subscription expired at period end",
                payload={"subscription_id": str(sub.id)},
            )
        if rows:
            await self.db.commit()
        return len(rows)

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

    def _assert_within_dedupe_window(self, payment: Payment) -> None:
        # START_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._assert_within_dedupe_window
        # purpose: Fail-closed guard for start-flow retries. YooKassa dedupes
        #   an Idempotence-Key only for 24h after the FIRST attempt; past the
        #   window the outcome of that attempt is unknowable client-side, so
        #   a same-key retry could double-charge. Inside the window the retry
        #   is safe (provider dedupes); after it the pending owner/payment
        #   stays observable for reconciliation (a webhook can still fulfill)
        #   and NO provider POST happens.
        # inputs: payment (reserved row about to be (re-)charged).
        # returns: None when the retry is inside the 24h window.
        # side_effects: system.error log on violation.
        # error_behavior: raises ValueError PAYMENT_NEEDS_RECONCILIATION past
        #   the window (-> API 409).
        # END_FUNCTION_CONTRACT: F-M-BILLING-SERVICE._assert_within_dedupe_window
        first_attempt_at = payment.first_attempt_at
        # SQLite returns tz-naive datetimes; Postgres returns aware ones.
        if first_attempt_at is not None and first_attempt_at.tzinfo is None:
            first_attempt_at = first_attempt_at.replace(tzinfo=UTC)
        if first_attempt_at is not None and datetime.now(UTC) - first_attempt_at >= self._KEY_DEDUPE_WINDOW:
            log_event(
                "system.error",
                msg="payment needs manual reconciliation: idempotence window expired",
                level="error",
                payload={"payment_id": payment.id},
            )
            raise ValueError("PAYMENT_NEEDS_RECONCILIATION")

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
