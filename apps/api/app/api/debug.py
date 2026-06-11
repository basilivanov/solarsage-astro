# ############################################################################
# AI_HEADER: MODULE_API_DEBUG
# ROLE: Debug information endpoint for troubleshooting
# DEPENDENCIES: fastapi, sqlalchemy, app.core.config
# GRACE_ANCHORS: [DEBUG_INFO_ENDPOINT]
# ############################################################################

# START_MODULE_CONTRACT: M-API-DEBUG
# purpose: Expose debug info for troubleshooting auth/session state.
# owns:
#   - apps/api/app/api/debug.py
# inputs:
#   - request headers, cookies
# outputs:
#   - debug_info dict
# dependencies:
#   - M-CONFIG
#   - M-DB-SESSION (optional)
# side_effects:
#   - none (read-only)
# invariants:
#   - works with or without auth
# failure_policy:
#   - returns error key in response on exception; never raises
# non_goals:
#   - never enabled in production
# END_MODULE_CONTRACT: M-API-DEBUG

# START_MODULE_MAP: M-API-DEBUG
# public_entrypoints:
#   - debug_info
# semantic_blocks:
#   - DEBUG_INFO_ENDPOINT: GET /api/debug
# END_MODULE_MAP: M-API-DEBUG

from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.core.dependencies import require_session_optional
from app.core.config import settings
from datetime import datetime
import sys

router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("")
async def debug_info(
    request: Request,
    current_user = Depends(require_session_optional)
):
    """Debug information for troubleshooting"""

    try:
        # Get cookies
        cookies = dict(request.cookies)

        # Get headers
        headers = dict(request.headers)

        # Check session cookie
        session_cookie = cookies.get("grace_session")

        # User info
        user_info = None
        if current_user:
            user_info = {
                "id": str(current_user.id),
                "tg_user_id": current_user.tg_user_id,
                "tg_username": current_user.tg_username,
                "first_name": current_user.profile.first_name if current_user.profile else None,
                "is_onboarded": current_user.profile.is_onboarded if current_user.profile else False,
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "dev_mode": settings.dev_mode,
            "session_cookie_present": session_cookie is not None,
            "session_cookie_length": len(session_cookie) if session_cookie else 0,
            "user_authenticated": current_user is not None,
            "user_info": user_info,
            "cookies": list(cookies.keys()),
            "headers": {
                "user-agent": headers.get("user-agent"),
                "origin": headers.get("origin"),
                "referer": headers.get("referer"),
            },
            "env": {
                "python_version": sys.version,
                "app_version": settings.app_version,
            }
        }
    except Exception as e:
        # Log error and return minimal response
        print(f"[DEBUG] Error in debug endpoint: {e}")
        import traceback
        traceback.print_exc()

        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "dev_mode": settings.dev_mode,
        }
