# AI_HEADER
# module: M-DAY-SERVICE.api
# canon: docs/GRACE_CANON.md §6; docs/05_API_contracts_и_TodayPayload.md
# wave: W-1.3 (pilot wave)
# purpose: GET /api/day/:date endpoint returns fixture-backed TodayPayload.

# START_MODULE_CONTRACT: M-DAY-SERVICE.api
# purpose: HTTP surface for /api/day/:date. Returns TodayPayload for a given date.
#          W-1.3: fixture-backed, access stub returns state=full.
#          W-3.4: real calculation pipeline.
#          W-ACCESS.1: real access logic.
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
#   - 'today' resolves to current date in user's timezone (UTC in W-1.3).
#   - Invalid date format → 400 INVALID_DATE.
#   - Not onboarded → 422 NOT_ONBOARDED.
#   - No auth → 401 (from require_session).
# failure_policy:
#   - HTTPException with code + message in detail.
# non_goals:
#   - no caching (W-3.4)
#   - no timezone handling (W-PROFILE.1)
# END_MODULE_CONTRACT

# START_MODULE_MAP: M-DAY-SERVICE.api
# public_entrypoints:
#   - router
# semantic_blocks:
#   - ROUTE_DAY_GET: GET /api/day/:date handler
# owned_tests:
#   - apps/api/tests/test_day_endpoints.py (W-1.3)
# END_MODULE_MAP

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
    """
    Get TodayPayload for a specific date.

    W-1.3: fixture-backed, access stub returns state=full.
    W-3.4: real calculation pipeline.
    W-ACCESS.1: real access logic.
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
    print(f"[day.py] user.profile: {user.profile}")
    print(f"[day.py] is_onboarded: {user.profile.is_onboarded if user.profile else None}")
    print(f"[day.py] birth_lat: {user.profile.birth_lat if user.profile else None}")
    print(f"[day.py] birth_lon: {user.profile.birth_lon if user.profile else None}")

    if (not user.profile or
        not user.profile.is_onboarded or
        user.profile.birth_lat is None or
        user.profile.birth_lon is None):
        print(f"[day.py] NOT_ONBOARDED triggered")
        raise HTTPException(
            status_code=422,
            detail={"code": "NOT_ONBOARDED", "message": "User must complete onboarding first"}
        )

    print(f"[day.py] Onboarding check passed, proceeding...")

    # Check access (stub in W-1.3, real in W-ACCESS.1)
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
