# ############################################################################
# AI_HEADER: MODULE_API_METRICS
# ROLE: Production metrics endpoint for monitoring user growth and onboarding.
# DEPENDENCIES: fastapi, sqlalchemy, app.db.session, app.models
# GRACE_ANCHORS: [METRICS_PAYLOAD]
# WAVE: W-2.7
# ############################################################################

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.db.models import User, UserProfile

router = APIRouter()


@router.get("/api/metrics")
async def get_metrics(db: AsyncSession = Depends(get_session)) -> dict[str, Any]:
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
