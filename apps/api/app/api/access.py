# ############################################################################
# AI_HEADER: MODULE_API_ACCESS
# ROLE: Authenticated HTTP surface for the current user's access summary
# DEPENDENCIES: fastapi, app.services.access_service
# GRACE_ANCHORS: []
# SLICE: SLICE-BACKEND-API-ROUTERS
# ############################################################################
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_user_id
from app.db.session import get_session
from app.schemas.access import AccessSummary
from app.services.access_service import AccessService

router = APIRouter()


@router.get("/api/access", response_model=AccessSummary)
async def get_access(
    user_id: uuid.UUID = Depends(current_user_id),
    db: AsyncSession = Depends(get_session),
) -> AccessSummary:
    return await AccessService(db).get_summary(user_id)
