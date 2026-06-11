
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_TELEGRAM_HMAC
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for telegram_hmac.py behavior
# owns:
#   - apps/api/tests/test_telegram_hmac.py
# inputs: Mocks, fixtures
# outputs: Assertion results
# dependencies: local modules
# side_effects: n/a (tests)
# emitted_logs: n/a (tests)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
"""Unit tests for the HMAC verifier in app.services.telegram_auth.

W-1.2 ## Decision: codes are
    INVALID_HMAC | MISSING_FIELDS | INITDATA_EXPIRED | MALFORMED_INITDATA.
"""
from __future__ import annotations

import time

import pytest

from app.core.config import settings
from app.services.telegram_auth import TelegramAuthError, verify_init_data
from tests.conftest import fake_initdata


def test_happy_path() -> None:
    raw = fake_initdata(user_id=42, first_name="Grace", username="grace")
    tu = verify_init_data(raw)
    assert tu.id == 42
    assert tu.first_name == "Grace"
    assert tu.username == "grace"


def test_invalid_hmac() -> None:
    raw = fake_initdata(user_id=1)
    bad = raw.replace("hash=", "hash=0", 1)
    if bad == raw:
        bad = raw[:-1] + ("0" if raw[-1] != "0" else "1")
    with pytest.raises(TelegramAuthError) as exc:
        verify_init_data(bad)
    assert exc.value.code == "INVALID_HMAC"


def test_missing_fields_no_hash() -> None:
    raw = "auth_date=1&user=%7B%22id%22%3A1%7D"
    with pytest.raises(TelegramAuthError) as exc:
        verify_init_data(raw)
    assert exc.value.code == "MISSING_FIELDS"


def test_missing_fields_no_user() -> None:
    # Hand-craft a valid HMAC over a payload that omits the required
    # ``user`` field; verify_init_data must still reject it.
    from tests.conftest import _sign

    parsed = {"auth_date": str(int(time.time())), "query_id": "x"}
    parsed["hash"] = _sign(parsed)
    raw_no_user = "&".join(f"{k}={v}" for k, v in parsed.items())
    with pytest.raises(TelegramAuthError) as exc:
        verify_init_data(raw_no_user)
    assert exc.value.code == "MISSING_FIELDS"


def test_initdata_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "telegram_auth_max_age_seconds", 60)
    old = int(time.time()) - 3600
    raw = fake_initdata(user_id=1, auth_date=old)
    with pytest.raises(TelegramAuthError) as exc:
        verify_init_data(raw)
    assert exc.value.code == "INITDATA_EXPIRED"


def test_malformed_initdata_empty() -> None:
    with pytest.raises(TelegramAuthError) as exc:
        verify_init_data("")
    # Empty payload reports MISSING_FIELDS per the contract.
    assert exc.value.code == "MISSING_FIELDS"


def test_malformed_initdata_bad_user_json() -> None:
    # auth_date present, hash present, user is not JSON.
    from tests.conftest import _sign

    parsed = {
        "auth_date": str(int(time.time())),
        "query_id": "x",
        "user": "not-json",
    }
    parsed["hash"] = _sign(parsed)
    raw = "&".join(f"{k}={v}" for k, v in parsed.items())
    with pytest.raises(TelegramAuthError) as exc:
        verify_init_data(raw)
    assert exc.value.code == "MALFORMED_INITDATA"
