# ############################################################################
# AI_HEADER: MODULE_AUTH_TG_SERVICE
# ROLE: Telegram WebApp initData verification (HMAC + freshness).
# DEPENDENCIES: hmac, hashlib, json, time, app.core.config
# GRACE_ANCHORS: [INITDATA_PARSE, HMAC_VERIFY]
# ############################################################################

# START_MODULE_CONTRACT: M-AUTH-TG.service
# purpose: Validate the `initData` blob produced by Telegram WebApp clients
#   per the official spec, extract the `user` object. Pure crypto + parsing;
#   no DB, no JWT, no session logic (sessions live in M-AUTH-TG.session).
# owns:
#   - apps/api/app/services/telegram_auth.py
# inputs:
#   - settings.telegram_bot_token (HMAC secret seed)
#   - settings.telegram_auth_max_age_seconds (replay window)
# outputs:
#   - verify_init_data(raw) -> TelegramUser
#   - TelegramAuthError exception with stable `code` field
# dependencies:
#   - M-CONFIG (settings)
# side_effects:
#   - none (pure crypto + parsing); never touches the DB or network
# invariants:
#   - constant-time HMAC comparison via hmac.compare_digest
#   - signature is computed against ALL keys except `hash`, sorted ASCII,
#     joined by "\n", per Telegram WebApp spec
#   - `auth_date` older than telegram_auth_max_age_seconds is rejected as
#     replay even if the HMAC matches
#   - empty bot_token is accepted ONLY when settings.app_env == "dev",
#     and the verifier degrades to "trust the payload's user.id"; this dev
#     bypass never activates in staging/production
#   - the function NEVER returns partial data on failure: any defect raises
# failure_policy:
#   - TelegramAuthError carries a stable machine code from the contract:
#     INVALID_HMAC | MISSING_FIELDS | INITDATA_EXPIRED | MALFORMED_INITDATA
#     Router maps INVALID_HMAC/MISSING_FIELDS/MALFORMED_INITDATA -> 400,
#     INITDATA_EXPIRED -> 401.
# non_goals:
#   - no DB writes, no JWT, no session minting (those live in session_service)
# END_MODULE_CONTRACT: M-AUTH-TG.service

# START_MODULE_MAP: M-AUTH-TG.service
# public_entrypoints:
#   - TelegramUser
#   - TelegramAuthError
#   - verify_init_data
# semantic_blocks:
#   - INITDATA_PARSE: parse_qsl(raw, strict) into the canonical mapping
#   - HMAC_VERIFY: derive secret_key, recompute hash, constant-time compare
# owned_tests:
#   - apps/api/tests/test_telegram_hmac.py
# END_MODULE_MAP: M-AUTH-TG.service

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Final
from urllib.parse import parse_qsl

from app.core.config import settings


@dataclass(frozen=True)
class TelegramUser:
    """Subset of Telegram's `user` object we trust after HMAC verify."""

    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool | None = None


class TelegramAuthError(Exception):
    """Raised when initData fails parsing, HMAC, or freshness checks.

    `code` is one of the contract-stable strings:
        INVALID_HMAC | MISSING_FIELDS | INITDATA_EXPIRED | MALFORMED_INITDATA
    """

    _ALLOWED: Final[frozenset[str]] = frozenset(
        {"INVALID_HMAC", "MISSING_FIELDS", "INITDATA_EXPIRED", "MALFORMED_INITDATA"}
    )

    def __init__(self, code: str, message: str) -> None:
        if code not in self._ALLOWED:
            raise ValueError(f"unknown TelegramAuthError code: {code}")
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


_TELEGRAM_SECRET_KEY_SEED: Final[bytes] = b"WebAppData"


