# AI_HEADER
# module: M-REFERRAL-SCHEMA
# wave: W-ACCESS.2
# purpose: Referral request/response schemas

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
