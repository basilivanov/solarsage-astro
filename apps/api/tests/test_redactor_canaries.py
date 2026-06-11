
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_REDACTOR_CANARIES
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for redactor_canaries.py behavior
# owns:
#   - apps/api/tests/test_redactor_canaries.py
# inputs: Mocks, fixtures
# outputs: Assertion results
# dependencies: local modules
# side_effects: n/a (tests)
# emitted_logs: n/a (tests)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# AI_HEADER
# module: M-TEST-REDACTOR-CANARIES
# wave: W-1.6
# purpose: Redactor canary tests — every canon §8.4 key and pattern is tested.

from typing import Any

import pytest

from app.core.redactor import (
    redact_dict,
    PII_KEYS,
    ALLOW_KEYS,
    REDACT_PATTERNS,
    _redact_string,
)

REDACTED = "[redacted]"


# ── Key-based redaction canaries ──────────────────────────────────────────

@pytest.mark.parametrize("pii_key", sorted(PII_KEYS))
def test_redact_key(pii_key: str):
    """Every redact key must be replaced by [redacted]."""
    data = {pii_key: "sensitive_value"}
    result = redact_dict(data)
    assert result[pii_key] == REDACTED, f"Key '{pii_key}' was not redacted"


def test_redact_nested():
    """Redaction must recurse into nested dicts."""
    data = {"user": {"email": "test@example.com", "name": "Alice"}}
    result = redact_dict(data)
    assert result["user"]["email"] == REDACTED
    assert result["user"]["name"] == "Alice"


def test_redact_list_of_dicts():
    """Redaction must recurse into lists of dicts."""
    data = {"users": [{"email": "a@b.com"}, {"email": "c@d.com"}]}
    result = redact_dict(data)
    assert result["users"][0]["email"] == REDACTED
    assert result["users"][1]["email"] == REDACTED


def test_redact_case_insensitive():
    """Redact keys are case-insensitive."""
    data = {"EMAIL": "test@example.com", "Api_Key": "secret"}
    result = redact_dict(data)
    assert result["EMAIL"] == REDACTED
    assert result["Api_Key"] == REDACTED


def test_redact_empty_dict():
    """Empty dict must pass through unchanged."""
    assert redact_dict({}) == {}


def test_redact_non_string_primitives():
    """Non-string primitives must pass through unchanged."""
    data = {
        "count": 42,
        "ratio": 3.14,
        "active": True,
        "tags": None,
    }
    result = redact_dict(data)
    assert result["count"] == 42
    assert result["ratio"] == 3.14
    assert result["active"] is True
    assert result["tags"] is None


# ── Allow-key canaries ────────────────────────────────────────────────────

@pytest.mark.parametrize("allow_key", sorted(ALLOW_KEYS))
def test_allow_key_not_redacted(allow_key: str):
    """Allow-list keys must round-trip unchanged."""
    data = {allow_key: "test_value"}
    result = redact_dict(data)
    assert result[allow_key] == "test_value", f"Allow key '{allow_key}' was redacted"


# ── Pattern-based redaction canaries ──────────────────────────────────────

def test_redact_email_pattern():
    """Email pattern must be replaced."""
    text = "Contact me at test.user@example.com for info"
    result = _redact_string(text)
    assert "test.user@example.com" not in result
    assert "[redacted-email]" in result


def test_redact_jwt_pattern():
    """JWT pattern must be replaced."""
    text = "Token: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
    result = _redact_string(text)
    assert "eyJhbGciOiJIUzI1NiJ9" not in result
    assert "[redacted-jwt]" in result


def test_redact_bearer_pattern():
    """Bearer token pattern must be replaced."""
    text = "Authorization: Bearer sk-1234567890abcdef"
    result = _redact_string(text)
    assert "Bearer sk-" not in result
    assert "[redacted-bearer]" in result


def test_redact_bearer_lowercase():
    """Lowercase 'bearer ' must also be redacted."""
    text = "bearer abcdef1234567890"
    result = _redact_string(text)
    assert "[redacted-bearer]" in result


def test_redact_tg_id_pattern():
    """tg_user_id pattern must be replaced."""
    text = "tg_user_id=1234567890"
    result = _redact_string(text)
    assert "1234567890" not in result
    assert "[redacted-tg-id]" in result


def test_redact_ipv4_pattern():
    """IPv4 pattern must be replaced."""
    text = "Client IP: 192.168.1.1"
    result = _redact_string(text)
    assert "192.168.1.1" not in result
    assert "[redacted-ip]" in result


def test_redact_all_patterns_in_text():
    """Multiple PII patterns in a single string must all be redacted."""
    text = "Email: user@test.com, IP: 10.0.0.1"
    result = _redact_string(text)
    assert "[redacted-email]" in result
    assert "[redacted-ip]" in result


# ── Dict-level pattern redaction ──────────────────────────────────────────

def test_redact_dict_patterns():
    """Pattern redaction must apply to string values in dicts."""
    data = {
        "message": "Contact: user@test.com",
        "description": "Bearer abc123",
    }
    result = redact_dict(data)
    assert "[redacted-email]" in result["message"]
    assert result["description"] == "[redacted-bearer]"


# ── Sentinels ─────────────────────────────────────────────────────────────

SENTINELS = [
    "secret@example.com",
    "Bearer abc",
    "tg_user_id=123456",
    "127.0.0.1",
]


@pytest.mark.parametrize("sentinel", SENTINELS)
def test_sentinel_redacted(sentinel: str):
    """Canon sentinels must never appear in redacted output."""
    data = {"test": sentinel}
    result = redact_dict(data)
    assert sentinel not in str(result), f"Sentinel '{sentinel}' found in redacted output"
