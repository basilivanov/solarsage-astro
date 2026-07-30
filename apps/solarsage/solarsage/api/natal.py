
# ############################################################################
# AI_HEADER: MODULE_API_NATAL
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ######################################### START_MODULE_CONTRACT
# purpose: HTTP routes for natal operations
# owns:
#   - apps/solarsage/solarsage/api/natal.py
# inputs: HTTP request, path/query params
# outputs: HTTP response / JSON body
# dependencies: local modules
# side_effects: Processes HTTP requests
# emitted_logs: n/a (pure)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# AI_HEADER
# module: M-SIDECAR-API-NATAL
# wave: W-3.2, W-SOLARSAGE-SVC
# purpose: POST /v1/natal endpoint

from fastapi import APIRouter, HTTPException

from ..schemas.natal import NatalRequest, NatalResponse
from ..services.calculation_core import calculate_natal_response

router = APIRouter(prefix="/v1", tags=["natal"])

@router.post("/natal")
async def post_natal(request: NatalRequest) -> NatalResponse:
    """
    Calculate natal chart.

    W-SOLARSAGE-SVC: Uses NatalService.

    Returns planets, houses, and special points.
    """
    try:
        return calculate_natal_response(
            birth_date=request.birth_date,
            birth_time=request.birth_time,
            birth_lat=request.birth_lat,
            birth_lon=request.birth_lon,
            birth_tz=request.birth_tz,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")
