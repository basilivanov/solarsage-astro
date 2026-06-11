# ############################################################################
# AI_HEADER: MODULE_API_REFERRAL
# ROLE: Referral info and claim endpoints
# DEPENDENCIES: fastapi, sqlalchemy, app.services.access_service
# GRACE_ANCHORS: [REFERRAL_INFO_ENDPOINT, REFERRAL_CLAIM_ENDPOINT]
# WAVE: W-ACCESS.2
# ############################################################################

# START_MODULE_CONTRACT: M-API-REFERRAL
# purpose: Get referral info and claim referral bonuses.
# owns:
#   - apps/api/app/api/referral.py
# inputs:
#   - GET /api/referral: user session
#   - POST /api/referral/claim: ReferralClaimRequest
# outputs:
#   - referral info or ReferralClaimResponse
# dependencies:
#   - M-ACCESS (AccessService)
#   - M-DB-SESSION
#   - M-AUTH-DEPENDENCIES
# side_effects:
#   - creates Referral rows
#   - grants access bonuses
# invariants:
#   - one claim per user
#   - cannot self-refer
# failure_policy:
#   - ALREADY_CLAIMED → 400
#   - INVALID_CODE → 400
#   - REFERRER_NOT_FOUND → 404
#   - SELF_REFERRAL → 400
# non_goals:
#   - no rate limiting
# END_MODULE_CONTRACT: M-API-REFERRAL

# START_MODULE_MAP: M-API-REFERRAL
# public_entrypoints:
#   - get_referral_info
#   - claim_referral
# semantic_blocks:
#   - REFERRAL_INFO_ENDPOINT: GET /api/referral
#   - REFERRAL_CLAIM_ENDPOINT: POST /api/referral/claim
# END_MODULE_MAP: M-API-REFERRAL

from datetime import UTC, date as Date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_session
from app.db.models import User, Referral
from app.db.session import get_session
from app.schemas.referral import ReferralClaimRequest, ReferralClaimResponse
from app.services.access_service import AccessService

router = APIRouter(prefix="/api/referral", tags=["referral"])


@router.get("")
async def get_referral_info(
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """Get user's referral info: invite code, invite URL, stats."""
    # Count referrals
    result = await db.execute(
        select(Referral).where(Referral.referrer_id == user.id)
    )
    referrals = result.scalars().all()

    invite_url = f"https://t.me/vi_astro_bot/app?startapp={user.tg_user_id}"

    return {
        "inviteCode": str(user.tg_user_id),
        "inviteUrl": invite_url,
        "totalInvited": len(referrals),
        "daysPerInvite": 14,
    }


@router.post("/claim")
async def claim_referral(
    request: ReferralClaimRequest,
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ReferralClaimResponse:
    """
    Claim referral bonus.

    Grants 14-day access bonus when user signs up via referral link.
    Can only be claimed once per user.
    """
    # Check if user already claimed referral
    result = await db.execute(
        select(Referral).where(Referral.invitee_id == user.id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail={"code": "ALREADY_CLAIMED", "message": "Referral bonus already claimed"}
        )

    # Find referrer by code (tg_user_id)
    try:
        referrer_tg_id = int(request.referrer_code)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_CODE", "message": "Invalid referrer code"}
        )

    result = await db.execute(
        select(User).where(User.tg_user_id == referrer_tg_id)
    )
    referrer = result.scalar_one_or_none()

    if not referrer:
        raise HTTPException(
            status_code=404,
            detail={"code": "REFERRER_NOT_FOUND", "message": "Referrer not found"}
        )

    if referrer.id == user.id:
        raise HTTPException(
            status_code=400,
            detail={"code": "SELF_REFERRAL", "message": "Cannot refer yourself"}
        )

    # Create referral record
    referral = Referral(
        referrer_id=referrer.id,
        invitee_id=user.id,
    )
    db.add(referral)

    # Grant 14-day bonus to BOTH
    access_service = AccessService(db)
    start_date = datetime.now(UTC).date()
    await access_service.grant_referral_bonus(user.id, start_date)
    await access_service.grant_referral_bonus(referrer.id, start_date)

    await db.commit()

    # Calculate access_until
    access_until = (start_date + timedelta(days=13)).isoformat()

    return ReferralClaimResponse(
        success=True,
        days_granted=14,
        access_until=access_until,
        message="Referral bonus granted! You have 14 days of full access.",
    )
