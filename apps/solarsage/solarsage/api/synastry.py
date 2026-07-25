# ############################################################################
# AI_HEADER: MODULE_API_SYNASTRY
# ROLE: Sidecar calculation HTTP router for synastry (/v1/synastry)
# DEPENDENCIES: fastapi, solarsage.schemas.synastry, solarsage.services.synastry
# GRACE_ANCHORS: []
# ############################################################################

# START_MODULE_CONTRACT: M-SIDECAR-API-SYNASTRY
# purpose: HTTP router for POST /v1/synastry calculation endpoint.
# owns:
#   - apps/solarsage/solarsage/api/synastry.py
# inputs: SynastryRequest
# outputs: SynastryResponse
# dependencies: solarsage.schemas.synastry, solarsage.services.synastry
# side_effects: Ephemeris calculation
# emitted_logs: none
# invariants:
#   - Additive only: natal/transits routes untouched
# failure_policy: FastAPI HTTP 400/500
# END_MODULE_CONTRACT: M-SIDECAR-API-SYNASTRY

# START_MODULE_MAP: M-SIDECAR-API-SYNASTRY
# public_entrypoints:
#   - router
# semantic_blocks: none
# owned_tests: none
# END_MODULE_MAP: M-SIDECAR-API-SYNASTRY

from fastapi import APIRouter, HTTPException
from ..schemas.synastry import SynastryRequest, SynastryResponse
from ..services.synastry import SynastryService

router = APIRouter(prefix="/v1", tags=["synastry"])

synastry_service = SynastryService()


@router.post("/synastry", response_model=SynastryResponse)
async def post_synastry(request: SynastryRequest) -> SynastryResponse:
    """Calculate synastry cross-aspects and partner chart positions."""
    try:
        return synastry_service.calculate_synastry(request)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Synastry calculation failed: {exc}",
        ) from exc
