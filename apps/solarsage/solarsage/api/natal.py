
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

from ..schemas.natal import NatalRequest, NatalResponse, Planet, House, SpecialPoint
from ..services.natal import NatalService

router = APIRouter(prefix="/v1", tags=["natal"])

# Initialize service
natal_service = NatalService()


@router.post("/natal")
async def post_natal(request: NatalRequest) -> NatalResponse:
    """
    Calculate natal chart.

    W-SOLARSAGE-SVC: Uses NatalService.

    Returns planets, houses, and special points.
    """
    try:
        # Calculate natal chart using service
        chart = natal_service.calculate_natal_chart(
            date_str=request.birth_date,
            time_str=request.birth_time,
            tz_str=request.birth_tz,
            latitude=request.birth_lat,
            longitude=request.birth_lon,
        )

        # Convert to response schema
        planets = [Planet(**p) for p in chart.positions]
        houses = [House(**h) for h in chart.houses]
        special_points = [SpecialPoint(**sp) for sp in chart.special_points]

        return NatalResponse(
            planets=planets,
            houses=houses,
            special_points=special_points,
            house_system=chart.house_system,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")
