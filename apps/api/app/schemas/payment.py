# AI_HEADER
# module: M-PAYMENT-SCHEMA
# wave: W-6.1
# purpose: Payment schemas

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
