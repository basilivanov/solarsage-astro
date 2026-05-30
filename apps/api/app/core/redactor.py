# ############################################################################
# AI_HEADER: MODULE_OBSERVABILITY_REDACTOR
# ROLE: PII redaction for logging and telemetry.
# DEPENDENCIES: re, typing
# GRACE_ANCHORS: [PII_KEYS, REDACT_DICT]
# WAVE: W-1.6
# ############################################################################

# START_MODULE_CONTRACT: M-OBSERVABILITY-REDACTOR
# purpose: Redact PII from dictionaries before logging or telemetry emission.
# owns:
#   - apps/api/app/core/redactor.py
# inputs:
#   - data: Dict[str, Any] containing potentially sensitive fields
# outputs:
#   - redacted: Dict[str, Any] with PII replaced by "[REDACTED]"
# dependencies:
#   - standard library: re, typing
# side_effects:
#   - none (pure function)
# invariants:
#   - PII_KEYS defines exhaustive list of sensitive field names
#   - redaction is case-insensitive
#   - nested dicts and lists are recursively redacted
# failure_policy:
#   - unknown types are passed through unchanged
# non_goals:
#   - no pattern-based redaction (e.g., regex for emails)
#   - no semantic analysis (deferred to W-CANON-LOG)
# END_MODULE_CONTRACT: M-OBSERVABILITY-REDACTOR

from typing import Any, Dict, List


# START_BLOCK: PII_KEYS
# PII keys to redact (case-insensitive)
PII_KEYS = {
    "password",
    "token",
    "api_key",
    "secret",
    "birth_date",
    "birth_time",
    "birth_lat",
    "birth_lon",
    "tg_user_id",
    "tg_username",
}
# END_BLOCK: PII_KEYS


# START_BLOCK: REDACT_DICT
def redact_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Redact PII from dictionary.

    Args:
        data: Dictionary potentially containing PII.

    Returns:
        New dictionary with PII fields replaced by "[REDACTED]".

    Examples:
        >>> redact_dict({"username": "test", "password": "secret"})
        {"username": "test", "password": "[REDACTED]"}

        >>> redact_dict({"user": {"name": "test", "token": "abc"}})
        {"user": {"name": "test", "token": "[REDACTED]"}}
    """
    redacted = {}

    for key, value in data.items():
        if key.lower() in PII_KEYS:
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = redact_dict(value)
        elif isinstance(value, list):
            redacted[key] = [
                redact_dict(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            redacted[key] = value

    return redacted
# END_BLOCK: REDACT_DICT
