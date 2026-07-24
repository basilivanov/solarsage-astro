# AI_HEADER: MODULE_CONTRACTS_PROMO
# module: M-CONTRACTS.promo
# wave: W-NAMED-PROMO-CAMPAIGN
# purpose: Pydantic v2 schemas for promo code requests, offer previews, redemptions, grant summaries and error details.

# START_MODULE_CONTRACT: M-CONTRACTS.promo
# purpose: Provide Pydantic v2 CamelModel schemas for promo API endpoints.
# owns:
#   - apps/api/app/schemas/promo.py
# inputs: none
# outputs:
#   - PromoCodeRequest: request body containing writeOnly/password token (SecretStr)
#   - PromoOffer: promo offer display name and benefit configurations
#   - PromoPreviewResponse: offer preview data with profile completeness status
#   - PromoGrantSummary: summary of issued access, credit and natal grants
#   - PromoRedeemResponse: redemption response with offer and grant summary
#   - PromoErrorDetail: structured promo error detail with safe error code
# dependencies:
#   - app.schemas._base (CamelModel)
# side_effects: none (type definitions)
# emitted_logs: none
# invariants:
#   - all models inherit CamelModel with extra="forbid" and camelCase wire aliases
#   - PromoCodeRequest.token uses SecretStr without min_length, max_length or pattern validators
# failure_policy: Pydantic validation error on wire schema mismatches
# END_MODULE_CONTRACT: M-CONTRACTS.promo

# START_MODULE_MAP: M-CONTRACTS.promo
# public_entrypoints:
#   - PromoCodeRequest
#   - PromoOffer
#   - PromoPreviewResponse
#   - PromoGrantSummary
#   - PromoRedeemResponse
#   - PromoErrorDetail
# semantic_blocks:
#   - PROMO_SCHEMAS: Pydantic v2 wire models for promo campaign endpoints
# owned_tests:
#   - apps/api/tests/test_contract_registry.py
# END_MODULE_MAP: M-CONTRACTS.promo

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field, SecretStr

from ._base import CamelModel


# START_BLOCK: PROMO_SCHEMAS
class PromoCodeRequest(CamelModel):
    """Request payload containing opaque promo code token."""

    token: SecretStr = Field(
        ...,
        json_schema_extra={"writeOnly": True, "format": "password"},
        description="Opaque promo token",
    )


class PromoOffer(CamelModel):
    """Promo offer details and benefit configuration."""

    display_name: str = Field(..., max_length=120)
    access_days: int = Field(..., ge=0)
    bonus_credits: int = Field(..., ge=0)
    unlock_natal: bool


class PromoPreviewResponse(CamelModel):
    """Promo offer preview response with profile completeness status."""

    offer: PromoOffer
    profile_complete: bool


class PromoGrantSummary(CamelModel):
    """Summary of access, credit and natal grants issued by redemption."""

    access_starts_at: date | None = None
    access_until: date | None = None
    bonus_credits: int = Field(..., ge=0)
    bonus_credits_expires_at: datetime | None = None
    natal_unlocked: bool
    natal_already_owned: bool


class PromoRedeemResponse(CamelModel):
    """Promo redemption response containing offer and grant summary."""

    status: Literal["redeemed"] = "redeemed"
    offer: PromoOffer
    grants: PromoGrantSummary


class PromoErrorDetail(CamelModel):
    """Structured promo error detail with safe error code."""

    code: Literal[
        "INVALID_CODE",
        "CAMPAIGN_EXPIRED",
        "CAMPAIGN_FULL",
        "ALREADY_REDEEMED",
        "PROFILE_INCOMPLETE",
        "RATE_LIMITED",
    ]
    message: str
# END_BLOCK: PROMO_SCHEMAS
