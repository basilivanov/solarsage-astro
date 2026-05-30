# AI_HEADER
# module: M-SIDECAR-API-TRANSITS
# wave: W-3.3, W-SOLARSAGE-SVC
# purpose: POST /v1/transits endpoint

from fastapi import APIRouter, HTTPException

from ..schemas.transits import TransitsRequest, TransitsResponse
from ..schemas.natal import Planet
from ..utils.ephemeris import calculate_julian_day, calculate_positions

router = APIRouter(prefix="/v1", tags=["transits"])


@router.post("/transits")
async def post_transits(request: TransitsRequest) -> TransitsResponse:
    """
    Calculate transit planets for target date.

    W-SOLARSAGE-SVC: Uses ephemeris utils.

    Returns planet positions at the specified moment.
    """
    try:
        # Calculate Julian Day for target date
        jd = calculate_julian_day(
            request.target_date,
            request.target_time,
            request.target_tz
        )

        # Calculate transit planets
        planets_data = calculate_positions(jd)
        planets = [Planet(**p) for p in planets_data]

        return TransitsResponse(
            planets=planets,
            target_jd=jd,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation failed: {str(e)}")
