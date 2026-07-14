# ############################################################################
# AI_HEADER: MODULE_LOG_IDENTITY — privacy-safe identity logging helper
# ROLE: Provides secure HMAC-SHA256 based identifier hashing to isolate values
#       and prevent raw user/entity IDs leaking to telemetry.
# ############################################################################

# START_MODULE_CONTRACT: M-LOG-IDENTITY
# purpose: HMAC-SHA256 hashing for user and entity identifiers used in logging.
# owns:
#   - apps/api/app/core/log_identity.py
# inputs:
#   - namespace: str (determines hashing isolation)
#   - value: object (the identifier value to hash)
# outputs:
#   - hashed string formatted as h1_ + first 24 lowercase hex chars
# dependencies:
#   - hmac, hashlib, re, uuid
#   - apps.api.app.core.config.settings
# side_effects: none
# emitted_logs: none
# invariants:
#   - HMAC key is settings.grace_user_salt or LOCAL_TEST_LOG_SALT if empty/short.
#   - namespaces isolate hashes (different namespaces give different hashes).
#   - Output is lowercase and starts with "h1_".
#   - Inputs/secrets are never printed/logged in exception paths.
# failure_policy:
#   - Handles non-string values gracefully by string conversion.
#   - Never raises or logs inputs on error, except validation errors in deployed envs.
# END_MODULE_CONTRACT: M-LOG-IDENTITY

# START_MODULE_MAP: M-LOG-IDENTITY
# public_entrypoints:
#   - hash_log_identifier
#   - hash_user_id
#   - new_correlation_id
#   - normalize_correlation_id
#   - is_opaque_log_id
# semantic_blocks:
#   - HASHING_LOGIC: HMAC-SHA256 calculation and formatting
#   - CORRELATION_HELPERS: correlation_id creation and normalization
# owned_tests:
#   - apps/api/tests/test_logging.py
# END_MODULE_MAP: M-LOG-IDENTITY

import hashlib
import hmac
import re
import uuid

from app.core.config import settings

LOCAL_TEST_LOG_SALT = "local-development-fallback-test-salt-32-chars-long"
NAMESPACE_PATTERN = re.compile(r"^[a-z0-9_-]+$")
OPAQUE_LOG_ID_PATTERN = re.compile(r"^h1_[0-9a-f]{24}$")


def is_opaque_log_id(value: object) -> bool:
    # START_FUNCTION_CONTRACT: F-M-LOG-IDENTITY.is_opaque_log_id
    # purpose: Determine if the value matches the exact h1_[0-9a-f]{24} format.
    # inputs: value — object to check.
    # returns: bool — True if it matches exactly.
    # side_effects: none
    # emitted_logs: none
    # error_behavior: never raises.
    # END_FUNCTION_CONTRACT: F-M-LOG-IDENTITY.is_opaque_log_id
    return isinstance(value, str) and OPAQUE_LOG_ID_PATTERN.fullmatch(value) is not None


