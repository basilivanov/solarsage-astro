# ############################################################################
# AI_HEADER: MODULE_API_PAYMENT — billing endpoints (YooKassa).
# ROLE: Product catalog, subscription start/status/cancel, one-time purchase
#       start, and the verified YooKassa webhook (IP allowlist + authenticated
#       provider GET before any grant).
# DEPENDENCIES: fastapi, sqlalchemy, app.services.billing_service
# GRACE_ANCHORS: [BILLING_PRODUCTS_ENDPOINT, SUBSCRIPTION_ENDPOINTS,
#                 PURCHASE_ENDPOINT, YOOKASSA_WEBHOOK_ENDPOINT]
# ############################################################################

# START_MODULE_CONTRACT: M-API-PAYMENT
# purpose: Billing endpoints backed by YooKassa with a strict webhook
#   verification contract. Nothing is granted from the webhook payload.
# owns:
#   - apps/api/app/api/payment.py
# inputs:
#   - GET /api/payment/products
#   - POST /api/payment/subscription/start: SubscriptionStartRequest
#   - GET /api/payment/subscription/status
#   - POST /api/payment/subscription/cancel: SubscriptionCancelRequest
#   - POST /api/payment/purchase/start: PurchaseStartRequest
#   - POST /api/payment/webhook/yookassa: YooKassa notification
# outputs: catalog, start payloads, status, cancel result, webhook ack.
# dependencies:
#   - M-BILLING-SERVICE
#   - M-DB-SESSION
#   - M-AUTH-DEPENDENCIES
# side_effects: payment/subscription/purchase creation via provider;
#   fulfillment only after verified webhook.
# emitted_logs: none (service owns events).
# invariants:
#   - All non-webhook endpoints require a session and return 503 when
#     YOOKASSA_ENABLED=false.
#   - The webhook requires no session but only processes events whose source
#     IP is in the official YooKassa allowlist (trusted direct peer as seen
#     by our nginx; X-Forwarded-For from the internet is never trusted) AND
#     whose provider state matches an authenticated GET by id.
#   - synastry stays fail-closed (not sellable).
# failure_policy: 400/404/409 domain mapping; 503 when disabled; 403 for a
#   non-allowlisted webhook source; 500 for a TRANSIENT webhook gap so
#   YooKassa redelivers (up to 24h per the official webhook contract).
# END_MODULE_CONTRACT: M-API-PAYMENT

# START_MODULE_MAP: M-API-PAYMENT
# public_entrypoints:
#   - list_products
#   - start_subscription
#   - get_subscription_status
#   - cancel_subscription
#   - start_purchase
#   - yookassa_webhook
# semantic_blocks:
#   - BILLING_PRODUCTS_ENDPOINT: GET /api/payment/products
#   - SUBSCRIPTION_ENDPOINTS: start/status/cancel
#   - PURCHASE_ENDPOINT: POST /api/payment/purchase/start
#   - YOOKASSA_WEBHOOK_ENDPOINT: POST /api/payment/webhook/yookassa
# owned_tests:
#   - apps/api/tests/test_billing_products.py
#   - apps/api/tests/test_billing_webhook.py
#   - apps/api/tests/test_billing_endpoints.py
# END_MODULE_MAP: M-API-PAYMENT

from __future__ import annotations

import ipaddress

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import require_session
from app.db.models import User
from app.db.session import get_session
from app.schemas.payment import (
    ProductsListResponse,
    PurchaseStartRequest,
    PurchaseStartResponse,
    SubscriptionCancelRequest,
    SubscriptionCancelResponse,
    SubscriptionStartRequest,
    SubscriptionStartResponse,
    SubscriptionStatusResponse,
    YooKassaWebhookEvent,
)
from app.services.billing_service import BillingService

router = APIRouter()

# Official YooKassa notification source ranges
# (https://yookassa.ru/developers/using-api/webhooks — "Проверка IP-адреса").
_YOOKASSA_IP_RANGES: tuple[str, ...] = (
    "185.71.76.0/27",
    "185.71.77.0/27",
    "77.75.153.0/25",
    "77.75.156.11/32",
    "77.75.156.35/32",
    "77.75.154.128/25",
    "2a02:5180::/32",
)


