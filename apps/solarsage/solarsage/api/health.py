# AI_HEADER
# module: M-SIDECAR-API-HEALTH
# wave: W-3.1
# purpose: GET /v1/health endpoint

from fastapi import APIRouter, HTTPException

from ..core.config import settings
from ..core.health import check_health
from ..schemas.health import HealthResponse

router = APIRouter(prefix="/v1", tags=["health"])


@router.get("/health")
async def get_health() -> HealthResponse:
    """
    Health check endpoint.

    Returns 200 if:
    - Ephemeris path exists
    - Probe calculation succeeds (W-3.2)

    Returns 503 otherwise.
    """
    ok, error = check_health()

    if not ok:
        raise HTTPException(status_code=503, detail=error)

    return HealthResponse(
        ok=True,
        version=settings.git_sha,
        ephemeris_path=settings.ephemeris_path,
        calculation_version=settings.calculation_version,
    )