# START_BLOCK: HASHING_LOGIC
def hash_log_identifier(namespace: str, value: object) -> str:
    # START_FUNCTION_CONTRACT: F-M-LOG-IDENTITY.hash_log_identifier
    # purpose: Hash an identifier securely using HMAC-SHA256 and namespace separation.
    # inputs: namespace — namespace string, value — identifier object.
    # returns: str — hashed identifier.
    # side_effects: none
    # emitted_logs: none
    # error_behavior: returns fallback/empty hash on extreme error, never raises except validation/salt issues in deployed envs.
    # END_FUNCTION_CONTRACT: F-M-LOG-IDENTITY.hash_log_identifier

    # Normalize environment and check if deployed
    env = settings.app_env.strip().lower() if settings.app_env else "development"
    deployed = env in ("stage", "staging", "preview", "prod", "production")

    # 1. Namespace validation
    if not namespace or not isinstance(namespace, str):
        raise ValueError("Namespace must be a non-empty string")

    ns_clean = namespace.strip().lower()
    if not NAMESPACE_PATTERN.fullmatch(ns_clean):
        raise ValueError("Namespace must match [a-z0-9_-]+")

    # 2. Salt validation
    salt = settings.grace_user_salt
    if len(salt) < 32:
        if deployed:
            raise ValueError("GRACE_USER_SALT must be at least 32 characters long in deployed environment")
        salt = LOCAL_TEST_LOG_SALT

    try:
        val_str = str(value)
        key_bytes = salt.encode("utf-8")
        msg_bytes = f"{ns_clean}:{val_str}".encode("utf-8")

        h = hmac.new(key_bytes, msg_bytes, hashlib.sha256)
        hex_digest = h.hexdigest()

        return f"h1_{hex_digest[:24].lower()}"
    except Exception as e:
        if deployed:
            raise RuntimeError("HMAC calculation failed in deployed environment") from e

        try:
            # Deterministic fallback h1_ from static safe marker
            fallback_key = LOCAL_TEST_LOG_SALT.encode("utf-8")
            fallback_msg = f"fallback:{hashlib.sha256(str(value).encode('utf-8')).hexdigest()}".encode("utf-8")
            h = hmac.new(fallback_key, fallback_msg, hashlib.sha256)
            return f"h1_{h.hexdigest()[:24].lower()}"
        except Exception:
            # Absolute static fallback that is a valid h1_ format
            return "h1_000000000000000000000000"


def hash_user_id(value: object) -> str:
    # START_FUNCTION_CONTRACT: F-M-LOG-IDENTITY.hash_user_id
    # purpose: Helper specifically for user_id hashing.
    # inputs: value — user identifier.
    # returns: str — hashed user identifier.
    # side_effects: none
    # emitted_logs: none
    # error_behavior: never raises except validation/salt issues in deployed envs.
    # END_FUNCTION_CONTRACT: F-M-LOG-IDENTITY.hash_user_id
    return hash_log_identifier("user", value)
# END_BLOCK: HASHING_LOGIC


# START_BLOCK: CORRELATION_HELPERS
def new_correlation_id() -> str:
    # START_FUNCTION_CONTRACT: F-M-LOG-IDENTITY.new_correlation_id
    # purpose: Generate a new safe correlation ID formatted as h1_ + 24 lowercase hex chars.
    # inputs: none
    # returns: str — normalized correlation ID.
    # side_effects: none
    # emitted_logs: none
    # error_behavior: never raises except validation/salt issues in deployed envs.
    # END_FUNCTION_CONTRACT: F-M-LOG-IDENTITY.new_correlation_id
    gen_uuid = str(uuid.uuid4())
    return hash_log_identifier("correlation", gen_uuid)


def normalize_correlation_id(raw: object | None) -> str:
    # START_FUNCTION_CONTRACT: F-M-LOG-IDENTITY.normalize_correlation_id
    # purpose: Normalize any correlation ID to be opaque h1_[0-9a-f]{24}.
    # inputs: raw — raw correlation ID object or None.
    # returns: str — normalized correlation ID.
    # side_effects: none
    # emitted_logs: none
    # error_behavior: never raises except validation/salt issues in deployed envs.
    # END_FUNCTION_CONTRACT: F-M-LOG-IDENTITY.normalize_correlation_id
    if not raw:
        return new_correlation_id()

    raw_str = str(raw).strip()
    if not raw_str:
        return new_correlation_id()

    # Check if already a valid h1_ format
    if is_opaque_log_id(raw_str):
        return raw_str

    # Oversized or control/non-printable character check
    if len(raw_str) > 100 or any(ord(c) < 32 or ord(c) > 126 for c in raw_str):
        return new_correlation_id()

    # Hash the printable caller value
    return hash_log_identifier("correlation", raw_str)
# END_BLOCK: CORRELATION_HELPERS
