#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: MODULE_NORMALIZE_TODAY_FOCUS_FIXTURE — deterministic fixture normalizer
# ROLE: Normalizes key order, indentation, and checks privacy/allowlists for TodayFocus fixtures.
# ############################################################################

# START_MODULE_CONTRACT: M-NORMALIZE-TODAY-FOCUS-FIXTURE
# purpose: Deterministically sort keys and check allowlist/privacy constraints on TodayFocus fixtures.
# owns:
#   - scripts/contracts/normalize_today_focus_fixture.py
# inputs: directory path or file paths, --check flag
# outputs: exit 0 on success, exit 1 on check failure or invalid syntax
# dependencies: json, sys, argparse, pathlib
# side_effects: overwrites JSON files in-place unless --check is specified
# emitted_logs: none
# invariants: no privacy leaks, deterministic key sorting
# failure_policy: exit 1 on error
# END_MODULE_CONTRACT

# START_MODULE_MAP: M-NORMALIZE-TODAY-FOCUS-FIXTURE
# public_entrypoints:
#   - main
# semantic_blocks:
#   - FIXTURE_NORMALIZER: recursive dict sorting and schema check
# owned_tests:
#   - apps/api/tests/test_today_focus_fixture_canaries.py
# END_MODULE_MAP: M-NORMALIZE-TODAY-FOCUS-FIXTURE

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PRIVACY_DENYLIST = [
    "tg",
    "telegram",
    "username",
    "userId",
    "user_id",
    "uuid",
    "birthday",
    "coordinates",
    "initData",
    "cookie",
    "token",
    "profile",
    "prompt",
    "response",
]


def _sort_dict_recursive(obj: any) -> any:
    if isinstance(obj, dict):
        return {k: _sort_dict_recursive(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_sort_dict_recursive(item) for item in obj]
    return obj


def _check_privacy(obj: any, path_str: str) -> list[str]:
    errors = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            for banned in PRIVACY_DENYLIST:
                if banned.lower() in k.lower():
                    errors.append(f"Privacy error: key '{k}' matches banned word '{banned}' in {path_str}")
            errors.extend(_check_privacy(v, f"{path_str}.{k}"))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            errors.extend(_check_privacy(item, f"{path_str}[{idx}]"))
    return errors


def process_file(file_path: Path, check_only: bool) -> bool:
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            raw_text = fh.read()
            data = json.loads(raw_text)
    except Exception as exc:
        print(f"ERROR: Failed to parse JSON {file_path}: {exc}", file=sys.stderr)
        return False

    privacy_errors = _check_privacy(data, str(file_path))
    if privacy_errors:
        for err in privacy_errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return False

    sorted_data = _sort_dict_recursive(data)
    normalized_text = json.dumps(sorted_data, ensure_ascii=False, indent=2) + "\n"

    if check_only:
        if raw_text != normalized_text:
            print(f"FAIL: Fixture {file_path} is not normalized", file=sys.stderr)
            return False
    else:
        with open(file_path, "w", encoding="utf-8") as fh:
            fh.write(normalized_text)

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize TodayFocus fixture files")
    parser.add_argument("target", help="Path to fixture file or directory")
    parser.add_argument("--check", action="store_true", help="Check without modifying files")
    args = parser.parse_args()

    target_path = Path(args.target)
    if not target_path.exists():
        print(f"ERROR: Path {target_path} does not exist", file=sys.stderr)
        sys.exit(1)

    files_to_process: list[Path] = []
    if target_path.is_file() and target_path.suffix == ".json":
        files_to_process.append(target_path)
    elif target_path.is_dir():
        files_to_process.extend(target_path.rglob("*.json"))

    success = True
    for f in files_to_process:
        if not process_file(f, args.check):
            success = False

    if not success:
        sys.exit(1)

    if args.check:
        print("OK: All fixtures normalized and pass privacy checks")


if __name__ == "__main__":
    main()
