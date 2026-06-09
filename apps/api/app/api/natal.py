# ############################################################################
# AI_HEADER: MODULE_API_NATAL
# ROLE: Natal reading endpoints — overview and section retrieval.
# DEPENDENCIES: fastapi, app.services.natal_service
# GRACE_ANCHORS: [NATAL_OVERVIEW, NATAL_SECTION]
# WAVE: W-7.2
# ############################################################################

# START_MODULE_CONTRACT: M-API-NATAL
# purpose: Expose natal reading endpoints.
#   GET /api/natal/overview — returns overview + section list
#   GET /api/natal/section/{section_id} — returns section with blocks
# owns:
#   - apps/api/app/api/natal.py
# inputs:
#   - user_id from session (via require_session)
#   - section_id path parameter
# outputs:
#   - JSON: overview + sections list OR full section
# dependencies:
#   - M-NATAL-SERVICE
#   - M-DB-SESSION
#   - M-AUTH-DEPENDENCIES
# side_effects:
#   - none (read-only)
# invariants:
#   - requires authenticated session
#   - returns 404 for non-existent section
# failure_policy:
#   - 401 if not authenticated
#   - 404 if section not found
# non_goals:
#   - no caching (future wave)
# END_MODULE_CONTRACT: M-API-NATAL

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_user_id, require_session
from app.db.session import get_session
from app.schemas.natal import NatalPreviewRead
from app.services.natal_service import NatalService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/natal/overview")
async def get_natal_overview(
    db: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(require_session),
):
    service = NatalService(db)
    reading = await service.get_natal_reading(user_id)

    return {
        "meta": reading.meta.model_dump(by_alias=True),
        "sections": [
            {
                "id": s.id,
                "title": s.title,
                "iconName": s.icon_name,
            }
            for s in reading.sections
        ],
    }


@router.get("/api/natal/preview", response_model=NatalPreviewRead)
async def get_natal_preview(
    db: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(current_user_id),
) -> NatalPreviewRead:
    service = NatalService(db)
    try:
        return await service.get_preview(user_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Natal preview failed for user {user_id}: {exc}")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "NATAL_PREVIEW_FAILED",
                "message": "Не удалось построить натальную карту. Попробуй позже или проверь данные профиля.",
            },
        ) from exc


@router.get("/api/natal/section/{section_id}")
async def get_natal_section(
    section_id: str,
    db: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(require_session),
):
    service = NatalService(db)
    reading = await service.get_natal_reading(user_id)

    section = next((s for s in reading.sections if s.id == section_id), None)

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    return section.model_dump(by_alias=True)
