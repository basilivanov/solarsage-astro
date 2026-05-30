# AI_HEADER
# module: M-PAYMENT-SERVICE
# wave: W-6.1, W-6.2
# purpose: Payment service (Telegram Payments integration)

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, UTC, date

from app.db.models import Payment
from app.services.access_service import AccessService
from app.services.chat_quota_service import ChatQuotaService


class PaymentService:
    """Payment service for Telegram Payments."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_payment_intent(
        self,
        user_id: uuid.UUID,
        amount: int,
        currency: str,
        description: str,
    ) -> Payment:
        """
        Create payment intent.
        
        W-6.1: Simplified for MVP (no real provider call).
        """
        payment = Payment(
            user_id=user_id,
            amount=amount,
            currency=currency,
            status="pending",
            provider="telegram",
            description=description,
        )
        
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        
        return payment
    
    async def handle_webhook(
        self,
        payment_id: str,
        status: str,
    ) -> None:
        """
        Handle payment webhook from provider.

        W-6.1: Updates payment status.
        W-6.2: Creates subscription entry on success.
        """
        # Find payment by ID
        result = await self.db.execute(
            select(Payment).where(Payment.id == int(payment_id))
        )
        payment = result.scalar_one_or_none()

        if not payment:
            return

        # Update status
        payment.status = status
        if status == "succeeded":
            payment.completed_at = datetime.now(UTC)

            # W-6.2: Create subscription entry
            access_service = AccessService(self.db)
            await access_service.grant_subscription(
                user_id=payment.user_id,
                start_date=date.today(),
                days=30,  # 1 month subscription
            )

            # W-CHAT-4: Increase chat quota
            quota_service = ChatQuotaService(self.db)
            await quota_service.increase_limit(
                user_id=payment.user_id,
                additional=100,  # Subscription adds 100 messages
            )

        await self.db.commit()
