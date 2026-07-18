#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: TOOL_SYNC_BOT_PROFILE — manual-gated Telegram bot profile sync
# ROLE: Validates the repo-owned bot profile config and, only behind an
#       explicit manual gate, syncs it via Bot API. Never prints the token.
# DEPENDENCIES: python3.12 stdlib only
# ############################################################################

# START_MODULE_CONTRACT: M-TOOL-SYNC-BOT-PROFILE
# purpose: Single repo-owned source for the bot short description, description
#   and chat menu button, plus a manual-gated sync to the Bot API.
# owns:
#   - scripts/telegram/sync_bot_profile.py
# inputs:
#   - --check (default): validate config and print intended operations (no HTTP)
#   - --apply --manual-confirm: validate and POST the three Bot API methods
#   - --env-file <path>: optional env file with TELEGRAM_BOT_TOKEN
#     (and optional WEBAPP_URL override for the menu button target)
# outputs: exit 0 on validated check / applied sync; non-zero otherwise
# dependencies: scripts/telegram/bot-profile.json
# side_effects:
#   - --check: none (validation + stdout only)
#   - --apply: HTTPS POSTs to api.telegram.org (NEVER executed in this slice)
# emitted_logs: none
# invariants:
#   - Token comes only from TELEGRAM_BOT_TOKEN env or an explicit --env-file;
#     it is never printed, logged, or included in any output.
#   - Identity gate (launch-gate doc 81): --apply and --audit FIRST call getMe
#     and fail closed unless ok, is_bot, and the exact expected_bot_id and
#     bot_username from the repo config match. --check stays fully offline.
#   - Every mutation is followed by an exact read-back comparison.
#   - The WebApp target is the canonical absolute WEBAPP_URL + /day/today
#     (config default, overridable via WEBAPP_URL env or --env-file);
#     it is never a t.me deep-link.
#   - Bot API length limits are enforced in check mode before any HTTP:
#     short_description <= 120 chars, description <= 512 chars.
#   - --apply without --manual-confirm exits 78 with no HTTP performed.
#   - start_copy is validated and reported but NOT synced (no production
#     message responder: ductor-astro is inactive on prod and Ductor has no
#     supported start-copy override; see work report blocker).
# failure_policy: exit 78 on any validation, confirmation, token or HTTP failure.
# END_MODULE_CONTRACT: M-TOOL-SYNC-BOT-PROFILE

# START_MODULE_MAP: M-TOOL-SYNC-BOT-PROFILE
# public_entrypoints:
#   - main
# semantic_blocks:
#   - CONFIG_LOAD: parse and validate bot-profile.json
#   - TOKEN_LOAD: resolve token from env/explicit env-file only
#   - WEBAPP_URL: compose canonical WebApp target URL
#   - IDENTITY_AUDIT: getMe proof + read-only online audit
#   - CHECK_MODE: validate and print intended operations
#   - APPLY_MODE: manual-gated Bot API POSTs with exact read-back
# owned_tests:
#   - apps/api/tests/test_sync_bot_profile.py
# END_MODULE_MAP: M-TOOL-SYNC-BOT-PROFILE

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

# START_BLOCK: CONSTANTS
CONFIG_PATH = Path(__file__).resolve().parent / "bot-profile.json"
API_BASE = "https://api.telegram.org"
SHORT_DESCRIPTION_LIMIT = 120
DESCRIPTION_LIMIT = 512
MENU_TEXT_LIMIT = 64
START_TEXT_LIMIT = 4096
SYNCED_METHODS = ("setMyShortDescription", "setMyDescription", "setChatMenuButton")


def die(message: str) -> None:
    sys.stderr.write(f"Error: {message}\n")
    sys.exit(78)
# END_BLOCK: CONSTANTS


