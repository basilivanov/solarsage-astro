# ############################################################################
# AI_HEADER: MODULE_API_AUTH
# ROLE: HTTP surface for /api/auth/telegram, /api/auth/logout, and the local-development-only /api/auth/dev surface (Option A).
# DEPENDENCIES: fastapi, sqlalchemy, app.services.*, app.core.*
# GRACE_ANCHORS: [ROUTE_AUTH_TG, ROUTE_AUTH_LOGOUT, ROUTE_AUTH_DEV]
# ############################################################################

# START_MODULE_CONTRACT: M-AUTH-TG.api
# purpose: Three auth surfaces:
#   - POST /api/auth/telegram: verify initData, upsert user, mint session,
#     set HttpOnly cookie. Body: AuthSession.
#   - POST /api/auth/logout: revoke the session row, clear the cookie. 204.
#   - POST /api/auth/dev: local-development-only fallback for synthetic login
#     in canonical dev environments.
# owns:
#   - apps/api/app/api/auth.py
# inputs:
#   - request body: TelegramAuthRequest
#   - cookie: settings.session_cookie_name (logout)
# outputs:
#   - APIRouter with the three auth endpoints
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
#   - local dev auth fail-closed outside canonical dev|development, even for
#     loopback requests.
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
#   - ROUTE_AUTH_DEV: POST /api/auth/dev handler
# owned_tests:
#   - apps/api/tests/test_auth_endpoints.py
# END_MODULE_MAP: M-AUTH-TG.api

from __future__ import annotations

from datetime import timezone
from ipaddress import ip_address

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.log_identity import hash_user_id
from app.core.logging import bind_log_context, log_event
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
_LOCAL_DEV_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_LOCAL_DEVELOPMENT_ENVS = frozenset({"dev", "development"})
_PROXY_ORIGIN_HEADER_NAMES = frozenset({"forwarded", "x-real-ip"})
_PROXY_ORIGIN_HEADER_PREFIX = "x-forwarded-"


def _telegram_error_to_http(exc: TelegramAuthError) -> HTTPException:
    if exc.code in _BAD_REQUEST_CODES:
        http_status = status.HTTP_400_BAD_REQUEST
    else:  # INITDATA_EXPIRED
        http_status = status.HTTP_401_UNAUTHORIZED
    return HTTPException(
        status_code=http_status,
        detail={"code": exc.code, "message": exc.message},
    )


def _host_header_name(host_header: str | None) -> str:
    if not host_header:
        return ""

    host = host_header.strip().lower()
    if host.startswith("["):
        end_bracket = host.find("]")
        return host[1:end_bracket] if end_bracket != -1 else host
    if host != "::1":
        return host.split(":", 1)[0]
    return host


def _is_loopback_client(request: Request) -> bool:
    if request.client is None:
        return False

    try:
        return ip_address(request.client.host).is_loopback
    except ValueError:
        return request.client.host == "localhost"


def _has_proxy_origin_header(request: Request) -> bool:
    for header in request.headers.keys():
        name = header.lower()
        if (
            name in _PROXY_ORIGIN_HEADER_NAMES
            or name.startswith(_PROXY_ORIGIN_HEADER_PREFIX)
        ):
            return True
    return False