# START_BLOCK: INITDATA_PARSE
def _parse_init_data(raw: str) -> dict[str, str]:
    """Decode the raw initData query string into a mapping.

    Telegram sends initData as `application/x-www-form-urlencoded`. We use
    `parse_qsl(strict_parsing=True)` so duplicated/malformed pairs raise
    rather than silently disappear, then enforce uniqueness manually.
    """
    if not raw:
        raise TelegramAuthError("MISSING_FIELDS", "initData is empty")
    try:
        pairs = parse_qsl(raw, strict_parsing=True, keep_blank_values=True)
    except ValueError as exc:
        raise TelegramAuthError(
            "MALFORMED_INITDATA", f"parse_qsl failed: {exc}"
        ) from exc

    out: dict[str, str] = {}
    for k, v in pairs:
        if k in out:
            raise TelegramAuthError(
                "MALFORMED_INITDATA", f"duplicated key: {k}"
            )
        out[k] = v
    if "hash" not in out:
        raise TelegramAuthError("MISSING_FIELDS", "missing `hash`")
    if "auth_date" not in out:
        raise TelegramAuthError("MISSING_FIELDS", "missing `auth_date`")
    return out
# END_BLOCK: INITDATA_PARSE


# START_BLOCK: HMAC_VERIFY
def _expected_hash(parsed: dict[str, str], bot_token: str) -> str:
    """Recompute the HMAC-SHA256 over the canonical data-check-string."""
    items = sorted((k, v) for k, v in parsed.items() if k != "hash")
    data_check_string = "\n".join(f"{k}={v}" for k, v in items)
    secret_key = hmac.new(
        _TELEGRAM_SECRET_KEY_SEED, bot_token.encode("utf-8"), hashlib.sha256
    ).digest()
    return hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def verify_init_data(raw: str) -> TelegramUser:
    # START_FUNCTION_CONTRACT: M-AUTH-TG.service.verify_init_data
    # purpose: Top-level entry: parse, HMAC-verify, freshness-check, then
    #   extract the `user` object. The only function the router should call.
    # inputs: raw (str) — value of the initData payload, untouched.
    # returns: TelegramUser with at least `id` populated.
    # side_effects: none.
    # error_behavior: raises TelegramAuthError on any defect; never returns None.
    # END_FUNCTION_CONTRACT: M-AUTH-TG.service.verify_init_data

    parsed = _parse_init_data(raw)

    bot_token = settings.telegram_bot_token
    if not bot_token:
        if settings.app_env != "dev":
            raise TelegramAuthError(
                "INVALID_HMAC",
                "TELEGRAM_BOT_TOKEN is empty in non-dev environment",
            )
        # Dev bypass: skip HMAC; freshness still enforced below.
    else:
        expected = _expected_hash(parsed, bot_token)
        if not hmac.compare_digest(expected, parsed["hash"]):
            raise TelegramAuthError(
                "INVALID_HMAC", "signature does not match"
            )

    # Freshness — even with a valid HMAC an old payload is a replay risk.
    try:
        auth_date = int(parsed["auth_date"])
    except ValueError as exc:
        raise TelegramAuthError(
            "MALFORMED_INITDATA", "auth_date is not an int"
        ) from exc
    age = int(time.time()) - auth_date
    if age < 0:
        raise TelegramAuthError(
            "MALFORMED_INITDATA", "auth_date is in the future"
        )
    if age > settings.telegram_auth_max_age_seconds:
        raise TelegramAuthError(
            "INITDATA_EXPIRED",
            f"auth_date is older than {settings.telegram_auth_max_age_seconds}s",
        )

    user_raw = parsed.get("user")
    if not user_raw:
        raise TelegramAuthError("MISSING_FIELDS", "missing `user` payload")
    try:
        user_obj = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise TelegramAuthError(
            "MALFORMED_INITDATA", f"user is not JSON: {exc}"
        ) from exc
    if not isinstance(user_obj, dict) or "id" not in user_obj:
        raise TelegramAuthError("MISSING_FIELDS", "user payload missing `id`")
    try:
        tg_id = int(user_obj["id"])
    except (TypeError, ValueError) as exc:
        raise TelegramAuthError(
            "MALFORMED_INITDATA", "user.id is not an int"
        ) from exc

    return TelegramUser(
        id=tg_id,
        first_name=user_obj.get("first_name"),
        last_name=user_obj.get("last_name"),
        username=user_obj.get("username"),
        language_code=user_obj.get("language_code"),
        is_premium=user_obj.get("is_premium"),
    )
# END_BLOCK: HMAC_VERIFY
