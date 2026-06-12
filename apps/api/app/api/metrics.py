# ############################################################################
# AI_HEADER: MODULE_API_METRICS
# ROLE: Production metrics endpoint for monitoring user growth and onboarding.
# DEPENDENCIES: fastapi, sqlalchemy, app.db.session, app.models
# GRACE_ANCHORS: [METRICS_PAYLOAD]
# WAVE: W-2.7
# ############################################################################

# START_MODULE_CONTRACT: M-API-METRICS
# purpose: Return production metrics — user counts, onboarding rates.
# owns:
#   - apps/api/app/api/metrics.py
# inputs:
#   - db session
# outputs:
#   - dict with user and onboarding metrics
# dependencies:
#   - M-DB-SESSION
# side_effects:
#   - read-only; no mutations
# invariants:
#   - returns current UTC timestamp
# failure_policy:
#   - DB errors propagate as 500
# non_goals:
#   - no business-specific metrics
# END_MODULE_CONTRACT: M-API-METRICS

# START_MODULE_MAP: M-API-METRICS
# public_entrypoints:
#   - get_metrics
# semantic_blocks:
#   - METRICS_PAYLOAD: GET /api/metrics handler
# END_MODULE_MAP: M-API-METRICS

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.db.models import User, UserProfile

router = APIRouter()


# START_BLOCK: METRICS_ENDPOINT
@router.get("/api/metrics")
async def get_metrics(db: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-API-METRICS.get_metrics
    # purpose: Return production metrics — user counts, onboarding rates.
    # inputs: db (AsyncSession)
    # returns: dict with users total/24h/7d and onboarding completed/rate
    # side_effects: read-only DB queries
    # emitted_logs: none
    # error_behavior: DB errors propagate as 500
    # END_FUNCTION_CONTRACT: F-M-API-METRICS.get_metrics
    """
    Production metrics for monitoring.

    Returns:
        Dictionary with user, onboarding, and system metrics.
    """
    now = datetime.now(UTC)
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    # User metrics
    from sqlalchemy import select

    result = await db.execute(select(func.count(User.id)))
    total_users = result.scalar() or 0

    result = await db.execute(select(func.count(User.id)).where(User.created_at >= last_24h))
    new_users_24h = result.scalar() or 0

    result = await db.execute(select(func.count(User.id)).where(User.created_at >= last_7d))
    new_users_7d = result.scalar() or 0

    # Onboarding metrics
    result = await db.execute(select(func.count(UserProfile.user_id)))
    total_profiles = result.scalar() or 0

    onboarding_rate = (total_profiles / total_users * 100) if total_users > 0 else 0

    # Profiles created in last 24h/7d
    result = await db.execute(select(func.count(UserProfile.user_id)).where(UserProfile.created_at >= last_24h))
    profiles_24h = result.scalar() or 0

    result = await db.execute(select(func.count(UserProfile.user_id)).where(UserProfile.created_at >= last_7d))
    profiles_7d = result.scalar() or 0

    return {
        "timestamp": now.isoformat(),
        "users": {
            "total": total_users,
            "new_24h": new_users_24h,
            "new_7d": new_users_7d,
        },
        "onboarding": {
            "completed": total_profiles,
            "completed_24h": profiles_24h,
            "completed_7d": profiles_7d,
            "rate": round(onboarding_rate, 2),
        },
    }
# END_BLOCK: METRICS_ENDPOINT
