from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_session
from app.db.models import User
from app.db.session import get_session
from app.schemas.checkin import (
    CheckinCreate,
    CheckinMetrics,
    CheckinResponse,
    YesterdayCheckinResponse,
)
from app.services.checkin_service import CheckinService

router = APIRouter()


@router.post("/api/checkin", response_model=CheckinResponse)
async def create_checkin(
    checkin: CheckinCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
) -> CheckinResponse:
    service = CheckinService(db)
    result = await service.create_checkin(
        user_id=user.id,
        target_date=checkin.target_date,
        mood=checkin.mood,
        accuracy=checkin.accuracy,
        energy=checkin.energy,
        tags=checkin.tags,
        note=checkin.note,
    )
    return service.to_response(result)


@router.get("/api/checkin/yesterday", response_model=YesterdayCheckinResponse)
async def get_yesterday_checkin(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
) -> YesterdayCheckinResponse:
    service = CheckinService(db)
    target_date = await service.local_yesterday(user)
    result = await service.get_checkin(user.id, target_date)
    if result is None:
        return YesterdayCheckinResponse(had_checkin=False, checkin=None)
    return YesterdayCheckinResponse(
        had_checkin=True,
        checkin=service.to_response(result),
    )


@router.get("/api/checkin/metrics", response_model=CheckinMetrics)
async def get_checkin_metrics(
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
) -> CheckinMetrics:
    service = CheckinService(db)
    return await service.metrics(
        user.id,
        from_date,
        to_date,
        fallback_to_date=await service.local_today(user),
    )


@router.get("/api/checkin/{target_date}")
async def get_checkin(
    target_date: date,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    service = CheckinService(db)
    result = await service.get_checkin(user.id, target_date)
    if result is None:
        return {"checkin": None}
    return service.to_response(result)


@router.post("/api/checkin/send-reminder")
async def send_checkin_reminder(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    service = CheckinService(db)
    today = await service.local_today(user)
    checkin = await service.get_checkin(user.id, today)
    if checkin:
        return {"sent": False, "reason": "Already checked in"}
    return {"sent": True, "message": "Reminder sent"}
