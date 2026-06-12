# ############################################################################
# ############################################################################
# AI_HEADER: MODULE_API_CHECKIN
# ROLE: Evening checkin endpoints — create, get, send reminder.
# DEPENDENCIES: fastapi, sqlalchemy, app.services.checkin_service
# GRACE_ANCHORS: [CREATE_CHECKIN_ENDPOINT, GET_CHECKIN_ENDPOINT, SEND_REMINDER_ENDPOINT]
# WAVE: W-8.1, W-8.3
# ############################################################################

# START_MODULE_CONTRACT: M-API-CHECKIN
# purpose: Create, get, and send reminders for evening checkins.
# owns:
#   - apps/api/app/api/checkin.py
# inputs:
#   - POST /api/checkin: checkin data
#   - GET /api/checkin/{target_date}: date
#   - POST /api/checkin/send-reminder: none
# outputs:
#   - CheckinResponse or {"checkin": None} or {"sent": bool}
# dependencies:
#   - M-CHECKIN-SERVICE
#   - M-DB-SESSION
#   - M-AUTH-DEPENDENCIES
# side_effects:
#   - creates/updates checkin rows
# invariants:
#   - requires authentication
# failure_policy:
#   - 401 if not authenticated
# non_goals:
#   - no push notification integration (MVP stub)
# END_MODULE_CONTRACT: M-API-CHECKIN

# START_MODULE_MAP: M-API-CHECKIN
# public_entrypoints:
#   - create_checkin
#   - get_checkin
#   - send_checkin_reminder
# semantic_blocks:
#   - CREATE_CHECKIN_ENDPOINT: POST /api/checkin
#   - GET_CHECKIN_ENDPOINT: GET /api/checkin/{target_date}
#   - SEND_REMINDER_ENDPOINT: POST /api/checkin/send-reminder
# END_MODULE_MAP: M-API-CHECKIN

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from app.db.session import get_session
from app.core.dependencies import require_session
from app.services.checkin_service import CheckinService
from app.schemas.checkin import CheckinCreate, CheckinResponse
from app.db.models import User

router = APIRouter()


# START_BLOCK: CREATE_CHECKIN_ENDPOINT
@router.post("/api/checkin")
async def create_checkin(
    checkin: CheckinCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    # START_FUNCTION_CONTRACT: F-M-API-CHECKIN.create_checkin
    # purpose: Create or update evening checkin (upsert).
    # inputs: checkin (CheckinCreate), db session, authenticated user
    # returns: CheckinResponse with id, date, mood, notes
    # side_effects: creates/updates row in evening_checkins table
    # emitted_logs: none
    # error_behavior: 401 if not authenticated (from require_session)
    # END_FUNCTION_CONTRACT: F-M-API-CHECKIN.create_checkin
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


# END_BLOCK: CREATE_CHECKIN_ENDPOINT

# START_BLOCK: GET_CHECKIN_ENDPOINT
@router.get("/api/checkin/{target_date}")
async def get_checkin(
    target_date: date,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    # START_FUNCTION_CONTRACT: F-M-API-CHECKIN.get_checkin
    # purpose: Get checkin for specific date.
    # inputs: target_date, db session, authenticated user
    # returns: CheckinResponse or {"checkin": None}
    # side_effects: reads from DB
    # emitted_logs: none
    # error_behavior: 401 if not authenticated (from require_session)
    # END_FUNCTION_CONTRACT: F-M-API-CHECKIN.get_checkin
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


# END_BLOCK: GET_CHECKIN_ENDPOINT

# START_BLOCK: SEND_REMINDER_ENDPOINT
@router.post("/api/checkin/send-reminder")
async def send_checkin_reminder(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    # START_FUNCTION_CONTRACT: F-M-API-CHECKIN.send_checkin_reminder
    # purpose: Send evening checkin reminder (MVP stub).
    # inputs: db session, authenticated user
    # returns: {"sent": bool, "reason": str} or {"sent": bool, "message": str}
    # side_effects: reads from DB to check existing checkin
    # emitted_logs: none
    # error_behavior: 401 if not authenticated (from require_session)
    # END_FUNCTION_CONTRACT: F-M-API-CHECKIN.send_checkin_reminder
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
# END_BLOCK: SEND_REMINDER_ENDPOINT
