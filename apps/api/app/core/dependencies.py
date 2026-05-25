# ############################################################################
# AI_HEADER: MODULE_CORE_DEPENDENCIES
# ROLE: Shared FastAPI dependencies for protected routes. Single home for
#   anything that resolves the current authenticated user.
# DEPENDENCIES: fastapi, app.services.session_service, app.db.session
# GRACE_ANCHORS: [CURRENT_USER_DEP]
# ############################################################################

# START_MODULE_CONTRACT: M-AUTH-TG.dependencies
# purpose: Expose `current_user_id` as the single import point used by every
#   protected router. Lives under app.core so router-to-router imports are
#   forbidden (per W-1.2 ## Decision: no router-to-router shape sharing).
# owns:
#   - apps/api/app/core/dependencies.py
# outputs:
#   - current_user_id(request, db) -> uuid.UUID
# dependencies:
#   - M-AUTH-TG.session (resolve_session)
#   - M-DB-SESSION (get_session)
#   - M-CONFIG (settings.session_cookie_name)
# failure_policy:
#   - InvalidSession -> HTTP 401 with {"code": ..., "reason": ...}
# END_MODULE_CONTRACT: M-AUTH-TG.dependencies

# START_MODULE_MAP: M-AUTH-TG.dependencies
# public_entrypoints:
#   - current_user_id
# semantic_blocks:
#   - CURRENT_USER_DEP: cookie -> session row -> user_id
# END_MODULE_MAP: M-AUTH-TG.dependencies

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.services.session_service import InvalidSession, resolve_session


# START_BLOCK: CURRENT_USER_DEP
async def current_user_id(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> uuid.UUID:
    """FastAPI dependency: returns the user UUID resolved from the session cookie."""
    token = request.cookies.get(settings.session_cookie_name, "")
    try:
        session = await resolve_session(db, token)
    except InvalidSession as exc:
        # TODO(W-1.6): log.event("auth.session_rejected", {code: exc.code})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": exc.code, "reason": exc.message},
        ) from exc
    return session.user_id
# END_BLOCK: CURRENT_USER_DEP
