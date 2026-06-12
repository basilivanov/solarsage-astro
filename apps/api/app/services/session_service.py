# ############################################################################
# AI_HEADER: MODULE_SESSION_SERVICE
# ROLE: Server-side session row CRUD (Option A — opaque cookie + sessions).
# DEPENDENCIES: secrets, hashlib, sqlalchemy.ext.asyncio, app.db.models.Session
# GRACE_ANCHORS: [SESSION_CREATE, SESSION_RESOLVE, SESSION_REVOKE]
# ############################################################################

# START_MODULE_CONTRACT: M-AUTH-TG.session
# purpose: Mint, resolve, and revoke server-side session rows. The opaque
#   token is a 32-byte URL-safe random string; we store sha256-hex of it
#   so that a stolen DB dump cannot replay.
# owns:
#   - apps/api/app/services/session_service.py
# inputs:
#   - DB session, user_id (UUID), TTL, optional user_agent
#   - opaque token from cookie (resolve/revoke paths)
# outputs:
#   - create_session() -> (opaque_token, Session row)
#   - resolve_session() -> Session row (or InvalidSession)
#   - revoke_session() -> None (idempotent)
# invariants:
#   - opaque token never persisted in plain text; only sha256-hex
#   - resolve checks both expires_at > now() and revoked_at IS NULL
#   - revoke is idempotent: missing/already-revoked tokens are no-ops
# failure_policy:
#   - InvalidSession with stable `code`: MISSING | MALFORMED | EXPIRED |
#     REVOKED | UNKNOWN. Router maps every code to HTTP 401.
# non_goals:
#   - no rate limiting / replay protection beyond uniqueness of token_hash
#   - no admin listing (W-ADMIN-AUTH)
# END_MODULE_CONTRACT: M-AUTH-TG.session

# START_MODULE_MAP: M-AUTH-TG.session
# public_entrypoints:
#   - InvalidSession
#   - create_session
#   - resolve_session
#   - revoke_session
#   - hash_token
# semantic_blocks:
#   - SESSION_CREATE: mint opaque token + insert row
#   - SESSION_RESOLVE: lookup by token_hash + freshness checks
#   - SESSION_REVOKE: idempotent revoke
# owned_tests:
#   - apps/api/tests/test_auth_endpoints.py
# END_MODULE_MAP: M-AUTH-TG.session

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Session


class InvalidSession(Exception):
    """Raised when an opaque session token cannot be resolved."""

    _ALLOWED: Final[frozenset[str]] = frozenset(
        {"MISSING", "MALFORMED", "EXPIRED", "REVOKED", "UNKNOWN"}
    )

    def __init__(self, code: str, message: str) -> None:
        if code not in self._ALLOWED:
            raise ValueError(f"unknown InvalidSession code: {code}")
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def hash_token(token: str) -> str:
    # START_FUNCTION_CONTRACT: F-M-AUTH-TG.session.hash_token
    # purpose: Compute SHA-256 hex digest of opaque token.
    # inputs: token (str)
    # returns: str (64-char lowercase hex digest)
    # side_effects: none (pure function)
    # emitted_logs: none
    # error_behavior: never raises
    # END_FUNCTION_CONTRACT: F-M-AUTH-TG.session.hash_token
    """sha256-hex of the opaque token. 64 chars, lowercase."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _is_safe_opaque(token: str) -> bool:
    """Reject anything that doesn't look like our `secrets.token_urlsafe(32)`.

    We accept the URL-safe alphabet [A-Za-z0-9_-] and length 1..512 (well
    above the ~43-char output of token_urlsafe(32)). This is just a cheap
    pre-filter so we don't go to the DB on garbage.
    """
    if not token or len(token) > 512:
        return False
    return all(c.isalnum() or c in "-_" for c in token)


# START_BLOCK: SESSION_CREATE
async def create_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    ttl: timedelta,
    user_agent: str | None,
) -> tuple[str, Session]:
    # START_FUNCTION_CONTRACT: F-M-AUTH-TG.session.create_session
    # purpose: Mint opaque session token and insert Session row.
    # inputs: db (AsyncSession), user_id (UUID), ttl (timedelta), user_agent (str | None)
    # returns: tuple[str, Session] — (opaque_token, session row)
    # side_effects: inserts Session row (caller must commit)
    # emitted_logs: none
    # error_behavior: DB errors propagate
    # END_FUNCTION_CONTRACT: F-M-AUTH-TG.session.create_session
    """Mint an opaque session token and insert the matching Session row.

    Returns (opaque_token, session). Caller is responsible for committing
    the transaction.
    """
    opaque_token = secrets.token_urlsafe(32)
    row = Session(
        id=uuid.uuid4(),
        user_id=user_id,
        token_hash=hash_token(opaque_token),
        expires_at=_now_utc() + ttl,
        user_agent=user_agent[:255] if user_agent else None,
    )
    db.add(row)
    await db.flush()
    return opaque_token, row
# END_BLOCK: SESSION_CREATE


# START_BLOCK: SESSION_RESOLVE
async def resolve_session(db: AsyncSession, opaque_token: str) -> Session:
    # START_FUNCTION_CONTRACT: F-M-AUTH-TG.session.resolve_session
    # purpose: Resolve session by opaque token with freshness and revocation checks.
    # inputs: db (AsyncSession), opaque_token (str)
    # returns: Session row if valid
    # side_effects: reads from Session table
    # emitted_logs: none
    # error_behavior: raises InvalidSession with code: MISSING, MALFORMED, UNKNOWN, REVOKED, EXPIRED
    # END_FUNCTION_CONTRACT: F-M-AUTH-TG.session.resolve_session
    """Look the row up by token_hash; enforce freshness and revocation."""
    if not opaque_token:
        raise InvalidSession("MISSING", "no session cookie")
    if not _is_safe_opaque(opaque_token):
        raise InvalidSession("MALFORMED", "session token is not URL-safe")

    th = hash_token(opaque_token)
    row = (
        await db.execute(select(Session).where(Session.token_hash == th))
    ).scalar_one_or_none()
    if row is None:
        raise InvalidSession("UNKNOWN", "session not found")
    if row.revoked_at is not None:
        raise InvalidSession("REVOKED", "session was revoked")
    # `expires_at` from the DB may be naive on sqlite; normalize before compare.
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= _now_utc():
        raise InvalidSession("EXPIRED", "session expired")
    return row
# END_BLOCK: SESSION_RESOLVE


# START_BLOCK: SESSION_REVOKE
async def revoke_session(db: AsyncSession, opaque_token: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-AUTH-TG.session.revoke_session
    # purpose: Mark session as revoked (idempotent).
    # inputs: db (AsyncSession), opaque_token (str)
    # returns: None
    # side_effects: sets revoked_at on Session row
    # emitted_logs: none
    # error_behavior: idempotent — no-ops on missing/already-revoked tokens
    # END_FUNCTION_CONTRACT: F-M-AUTH-TG.session.revoke_session
    """Mark a session as revoked. Idempotent on missing/already-revoked rows."""
    if not opaque_token or not _is_safe_opaque(opaque_token):
        return
    th = hash_token(opaque_token)
    row = (
        await db.execute(select(Session).where(Session.token_hash == th))
    ).scalar_one_or_none()
    if row is None:
        return
    if row.revoked_at is None:
        row.revoked_at = _now_utc()
        await db.flush()
# END_BLOCK: SESSION_REVOKE
