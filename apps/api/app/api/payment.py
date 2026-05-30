# AI_HEADER
# module: M-API-PAYMENT
# wave: W-6.1
# purpose: Payment endpoints

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.core.dependencies import require_session
from app.services.payment_service import PaymentService
from app.schemas.payment import PaymentIntent, PaymentWebhook
from app.db.models import User

router = APIRouter()


@router.post("/api/payment/create-intent")
async def create_payment_intent(
    intent: PaymentIntent,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
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


@router.post("/api/payment/webhook")
async def payment_webhook(
    webhook: PaymentWebhook,
    db: AsyncSession = Depends(get_session),
):
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
