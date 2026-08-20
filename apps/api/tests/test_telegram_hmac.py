
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
from pathlib import Path

import pytest

from app.core.config import settings
from app.services.telegram_auth import (
    TelegramAuthError,
    parse_start_param,
    verify_init_data,
)
from tests.conftest import fake_initdata

# Define PROJECT_ROOT for the new env test
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def test_happy_path() -> None:
    raw = fake_initdata(user_id=42, first_name="Grace", username="grace")
    tu = verify_init_data(raw)
    assert tu.id == 42
    assert tu.first_name == "Grace"
    assert tu.username == "grace"
    assert parse_start_param(raw) is None


def test_parse_start_param() -> None:
    raw = fake_initdata(user_id=42, start_param="sfnqpmfdwkuk")
    assert parse_start_param(raw) == "sfnqpmfdwkuk"

    raw_no_param = fake_initdata(user_id=42)
    assert parse_start_param(raw_no_param) is None


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


def test_generate_initdata_default_safety() -> None:
    """Ensure the default generated initData does not contain the real Basil user ID."""
    import subprocess
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parent.parent.parent.parent
    script_path = project_root / "scripts" / "generate-telegram-test-initdata.py"

    # Run the script with environment variable set
    import os
    test_env = {**os.environ, "TELEGRAM_BOT_TOKEN": "dummy_env_token_value_for_test"}
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(project_root),
        env=test_env
    )
    output = result.stdout
    assert "833478509" not in output, "Default generated initData contains the real user ID 833478509!"
    assert "testuser" not in output, "Default generated initData contains the real username 'testuser'!"
    assert "999999999" in output, "Default generated initData should use synthetic user ID 999999999."
    assert "synthetic_test_user" in output, "Default generated initData should use username 'synthetic_test_user'."
    assert "dummy_env_token_value_for_test" not in output, "Token leaked in stdout!"
    assert "dummy_env_token_value_for_test" not in result.stderr, "Token leaked in stderr!"


def test_generate_initdata_env_first(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test load_bot_token prioritizing process env and falling back to file safely."""
    import sys
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    import importlib.util

    script_file = PROJECT_ROOT / "scripts" / "generate-telegram-test-initdata.py"
    spec = importlib.util.spec_from_file_location("generate_initdata_mod", str(script_file))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # 1. Environment variable exists
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token_from_env")
    assert mod.load_bot_token() == "token_from_env"

    # 2. Environment variable empty, test explicit env_file_path
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    # Missing file -> FileNotFoundError
    nonexistent = tmp_path / "nonexistent.env"
    with pytest.raises(FileNotFoundError):
        mod.load_bot_token(env_file_path=str(nonexistent))

    # File exists with token
    env_prod = tmp_path / "test.env"
    env_prod.write_text("TELEGRAM_BOT_TOKEN=token_from_file\n", encoding="utf-8")
    assert mod.load_bot_token(env_file_path=str(env_prod)) == "token_from_file"

    # File exists without token -> ValueError
    env_prod.write_text("SOME_OTHER_VAR=value\n", encoding="utf-8")
    with pytest.raises(ValueError):
        mod.load_bot_token(env_file_path=str(env_prod))
