#!/usr/bin/env python3

# ############################################################################
# AI_HEADER: MODULE_SCRIPTS_GENERATE_TELEGRAM_TEST_INITDATA
# ROLE: Tooling script
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-GUARDRAILS-TOOLING
# ######################################### START_MODULE_CONTRACT
# purpose: Generate valid Telegram WebApp initData for E2E testing.
# owns:
#   - scripts/generate-telegram-test-initdata.py
# inputs: Mocks, fixtures, process environment or --env-file
# outputs: Assertion results
# dependencies: local modules
# side_effects: n/a
# emitted_logs: n/a
# invariants:
#   - TELEGRAM_BOT_TOKEN value is never printed in success or error output
# failure_policy: log safe error and raise SystemExit
# END_MODULE_CONTRACT
"""
Generate valid Telegram WebApp initData for E2E testing.
Uses the real bot token to compute HMAC, producing
verifiable initData that passes the backend's check.

Usage:
  python scripts/generate-telegram-test-initdata.py

Output: a URL query string starting with tgWebAppData=...
  that can be appended to the frontend URL for browser tests.

Reads TELEGRAM_BOT_TOKEN from process environment first,
then falls back to the explicit --env-file if provided.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from urllib.parse import quote_plus

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_bot_token(env_file_path: str | None = None) -> str:
    # First check process environment
    env_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if env_token:
        return env_token

    if env_file_path:
        p = Path(env_file_path)
        if not p.exists():
            raise FileNotFoundError(f"Explicit env file not found at {env_file_path}")
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                value = line.split("=", 1)[1].strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                if value:
                    return value
        raise ValueError(f"TELEGRAM_BOT_TOKEN not found in explicit env file: {env_file_path}")

    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment. Export TELEGRAM_BOT_TOKEN or pass an explicit --env-file (e.g. /etc/solarsage/app.env).")


def generate_initdata(
    user_id: int = 999999999,
    first_name: str = "Test",
    last_name: str = "User",
    username: str = "synthetic_test_user",
    env_file_path: str | None = None,
) -> str:
    """Generate a URL-encoded initData string with valid HMAC."""
    bot_token = load_bot_token(env_file_path)

    auth_date = int(time.time())
    user_obj = {
        "id": user_id,
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "language_code": "ru",
        "is_premium": False,
    }

    params = {
        "query_id": "AAFt360xAAAAAG3frTEuTeWX",
        "user": json.dumps(user_obj, separators=(",", ":")),
        "auth_date": str(auth_date),
    }

    # Build data-check-string: sorted keys, excluding hash, joined by \n
    items = sorted(params.items())
    data_check_string = "\n".join(f"{k}={v}" for k, v in items)

    # Compute secret key: HMAC-SHA256(WebAppData, bot_token)
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256
    ).digest()

    # Compute hash: HMAC-SHA256(secret_key, data_check_string)
    signature = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    params["hash"] = signature

    # Build initData query string
    initdata_raw = "&".join(f"{k}={v}" for k, v in params.items())

    return initdata_raw


def build_full_url(initdata: str, base_url: str = "") -> str:
    """Build the full URL with tgWebAppData and additional Telegram params."""
    params = [
        ("tgWebAppData", initdata),
        ("tgWebAppVersion", "9.5"),
        ("tgWebAppPlatform", "web"),
        (
            "tgWebAppThemeParams",
            quote_plus(
                json.dumps(
                    {
                        "bg_color": "#ffffff",
                        "button_color": "#3390ec",
                        "button_text_color": "#ffffff",
                        "hint_color": "#707579",
                        "link_color": "#00488f",
                        "secondary_bg_color": "#f4f4f5",
                        "text_color": "#000000",
                        "header_bg_color": "#ffffff",
                        "accent_text_color": "#3390ec",
                        "section_bg_color": "#ffffff",
                        "section_header_text_color": "#3390ec",
                        "subtitle_text_color": "#707579",
                        "destructive_text_color": "#df3f40",
                    }
                )
            ),
        ),
    ]
    query_string = "&".join(f"{k}={v}" for k, v in params)
    if base_url:
        return f"{base_url}#{query_string}"
    return f"#{query_string}"


if __name__ == "__main__":
    import sys
    user_id = 999999999
    username = "synthetic_test_user"
    first_name = "Test"
    env_file_path = None
    
    for arg in sys.argv[1:]:
        if arg.startswith("--user-id="):
            user_id = int(arg.split("=")[1])
        elif arg.startswith("--username="):
            username = arg.split("=")[1]
        elif arg.startswith("--first-name="):
            first_name = arg.split("=")[1]
        elif arg.startswith("--env-file="):
            env_file_path = arg.split("=")[1]
        else:
            print(f"ERROR: Unknown or malformed argument: {arg}", file=sys.stderr)
            raise SystemExit(2)

    try:
        initdata = generate_initdata(
            user_id=user_id,
            username=username,
            first_name=first_name,
            env_file_path=env_file_path,
        )
        full_url = build_full_url(initdata)
        print(f"# Generated at UNIX timestamp {int(time.time())}")
        print(f"# user_id={user_id}, username={username}")
        print(f"# Validity window: ~24 hours (86400s by default)")
        print()
        print(initdata)
        print()
        print("# Full URL fragment (append to your frontend URL):")
        print(full_url)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
