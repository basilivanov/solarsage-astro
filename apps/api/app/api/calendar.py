# ############################################################################
# AI_HEADER: MODULE_CALENDAR_API
# ROLE: GET /api/calendar endpoint — returns 3-month calendar grid.
# DEPENDENCIES: fastapi, app.services.calendar_service, app.core.dependencies
# GRACE_ANCHORS: [ROUTE_CALENDAR_GET, MONTH_VALIDATION, RANGE_CHECK]
# ############################################################################

# START_MODULE_CONTRACT: M-CALENDAR-API
# purpose: HTTP surface for GET /api/calendar?month=YYYY-MM.
#   Returns CalendarPayload for prev/current/next month grid.
#   W-1.4: neutral statuses, access stub.
#   W-4.3: real statuses from semantic layer.
#   W-ACCESS.1: real access logic.
# owns:
#   - apps/api/app/api/calendar.py
# inputs:
#   - month: query parameter (YYYY-MM format)
#   - user: from require_session dependency
#   - db: AsyncSession
# outputs:
#   - CalendarPayload
# dependencies:
#   - M-AUTH-TG.dependencies (require_session)
#   - M-CALENDAR-SERVICE (CalendarService)
#   - M-DB-SESSION (get_session)
# invariants:
#   - Month must be in YYYY-MM format
#   - Month must be within ±2 years from current date
#   - User must be onboarded
#   - Requires session cookie (401 if missing)
# failure_policy:
#   - Invalid month format → 400 INVALID_DATE
#   - Out of range → 400 INVALID_DATE
#   - Not onboarded → 422 NOT_ONBOARDED
#   - No auth → 401 (from require_session)
# non_goals:
#   - no caching (W-3.4)
#   - no timezone handling (W-PROFILE.1)
# END_MODULE_CONTRACT: M-CALENDAR-API

# START_MODULE_MAP: M-CALENDAR-API
# public_entrypoints:
#   - router
# semantic_blocks:
#   - ROUTE_CALENDAR_GET: GET /api/calendar handler
#   - MONTH_VALIDATION: validate month format
#   - RANGE_CHECK: check allowed range
# owned_tests:
#   - apps/api/tests/test_calendar_endpoints.py (W-1.4)
# END_MODULE_MAP: M-CALENDAR-API

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_session
from app.db.models import User
from app.db.session import get_session
from app.schemas.calendar import CalendarPayload
from app.services.calendar_service import CalendarService

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


# START_BLOCK: ROUTE_CALENDAR_GET
@router.get("")
async def get_calendar(
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> CalendarPayload:
    """
    Get 3-month calendar grid (prev/curr/next).

    W-1.4: neutral statuses (steady/supportive/tense rotation), access stub.
    W-4.3: real statuses from semantic layer.
    W-ACCESS.1: real access logic.
    """
    # START_BLOCK: MONTH_VALIDATION
    # Validate month format
    try:
        requested_date = datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_DATE", "message": f"Invalid month format: {month}. Expected YYYY-MM."}
        )
    # END_BLOCK: MONTH_VALIDATION

    # START_BLOCK: RANGE_CHECK
    # Check range (allow ±2 years from now)
    now = datetime.now(UTC)
    min_date = datetime(now.year - 2, 1, 1)
    max_date = datetime(now.year + 2, 12, 31)

    if requested_date < min_date or requested_date > max_date:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_DATE", "message": f"Month out of allowed range: {month}"}
        )
    # END_BLOCK: RANGE_CHECK

    # Check if user is onboarded
    if not user.profile or not user.profile.is_onboarded:
        raise HTTPException(
            status_code=422,
            detail={"code": "NOT_ONBOARDED", "message": "User must complete onboarding first"}
        )

    # Get calendar
    calendar_service = CalendarService(db)
    payload = await calendar_service.get_calendar(
        user_id=user.id,
        month=month
    )

    return payload
# END_BLOCK: ROUTE_CALENDAR_GET
