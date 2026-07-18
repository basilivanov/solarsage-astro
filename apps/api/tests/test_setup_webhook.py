# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_SETUP_WEBHOOK
# ROLE: Contract tests for the manual-gated webhook registration tool.
# DEPENDENCIES: pytest, unittest.mock, stdlib importlib
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-SETUP-WEBHOOK
# purpose: Prove the webhook tool validates offline with no HTTP, gates
#   mutations behind identity and --manual-confirm, sends the exact setWebhook
#   payload (url, allowed_updates=["message"], drop_pending_updates, secret
#   redacted from output), sets exactly /start, reads both back exactly, and
#   never leaks token or secret.
# owns:
#   - apps/api/tests/test_setup_webhook.py
# inputs: module functions of scripts/telegram/setup_webhook.py
# outputs: pytest assertions
# dependencies: repo config scripts/telegram/bot-profile.json
# side_effects: none (HTTP mocked)
# emitted_logs: n/a (tests)
# invariants:
#   - no real Bot API call in tests; secret/token never printed anywhere
# failure_policy: assertion failure on contract violation
# END_MODULE_CONTRACT: M-TEST-SETUP-WEBHOOK

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "telegram"))

import setup_webhook as sw  # noqa: E402

SECRET = "s3cr3t" * 6  # 36 chars, passes the >= 32 gate


@pytest.fixture()
def config() -> dict:
    return sw.load_config(sw.CONFIG_PATH)


@pytest.fixture()
def url(config: dict, monkeypatch) -> str:
    monkeypatch.delenv("WEBAPP_URL", raising=False)
    return sw.webhook_url(config)


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _opener(config: dict, url: str, calls: list, bot_id=None):
    def fake_open(req, timeout=0):
        if isinstance(req, str):
            method, data = req.split("/")[-1], None
        else:
            method = req.full_url.split("/")[-1]
            data = json.loads(req.data.decode("utf-8"))
        calls.append({"method": method, "data": data})
        if method == "getMe":
            return _FakeResponse({"ok": True, "result": {
                "is_bot": True,
                "id": bot_id if bot_id is not None else config["expected_bot_id"],
                "username": config["bot_username"],
            }})
        if method == "getWebhookInfo":
            return _FakeResponse({"ok": True, "result": {
                "url": url, "allowed_updates": ["message"],
                "pending_update_count": 0, "max_connections": 40}})
        if method == "getMyCommands":
            return _FakeResponse({"ok": True, "result": [sw.START_COMMAND]})
        return _FakeResponse({"ok": True, "result": True})
    return fake_open


def test_webhook_url_is_canonical(config: dict, url: str) -> None:
    assert url == "https://astro.vasiliy-ivanov.ru/api/telegram/webhook"


def test_check_mode_performs_no_http(config: dict, url: str, capsys) -> None:
    rc = sw.run_check(config, url)
    assert rc == 0
    out = capsys.readouterr().out
    assert "setWebhook" in out and "setMyCommands" in out
    assert "<redacted>" in out


def test_apply_requires_manual_confirm() -> None:
    with pytest.raises(SystemExit) as exc:
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(sys, "argv", ["setup", "--apply"])
            sw.main()
    assert exc.value.code == 78


def test_apply_exact_payload_and_readback_no_secret_leak(config: dict, url: str, capsys) -> None:
    calls: list[dict] = []
    rc = sw.run_apply(config, "TEST_TOKEN_NEVER_PRINTED", SECRET, url,
                      opener=_opener(config, url, calls))
    assert rc == 0

    methods = [c["method"] for c in calls]
    assert methods == ["getMe", "setWebhook", "setMyCommands", "getWebhookInfo", "getMyCommands"]

    wh = calls[1]["data"]
    assert wh["url"] == url
    assert wh["allowed_updates"] == ["message"]
    assert wh["drop_pending_updates"] is True
    assert wh["secret_token"] == SECRET

    assert calls[2]["data"] == {"commands": [sw.START_COMMAND]}

    out = capsys.readouterr().out
    assert "read-back webhook: exact" in out
    assert "read-back commands: exact" in out
    assert SECRET not in out
    assert "TEST_TOKEN_NEVER_PRINTED" not in out


def test_apply_blocked_on_identity_mismatch(config: dict, url: str) -> None:
    calls: list[dict] = []
    with pytest.raises(SystemExit) as exc:
        sw.run_apply(config, "TEST_TOKEN_NEVER_PRINTED", SECRET, url,
                     opener=_opener(config, url, calls, bot_id=1111111111))
    assert exc.value.code == 78
    assert not [c for c in calls if c["method"].startswith("set")]


def test_secret_gate_minimum_length(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "short")
    with pytest.raises(SystemExit) as exc:
        sw.load_webhook_secret(None)
    assert exc.value.code == 78

    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", SECRET)
    assert sw.load_webhook_secret(None) == SECRET


def test_secret_from_env_file(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
    env_file = tmp_path / "app.env"
    env_file.write_text(f"TELEGRAM_WEBHOOK_SECRET={SECRET}\n", encoding="utf-8")
    assert sw.load_webhook_secret(str(env_file)) == SECRET
    with pytest.raises(SystemExit):
        sw.load_webhook_secret(None)
