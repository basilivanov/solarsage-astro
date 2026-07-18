# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_SYNC_BOT_PROFILE
# ROLE: Contract tests for the manual-gated bot profile sync script.
# DEPENDENCIES: pytest, unittest.mock, stdlib importlib
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-SYNC-BOT-PROFILE
# purpose: Prove the bot profile config validates, --check performs no HTTP,
#   --apply requires --manual-confirm, exact three Bot API calls are built with
#   exact payloads, the token never leaks into output, length limits and the
#   tone rule fail closed, start_copy is never synced, and the WebApp target is
#   the canonical absolute WEBAPP_URL + /day/today (never a t.me deep-link).
# owns:
#   - apps/api/tests/test_sync_bot_profile.py
# inputs: module functions of scripts/telegram/sync_bot_profile.py
# outputs: pytest assertions
# dependencies: repo config scripts/telegram/bot-profile.json
# side_effects: none (HTTP mocked)
# emitted_logs: n/a (tests)
# invariants:
#   - no real Bot API call in tests; token never printed anywhere
# failure_policy: assertion failure on contract violation
# END_MODULE_CONTRACT: M-TEST-SYNC-BOT-PROFILE

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "telegram"))

import sync_bot_profile as sbp  # noqa: E402


@pytest.fixture()
def config() -> dict:
    return sbp.load_config(sbp.CONFIG_PATH)


@pytest.fixture()
def webapp_url(config: dict, monkeypatch) -> str:
    monkeypatch.delenv("WEBAPP_URL", raising=False)
    return sbp.load_webapp_url(config, None)


def test_repo_config_is_valid(config: dict, webapp_url: str) -> None:
    sbp.validate_config(config)
    ops = sbp.build_operations(config, webapp_url)
    assert [op["method"] for op in ops] == ["setMyShortDescription", "setMyDescription", "setChatMenuButton"]


def test_menu_url_is_canonical_webapp_plus_day_path(config: dict, webapp_url: str) -> None:
    # Contract: the WebApp target is the canonical absolute WEBAPP_URL + /day/today,
    # never a t.me deep-link. Canonical base is the public prod domain (also in
    # docs/PRODUCTION_RUNBOOK.md and infra/nginx), not a secret.
    assert webapp_url == "https://astro.vasiliy-ivanov.ru/day/today"
    assert webapp_url.startswith("https://")
    assert "t.me" not in webapp_url
    assert webapp_url.endswith(config["day_path"])
    ops = sbp.build_operations(config, webapp_url)
    assert ops[2]["payload"]["menu_button"]["web_app"]["url"] == webapp_url


def test_webapp_url_env_override(config: dict, monkeypatch) -> None:
    monkeypatch.setenv("WEBAPP_URL", "https://dev.astro.vasiliy-ivanov.ru/")
    assert sbp.load_webapp_url(config, None) == "https://dev.astro.vasiliy-ivanov.ru/day/today"


