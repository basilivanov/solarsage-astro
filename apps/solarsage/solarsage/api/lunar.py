# ############################################################################
# AI_HEADER: MODULE_API_LUNAR
# ROLE: Sidecar calculation API for lunar window
# DEPENDENCIES: fastapi
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ######################################### START_MODULE_CONTRACT
# purpose: HTTP routes for lunar calculations
# owns:
#   - apps/solarsage/solarsage/api/lunar.py
# inputs: LunarWindowRequest
# outputs: LunarWindowResponse
# dependencies: LunarService
# side_effects: Ephemeris calculations
# emitted_logs: n/a (pure)
# failure_policy: 422 on invalid date range
# END_MODULE_CONTRACT

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..schemas.lunar import LunarWindowRequest, LunarWindowResponse
from ..services.lunar import LunarService

router = APIRouter(prefix="/v1", tags=["lunar"])
lunar_service = LunarService()


@router.post("/lunar-window", response_model=LunarWindowResponse)
async def post_lunar_window(request: LunarWindowRequest) -> LunarWindowResponse:
    """Calculate daily lunar window details for date range (max 62 days)."""
    if request.to_date < request.from_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="to_date must be on or after from_date",
        )

    try:
        days = lunar_service.compute_window(request.from_date, request.to_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return LunarWindowResponse(days=days)
