# AI_HEADER: MODULE_DAY_API
# module: M-DAY-SERVICE.api
# canon: docs/GRACE_CANON.md §6; docs/05_API_contracts_и_TodayPayload.md
# wave: W-NATAL-FULL (Wave 3 — day pipeline reuse)
# purpose: GET /api/day/:date endpoint returns TodayPayload.

# START_MODULE_CONTRACT: M-DAY-SERVICE.api
# purpose: HTTP surface for /api/day/:date. Returns TodayPayload for a given date.
#          W-3.4: real calculation pipeline via NatalContextService.
#          W-ACCESS.1: real access logic.
#          W-NATAL-FULL: day pipeline reuses cached natal context.
# owns:
#   - apps/api/app/api/day.py
# inputs:
#   - date_str: path parameter (YYYY-MM-DD or 'today')
#   - user: from require_session dependency
#   - db: AsyncSession
# outputs:
#   - TodayPayload
# dependencies:
#   - M-AUTH-TG.dependencies (require_session)
#   - M-DAY-SERVICE (TodayService)
#   - M-ACCESS (AccessService)
#   - M-DB-SESSION (get_session)
# invariants:
#   - 'today' resolves to current date (UTC for now, W-PROFILE.1 for timezone).
#   - Invalid date format → 400 INVALID_DATE.
#   - Not onboarded → 422 NOT_ONBOARDED.
#   - No auth → 401 (from require_session).
# failure_policy:
#   - HTTPException with code + message in detail.
# non_goals:
#   - timezone-aware 'today' resolution (W-PROFILE.1)
# END_MODULE_CONTRACT: M-DAY-SERVICE.api

# START_MODULE_MAP: M-DAY-SERVICE.api
# public_entrypoints:
#   - router
# semantic_blocks:
#   - ROUTE_DAY_GET: GET /api/day/:date handler
# owned_tests:
#   - apps/api/tests/test_day_endpoints.py (W-1.3)
# END_MODULE_MAP: M-DAY-SERVICE.api

from __future__ import annotations

from datetime import UTC, date as Date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_session
from app.db.models import User
from app.db.session import get_session
from app.schemas.today import TodayPayload
from app.services.access_service import AccessService
from app.services.today_service import TodayService

router = APIRouter(prefix="/api/day", tags=["day"])


# START_BLOCK: ROUTE_DAY_GET
@router.get("/{date_str}")
async def get_day(
    date_str: Annotated[str, Path(description="Date in YYYY-MM-DD format or 'today'")],
    user: Annotated[User, Depends(require_session)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> TodayPayload:
    # START_FUNCTION_CONTRACT: F-M-API-DAY.get_day
    # purpose: Get TodayPayload for a specific date.
    # inputs: date_str (str YYYY-MM-DD or 'today'), user (User), db (AsyncSession)
    # returns: TodayPayload with day status, signals, reading, etc.
    # side_effects: reads from DB, calls sidecar for transits, calls LLM
    # emitted_logs: none (TODO: W-1.6 — add day.viewed)
    # error_behavior: 400 INVALID_DATE, 422 NOT_ONBOARDED, 401 from require_session
    # END_FUNCTION_CONTRACT: F-M-API-DAY.get_day
    """
    Get TodayPayload for a specific date.

    W-3.4: real calculation pipeline via NatalContextService.
    W-ACCESS.1: real access logic.
    W-NATAL-FULL: day pipeline reuses cached natal context.
    """
    # Resolve 'today' to current date in user's timezone
    if date_str == "today":
        # TODO(W-PROFILE.1): use user.profile.current_location.timezone when available
        target_date = datetime.now(UTC).date()
    else:
        try:
            target_date = Date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_DATE", "message": f"Invalid date format: {date_str}"}
            )

    # Check if user is onboarded and has required birth data
    has_birth_coords = (
        user.profile.birth_lat is not None and user.profile.birth_lon is not None
    )
    if (not user.profile or
        not user.profile.is_onboarded or
        not has_birth_coords):
        raise HTTPException(
            status_code=422,
            detail={"code": "NOT_ONBOARDED", "message": "User must complete onboarding first"}
        )

    # Check access (real in W-ACCESS.1)
    access_service = AccessService(db)
    access_state = await access_service.can_access_day(user.id, target_date)

    # Get TodayPayload (fixture-backed in W-1.3, real in W-3.4)
    today_service = TodayService(db)
    payload = await today_service.get_today_payload(
        user_id=user.id,
        target_date=target_date,
        access_state=access_state
    )

    return payload
# END_BLOCK: ROUTE_DAY_GET
