# ############################################################################
# AI_HEADER: MODULE_READINGS_API — authenticated published Today history route.
# ROLE: Exposes compact Readings day-history without invoking day calculation.
# ############################################################################

# START_MODULE_CONTRACT: M-API-READINGS
# purpose: Serve GET /api/readings/day-history from the owner snapshot index.
# owns:
#   - apps/api/app/api/readings.py
# inputs: authenticated session and limit query parameter in [1, 60].
# outputs: DayHistoryPayload with access projection and compact history items.
# dependencies: require_session, get_session, user local-date resolver,
#   TodayDayHistoryService.
# side_effects: database reads only; no sidecar, LLM, or cold day calculation.
# emitted_logs: none.
# invariants:
#   - missing/invalid session returns 401;
#   - limit defaults to 14 and FastAPI rejects values outside 1..60 with 422;
#   - local access date is resolved through the canonical resolver.
# failure_policy: invalid user timezone returns 422 INVALID_USER_TIMEZONE;
#   authentication and validation errors use standard FastAPI responses.
# END_MODULE_CONTRACT: M-API-READINGS

# START_MODULE_MAP: M-API-READINGS
# public_entrypoints:
#   - router
# semantic_blocks:
#   - ROUTE_DAY_HISTORY_GET: GET /api/readings/day-history handler.
# owned_tests:
#   - apps/api/tests/test_today_day_history_api.py
# END_MODULE_MAP: M-API-READINGS

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_session
from app.db.models import User
from app.db.session import get_session
from app.schemas.today_day_history import DayHistoryPayload
from app.services.today_day_history_service import TodayDayHistoryService
from app.services.user_local_date import UserLocalDateError, resolve_user_local_date

router = APIRouter(prefix="/api/readings", tags=["readings"])


# START_BLOCK: ROUTE_DAY_HISTORY_GET
@router.get("/day-history", response_model=DayHistoryPayload)
async def get_day_history(
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=60, description="Maximum number of history items")] = 14,
) -> DayHistoryPayload:
    # START_FUNCTION_CONTRACT: F-M-API-READINGS.get_day_history
    # purpose: Return compact owner-scoped published Today history.
    # inputs: limit query parameter, authenticated user, and DB session.
    # returns: DayHistoryPayload; locked access has no items.
    # side_effects: reads access and snapshot index; never starts calculation.
    # emitted_logs: none
    # error_behavior: 401 from require_session, 422 for limit/timezone validation.
    # END_FUNCTION_CONTRACT: F-M-API-READINGS.get_day_history
    try:
        access_date = resolve_user_local_date(user, datetime.now(UTC))
    except UserLocalDateError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_USER_TIMEZONE", "reason": exc.code},
        ) from None

    return await TodayDayHistoryService(db).get_day_history(
        user.id,
        limit=limit,
        access_date=access_date,
    )
# END_BLOCK: ROUTE_DAY_HISTORY_GET