# START_BLOCK: CONFIG_LOAD
def load_config(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        die(f"bot profile config is missing or not a regular file: {path}")
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        die(f"bot profile config is not valid JSON: {exc}")
    if not isinstance(config, dict):
        die("bot profile config must be a JSON object")
    if config.get("schema") != "solarsage-bot-profile/v1":
        die("bot profile config schema must be solarsage-bot-profile/v1")
    username = config.get("bot_username")
    if not isinstance(username, str) or not username.strip():
        die("bot_username must be a non-empty string")
    expected_id = config.get("expected_bot_id")
    if not isinstance(expected_id, int) or expected_id <= 0:
        die("expected_bot_id must be a positive integer")
    return config


def validate_config(config: dict) -> None:
    short = config.get("short_description")
    if not isinstance(short, str) or not short.strip():
        die("short_description must be a non-empty string")
    if len(short) > SHORT_DESCRIPTION_LIMIT:
        die(f"short_description exceeds {SHORT_DESCRIPTION_LIMIT} chars ({len(short)})")
    desc = config.get("description")
    if not isinstance(desc, str) or not desc.strip():
        die("description must be a non-empty string")
    if len(desc) > DESCRIPTION_LIMIT:
        die(f"description exceeds {DESCRIPTION_LIMIT} chars ({len(desc)})")
    menu = config.get("menu_button")
    if not isinstance(menu, dict):
        die("menu_button must be an object")
    if menu.get("type") != "web_app":
        die("menu_button.type must be web_app")
    text = menu.get("text")
    if not isinstance(text, str) or not text.strip():
        die("menu_button.text must be a non-empty string")
    if len(text) > MENU_TEXT_LIMIT:
        die(f"menu_button.text exceeds {MENU_TEXT_LIMIT} chars")
    base = config.get("webapp_url")
    if not isinstance(base, str) or not base.startswith("https://"):
        die("webapp_url must be an https URL")
    day_path = config.get("day_path")
    if not isinstance(day_path, str) or not day_path.startswith("/") or "?" in day_path or "#" in day_path:
        die("day_path must be an absolute path without query/fragment")
    start = config.get("start_copy")
    if not isinstance(start, dict) or not isinstance(start.get("text"), str) or not start["text"].strip():
        die("start_copy.text must be a non-empty string")
    if len(start["text"]) > START_TEXT_LIMIT:
        die(f"start_copy.text exceeds {START_TEXT_LIMIT} chars")
    cta = start.get("cta")
    if not isinstance(cta, dict) or not isinstance(cta.get("text"), str) or not cta["text"].strip():
        die("start_copy.cta.text must be a non-empty string")
    # Tone guard: the word «гороскоп» may appear only with a negation nearby.
    for field, value in (("short_description", short), ("description", desc), ("start_copy.text", start["text"])):
        idx = value.find("гороскоп")
        if idx != -1:
            window = value[max(0, idx - 30):idx]
            if "Не " not in window and "не " not in window:
                die(f"tone violation: «гороскоп» without negation in {field}")
# END_BLOCK: CONFIG_LOAD


# START_BLOCK: TOKEN_LOAD
def load_token(env_file: str | None) -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if token:
        return token
    if env_file:
        path = Path(env_file)
        if not path.is_file() or path.is_symlink():
            die(f"env file is missing or not a regular file: {env_file}")
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                value = line.split("=", 1)[1].strip().strip('"')
                if value:
                    return value
        die(f"TELEGRAM_BOT_TOKEN not found in env file: {env_file}")
    die("TELEGRAM_BOT_TOKEN is required (export it or pass --env-file); it is never printed")
# END_BLOCK: TOKEN_LOAD


# START_BLOCK: WEBAPP_URL
def load_webapp_url(config: dict, env_file: str | None) -> str:
    # START_FUNCTION_CONTRACT: F-M-TOOL-SYNC-BOT-PROFILE.load_webapp_url
    # purpose: Compose the canonical WebApp target URL for the menu button
    #   and start CTA: absolute WEBAPP_URL + config day_path.
    # inputs: config — validated bot profile config; env_file — optional env path.
    # returns: https URL string, e.g. https://astro.vasiliy-ivanov.ru/day/today.
    # side_effects: reads WEBAPP_URL from process env or the optional env file.
    # emitted_logs: none.
    # error_behavior: dies (exit 78) if the resolved URL is not https.
    # END_FUNCTION_CONTRACT: F-M-TOOL-SYNC-BOT-PROFILE.load_webapp_url
    override = os.environ.get("WEBAPP_URL", "").strip()
    if not override and env_file:
        path = Path(env_file)
        if path.is_file() and not path.is_symlink():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("WEBAPP_URL="):
                    override = line.split("=", 1)[1].strip().strip('"')
                    break
    base = (override or config["webapp_url"]).rstrip("/")
    if not base.startswith("https://"):
        die("webapp url must be an https URL")
    return base + config["day_path"]
# END_BLOCK: WEBAPP_URL


# START_BLOCK: IDENTITY_AUDIT
def api_get(token: str, method: str, opener=urllib.request.urlopen) -> dict:
    # START_FUNCTION_CONTRACT: F-M-TOOL-SYNC-BOT-PROFILE.api_get
    # purpose: Call a read-only Bot API GET method; never expose the token.
    # inputs: token — bot token (never printed); method — API method name.
    # returns: parsed JSON dict.
    # side_effects: one HTTPS GET to api.telegram.org.
    # emitted_logs: none.
    # error_behavior: dies (exit 78) with the exception TYPE only, never the URL.
    # END_FUNCTION_CONTRACT: F-M-TOOL-SYNC-BOT-PROFILE.api_get
    url = f"{API_BASE}/bot{token}/{method}"
    try:
        with opener(url, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        die(f"{method} request failed: {type(exc).__name__}")
    if not isinstance(body, dict) or not body.get("ok"):
        die(f"{method} rejected by Bot API")
    return body


def prove_identity(config: dict, token: str, opener=urllib.request.urlopen) -> None:
    # START_FUNCTION_CONTRACT: F-M-TOOL-SYNC-BOT-PROFILE.prove_identity
    # purpose: Launch-gate identity proof before ANY mutation or audit:
    #   getMe must be ok, is_bot true, and match the exact expected_bot_id
    #   and bot_username from the repo config. Fails closed otherwise.
    # inputs: config — validated config; token — never printed.
    # returns: None on proven identity.
    # side_effects: one getMe HTTPS GET.
    # emitted_logs: none.
    # error_behavior: dies (exit 78) on any mismatch, rejection, or failure.
    # END_FUNCTION_CONTRACT: F-M-TOOL-SYNC-BOT-PROFILE.prove_identity
    result = api_get(token, "getMe", opener).get("result", {})
    if not result.get("is_bot"):
        die("identity proof failed: account is not a bot")
    if result.get("id") != config["expected_bot_id"]:
        die(f"identity proof failed: bot id {result.get('id')} != expected {config['expected_bot_id']}")
    if result.get("username") != config["bot_username"]:
        die(f"identity proof failed: username {result.get('username')} != expected {config['bot_username']}")


def run_audit(config: dict, token: str, opener=urllib.request.urlopen) -> int:
    # Read-only online audit: identity proof + safe current-state read-back.
    prove_identity(config, token, opener)
    print(f"identity OK: id={config['expected_bot_id']} username={config['bot_username']} is_bot=true")
    name = api_get(token, "getMyName", opener).get("result", {})
    print(f"name: {name.get('name', '')}")
    short = api_get(token, "getMyShortDescription", opener).get("result", {})
    print(f"short_description: {short.get('short_description', '')}")
    desc = api_get(token, "getMyDescription", opener).get("result", {})
    print(f"description: {desc.get('description', '')}")
    menu = api_get(token, "getChatMenuButton", opener).get("result", {})
    print(f"menu_button: {json.dumps(menu, ensure_ascii=False)}")
    commands = api_get(token, "getMyCommands", opener).get("result", [])
    print(f"commands count: {len(commands)}")
    webhook = api_get(token, "getWebhookInfo", opener).get("result", {})
    print(f"webhook url present: {bool(webhook.get('url'))} | pending: {webhook.get('pending_update_count')}")
    return 0
# END_BLOCK: IDENTITY_AUDIT


# START_BLOCK: CHECK_MODE
def build_operations(config: dict, webapp_url: str) -> list[dict]:
    menu = config["menu_button"]
    return [
        {"method": "setMyShortDescription", "payload": {"short_description": config["short_description"]}},
        {"method": "setMyDescription", "payload": {"description": config["description"]}},
        {"method": "setChatMenuButton", "payload": {"menu_button": {"type": "web_app", "text": menu["text"], "web_app": {"url": webapp_url}}}},
    ]


def run_check(config: dict, webapp_url: str) -> int:
    ops = build_operations(config, webapp_url)
    print("=== bot profile sync: CHECK (no HTTP performed) ===")
    for op in ops:
        print(f"would call {op['method']}: {json.dumps(op['payload'], ensure_ascii=False)}")
    start = config["start_copy"]
    print("start_copy is canonical-ready in repo config; NOT synced (no supported Ductor override):")
    print(start["text"])
    print(f"CTA: {start['cta']['text']} -> {webapp_url}")
    print("check OK")
    return 0
# END_BLOCK: CHECK_MODE


# START_BLOCK: APPLY_MODE
def post_method(token: str, method: str, payload: dict, opener=urllib.request.urlopen) -> dict:
    url = f"{API_BASE}/bot{token}/{method}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with opener(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # network/HTTP errors — never include token in output
        die(f"{method} request failed: {type(exc).__name__}")
    if not body.get("ok"):
        die(f"{method} rejected by Bot API: {body.get('description', 'unknown error')}")
    return body


def run_apply(config: dict, token: str, webapp_url: str, opener=urllib.request.urlopen) -> int:
    # Identity gate (doc 81): always before any mutation.
    prove_identity(config, token, opener)
    print(f"identity OK: id={config['expected_bot_id']} username={config['bot_username']}")
    for op in build_operations(config, webapp_url):
        post_method(token, op["method"], op["payload"], opener)
        print(f"{op['method']}: ok")
    # Exact read-back of every mutation (fail closed on any drift).
    short = api_get(token, "getMyShortDescription", opener).get("result", {}).get("short_description", "")
    if short != config["short_description"]:
        die("read-back mismatch: short_description")
    print("read-back short_description: exact")
    desc = api_get(token, "getMyDescription", opener).get("result", {}).get("description", "")
    if desc != config["description"]:
        die("read-back mismatch: description")
    print("read-back description: exact")
    menu = api_get(token, "getChatMenuButton", opener).get("result", {})
    if menu.get("type") != "web_app" or menu.get("text") != config["menu_button"]["text"] \
            or menu.get("web_app", {}).get("url") != webapp_url:
        die("read-back mismatch: menu_button")
    print("read-back menu_button: exact")
    print("apply OK (start_copy intentionally not synced — no production responder)")
    return 0
# END_BLOCK: APPLY_MODE


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync repo-owned Telegram bot profile (manual-gated).")
    parser.add_argument("--check", action="store_true", help="validate config and print intended operations (default, no HTTP)")
    parser.add_argument("--audit", action="store_true", help="read-only online audit: identity proof + current profile/menu/webhook (no mutations)")
    parser.add_argument("--apply", action="store_true", help="sync via Bot API (requires --manual-confirm)")
    parser.add_argument("--manual-confirm", action="store_true", help="explicit manual confirmation for --apply")
    parser.add_argument("--env-file", default=None, help="optional env file containing TELEGRAM_BOT_TOKEN (and optional WEBAPP_URL override)")
    args = parser.parse_args()

    config = load_config(CONFIG_PATH)
    validate_config(config)
    webapp_url = load_webapp_url(config, args.env_file)

    if args.apply:
        if not args.manual_confirm:
            die("--apply requires explicit --manual-confirm")
        token = load_token(args.env_file)
        return run_apply(config, token, webapp_url)
    if args.audit:
        token = load_token(args.env_file)
        return run_audit(config, token)
    return run_check(config, webapp_url)


if __name__ == "__main__":
    sys.exit(main())
# END_BLOCK: M-TOOL-SYNC-BOT-PROFILE
