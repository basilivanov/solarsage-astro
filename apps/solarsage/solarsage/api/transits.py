
# ############################################################################
# AI_HEADER: MODULE_API_TRANSITS
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ######################################### START_MODULE_CONTRACT
# purpose: HTTP routes for transits operations
# owns:
#   - apps/solarsage/solarsage/api/transits.py
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
# module: M-SIDECAR-API-TRANSITS
# wave: W-3.3, W-SOLARSAGE-SVC
# purpose: POST /v1/transits endpoint

from fastapi import APIRouter, HTTPException

from ..schemas.transits import TransitsRequest, TransitsResponse
from ..services.calculation_core import calculate_transits_response

router = APIRouter(prefix="/v1", tags=["transits"])


@router.post("/transits")
async def post_transits(request: TransitsRequest) -> TransitsResponse:
    """
    Calculate transit planets for target date.

    W-SOLARSAGE-SVC: Uses ephemeris utils.

    Returns planet positions at the specified moment.
    """
    try:
        return calculate_transits_response(
            target_date=request.target_date,
            target_time=request.target_time,
            target_tz=request.target_tz,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")
