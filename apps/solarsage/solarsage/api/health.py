
# ############################################################################
# AI_HEADER: MODULE_API_HEALTH
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Sidecar calculation — apps/solarsage/solarsage/api/health.py
# owns:
#   - apps/solarsage/solarsage/api/health.py
# inputs: varies
# outputs: varies
# dependencies: local modules
# side_effects: varies
# emitted_logs: n/a
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

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
