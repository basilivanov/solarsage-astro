# ############################################################################
# AI_HEADER: MODULE_AUTH_SCHEMAS
# ROLE: Pydantic v2 schemas for /api/auth/* surface (Option A).
# DEPENDENCIES: pydantic, app.schemas._base.CamelModel
# GRACE_ANCHORS: [AUTH_REQUEST, AUTH_SESSION, AUTH_ERROR]
# ############################################################################

# START_MODULE_CONTRACT: M-AUTH-TG.schemas
# purpose: Wire-format contracts for POST /api/auth/telegram and
#   POST /api/auth/logout. AuthError is reused for both 400 and 401 bodies
#   via FastAPI `responses=`.
# owns:
#   - apps/api/app/schemas/auth.py
# outputs:
#   - TelegramAuthRequest, AuthSession, AuthError
# invariants:
#   - all fields snake_case in Python; camelCase on the wire (CamelModel).
#   - AuthError.code is a Literal whitelist; mismatched values are 422.
# END_MODULE_CONTRACT: M-AUTH-TG.schemas

# START_MODULE_MAP: M-AUTH-TG.schemas
# public_entrypoints:
#   - TelegramAuthRequest
#   - AuthSession
#   - AuthError
# semantic_blocks:
#   - AUTH_REQUEST: TelegramAuthRequest
#   - AUTH_SESSION: AuthSession (response of POST /api/auth/telegram)
#   - AUTH_ERROR: AuthError (used in responses= for 400/401)
# owned_tests:
#   - apps/api/tests/test_auth_endpoints.py
# END_MODULE_MAP: M-AUTH-TG.schemas

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas._base import CamelModel


# START_BLOCK: AUTH_REQUEST
class TelegramAuthRequest(CamelModel):
    """POST /api/auth/telegram — request body."""

    init_data: str = Field(..., min_length=1, max_length=8192)
# END_BLOCK: AUTH_REQUEST


# START_BLOCK: AUTH_SESSION
class AuthSession(CamelModel):
    """POST /api/auth/telegram — 200 response body.

    The opaque session token itself is NEVER in the body; it travels in the
    HttpOnly Set-Cookie header.
    """

    user_id: UUID
    expires_at: datetime
    is_new_user: bool
# END_BLOCK: AUTH_SESSION


# START_BLOCK: AUTH_ERROR
class AuthError(CamelModel):
    """Stable error envelope for 400 and 401 bodies on /api/auth/*."""

    code: Literal[
        "INVALID_HMAC",
        "MISSING_FIELDS",
        "MALFORMED_INITDATA",
        "INITDATA_EXPIRED",
        "UNAUTHORIZED",
    ]
    message: str
# END_BLOCK: AUTH_ERROR
