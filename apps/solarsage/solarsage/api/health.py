
# ############################################################################
# AI_HEADER: MODULE_API_HEALTH
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ######################################### START_MODULE_CONTRACT
# purpose: HTTP routes for health operations
# owns:
#   - apps/solarsage/solarsage/api/health.py
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
    Health check endpoint (v2).

    Returns 200 only when the pinned Swiss artifact verifies AND the engine
    probe returns FLG_SWIEPH (explicit moshier test mode reports
    engine="moshier", fallback=true).

    Returns 503 otherwise.
    """
    ok, error, identity = check_health()

    if not ok or identity is None:
        raise HTTPException(status_code=503, detail=error)

    return HealthResponse(
        ok=True,
        version=settings.git_sha,
        ephemeris_path=identity.ephemeris_path,
        calculation_version=settings.calculation_version,
        release_sha=settings.release_sha,
        ephemeris_artifact_id=identity.artifact_id,
        ephemeris_manifest_sha256=identity.manifest_sha256,
        engine=identity.engine,
        pyswisseph_version=identity.pyswisseph_version,
        swiss_data_version=identity.swiss_data_version,
        fallback=identity.fallback,
    )
