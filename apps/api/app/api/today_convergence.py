# ############################################################################
# AI_HEADER: MODULE_API_TODAY-CONVERGENCE — authenticated snapshot impressions.
# ROLE: Exposes the packet-34 impression mutation without importing legacy Today routes.
# ############################################################################

# START_MODULE_CONTRACT: M-API-TODAY-CONVERGENCE
# purpose: Accept one authenticated day/lookahead snapshot impression and return no body.
# owns:
#   - apps/api/app/api/today_convergence.py
# inputs: Authenticated session, UUID snapshot path, strict impression request body.
# outputs: HTTP 204 on accepted/idempotent impression, uniform 404 otherwise.
# dependencies: require_session, DB session, TodaySnapshotService, TodaySnapshotImpressionRequest.
# side_effects: May commit one immutable first-seen timestamp and emit packet-34 events.
# emitted_logs: day.impression_recorded, day.impression_rejected, system.error.
# invariants: client supplies no identity/time/date/timezone; legacy Today types/routes are not imported.
# failure_policy: authentication/validation use FastAPI 401/422; missing/invalid relations use public 404.
# END_MODULE_CONTRACT: M-API-TODAY-CONVERGENCE

# START_MODULE_MAP: M-API-TODAY-CONVERGENCE
# public_entrypoints:
#   - router
# semantic_blocks:
#   - SNAPSHOT_IMPRESSION: authenticated POST snapshot impression.
# owned_tests:
#   - apps/api/tests/test_today_snapshot_impression_api.py
# END_MODULE_MAP: M-API-TODAY-CONVERGENCE

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_session
from app.db.models import User
from app.db.session import get_session
from app.schemas.today_convergence import TodaySnapshotImpressionRequest
from app.services.today_snapshot_service import TodaySnapshotService


router = APIRouter()


# START_BLOCK: SNAPSHOT_IMPRESSION
@router.post(
    "/api/day/snapshots/{snapshot_id}/impression",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def record_snapshot_impression(
    snapshot_id: UUID,
    body: TodaySnapshotImpressionRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
) -> Response:
    # START_FUNCTION_CONTRACT: F-M-API-TODAY-CONVERGENCE.record_snapshot_impression
    # purpose: Record one authenticated snapshot surface exposure.
    # inputs: UUID path, strict surface/source body, authenticated User, DB session.
    # returns: Empty HTTP 204 or uniform HTTP 404.
    # side_effects: Conditional first-seen update and structured service events.
    # emitted_logs: day.impression_recorded, day.impression_rejected, system.error.
    # error_behavior: None result becomes public 404 without existence details.
    # END_FUNCTION_CONTRACT: F-M-API-TODAY-CONVERGENCE.record_snapshot_impression
    result = await TodaySnapshotService(db).record_impression(
        user.id,
        snapshot_id,
        body.surface,
        source_snapshot_id=body.source_snapshot_id,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SNAPSHOT_NOT_FOUND", "message": "Snapshot not found"},
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
# END_BLOCK: SNAPSHOT_IMPRESSION


__all__ = ["router"]
