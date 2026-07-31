# ############################################################################
# AI_HEADER: MODULE_API_TODAY-SPHERE-DRILLDOWN — authenticated deterministic sphere route.
# ROLE: Exposes GET /api/day/snapshots/{id}/spheres/{key} with owner and
#   full-access authorization.
# ############################################################################

# START_MODULE_CONTRACT: M-API-TODAY-SPHERE-DRILLDOWN
# purpose: Serve deterministic sphere evidence from a published Today snapshot.
# owns:
#   - apps/api/app/api/today_sphere_drilldown.py
# inputs: authenticated session, snapshot UUID, and canonical sphere path key.
# outputs: TodaySphereDrilldownPayload.
# dependencies: require_session, get_session, TodaySphereDrilldownService.
# side_effects: database reads only; no sidecar, LLM, or calculation calls.
# emitted_logs: none.
# invariants:
#   - foreign/missing/unpublished snapshots have the same 404 response;
#   - preview/locked access returns 403 without evidence;
#   - invalid sphere keys return 422.
# failure_policy: typed service errors map to stable HTTP detail codes.
# END_MODULE_CONTRACT: M-API-TODAY-SPHERE-DRILLDOWN

# START_MODULE_MAP: M-API-TODAY-SPHERE-DRILLDOWN
# public_entrypoints:
#   - router
#   - get_sphere_drilldown
# semantic_blocks:
#   - ROUTE_SPHERE_DRILLDOWN_GET: authenticated snapshot sphere route.
# owned_tests:
#   - apps/api/tests/test_today_sphere_drilldown_api.py
# END_MODULE_MAP: M-API-TODAY-SPHERE-DRILLDOWN

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_session
from app.db.models import User
from app.db.session import get_session
from app.schemas.today_sphere_drilldown import TodaySphereDrilldownPayload
from app.services.today_sphere_drilldown_service import (
    AccessRequiredError,
    InvalidSphereError,
    SnapshotNotFoundError,
    SphereNotInSnapshotError,
    TodaySphereDrilldownService,
)


router = APIRouter(prefix="/api/day/snapshots", tags=["today-sphere-drilldown"])


# START_BLOCK: ROUTE_SPHERE_DRILLDOWN_GET
@router.get("/{snapshot_id}/spheres/{sphere_key}", response_model=TodaySphereDrilldownPayload)
async def get_sphere_drilldown(
    snapshot_id: UUID = Path(..., description="Published Today snapshot UUID"),
    sphere_key: str = Path(..., description="Canonical sphere key"),
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
) -> TodaySphereDrilldownPayload:
    # START_FUNCTION_CONTRACT: F-M-API-TODAY-SPHERE-DRILLDOWN.get_sphere_drilldown
    # purpose: Return owner/full-access deterministic evidence for one sphere.
    # inputs: snapshot_id, sphere_key, authenticated user, and DB session.
    # returns: TodaySphereDrilldownPayload.
    # side_effects: reads snapshot and access ledger; never starts calculation.
    # emitted_logs: none.
    # error_behavior: 422 invalid sphere, 403 insufficient access, 404 hidden
    #   snapshot/sphere details.
    # END_FUNCTION_CONTRACT: F-M-API-TODAY-SPHERE-DRILLDOWN.get_sphere_drilldown
    try:
        return await TodaySphereDrilldownService(db).get_drilldown(
            user.id,
            snapshot_id,
            sphere_key,
        )
    except InvalidSphereError:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_SPHERE"},
        ) from None
    except AccessRequiredError:
        raise HTTPException(
            status_code=403,
            detail={"code": "ACCESS_REQUIRED"},
        ) from None
    except SphereNotInSnapshotError:
        raise HTTPException(
            status_code=404,
            detail={"code": "SPHERE_NOT_IN_SNAPSHOT"},
        ) from None
    except SnapshotNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "snapshot_not_found"},
        ) from None
# END_BLOCK: ROUTE_SPHERE_DRILLDOWN_GET

