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

    # DEBUG: Log cookie presence
    print(f"[Auth] Cookie '{settings.session_cookie_name}': {'present' if token else 'MISSING'}")
    print(f"[Auth] All cookies: {list(request.cookies.keys())}")
    print(f"[Auth] Token length: {len(token) if token else 0}")

    try:
        session = await resolve_session(db, token)
    except InvalidSession as exc:
        # TODO(W-1.6): log.event("auth.session_rejected", {code: exc.code})
        print(f"[Auth] Session rejected: {exc.code} - {exc.message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": exc.code, "reason": exc.message},
        ) from exc
    return session.user_id


async def require_session(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """
    FastAPI dependency: returns the User object with profile relationship loaded.

    W-1.3: Used by /api/day/:date to check onboarding status.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.db.models import User

    user_id = await current_user_id(request, db)

    stmt = select(User).where(User.id == user_id).options(selectinload(User.profile))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "reason": "User not found"},
        )

    return user


async def require_session_optional(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """
    FastAPI dependency: returns the User object or None if not authenticated.

    Used for debug endpoints that should work regardless of auth status.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.db.models import User

    token = request.cookies.get(settings.session_cookie_name, "")
    if not token:
        return None

    try:
        session = await resolve_session(db, token)
    except InvalidSession:
        return None

    stmt = select(User).where(User.id == session.user_id).options(selectinload(User.profile))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    return user
# END_BLOCK: CURRENT_USER_DEP
