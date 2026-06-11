# ############################################################################
# AI_HEADER: MODULE_PAYMENT_SCHEMA
# ROLE: Payment schemas
# DEPENDENCIES: pydantic, datetime
# GRACE_ANCHORS: [PAYMENT_SCHEMAS]
# WAVE: W-6.1
# ############################################################################

# START_MODULE_CONTRACT: M-PAYMENT-SCHEMA
# purpose: Define PaymentIntent and PaymentWebhook Pydantic schemas.
# owns:
#   - apps/api/app/schemas/payment.py
# inputs:
#   - none (type definitions)
# outputs:
#   - PaymentIntent, PaymentWebhook
# dependencies:
#   - pydantic.BaseModel
# side_effects:
#   - none (type-only module)
# END_MODULE_CONTRACT: M-PAYMENT-SCHEMA

# START_MODULE_MAP: M-PAYMENT-SCHEMA
# public_entrypoints:
#   - PaymentIntent
#   - PaymentWebhook
# semantic_blocks:
#   - PAYMENT_SCHEMAS: Pydantic models for payment endpoints
# END_MODULE_MAP: M-PAYMENT-SCHEMA

from pydantic import BaseModel


class PaymentIntent(BaseModel):
    """Payment intent for subscription."""
    amount: int  # In cents
    currency: str  # "RUB", "USD", etc
    description: str


class PaymentWebhook(BaseModel):
    """Webhook payload from payment provider."""
    event_type: str  # "payment.succeeded", "payment.failed"
    payment_id: str
    status: str
