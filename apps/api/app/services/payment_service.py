# ############################################################################
# AI_HEADER: MODULE_PAYMENT_SERVICE
# ROLE: Payment service (Telegram Payments integration)
# DEPENDENCIES: sqlalchemy, app.db.models, app.services.access_service
# GRACE_ANCHORS: [CREATE_PAYMENT_INTENT, HANDLE_WEBHOOK]
# WAVE: W-6.1, W-6.2
# ############################################################################

# START_MODULE_CONTRACT: M-PAYMENT-SERVICE
# purpose: Create payment intents and handle webhook callbacks.
# owns:
#   - apps/api/app/services/payment_service.py
# inputs:
#   - user_id, amount, currency, description
#   - payment_id, status (webhook)
# outputs:
#   - Payment DB model
# dependencies:
#   - M-DB-MODELS (Payment)
#   - M-ACCESS (AccessService)
#   - M-CHAT-QUOTA-SERVICE (ChatQuotaService)
# side_effects:
#   - creates/updates payment rows
#   - grants subscription on successful payment
#   - increases chat quota on successful payment
# invariants:
#   - webhook is idempotent (silent no-op on unknown payments)
# failure_policy:
#   - webhook silently returns if payment not found
# non_goals:
#   - no real payment provider (MVP stub)
# END_MODULE_CONTRACT: M-PAYMENT-SERVICE

# START_MODULE_MAP: M-PAYMENT-SERVICE
# public_entrypoints:
#   - create_payment_intent
#   - handle_webhook
# semantic_blocks:
#   - CREATE_PAYMENT_INTENT: create pending payment
#   - HANDLE_WEBHOOK: process payment callback
# END_MODULE_MAP: M-PAYMENT-SERVICE

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
        # START_FUNCTION_CONTRACT: F-M-PAYMENT-SERVICE.create_payment_intent
        # purpose: Create pending payment intent (MVP stub, no real provider).
        # inputs: user_id (UUID), amount (int), currency (str), description (str)
        # returns: Payment DB model with id, status, amount, currency
        # side_effects: creates Payment row with status "pending"
        # emitted_logs: payment.intent_created
        # error_behavior: DB errors propagate
        # END_FUNCTION_CONTRACT: F-M-PAYMENT-SERVICE.create_payment_intent
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
        # START_FUNCTION_CONTRACT: F-M-PAYMENT-SERVICE.handle_webhook
        # purpose: Handle payment webhook: update status, grant access on success.
        # inputs: payment_id (str), status (str)
        # returns: None
        # side_effects: updates Payment status, creates subscription, increases chat quota
        # emitted_logs: payment.succeeded, payment.failed
        # error_behavior: idempotent — silently returns if payment not found
        # END_FUNCTION_CONTRACT: F-M-PAYMENT-SERVICE.handle_webhook
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
