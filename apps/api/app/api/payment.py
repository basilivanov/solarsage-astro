# ############################################################################
# AI_HEADER: MODULE_API_PAYMENT
# ROLE: Payment endpoints — create intent and handle webhook
# DEPENDENCIES: fastapi, sqlalchemy, app.services.payment_service
# GRACE_ANCHORS: [CREATE_PAYMENT_ENDPOINT, PAYMENT_WEBHOOK_ENDPOINT]
# WAVE: W-6.1, W-6.2
# ############################################################################

# START_MODULE_CONTRACT: M-API-PAYMENT
# purpose: Payment intent creation and webhook handling.
# owns:
#   - apps/api/app/api/payment.py
# inputs:
#   - POST /api/payment/create-intent: PaymentIntent
#   - POST /api/payment/webhook: PaymentWebhook
# outputs:
#   - payment with id/status/amount/currency
#   - {"ok": true}
# dependencies:
#   - M-PAYMENT-SERVICE
#   - M-DB-SESSION
#   - M-AUTH-DEPENDENCIES
# side_effects:
#   - creates/updates payment rows
#   - creates subscription on successful webhook
# invariants:
#   - create-intent requires authentication
#   - webhook is idempotent
# failure_policy:
#   - webhook: silently ignores unknown payments
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

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.core.dependencies import require_session
from app.services.payment_service import PaymentService
from app.schemas.payment import PaymentIntent, PaymentWebhook
from app.db.models import User

router = APIRouter()


# START_BLOCK: CREATE_PAYMENT_ENDPOINT
@router.post("/api/payment/create-intent")
async def create_payment_intent(
    intent: PaymentIntent,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    # START_FUNCTION_CONTRACT: F-M-API-PAYMENT.create_payment_intent
    # purpose: Create payment intent for subscription (MVP stub).
    # inputs: intent (PaymentIntent), db session, authenticated user
    # returns: dict with payment_id, status, amount, currency
    # side_effects: creates Payment row in database
    # emitted_logs: payment.intent_created
    # error_behavior: 401 if not authenticated; DB errors propagate
    # END_FUNCTION_CONTRACT: F-M-API-PAYMENT.create_payment_intent
    """
    Create payment intent for subscription.

    W-6.1: Simplified for MVP (test mode).
    """
    service = PaymentService(db)

    payment = await service.create_payment_intent(
        user_id=user.id,
        amount=intent.amount,
        currency=intent.currency,
        description=intent.description,
    )
    
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
    # purpose: Handle payment webhook callback from provider.
    # inputs: webhook (PaymentWebhook), db session
    # returns: {"ok": True}
    # side_effects: updates payment status, creates subscription on success, increases chat quota
    # emitted_logs: payment.succeeded, payment.failed
    # error_behavior: idempotent — silently returns if payment not found
    # END_FUNCTION_CONTRACT: F-M-API-PAYMENT.payment_webhook
    """
    Handle payment webhook from provider.
    
    W-6.1: Updates payment status.
    """
    service = PaymentService(db)
    
    await service.handle_webhook(
        payment_id=webhook.payment_id,
        status=webhook.status,
    )
    
    return {"ok": True}
# END_BLOCK: PAYMENT_WEBHOOK_ENDPOINT
