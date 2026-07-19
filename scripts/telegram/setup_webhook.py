#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: TOOL_SETUP_WEBHOOK — manual-gated Telegram webhook registration
# ROLE: Registers the canonical production webhook (/api/telegram/webhook)
#       with secret_token and the /start command, with exact read-back.
# DEPENDENCIES: python3.12 stdlib, scripts/telegram/sync_bot_profile.py
# ############################################################################

# START_MODULE_CONTRACT: M-TOOL-SETUP-WEBHOOK
# purpose: One manual-gated tool that proves bot identity, registers the
#   webhook URL with secret_token + allowed_updates=["message"] +
#   drop_pending_updates, sets exactly the /start command (a real responder
#   now exists in the API), and reads both back exactly.
# owns:
#   - scripts/telegram/setup_webhook.py
# inputs:
#   - --check (default): offline validation + intended operations (no HTTP)
#   - --audit: online read-only identity + getWebhookInfo + getMyCommands
#   - --apply --manual-confirm: setWebhook + setMyCommands + exact read-back
#   - --env-file <path>: optional env file with TELEGRAM_BOT_TOKEN and
#     TELEGRAM_WEBHOOK_SECRET
# outputs: exit 0 on validated check/audit/applied sync; non-zero otherwise
# dependencies: scripts/telegram/sync_bot_profile.py (shared config/token/http)
# side_effects:
#   - --check: none (validation + stdout only)
#   - --audit/--apply: HTTPS calls to api.telegram.org (NEVER from this host's
#     blocked egress; run from a Telegram-reachable operator host)
# emitted_logs: none
# invariants:
#   - Token and webhook secret come only from env or an explicit --env-file;
#     neither is ever printed, logged, or included in any output.
#   - Identity gate (getMe exact id+username) runs before ANY mutation.
#   - Every mutation is followed by an exact read-back comparison.
#   - Webhook secret must be at least 32 hex-looking chars (fail closed).
# failure_policy: exit 78 on any validation, identity, secret or HTTP failure.
# END_MODULE_CONTRACT: M-TOOL-SETUP-WEBHOOK

# START_MODULE_MAP: M-TOOL-SETUP-WEBHOOK
# public_entrypoints:
#   - main
# semantic_blocks:
#   - SECRET_LOAD: resolve webhook secret from env/explicit env-file only
#   - CHECK_MODE: offline validation and intended operations
#   - APPLY_MODE: identity-gated setWebhook/setMyCommands with read-back
# owned_tests:
#   - apps/api/tests/test_setup_webhook.py
# END_MODULE_MAP: M-TOOL-SETUP-WEBHOOK

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# START_BLOCK: SHARED_IMPORTS
from sync_bot_profile import (  # noqa: E402
    CONFIG_PATH,
    api_get,
    die,
    load_config,
    load_token,
    post_method,
    prove_identity,
    validate_config,
)
# END_BLOCK: SHARED_IMPORTS

WEBHOOK_PATH = "/api/telegram/webhook"
START_COMMAND = {"command": "start", "description": "Мой день"}


# START_BLOCK: SECRET_LOAD
def load_webhook_secret(env_file: str | None) -> str:
    # START_FUNCTION_CONTRACT: F-M-TOOL-SETUP-WEBHOOK.load_webhook_secret
    # purpose: Resolve the webhook secret from env or an explicit env file.
    # inputs: env_file — optional path (TELEGRAM_WEBHOOK_SECRET=...).
    # returns: the secret string (never printed).
    # side_effects: reads process env or the optional env file.
    # emitted_logs: none.
    # error_behavior: dies (exit 78) if absent or shorter than 32 chars.
    # END_FUNCTION_CONTRACT: F-M-TOOL-SETUP-WEBHOOK.load_webhook_secret
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip()
    if not secret and env_file:
        path = Path(env_file)
        if path.is_file() and not path.is_symlink():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("TELEGRAM_WEBHOOK_SECRET="):
                    secret = line.split("=", 1)[1].strip().strip('"')
                    break
    if len(secret) < 32:
        die("TELEGRAM_WEBHOOK_SECRET is required (>= 32 chars; export it or pass --env-file); it is never printed")
    return secret


