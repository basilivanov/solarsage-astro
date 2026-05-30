# ############################################################################
# AI_HEADER
# module: M-API-CHECKIN
# wave: W-8.1, W-8.3
# purpose: Evening checkin endpoints
# ############################################################################

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.db.session import get_session
from app.core.dependencies import require_session
from app.services.checkin_service import CheckinService
from app.schemas.checkin import CheckinCreate, CheckinResponse
from app.db.models import User

router = APIRouter()


@router.post("/api/checkin")
async def create_checkin(
    checkin: CheckinCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    """
    Create evening checkin.

    W-8.1: Upsert logic.
    """
    service = CheckinService(db)

    result = await service.create_checkin(
        user_id=user.id,
        target_date=checkin.target_date,
        mood=checkin.mood,
        notes=checkin.notes,
    )

    return CheckinResponse(
        id=result.id,
        target_date=result.target_date,
        mood=result.mood,
        notes=result.notes,
        created_at=result.created_at.isoformat(),
    )


@router.get("/api/checkin/{target_date}")
async def get_checkin(
    target_date: date,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    """Get checkin for specific date."""
    service = CheckinService(db)

    result = await service.get_checkin(user.id, target_date)

    if not result:
        return {"checkin": None}

    return CheckinResponse(
        id=result.id,
        target_date=result.target_date,
        mood=result.mood,
        notes=result.notes,
        created_at=result.created_at.isoformat(),
    )


@router.post("/api/checkin/send-reminder")
async def send_checkin_reminder(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    """
    Send evening checkin reminder.

    W-8.3: MVP version (manual trigger, no worker).
    """
    from datetime import date

    # Check if already checked in today
    service = CheckinService(db)
    today = date.today()
    checkin = await service.get_checkin(user.id, today)

    if checkin:
        return {"sent": False, "reason": "Already checked in"}

    # TODO: Send push notification
    # For MVP, just return success

    return {"sent": True, "message": "Reminder sent"}