def _webhook_allowlist() -> list[ipaddress._BaseNetwork]:
    override = (settings.yookassa_webhook_ip_allowlist or "").strip()
    ranges = [r.strip() for r in override.split(",") if r.strip()] if override else list(_YOOKASSA_IP_RANGES)
    return [ipaddress.ip_network(r) for r in ranges]


def _trusted_proxies() -> list[ipaddress._BaseNetwork]:
    raw = (settings.yookassa_trusted_proxy_cidrs or "").strip()
    return [ipaddress.ip_network(r.strip()) for r in raw.split(",") if r.strip()]


def _in_any(ip: ipaddress._BaseAddress, networks) -> bool:
    return any(ip in network for network in networks)


def _webhook_source_allowed(request: Request) -> bool:
    # START_FUNCTION_CONTRACT: F-M-API-PAYMENT._webhook_source_allowed
    # purpose: Trusted-proxy source verification for the webhook: a direct
    #   YooKassa peer is accepted from the official ranges; forwarded
    #   X-Real-IP / X-Forwarded-For is believed ONLY when the direct peer is
    #   an explicitly trusted proxy CIDR (our own nginx). Anything else fails
    #   closed, so forged headers from an untrusted peer never pass.
    # inputs: incoming Request.
    # returns: True when the effective source is verified.
    # END_FUNCTION_CONTRACT: F-M-API-PAYMENT._webhook_source_allowed
    if request.client is None:
        return False
    try:
        peer = ipaddress.ip_address(request.client.host)
    except ValueError:
        return False

    allowlist = _webhook_allowlist()
    if _in_any(peer, allowlist):
        return True

    # Forwarded headers are honoured only from an explicitly trusted proxy.
    if not _in_any(peer, _trusted_proxies()):
        return False
    forwarded = request.headers.get("x-real-ip") or (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if not forwarded:
        return False
    try:
        source = ipaddress.ip_address(forwarded)
    except ValueError:
        return False
    return _in_any(source, allowlist)


def _require_enabled() -> None:
    if not settings.yookassa_enabled:
        raise HTTPException(status_code=503, detail="Payments are not available")


def _domain_error(exc: ValueError) -> HTTPException:
    code = str(exc)
    if code == "PRODUCT_NOT_FOUND":
        return HTTPException(status_code=404, detail={"code": code, "message": "Product not found or inactive"})
    if code == "NATAL_CONTEXT_MISSING":
        return HTTPException(status_code=400, detail={"code": code, "message": "Natal context is missing"})
    if code == "LIVE_SUBSCRIPTION_EXISTS":
        return HTTPException(
            status_code=409,
            detail={"code": code, "message": "A live subscription already exists; cancel it before starting another"},
        )
    if code == "PENDING_SUBSCRIPTION_NOT_CANCELABLE":
        return HTTPException(
            status_code=409,
            detail={
                "code": code,
                "message": "The pending payment remains open and payable; retry the same plan or wait for the provider's final status",
            },
        )
    return HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": code})


# START_BLOCK: BILLING_PRODUCTS_ENDPOINT
@router.get("/api/payment/products", response_model=ProductsListResponse)
async def list_products(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    _require_enabled()
    service = BillingService(db)
    products = await service.get_products()
    return ProductsListResponse(
        products=[
            {
                "slug": p.slug,
                "name": p.name,
                "description": p.description,
                "product_type": p.product_type,
                "price_kopecks": p.price_kopecks,
                "currency": p.currency,
                "period_days": p.period_days,
                "horary_quota": p.horary_quota,
            }
            for p in products
        ]
    )
# END_BLOCK: BILLING_PRODUCTS_ENDPOINT


# START_BLOCK: SUBSCRIPTION_ENDPOINTS
@router.post("/api/payment/subscription/start", response_model=SubscriptionStartResponse)
async def start_subscription(
    body: SubscriptionStartRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    _require_enabled()
    service = BillingService(db)
    try:
        result = await service.start_subscription(user.id, body.product_slug)
    except ValueError as exc:
        raise _domain_error(exc) from exc
    if result.get("status") == "already_active":
        raise HTTPException(status_code=409, detail={"code": "ALREADY_ACTIVE", "message": "Subscription is already active"})
    return SubscriptionStartResponse(**result)


@router.get("/api/payment/subscription/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    _require_enabled()
    service = BillingService(db)
    result = await service.get_subscription_status(user.id)
    return SubscriptionStatusResponse(**result)


@router.post("/api/payment/subscription/cancel", response_model=SubscriptionCancelResponse)
async def cancel_subscription(
    body: SubscriptionCancelRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    _require_enabled()
    service = BillingService(db)
    try:
        result = await service.cancel_subscription(user.id, body.reason)
    except ValueError as exc:
        raise _domain_error(exc) from exc
    return SubscriptionCancelResponse(**result)
# END_BLOCK: SUBSCRIPTION_ENDPOINTS


# START_BLOCK: PURCHASE_ENDPOINT
@router.post("/api/payment/purchase/start", response_model=PurchaseStartResponse)
async def start_purchase(
    body: PurchaseStartRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    _require_enabled()
    service = BillingService(db)
    try:
        result = await service.start_purchase(user.id, body.product_slug)
    except ValueError as exc:
        raise _domain_error(exc) from exc
    if result.get("status") == "already_entitled":
        raise HTTPException(status_code=409, detail={"code": "ALREADY_ENTITLED", "message": "Report already purchased for the current context"})
    return PurchaseStartResponse(**result)
# END_BLOCK: PURCHASE_ENDPOINT


# START_BLOCK: YOOKASSA_WEBHOOK_ENDPOINT
# Ack classification (YooKassa retries any non-200 for up to 24h):
# terminal/processed/duplicate/mismatch/canceled -> 200; transient local gaps
# -> retryable 5xx so a redelivery can fulfill after the gap closes.
_RETRYABLE_WEBHOOK_REASONS = frozenset(
    {
        # Early webhook before provider_payment_id was committed locally
        # (webhook vs create-response order is NOT guaranteed).
        "unknown_payment",
        # Owner/product gaps: local state may be repaired before a redelivery.
        "owner_missing",
        "product_missing",
        "unknown_product_type",
        # Verified money against an inactive subscription is NOT a terminal
        # success: the operator reconciles/refunds within the 24h redelivery
        # window instead of the grant being lost behind a false 200.
        "subscription_inactive",
    }
)


@router.post("/api/payment/webhook/yookassa")
async def yookassa_webhook(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    # START_FUNCTION_CONTRACT: F-M-API-PAYMENT.yookassa_webhook
    # purpose: Process YooKassa notifications ONLY from allowlisted source
    #   IPs and ONLY after an authenticated provider GET by id (the payload
    #   alone never grants anything).
    # inputs: raw YooKassa notification (no session, no trust).
    # returns: {"ok": true} with 200 for terminal outcomes (fulfilled,
    #   duplicate, mismatch, canceled, untracked event); 500 for a TRANSIENT
    #   local gap (unknown_payment / owner_missing / product_missing /
    #   unknown_product_type / subscription_inactive / provider non-final) so
    #   YooKassa's redelivery (up to 24h) can complete the grant or the
    #   operator can reconcile; 403 non-allowlisted source; 503 when payments
    #   are disabled.
    # side_effects: idempotent fulfillment via BillingService.
    # error_behavior: 403 non-allowlisted source; 400 malformed body.
    # END_FUNCTION_CONTRACT: F-M-API-PAYMENT.yookassa_webhook
    if not settings.yookassa_enabled:
        raise HTTPException(status_code=503, detail="Payments are not available")
    if not _webhook_source_allowed(request):
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        event = YooKassaWebhookEvent.model_validate(await request.json())
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Malformed notification") from exc

    if event.event not in ("payment.succeeded", "payment.canceled"):
        return {"ok": True}

    provider_payment_id = str((event.object or {}).get("id", ""))
    if not provider_payment_id:
        raise HTTPException(status_code=400, detail="Malformed notification")

    service = BillingService(db)
    result = await service.verify_and_process_webhook(provider_payment_id)
    if not result.get("processed"):
        reason = str(result.get("reason", ""))
        if reason in _RETRYABLE_WEBHOOK_REASONS or reason.startswith("provider_status_"):
            raise HTTPException(status_code=500, detail="Temporary processing failure")
    return {"ok": True}
# END_BLOCK: YOOKASSA_WEBHOOK_ENDPOINT
