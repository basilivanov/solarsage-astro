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

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.dependencies import require_session
from app.db.session import get_session
from app.services.natal_service import NatalService

router = APIRouter()


@router.get("/api/natal/overview")
async def get_natal_overview(
    db: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(require_session),
):
    """
    Get natal reading overview.

    W-7.2: Returns meta + section list (without blocks).

    Returns:
        JSON with meta and sections list
    """
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


@router.get("/api/natal/section/{section_id}")
async def get_natal_section(
    section_id: str,
    db: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(require_session),
):
    """
    Get specific natal reading section.

    W-7.2: Returns section with blocks.

    Args:
        section_id: Section identifier (e.g., "sun", "moon", "ascendant")

    Returns:
        JSON with section data including blocks

    Raises:
        HTTPException: 404 if section not found
    """
    service = NatalService(db)
    reading = await service.get_natal_reading(user_id)

    # Find section
    section = next((s for s in reading.sections if s.id == section_id), None)

    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    return section.model_dump(by_alias=True)
