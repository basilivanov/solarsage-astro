# AI_HEADER
# module: M-REFERRAL-API
# wave: W-ACCESS.2
# purpose: POST /api/referral/claim endpoint

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
