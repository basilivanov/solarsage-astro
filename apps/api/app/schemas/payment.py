# ############################################################################
# AI_HEADER: MODULE_PAYMENT_SCHEMA — billing/payment API schemas.
# ROLE: Public wire contracts for products, subscription start/status/cancel,
#       one-time purchase start and the YooKassa webhook envelope.
# DEPENDENCIES: pydantic, app.schemas._base.CamelModel
# GRACE_ANCHORS: [BILLING_SCHEMAS]
# ############################################################################

# START_MODULE_CONTRACT: M-PAYMENT-SCHEMA
# purpose: Typed request/response contracts for the billing endpoints.
# owns:
#   - apps/api/app/schemas/payment.py
# inputs: none (type definitions)
# outputs: ProductRead, SubscriptionStart*, SubscriptionStatus*, SubscriptionCancel*,
#   PurchaseStart*, PurchaseStatusResponse, ProductsListResponse, YooKassaWebhookEvent
# dependencies: pydantic, CamelModel
# side_effects: none (type-only module)
# emitted_logs: none
# invariants:
#   - Wire-facing schemas stay camelCase via CamelModel where applicable.
#   - The webhook envelope is permissive (payload is never trusted; the real
#     verification is the authenticated provider GET, not this schema).
# failure_policy: validation errors bubble to FastAPI 422.
# END_MODULE_CONTRACT: M-PAYMENT-SCHEMA

# START_MODULE_MAP: M-PAYMENT-SCHEMA
# public_entrypoints:
#   - ProductRead
#   - SubscriptionStartRequest / SubscriptionStartResponse
#   - SubscriptionStatusResponse
#   - SubscriptionCancelRequest / SubscriptionCancelResponse
#   - PurchaseStartRequest / PurchaseStartResponse
#   - PurchaseStatusResponse
#   - ProductsListResponse
#   - YooKassaWebhookEvent
# semantic_blocks:
#   - BILLING_SCHEMAS: Pydantic models for billing endpoints
# END_MODULE_MAP: M-PAYMENT-SCHEMA

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ._base import CamelModel


# ---- Catalog ----

class ProductRead(CamelModel):
    slug: str
    name: str
    description: str | None = None
    product_type: Literal["subscription_recurrent", "one_time"]
    price_kopecks: int
    currency: str
    period_days: int | None = None
    horary_quota: int | None = None


class ProductsListResponse(CamelModel):
    products: list[ProductRead]


# ---- Subscription ----

class SubscriptionStartRequest(CamelModel):
    product_slug: Literal["subscription_month", "subscription_year"] = "subscription_month"


class SubscriptionStartResponse(CamelModel):
    subscription_id: UUID
    product_slug: str
    provider_payment_id: str
    confirmation_url: str | None = None
    status: str


class SubscriptionStatusResponse(CamelModel):
    subscription_id: UUID | None = None
    product_slug: str | None = None
    status: Literal["none", "pending", "active", "past_due", "canceled", "expired"]
    price_kopecks: int | None = None
    currency: str | None = None
    current_period_end: str | None = None
    next_charge_at: str | None = None
    has_access: bool
    access_until: str | None = None
    # Backend-computed state machine fields (the UI never derives these):
    # renewing = live (active/past_due) with a saved method AND a scheduled
    # next charge; cancelable = a real recurring enrollment exists that the
    # cancel endpoint meaningfully cancels (active/past_due with a method).
    renewing: bool = False
    cancelable: bool = False


class SubscriptionCancelRequest(CamelModel):
    reason: str | None = None


class SubscriptionCancelResponse(CamelModel):
    subscription_id: UUID | None
    status: str


# ---- One-time purchase ----

class PurchaseStartRequest(CamelModel):
    product_slug: Literal[
        "natal_full_report",
        "horary_1", "horary_3", "horary_5", "horary_10",
        "election_1", "synastry",
    ]


class PurchaseStartResponse(CamelModel):
    purchase_id: UUID
    product_slug: str
    provider_payment_id: str
    confirmation_url: str | None = None
    status: str


class PurchaseStatusResponse(CamelModel):
    # Authenticated owner-only status read for the polling flow. NEVER calls
    # the provider: answers strictly from local rows. confirmation_url is
    # exposed only while the payment is still pending.
    purchase_id: UUID
    product_slug: str
    status: str  # pending | succeeded | consumed | delivered | canceled
    provider_payment_id: str | None = None
    confirmation_url: str | None = None


# ---- Webhook envelope (permissive; real verification is provider GET) ----

class YooKassaWebhookEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str | None = None
    event: str
    object: dict
