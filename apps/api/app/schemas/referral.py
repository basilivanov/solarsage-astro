# ############################################################################
# AI_HEADER: MODULE_REFERRAL_SCHEMA
# ROLE: Referral request/response schemas
# DEPENDENCIES: pydantic, datetime
# GRACE_ANCHORS: [REFERRAL_SCHEMAS]
# WAVE: W-ACCESS.2
# ############################################################################

# START_MODULE_CONTRACT: M-REFERRAL-SCHEMA
# purpose: Define ReferralClaimRequest and ReferralClaimResponse Pydantic schemas.
# owns:
#   - apps/api/app/schemas/referral.py
# inputs:
#   - none (type definitions)
# outputs:
#   - ReferralClaimRequest, ReferralClaimResponse
# dependencies:
#   - pydantic.BaseModel
# side_effects:
#   - none (type-only module)
# END_MODULE_CONTRACT: M-REFERRAL-SCHEMA

# START_MODULE_MAP: M-REFERRAL-SCHEMA
# public_entrypoints:
#   - ReferralClaimRequest
#   - ReferralClaimResponse
# semantic_blocks:
#   - REFERRAL_SCHEMAS: Pydantic models for referral endpoints
# END_MODULE_MAP: M-REFERRAL-SCHEMA

from pydantic import BaseModel, Field


class ReferralClaimRequest(BaseModel):
    """Referral claim request."""
    referrer_code: str = Field(..., description="Referrer's invite code (tg_user_id)")


class ReferralClaimResponse(BaseModel):
    """Referral claim response."""
    success: bool
    days_granted: int
    access_until: str  # ISO date
    message: str


class ReferralInfo(BaseModel):
    """Referral info for profile display."""
    invite_code: str
    invite_url: str
    total_invited: int
    days_per_invite: int = 14
