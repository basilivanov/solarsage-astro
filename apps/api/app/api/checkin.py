# ############################################################################
# AI_HEADER: MODULE_API_CHECKIN
# ROLE: Evening checkin endpoints
# DEPENDENCIES: fastapi, sqlalchemy, app.services.checkin_service
# GRACE_ANCHORS: [CHECKIN_CREATE, CHECKIN_YESTERDAY, CHECKIN_METRICS, CHECKIN_GET_BY_DATE, CHECKIN_REMINDER]
# ############################################################################

# START_MODULE_CONTRACT: M-API-CHECKIN
# purpose: Evening checkin API surface.
# owns:
#   - apps/api/app/api/checkin.py
# inputs:
#   - POST /api/checkin: CheckinCreate
#   - GET /api/checkin/yesterday
#   - GET /api/checkin/metrics
#   - GET /api/checkin/{target_date}
#   - POST /api/checkin/send-reminder
# outputs:
#   - CheckinResponse, YesterdayCheckinResponse, CheckinMetrics
# dependencies:
#   - M-CHECKIN-SERVICE
#   - M-DB-SESSION
#   - M-AUTH-DEPENDENCIES
# side_effects:
#   - creates/updates EveningCheckin rows
# emitted_logs: checkin.submitted
# failure_policy: 400/401 standard FastAPI exceptions
# END_MODULE_CONTRACT: M-API-CHECKIN

# START_MODULE_MAP: M-API-CHECKIN
# public_entrypoints:
#   - router
# semantic_blocks:
#   - CHECKIN_CREATE: POST /api/checkin endpoint
#   - CHECKIN_YESTERDAY: GET /api/checkin/yesterday endpoint
#   - CHECKIN_METRICS: GET /api/checkin/metrics endpoint
#   - CHECKIN_GET_BY_DATE: GET /api/checkin/{target_date} endpoint
#   - CHECKIN_REMINDER: POST /api/checkin/send-reminder endpoint
# owned_tests:
#   - apps/api/tests/test_checkin_endpoints.py
#   - apps/api/tests/test_checkin.py
#   - apps/api/tests/test_checkin_snapshot_lineage.py
# END_MODULE_MAP: M-API-CHECKIN

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_session
from app.core.logging import log_event
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


# START_BLOCK: CHECKIN_CREATE
@router.post("/api/checkin", response_model=CheckinResponse)
async def create_checkin(
    checkin: CheckinCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
) -> CheckinResponse:
    # START_FUNCTION_CONTRACT: F-M-API-CHECKIN.create_checkin
    # purpose: Submit or update evening checkin for target_date.
    # inputs: checkin (CheckinCreate), db (AsyncSession), user (User)
    # returns: CheckinResponse
    # side_effects: inserts/updates EveningCheckin through CheckinService; emits checkin.submitted
    # emitted_logs: checkin.submitted
    # error_behavior: 400/401 standard FastAPI error
    # END_FUNCTION_CONTRACT: F-M-API-CHECKIN.create_checkin
    service = CheckinService(db)
    result = await service.create_checkin(
        user_id=user.id,
        target_date=checkin.target_date,
        mood=checkin.mood,
        accuracy=checkin.accuracy,
        energy=checkin.energy,
        tags=checkin.tags,
        note=checkin.note,
        observed_spheres=checkin.observed_spheres,
    )
    log_event("checkin.submitted", payload={
        "has_accuracy": checkin.accuracy is not None,
        "has_note": bool(checkin.note and checkin.note.strip()),
        "source": "webapp",
    })
    return service.to_response(result)
# END_BLOCK: CHECKIN_CREATE


# START_BLOCK: CHECKIN_YESTERDAY
@router.get("/api/checkin/yesterday", response_model=YesterdayCheckinResponse)
async def get_yesterday_checkin(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
) -> YesterdayCheckinResponse:
    # START_FUNCTION_CONTRACT: F-M-API-CHECKIN.get_yesterday_checkin
    # purpose: Retrieve checkin for user's local yesterday date.
    # inputs: db (AsyncSession), user (User)
    # returns: YesterdayCheckinResponse
    # side_effects: none
    # error_behavior: 401 if unauthenticated
    # END_FUNCTION_CONTRACT: F-M-API-CHECKIN.get_yesterday_checkin
    service = CheckinService(db)
    target_date = await service.local_yesterday(user)
    result = await service.get_checkin(user.id, target_date)
    if result is None:
        return YesterdayCheckinResponse(had_checkin=False, checkin=None)
    return YesterdayCheckinResponse(
        had_checkin=True,
        checkin=service.to_response(result),
    )
# END_BLOCK: CHECKIN_YESTERDAY


# START_BLOCK: CHECKIN_METRICS
@router.get("/api/checkin/metrics", response_model=CheckinMetrics)
async def get_checkin_metrics(
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
) -> CheckinMetrics:
    # START_FUNCTION_CONTRACT: F-M-API-CHECKIN.get_checkin_metrics
    # purpose: Retrieve aggregated checkin statistics and history for date range.
    # inputs: from_date, to_date, db, user
    # returns: CheckinMetrics
    # side_effects: none
    # error_behavior: 401 if unauthenticated
    # END_FUNCTION_CONTRACT: F-M-API-CHECKIN.get_checkin_metrics
    service = CheckinService(db)
    return await service.metrics(
        user.id,
        from_date,
        to_date,
        fallback_to_date=await service.local_today(user),
    )
# END_BLOCK: CHECKIN_METRICS


# START_BLOCK: CHECKIN_GET_BY_DATE
@router.get("/api/checkin/{target_date}")
async def get_checkin(
    target_date: date,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    # START_FUNCTION_CONTRACT: F-M-API-CHECKIN.get_checkin
    # purpose: Retrieve checkin record for specific target date.
    # inputs: target_date (date), db (AsyncSession), user (User)
    # returns: dict with checkin or None
    # side_effects: none
    # error_behavior: 401 if unauthenticated
    # END_FUNCTION_CONTRACT: F-M-API-CHECKIN.get_checkin
    service = CheckinService(db)
    result = await service.get_checkin(user.id, target_date)
    if result is None:
        return {"checkin": None}
    return service.to_response(result)
# END_BLOCK: CHECKIN_GET_BY_DATE


# START_BLOCK: CHECKIN_REMINDER
@router.post("/api/checkin/send-reminder")
async def send_checkin_reminder(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    # START_FUNCTION_CONTRACT: F-M-API-CHECKIN.send_checkin_reminder
    # purpose: Check if checkin is missing for today and send reminder.
    # inputs: db (AsyncSession), user (User)
    # returns: dict with status
    # side_effects: none
    # error_behavior: 401 if unauthenticated
    # END_FUNCTION_CONTRACT: F-M-API-CHECKIN.send_checkin_reminder
    service = CheckinService(db)
    today = await service.local_today(user)
    checkin = await service.get_checkin(user.id, today)
    if checkin:
        return {"sent": False, "reason": "Already checked in"}
    return {"sent": True, "message": "Reminder sent"}
# END_BLOCK: CHECKIN_REMINDER
