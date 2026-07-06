# ############################################################################
# AI_HEADER: MODULE_API_PAYMENT
# ROLE: Disabled payment endpoints
# DEPENDENCIES: fastapi, sqlalchemy, app.services.payment_service
# GRACE_ANCHORS: [CREATE_PAYMENT_ENDPOINT, PAYMENT_WEBHOOK_ENDPOINT]
# WAVE: W-6.1, W-6.2
# ############################################################################

# START_MODULE_CONTRACT: M-API-PAYMENT
# purpose: Reject payment requests until real fulfillment exists.
# owns:
#   - apps/api/app/api/payment.py
# inputs:
#   - POST /api/payment/create-intent: PaymentIntent
#   - POST /api/payment/webhook: PaymentWebhook
# outputs:
#   - HTTP 503 PAYMENT_UNAVAILABLE
# dependencies:
#   - M-PAYMENT-SERVICE
#   - M-DB-SESSION
#   - M-AUTH-DEPENDENCIES
# side_effects:
#   - none
# invariants:
#   - create-intent requires authentication
#   - neither endpoint creates or grants anything
# failure_policy:
#   - both endpoints return explicit 503 unavailable responses
# non_goals:
#   - no real payment provider (MVP stub)
# END_MODULE_CONTRACT: M-API-PAYMENT

# START_MODULE_MAP: M-API-PAYMENT
# public_entrypoints:
#   - create_payment_intent
#   - payment_webhook
# semantic_blocks:
#   - CREATE_PAYMENT_ENDPOINT: POST /api/payment/create-intent
#   - PAYMENT_WEBHOOK_ENDPOINT: POST /api/payment/webhook
# END_MODULE_MAP: M-API-PAYMENT

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.core.dependencies import require_session
from app.services.payment_service import PaymentService, PaymentUnavailableError
from app.schemas.payment import PaymentIntent, PaymentWebhook
from app.db.models import User

router = APIRouter()


def _payment_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "PAYMENT_UNAVAILABLE",
            "message": (
                "Payment fulfillment is disabled until a real provider catalog, "
                "provider confirmation, verified webhook, and idempotent grant exist."
            ),
        },
    )


# START_BLOCK: CREATE_PAYMENT_ENDPOINT
@router.post("/api/payment/create-intent")
async def create_payment_intent(
    intent: PaymentIntent,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    # START_FUNCTION_CONTRACT: F-M-API-PAYMENT.create_payment_intent
    # purpose: Reject payment intent creation until real fulfillment exists.
    # inputs: intent (PaymentIntent), db session, authenticated user
    # returns: HTTP 503 PAYMENT_UNAVAILABLE
    # side_effects: none
    # emitted_logs: none
    # error_behavior: 401 if not authenticated; otherwise 503
    # END_FUNCTION_CONTRACT: F-M-API-PAYMENT.create_payment_intent
    """
    Reject payment intent creation until real provider fulfillment exists.
    """
    service = PaymentService(db)

    try:
        payment = await service.create_payment_intent(
            user_id=user.id,
            amount=intent.amount,
            currency=intent.currency,
            description=intent.description,
        )
    except PaymentUnavailableError:
        raise _payment_unavailable()

    return {
        "payment_id": payment.id,
        "status": payment.status,
        "amount": payment.amount,
        "currency": payment.currency,
    }


# END_BLOCK: CREATE_PAYMENT_ENDPOINT

# START_BLOCK: PAYMENT_WEBHOOK_ENDPOINT
@router.post("/api/payment/webhook")
async def payment_webhook(
    webhook: PaymentWebhook,
    db: AsyncSession = Depends(get_session),
):
    # START_FUNCTION_CONTRACT: F-M-API-PAYMENT.payment_webhook
    # purpose: Reject webhook payloads until provider verification exists.
    # inputs: webhook (PaymentWebhook), db session
    # returns: HTTP 503 PAYMENT_UNAVAILABLE
    # side_effects: none
    # emitted_logs: none
    # error_behavior: always 503
    # END_FUNCTION_CONTRACT: F-M-API-PAYMENT.payment_webhook
    """
    Reject payment webhooks until provider verification and fulfillment exist.
    """
    service = PaymentService(db)
    
    try:
        await service.handle_webhook(
            payment_id=webhook.payment_id,
            status=webhook.status,
        )
    except PaymentUnavailableError:
        raise _payment_unavailable()
    
    return {"ok": True}
# END_BLOCK: PAYMENT_WEBHOOK_ENDPOINT
