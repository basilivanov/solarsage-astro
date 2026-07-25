# ############################################################################
# AI_HEADER: MODULE_API_ACCESS
# ROLE: Authenticated HTTP surface for the current user's access summary
# DEPENDENCIES: fastapi, app.services.access_service
# GRACE_ANCHORS: [ROUTE_ACCESS_GET]
# SLICE: SLICE-BACKEND-API-ROUTERS
# ############################################################################

# START_MODULE_CONTRACT: M-API-ACCESS
# purpose: Expose GET /api/access endpoint returning current user's access summary.
# owns:
#   - apps/api/app/api/access.py
# inputs: user_id from current_user_id, DB session
# outputs: AccessSummary
# dependencies:
#   - M-ACCESS-SERVICE (AccessService)
#   - M-DB-SESSION
# side_effects: none (reads access summary)
# emitted_logs: none
# failure_policy: returns standard 401 if unauthenticated
# END_MODULE_CONTRACT: M-API-ACCESS

# START_MODULE_MAP: M-API-ACCESS
# public_entrypoints:
#   - router
# semantic_blocks:
#   - ROUTE_ACCESS_GET: GET /api/access route
# owned_tests:
#   - apps/api/tests/test_access_service.py
# END_MODULE_MAP: M-API-ACCESS

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_user_id
from app.db.session import get_session
from app.schemas.access import AccessSummary
from app.services.access_service import AccessService

router = APIRouter()


# START_BLOCK: ROUTE_ACCESS_GET
@router.get("/api/access", response_model=AccessSummary)
async def get_access(
    user_id: uuid.UUID = Depends(current_user_id),
    db: AsyncSession = Depends(get_session),
) -> AccessSummary:
    # START_FUNCTION_CONTRACT: F-M-API-ACCESS.get_access
    # purpose: Authenticated endpoint returning user's access summary.
    # inputs: user_id (UUID), db (AsyncSession)
    # returns: AccessSummary
    # side_effects: calls AccessService.get_summary
    # emitted_logs: none
    # error_behavior: 401 if unauthenticated
    # END_FUNCTION_CONTRACT: F-M-API-ACCESS.get_access
    return await AccessService(db).get_summary(user_id)
# END_BLOCK: ROUTE_ACCESS_GET
