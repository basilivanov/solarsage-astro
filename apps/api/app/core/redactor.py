# ############################################################################
# AI_HEADER: MODULE_OBSERVABILITY_REDACTOR
# ROLE: PII redaction for logging and telemetry — canon §8.4 parity.
# DEPENDENCIES: re, typing
# GRACE_ANCHORS: [PII_KEYS, REDACT_DICT, REDACT_PATTERNS, REDACT_STRING]
# WAVE: W-1.6
# ############################################################################

# START_MODULE_CONTRACT: M-OBSERVABILITY-REDACTOR
# purpose: Redact PII from dictionaries before logging or telemetry emission.
#   Covers canon §8.4 exhaustive key list + value-based pattern redaction.
# owns:
#   - apps/api/app/core/redactor.py
# inputs:
#   - data: Any (dict, list, string, or primitive) potentially containing PII
# outputs:
#   - redacted: same shape with PII replaced by "[redacted]" markers
# dependencies:
#   - standard library: re, typing
# side_effects:
#   - none (pure function)
# invariants:
#   - PII_KEYS defines exhaustive list of sensitive field names (canon §8.4)
#   - redaction is case-insensitive
#   - nested dicts and lists are recursively redacted
#   - value-based patterns match canon §8.4 patterns
#   - allow-keys are never redacted
# failure_policy:
#   - unknown types are passed through unchanged
# END_MODULE_CONTRACT: M-OBSERVABILITY-REDACTOR

from __future__ import annotations

import re
from typing import Any


# START_BLOCK: PII_KEYS
# Canon §8.4 redact-keys — case-insensitive exact match at any depth
PII_KEYS = {
    # user-pii (snake_case + camelCase/lowercase)
    "note", "email", "phone", "full_name", "first_name", "last_name", "display_name",
    "fullname", "firstname", "lastname", "displayname",
    # telegram
    "tg_user_id", "telegram_id", "tg_username", "username", "init_data",
    "tg_init_data", "hash", "auth_date",
    "tguserid", "telegramid", "tgusername", "initdata", "tginitdata", "authdate",
    # birth-data
    "birth_date", "birth_time", "birth_place", "place", "lat", "latitude",
    "birthdate", "birthtime", "birthplace", "lng", "longitude", "tz", "timezone",
    # auth-secrets
    "password", "password_hash", "token", "access_token", "refresh_token",
    "passwordhash", "accesstoken", "refreshtoken",
    "session_token", "bot_token", "api_key", "secret", "authorization",
    "sessiontoken", "bottoken", "apikey", "cookie", "set-cookie", "setcookie",
    # payments
    "payment_id", "provider_payment_id", "receipt", "card", "card_number",
    "paymentid", "providerpaymentid", "cardnumber",
    "cvv", "pan", "iban",
    # network
    "ip", "remote_addr", "x-forwarded-for", "user_agent",
    "remoteaddr", "xforwardedfor", "useragent",
}
# END_BLOCK: PII_KEYS

# START_BLOCK: ALLOW_KEYS
# Canon §8.4 allow-list — these keys are never redacted even if key name matches
ALLOW_KEYS: set[str] = {
    "correlation_id", "session_id", "packet_id", "user_id_hash",
    "service", "service_version", "route", "method", "status",
    "duration_ms", "contract_version", "calculation_version", "prompt_version",
}
# END_BLOCK: ALLOW_KEYS

# START_BLOCK: REDACT_PATTERNS
# Canon §8.4 value-based patterns — applied to all string values
REDACT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Order matters: more specific patterns first
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"), "[redacted-jwt]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[redacted-email]"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]+\b"), "[redacted-bearer]"),
    (re.compile(r"\btg_user_id[=:\s]+\d{5,}\b"), "[redacted-tg-id]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[redacted-ip]"),
]
# END_BLOCK: REDACT_PATTERNS


# START_BLOCK: REDACT_DICT
def redact_dict(data: Any) -> Any:
    """Recursively redact PII from a nested dict/list/string/primitive.

    Args:
        data: Input data structure.

    Returns:
        Redacted copy with PII replaced by "[redacted]" markers.
    """
    if isinstance(data, dict):
        redacted: dict[str, Any] = {}
        for key, value in data.items():
            key_lower = str(key).lower()
            if key_lower in ALLOW_KEYS:
                redacted[key] = value
            elif key_lower in PII_KEYS:
                redacted[key] = "[redacted]"
            elif isinstance(value, (dict, list)):
                redacted[key] = redact_dict(value)
            elif isinstance(value, str):
                redacted[key] = _redact_string(value)
            else:
                redacted[key] = value
        return redacted

    if isinstance(data, list):
        return [redact_dict(item) for item in data]

    if isinstance(data, str):
        return _redact_string(data)

    return data
# END_BLOCK: REDACT_DICT


# START_BLOCK: REDACT_STRING
def _redact_string(value: str) -> str:
    """Apply value-based pattern redaction to a string.

    Args:
        value: Input string.

    Returns:
        String with PII patterns replaced by markers.
    """
    result = value
    for pattern, replacement in REDACT_PATTERNS:
        result = pattern.sub(replacement, result)
    return result
# END_BLOCK: REDACT_STRING