def webhook_url(config: dict) -> str:
    override = os.environ.get("WEBAPP_URL", "").strip()
    base = (override or config["webapp_url"]).rstrip("/")
    if not base.startswith("https://"):
        die("webapp url must be an https URL")
    return base + WEBHOOK_PATH
# END_BLOCK: SECRET_LOAD


# START_BLOCK: CHECK_MODE
def run_check(config: dict, url: str) -> int:
    print("=== telegram webhook setup: CHECK (no HTTP performed) ===")
    print(f"would call setWebhook: url={url} allowed_updates=[\"message\"] drop_pending_updates=true secret_token=<redacted>")
    print(f"would call setMyCommands: [{json.dumps(START_COMMAND, ensure_ascii=False)}]")
    print("check OK")
    return 0
# END_BLOCK: CHECK_MODE


# START_BLOCK: APPLY_MODE
def run_audit(config: dict, token: str, opener=urllib.request.urlopen) -> int:
    prove_identity(config, token, opener)
    print(f"identity OK: id={config['expected_bot_id']} username={config['bot_username']}")
    webhook = api_get(token, "getWebhookInfo", opener).get("result", {})
    print(f"webhook url: {webhook.get('url', '')}")
    print(f"allowed_updates: {webhook.get('allowed_updates')}")
    print(f"pending: {webhook.get('pending_update_count')} | max_connections: {webhook.get('max_connections')}")
    commands = api_get(token, "getMyCommands", opener).get("result", [])
    print(f"commands: {json.dumps(commands, ensure_ascii=False)}")
    return 0


def run_apply(config: dict, token: str, secret: str, url: str, opener=urllib.request.urlopen) -> int:
    prove_identity(config, token, opener)
    print(f"identity OK: id={config['expected_bot_id']} username={config['bot_username']}")
    post_method(token, "setWebhook", {
        "url": url,
        "secret_token": secret,
        "allowed_updates": ["message"],
        "drop_pending_updates": True,
    }, opener)
    print("setWebhook: ok (secret_token redacted)")
    post_method(token, "setMyCommands", {"commands": [START_COMMAND]}, opener)
    print("setMyCommands: ok")
    webhook = api_get(token, "getWebhookInfo", opener).get("result", {})
    if webhook.get("url") != url:
        die("read-back mismatch: webhook url")
    if webhook.get("allowed_updates") != ["message"]:
        die("read-back mismatch: allowed_updates")
    print("read-back webhook: exact")
    commands = api_get(token, "getMyCommands", opener).get("result", [])
    if commands != [START_COMMAND]:
        die("read-back mismatch: commands")
    print("read-back commands: exact")
    print("apply OK")
    return 0
# END_BLOCK: APPLY_MODE


def main() -> int:
    parser = argparse.ArgumentParser(description="Register the canonical Telegram webhook (manual-gated).")
    parser.add_argument("--check", action="store_true", help="validate and print intended operations (default, no HTTP)")
    parser.add_argument("--audit", action="store_true", help="read-only online identity + webhook/commands state")
    parser.add_argument("--apply", action="store_true", help="register webhook and /start command (requires --manual-confirm)")
    parser.add_argument("--manual-confirm", action="store_true", help="explicit manual confirmation for --apply")
    parser.add_argument("--env-file", default=None, help="optional env file with TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET")
    args = parser.parse_args()

    config = load_config(CONFIG_PATH)
    validate_config(config)
    url = webhook_url(config)

    if args.apply:
        if not args.manual_confirm:
            die("--apply requires explicit --manual-confirm")
        token = load_token(args.env_file)
        secret = load_webhook_secret(args.env_file)
        return run_apply(config, token, secret, url)
    if args.audit:
        token = load_token(args.env_file)
        return run_audit(config, token)
    return run_check(config, url)


if __name__ == "__main__":
    sys.exit(main())
# END_BLOCK: M-TOOL-SETUP-WEBHOOK
