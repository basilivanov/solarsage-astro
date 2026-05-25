# ############################################################################
# AI_HEADER: MODULE_API_AUTH
# ROLE: HTTP surface for /api/auth/telegram and /api/auth/logout (Option A).
# DEPENDENCIES: fastapi, sqlalchemy, app.services.*, app.core.*
# GRACE_ANCHORS: [ROUTE_AUTH_TG, ROUTE_AUTH_LOGOUT]
# ############################################################################

# START_MODULE_CONTRACT: M-AUTH-TG.api
# purpose: Two endpoints:
#   - POST /api/auth/telegram: verify initData, upsert user, mint session,
#     set HttpOnly cookie. Body: AuthSession.
#   - POST /api/auth/logout: revoke the session row, clear the cookie. 204.
# owns:
#   - apps/api/app/api/auth.py
# inputs:
#   - request body: TelegramAuthRequest
#   - cookie: settings.session_cookie_name (logout)
# outputs:
#   - APIRouter with the two endpoints
# dependencies:
#   - M-AUTH-TG.service (verify_init_data)
#   - M-AUTH-TG.session (create_session, revoke_session)
#   - M-PROFILE.service (get_or_create_user, read_profile)
#   - M-AUTH-TG.security (set_session_cookie, clear_session_cookie)
#   - M-AUTH-TG.dependencies (current_user_id) — for logout
# invariants:
#   - tampered initData -> 400 INVALID_HMAC, NO DB write (HMAC fails before any
#     session write).
#   - stale initData -> 401 INITDATA_EXPIRED.
#   - upsert is idempotent on tg_user_id; the response carries is_new_user.
#   - error bodies expose only AuthError(code, message); never the raw payload.
# failure_policy:
#   - TelegramAuthError -> 400 or 401 per code mapping in the route.
# non_goals:
#   - no rate limiting (W-RATELIMIT)
# END_MODULE_CONTRACT: M-AUTH-TG.api

# START_MODULE_MAP: M-AUTH-TG.api
# public_entrypoints:
#   - router
# semantic_blocks:
#   - ROUTE_AUTH_TG: POST /api/auth/telegram handler
#   - ROUTE_AUTH_LOGOUT: POST /api/auth/logout handler
# owned_tests:
#   - apps/api/tests/test_auth_endpoints.py
# END_MODULE_MAP: M-AUTH-TG.api

from __future__ import annotations

from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    SESSION_TTL,
    clear_session_cookie,
    set_session_cookie,
)
from app.db.session import get_session
from app.schemas.auth import AuthError, AuthSession, TelegramAuthRequest
from app.services.profile_service import get_or_create_user, read_profile
from app.services.session_service import create_session, revoke_session
from app.services.telegram_auth import TelegramAuthError, verify_init_data

router = APIRouter()

_BAD_REQUEST_CODES = frozenset(
    {"INVALID_HMAC", "MISSING_FIELDS", "MALFORMED_INITDATA"}
)


def _telegram_error_to_http(exc: TelegramAuthError) -> HTTPException:
    if exc.code in _BAD_REQUEST_CODES:
        http_status = status.HTTP_400_BAD_REQUEST
    else:  # INITDATA_EXPIRED
        http_status = status.HTTP_401_UNAUTHORIZED
    return HTTPException(
        status_code=http_status,
        detail={"code": exc.code, "message": exc.message},
    )


# START_BLOCK: ROUTE_AUTH_TG
@router.post(
    "/api/auth/telegram",
    response_model=AuthSession,
    responses={
        400: {"model": AuthError},
        401: {"model": AuthError},
    },
)
async def auth_telegram(
    body: TelegramAuthRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> AuthSession:
    # START_FUNCTION_CONTRACT: M-AUTH-TG.api.auth_telegram
    # purpose: Verify initData, upsert user, lazy-create profile row, mint
    #   server-side session, set HttpOnly cookie.
    # error_behavior: TelegramAuthError -> 400/401 per code mapping; commit
    #   only on success (exception bubbles before flush+commit).
    # END_FUNCTION_CONTRACT: M-AUTH-TG.api.auth_telegram
    try:
        tg = verify_init_data(body.init_data)
    except TelegramAuthError as exc:
        # TODO(W-1.6): log.event("auth.tg_login_failed", {code: exc.code})
        raise _telegram_error_to_http(exc) from exc

    user, is_new = await get_or_create_user(db, tg)
    # Ensure a (possibly empty) profile row exists; later reads never 404.
    await read_profile(db, user.id)

    user_agent = request.headers.get("user-agent")
    opaque_token, session = await create_session(
        db, user.id, ttl=SESSION_TTL, user_agent=user_agent
    )
    await db.commit()

    set_session_cookie(
        response, opaque_token, max_age=settings.session_ttl_seconds
    )

    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    # TODO(W-1.6): log.event("auth.tg_login_succeeded", {is_new_user, ...})
    return AuthSession(user_id=user.id, expires_at=expires_at, is_new_user=is_new)
# END_BLOCK: ROUTE_AUTH_TG


# START_BLOCK: ROUTE_AUTH_LOGOUT
@router.post(
    "/api/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def auth_logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> Response:
    # START_FUNCTION_CONTRACT: M-AUTH-TG.api.auth_logout
    # purpose: Revoke the session row keyed by the cookie token; always
    #   clear the cookie. Idempotent: missing/expired/revoked cookie still
    #   returns 204.
    # END_FUNCTION_CONTRACT: M-AUTH-TG.api.auth_logout
    token = request.cookies.get(settings.session_cookie_name, "")
    await revoke_session(db, token)
    await db.commit()
    clear_session_cookie(response)
    # TODO(W-1.6): log.event("auth.logout", {})
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers=dict(response.headers))
# END_BLOCK: ROUTE_AUTH_LOGOUT
