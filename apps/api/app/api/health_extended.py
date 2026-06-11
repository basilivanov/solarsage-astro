# ############################################################################
# AI_HEADER: MODULE_API_HEALTH_EXTENDED
# ROLE: Extended health check with dependency status checks.
# DEPENDENCIES: fastapi, sqlalchemy, httpx, app.core.config
# GRACE_ANCHORS: [HEALTH_CHECKS]
# WAVE: W-2.7
# ############################################################################

# START_MODULE_CONTRACT: M-API-HEALTH-EXT
# purpose: Extended health check endpoint testing DB, LLM, and GeoNames.
# owns:
#   - apps/api/app/api/health_extended.py
# inputs:
#   - db session
# outputs:
#   - dict with api/database/llm/geonames status
# dependencies:
#   - M-DB-SESSION
#   - M-CONFIG
# side_effects:
#   - makes HTTP requests to OpenRouter and GeoNames
# invariants:
#   - non-critical checks return "not configured" instead of failing
# failure_policy:
#   - per-check errors are scoped; overall status reflects critical checks only
# non_goals:
#   - no detailed dependency debugging
# END_MODULE_CONTRACT: M-API-HEALTH-EXT

# START_MODULE_MAP: M-API-HEALTH-EXT
# public_entrypoints:
#   - health_check_extended
# semantic_blocks:
#   - HEALTH_CHECKS: per-dependency status probes
# END_MODULE_MAP: M-API-HEALTH-EXT

from typing import Any

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session

router = APIRouter()


@router.get("/api/health/extended")
async def health_check_extended(db: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    """
    Extended health check endpoint with dependency status.

    Checks:
    - API status (always ok if this endpoint responds)
    - Database connectivity
    - LLM service (OpenRouter)
    - GeoNames API

    Returns:
        Dictionary with overall status and individual check results.
    """
    checks: dict[str, str] = {
        "api": "ok",
        "database": "unknown",
        "llm": "unknown",
        "geonames": "unknown",
    }

    # Check database
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:100]}"

    # Check LLM (OpenRouter)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                timeout=5.0,
            )
            if response.status_code == 200:
                checks["llm"] = "ok"
            else:
                checks["llm"] = f"error: status {response.status_code}"
    except httpx.TimeoutException:
        checks["llm"] = "error: timeout"
    except Exception as e:
        checks["llm"] = f"error: {str(e)[:100]}"

    # Check GeoNames
    try:
        import os
        geonames_username = os.getenv("GEONAMES_USERNAME", "").strip()
        if not geonames_username:
            checks["geonames"] = "not configured"
        else:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://secure.geonames.org/searchJSON?q=test&maxRows=1&username={geonames_username}",
                    timeout=5.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    if "geonames" in data:
                        checks["geonames"] = "ok"
                    else:
                        checks["geonames"] = f"error: unexpected response"
                else:
                    checks["geonames"] = f"error: status {response.status_code}"
    except httpx.TimeoutException:
        checks["geonames"] = "error: timeout"
    except Exception as e:
        checks["geonames"] = f"error: {str(e)[:100]}"

    # Overall status
    # Consider "not configured" as acceptable for optional services
    critical_checks = {k: v for k, v in checks.items() if k in ["api", "database"]}
    all_critical_ok = all(v == "ok" for v in critical_checks.values())

    # Optional services (llm, geonames) can be "not configured" or "ok"
    optional_checks = {k: v for k, v in checks.items() if k not in ["api", "database"]}
    all_optional_ok = all(v in ["ok", "not configured"] for v in optional_checks.values())

    return {
        "status": "healthy" if (all_critical_ok and all_optional_ok) else "degraded",
        "checks": checks,
    }