def _is_local_dev_auth_request(request: Request) -> bool:
    # START_FUNCTION_CONTRACT: M-AUTH-TG.api._is_local_dev_auth_request
    # purpose: Determine whether /api/auth/dev is a trusted local-development request.
    # inputs: request — Starlette Request carrying client and host headers.
    # returns: bool — True only for canonical dev|development envs with loopback
    #   client, local host header, and no proxy-origin headers.
    # side_effects: none
    # emitted_logs: none
    # error_behavior: fail-closed False for non-string/unknown env values.
    # END_FUNCTION_CONTRACT: M-AUTH-TG.api._is_local_dev_auth_request
    raw_env = settings.app_env
    environment = raw_env.strip().lower() if isinstance(raw_env, str) else ""
    if environment not in _LOCAL_DEVELOPMENT_ENVS:
        return False
    if not _is_loopback_client(request):
        return False
    if _host_header_name(request.headers.get("host")) not in _LOCAL_DEV_HOSTS:
        return False
    return not _has_proxy_origin_header(request)


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
    # inputs: body (TelegramAuthRequest), request, response, db
    # returns: AuthSession with user_id, expires_at, is_new_user
    # side_effects: upserts User row, creates Session row, sets cookie
    # emitted_logs: auth.tg_login_succeeded, auth.tg_login_failed
    # error_behavior: TelegramAuthError -> 400/401 per code mapping; commit
    #   only on success (exception bubbles before flush+commit).
    # END_FUNCTION_CONTRACT: M-AUTH-TG.api.auth_telegram
    try:
        tg = verify_init_data(body.init_data)
    except TelegramAuthError as exc:
        log_event("auth.tg_login_failed", payload={"reason": exc.code.lower()})
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

    # Bind user_id_hash to context
    bind_log_context(user_id_hash=hash_user_id(user.id))

    log_event(
        "auth.tg_login_succeeded",
        payload={"is_new_user": is_new, "has_start_param": "start_param=" in body.init_data},
    )
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
    # inputs: request, response, db
    # returns: Response with status 204
    # side_effects: revokes session row, clears cookie
    # emitted_logs: auth.logout
    # error_behavior: idempotent — missing/already-revoked cookies still return 204
    # END_FUNCTION_CONTRACT: M-AUTH-TG.api.auth_logout
    token = request.cookies.get(settings.session_cookie_name, "")
    await revoke_session(db, token)
    await db.commit()
    clear_session_cookie(response)
    log_event("auth.logout")
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers=dict(response.headers))
# END_BLOCK: ROUTE_AUTH_LOGOUT


# START_BLOCK: ROUTE_AUTH_DEV
@router.post(
    "/api/auth/dev",
    response_model=AuthSession,
    responses={
        403: {"model": AuthError},
    },
)
async def auth_dev(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> AuthSession:
    # START_FUNCTION_CONTRACT: M-AUTH-TG.api.auth_dev
    # purpose: Local-development auth fallback that creates a synthetic test
    #   user session for /api/auth/dev.
    # inputs: request, response, db
    # returns: AuthSession with user_id, expires_at, is_new_user
    # side_effects: upserts test User, creates Session, sets test birth data
    # emitted_logs: auth.dev_login_succeeded, auth.dev_login_blocked
    # error_behavior: 403 outside canonical local development or when the
    #   request is not trusted-local while DEV_MODE is disabled.
    # END_FUNCTION_CONTRACT: M-AUTH-TG.api.auth_dev

    if not settings.dev_mode and not _is_local_dev_auth_request(request):
        log_event("auth.dev_login_blocked")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "DEV_MODE_DISABLED", "message": "Dev mode not enabled"},
        )

    # Create test TelegramUser
    from app.services.telegram_auth import TelegramUser
    test_tg_user = TelegramUser(
        id=999999999,
        username="dev_user",
        first_name="Dev",
        last_name="User",
    )

    # Upsert test user
    user, is_new = await get_or_create_user(db, test_tg_user)

    # Ensure profile exists
    profile = await read_profile(db, user.id)

    # If new user or profile not onboarded, set up test birth data
    should_flush_profile = False
    if is_new or not profile.is_onboarded:
        from datetime import date, time
        from decimal import Decimal

        profile.first_name = "Dev"
        profile.gender = profile.gender or "female"
        profile.birthday = date(1990, 1, 1)
        profile.birth_time = time(12, 0, 0)
        profile.birth_city = "Moscow, Russia"
        profile.birth_lat = Decimal("55.75580")
        profile.birth_lon = Decimal("37.61730")
        profile.birth_tz = "Europe/Moscow"
        profile.is_onboarded = True
        should_flush_profile = True

    if profile.gender not in {"female", "male"}:
        profile.gender = "female"
        should_flush_profile = True

    if should_flush_profile:
        await db.flush()

    # Create session
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

    # Bind user_id_hash to context
    bind_log_context(user_id_hash=hash_user_id(user.id))

    log_event("auth.dev_login_succeeded", payload={"is_new_user": is_new})
    return AuthSession(user_id=user.id, expires_at=expires_at, is_new_user=is_new)
# END_BLOCK: ROUTE_AUTH_DEV
