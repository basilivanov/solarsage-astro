# ############################################################################
# AI_HEADER: MODULE_CORE_SECURITY
# ROLE: Cookie helpers for the opaque session token (Option A).
# DEPENDENCIES: fastapi.Response, app.core.config
# GRACE_ANCHORS: [SET_SESSION_COOKIE, CLEAR_SESSION_COOKIE]
# ############################################################################

# START_MODULE_CONTRACT: M-AUTH-TG.security
# purpose: Concentrate cookie attribute decisions (HttpOnly, Secure, SameSite)
#   in one place so the auth router can stay declarative.
# owns:
#   - apps/api/app/core/security.py
# inputs:
#   - fastapi.Response, opaque token, max_age (seconds)
#   - settings.session_cookie_name, settings.session_cookie_secure
# outputs:
#   - set_session_cookie(response, token, *, max_age)
#   - clear_session_cookie(response)
#   - SESSION_TTL (timedelta)
# invariants:
#   - cookie attributes: HttpOnly=True, Secure=settings.session_cookie_secure,
#     SameSite=None (REQUIRED for Telegram Web App iframe), Path=/.
#   - clear writes the same cookie with max_age=0 (NOT delete_cookie, which
#     omits the Max-Age attribute on some FastAPI/Starlette versions).
# END_MODULE_CONTRACT: M-AUTH-TG.security

# START_MODULE_MAP: M-AUTH-TG.security
# public_entrypoints:
#   - SESSION_TTL
#   - set_session_cookie
#   - clear_session_cookie
# semantic_blocks:
#   - SET_SESSION_COOKIE: response.set_cookie with locked attributes
#   - CLEAR_SESSION_COOKIE: same cookie, max_age=0
# END_MODULE_MAP: M-AUTH-TG.security

from __future__ import annotations

from datetime import timedelta

from fastapi import Response

from app.core.config import settings

SESSION_TTL: timedelta = timedelta(seconds=settings.session_ttl_seconds)


# START_BLOCK: SET_SESSION_COOKIE
def set_session_cookie(response: Response, token: str, *, max_age: int) -> None:
    # START_FUNCTION_CONTRACT: F-M-CORE-SECURITY.set_session_cookie
    # purpose: Set HttpOnly+Secure+SameSite=None session cookie.
    # inputs: response (Response), token (str), max_age (int seconds)
    # returns: None (mutates response)
    # side_effects: sets cookie on response object
    # emitted_logs: none
    # error_behavior: never raises
    # END_FUNCTION_CONTRACT: F-M-CORE-SECURITY.set_session_cookie
    """Persist the opaque session token in an HttpOnly + Secure + None cookie.

    SameSite=None is REQUIRED for Telegram Web App (iframe context).
    Secure=True is REQUIRED when SameSite=None.
    """
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        samesite="none",
        secure=settings.session_cookie_secure,
        path="/",
    )
# END_BLOCK: SET_SESSION_COOKIE


# START_BLOCK: CLEAR_SESSION_COOKIE
def clear_session_cookie(response: Response) -> None:
    # START_FUNCTION_CONTRACT: F-M-CORE-SECURITY.clear_session_cookie
    # purpose: Clear session cookie by setting Max-Age=0.
    # inputs: response (Response)
    # returns: None (mutates response)
    # side_effects: clears cookie on response object
    # emitted_logs: none
    # error_behavior: never raises
    # END_FUNCTION_CONTRACT: F-M-CORE-SECURITY.clear_session_cookie
    """Tell the browser to drop the cookie (Max-Age=0, same name + Path)."""
    response.set_cookie(
        key=settings.session_cookie_name,
        value="",
        max_age=0,
        httponly=True,
        samesite="none",
        secure=settings.session_cookie_secure,
        path="/",
    )
# END_BLOCK: CLEAR_SESSION_COOKIE
