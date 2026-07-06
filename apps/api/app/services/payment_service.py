# ############################################################################
# AI_HEADER: MODULE_PAYMENT_SERVICE
# ROLE: Disabled payment fulfillment boundary
# DEPENDENCIES: sqlalchemy, app.db.models
# GRACE_ANCHORS: [CREATE_PAYMENT_INTENT, HANDLE_WEBHOOK]
# WAVE: W-6.1, W-6.2
# ############################################################################

# START_MODULE_CONTRACT: M-PAYMENT-SERVICE
# purpose: Reject payment intents and webhooks until real fulfillment exists.
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
#   - none
# invariants:
#   - no payment row, subscription, access, or quota is created
# failure_policy:
#   - all operations raise PaymentUnavailableError
# non_goals:
#   - partial provider integration
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
from app.db.models import Payment


class PaymentUnavailableError(RuntimeError):
    """Raised while payment fulfillment is intentionally disabled."""


class PaymentService:
    """Disabled boundary for payment operations."""

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
        # purpose: Reject payment intent creation while fulfillment is unavailable.
        # inputs: user_id (UUID), amount (int), currency (str), description (str)
        # returns: never
        # side_effects: none
        # emitted_logs: none
        # error_behavior: always raises PaymentUnavailableError
        # END_FUNCTION_CONTRACT: F-M-PAYMENT-SERVICE.create_payment_intent
        raise PaymentUnavailableError(
            "Payment intent creation is disabled until real provider fulfillment exists."
        )
    
    async def handle_webhook(
        self,
        payment_id: str,
        status: str,
    ) -> None:
        # START_FUNCTION_CONTRACT: F-M-PAYMENT-SERVICE.handle_webhook
        # purpose: Reject webhook handling while provider verification is unavailable.
        # inputs: payment_id (str), status (str)
        # returns: None
        # side_effects: none
        # emitted_logs: none
        # error_behavior: always raises PaymentUnavailableError
        # END_FUNCTION_CONTRACT: F-M-PAYMENT-SERVICE.handle_webhook
        raise PaymentUnavailableError(
            "Payment webhook handling is disabled until provider verification exists."
        )
