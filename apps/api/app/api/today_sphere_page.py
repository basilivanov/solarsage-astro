# ############################################################################
# AI_HEADER: MODULE_API_TODAY-SPHERE-PAGE — authenticated static sphere route.
# ROLE: Exposes GET /api/spheres/{key} and maps typed service failures to the
#   existing stable HTTP error detail convention.
# ############################################################################

# START_MODULE_CONTRACT: M-API-TODAY-SPHERE-PAGE
# purpose: Serve the static two-layer sphere page for an authenticated user.
# owns:
#   - apps/api/app/api/today_sphere_page.py
# inputs: authenticated session, canonical sphere path key, and DB session.
# outputs: TodaySpherePagePayload.
# dependencies: require_session, get_session, TodaySpherePageService.
# side_effects: delegated profile/access reads, cache write, sidecar/LLM work.
# emitted_logs: delegated sphere natal generation events only.
# invariants:
#   - invalid spheres return 422 before downstream work;
#   - locked users receive 403 without page evidence;
#   - incomplete onboarding/profile returns 422 with stable detail code.
# failure_policy: typed service errors map to safe HTTP detail codes.
# END_MODULE_CONTRACT: M-API-TODAY-SPHERE-PAGE

# START_MODULE_MAP: M-API-TODAY-SPHERE-PAGE
# public_entrypoints:
#   - router
#   - get_sphere_page
# semantic_blocks:
#   - ROUTE_SPHERE_PAGE_GET: authenticated static sphere page route.
# owned_tests:
#   - apps/api/tests/test_today_sphere_page_api.py
# END_MODULE_MAP: M-API-TODAY-SPHERE-PAGE

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_session
from app.db.models import User
from app.db.session import get_session
from app.schemas.today_sphere_page import TodaySpherePagePayload
from app.services.today_sphere_page_service import (
    AccessRequiredError,
    InvalidSphereError,
    InvalidUserTimezoneError,
    ProfileIncompleteError,
    TodaySpherePageService,
)


router = APIRouter(prefix="/api/spheres", tags=["today-sphere-page"])


# START_BLOCK: ROUTE_SPHERE_PAGE_GET
@router.get("/{sphere_key}", response_model=TodaySpherePagePayload)
async def get_sphere_page(
    sphere_key: str = Path(..., description="Canonical sphere key"),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
) -> TodaySpherePagePayload:
    # START_FUNCTION_CONTRACT: F-M-API-TODAY-SPHERE-PAGE.get_sphere_page
    # purpose: Return the authenticated user's static sphere page.
    # inputs: canonical path key, authenticated user, and DB session.
    # returns: TodaySpherePagePayload.
    # side_effects: delegates profile/access/period/natal cache work.
    # emitted_logs: sphere.natal_generation_completed,
    #   sphere.natal_generation_failed.
    # error_behavior: 422 INVALID_SPHERE/NOT_ONBOARDED/INVALID_USER_TIMEZONE;
    #   403 ACCESS_REQUIRED; generation failures remain honest in the payload.
    # END_FUNCTION_CONTRACT: F-M-API-TODAY-SPHERE-PAGE.get_sphere_page
    try:
        return await TodaySpherePageService(db).get_page(user.id, sphere_key)
    except InvalidSphereError:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_SPHERE"},
        ) from None
    except ProfileIncompleteError as exc:
        detail: dict[str, object] = {
            "code": "NOT_ONBOARDED",
            "message": "User must complete onboarding first",
        }
        if exc.missing_fields:
            detail["missingFields"] = list(exc.missing_fields)
        raise HTTPException(status_code=422, detail=detail) from None
    except InvalidUserTimezoneError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_USER_TIMEZONE", "reason": str(exc)},
        ) from None
    except AccessRequiredError:
        raise HTTPException(
            status_code=403,
            detail={"code": "ACCESS_REQUIRED"},
        ) from None
# END_BLOCK: ROUTE_SPHERE_PAGE_GET