def test_webapp_url_from_env_file(config: dict, tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("WEBAPP_URL", raising=False)
    env_file = tmp_path / "app.env"
    env_file.write_text("WEBAPP_URL=https://staging.example.ru\n", encoding="utf-8")
    assert sbp.load_webapp_url(config, str(env_file)) == "https://staging.example.ru/day/today"


def test_copy_length_limits_hold(config: dict) -> None:
    assert len(config["short_description"]) <= sbp.SHORT_DESCRIPTION_LIMIT
    assert len(config["description"]) <= sbp.DESCRIPTION_LIMIT
    assert len(config["menu_button"]["text"]) <= sbp.MENU_TEXT_LIMIT
    assert len(config["start_copy"]["text"]) <= sbp.START_TEXT_LIMIT


def test_tone_rule_word_goroskop_only_with_negation(config: dict) -> None:
    for field in ("short_description", "description"):
        value = config[field]
        idx = value.find("гороскоп")
        if idx != -1:
            window = value[max(0, idx - 30):idx]
            assert "Не " in window or "не " in window, f"«гороскоп» without negation in {field}"


def test_check_mode_performs_no_http_and_prints_ops(config: dict, webapp_url: str, capsys) -> None:
    with patch.object(sbp.urllib.request, "urlopen", side_effect=AssertionError("HTTP must not happen in --check")):
        rc = sbp.run_check(config, webapp_url)
    assert rc == 0
    out = capsys.readouterr().out
    assert "setMyShortDescription" in out
    assert "setMyDescription" in out
    assert "setChatMenuButton" in out
    assert "NOT synced" in out
    assert webapp_url in out
    assert "t.me" not in out


def test_apply_requires_manual_confirm() -> None:
    with pytest.raises(SystemExit) as exc:
        with patch.object(sys, "argv", ["sync", "--apply"]):
            sbp.main()
    assert exc.value.code == 78


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_apply_makes_exact_three_calls_with_exact_payloads_and_no_token_leak(config: dict, webapp_url: str, capsys) -> None:
    calls: list[dict] = []

    def fake_open(req, timeout=0):
        calls.append({"url": req.full_url, "data": json.loads(req.data.decode("utf-8"))})
        return _FakeResponse({"ok": True, "result": True})

    rc = sbp.run_apply(config, "TEST_TOKEN_NEVER_PRINTED", webapp_url, opener=fake_open)
    assert rc == 0

    assert len(calls) == 3
    methods = [c["url"].split("/")[-1] for c in calls]
    assert methods == ["setMyShortDescription", "setMyDescription", "setChatMenuButton"]

    assert calls[0]["data"] == {"short_description": config["short_description"]}
    assert calls[1]["data"] == {"description": config["description"]}
    assert calls[2]["data"]["menu_button"]["type"] == "web_app"
    assert calls[2]["data"]["menu_button"]["text"] == config["menu_button"]["text"]
    assert calls[2]["data"]["menu_button"]["web_app"]["url"] == webapp_url

    out = capsys.readouterr().out
    assert "TEST_TOKEN_NEVER_PRINTED" not in out
    assert "botTEST_TOKEN_NEVER_PRINTED" not in out


def test_start_copy_is_never_synced(config: dict, webapp_url: str) -> None:
    calls: list[str] = []

    def fake_open(req, timeout=0):
        calls.append(req.full_url)
        return _FakeResponse({"ok": True, "result": True})

    sbp.run_apply(config, "TEST_TOKEN_NEVER_PRINTED", webapp_url, opener=fake_open)
    assert not any("start" in url.lower() for url in calls)
    assert all(url.split("/")[-1] in sbp.SYNCED_METHODS for url in calls)


def test_validation_fails_closed_on_limits(config: dict) -> None:
    bad = dict(config)
    bad["short_description"] = "x" * (sbp.SHORT_DESCRIPTION_LIMIT + 1)
    with pytest.raises(SystemExit) as exc:
        sbp.validate_config(bad)
    assert exc.value.code == 78

    bad2 = dict(config)
    bad2["description"] = "x" * (sbp.DESCRIPTION_LIMIT + 1)
    with pytest.raises(SystemExit) as exc2:
        sbp.validate_config(bad2)
    assert exc2.value.code == 78


def test_validation_fails_closed_on_tone_violation(config: dict) -> None:
    bad = dict(config)
    bad["description"] = "Ваш гороскоп на сегодня от наших астрологов."
    with pytest.raises(SystemExit) as exc:
        sbp.validate_config(bad)
    assert exc.value.code == 78


def test_token_from_env_file_only(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / "app.env"
    env_file.write_text("TELEGRAM_BOT_TOKEN=from-env-file\n", encoding="utf-8")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert sbp.load_token(str(env_file)) == "from-env-file"
    with pytest.raises(SystemExit) as exc:
        sbp.load_token(None)
    assert exc.value.code == 78
