# ############################################################################
# AI_HEADER: MODULE_API_MICROCOPY
# ROLE: Microcopy admin endpoints (W-9.2)
# DEPENDENCIES: fastapi, app.services.microcopy_service, app.db.session
# GRACE_ANCHORS: [MICROCOPY_MISSES_ENDPOINT]
# WAVE: W-9.2
# ############################################################################

# START_MODULE_CONTRACT: M-API-MICROCOPY
# purpose: Admin endpoint for monitoring missing microcopy keys.
# owns:
#   - apps/api/app/api/microcopy.py
# inputs:
#   - GET /api/admin/microcopy/misses
# outputs:
#   - {"misses": [{"key": str, "hit_count": int, "first_seen": str, "last_seen": str}]}
# dependencies:
#   - M-MICROCOPY-SERVICE
#   - M-DB-SESSION
# side_effects:
#   - reads from microcopy_misses table
# invariants:
#   - returns last 7 days of misses
# failure_policy:
#   - 500 on DB errors
# non_goals:
#   - no auth for MVP (admin endpoint, simplified)
# END_MODULE_CONTRACT: M-API-MICROCOPY

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.microcopy_service import MicrocopyService

router = APIRouter()


@router.get("/api/admin/microcopy/misses")
async def get_microcopy_misses(db: AsyncSession = Depends(get_session)):
    """
    Get weekly report of missed microcopy keys.

    W-9.2: Admin endpoint for monitoring missing keys.

    Returns:
        {"misses": [{"key": str, "hit_count": int, "first_seen": str, "last_seen": str}]}
    """
    service = MicrocopyService(db)
    report = await service.get_weekly_report()

    return {"misses": report}
