# ############################################################################
# AI_HEADER: MODULE_NORMALIZE_TODAY_FIXTURE — JSON payload normalizer script.
# ROLE: CLI tool to validate fixture JSON against Pydantic TodayPayload and format it deterministically.
# DEPENDENCIES: sys, os, json, argparse, pydantic, app.schemas.today.TodayPayload
# ############################################################################

# START_MODULE_CONTRACT: M-NORMALIZE-TODAY-FIXTURE
# purpose: Validate visual fixture JSON and format it deterministically.
# owns:
#   - scripts/contracts/normalize_today_fixture.py
# inputs: CLI arguments: json file path, optional --check flag.
# outputs: exit code, normalized JSON file or print summary.
# dependencies: python libraries, apps/api/app/schemas/today.py.
# side_effects:
#   - Reads JSON file.
#   - Atomically overwrites JSON file if not in check mode.
# emitted_logs: none.
# invariants:
#   - The output JSON is deterministic, sorted keys, 2 spaces indent, ending with exactly one newline.
# failure_policy: exits non-zero on IO, JSON parsing, validation, or drift errors.
# END_MODULE_CONTRACT: M-NORMALIZE-TODAY-FIXTURE

# START_MODULE_MAP: M-NORMALIZE-TODAY-FIXTURE
# public_entrypoints:
#   - main
# semantic_blocks:
#   - FIXTURE_NORMALIZATION: load, validate, dump, and format logic.
# END_MODULE_MAP: M-NORMALIZE-TODAY-FIXTURE

import argparse
import json
import os
import sys
from pathlib import Path
from pydantic import ValidationError

# Add apps/api to path to resolve imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../apps/api"))
from app.schemas.today import TodayPayload

# START_BLOCK: FIXTURE_NORMALIZATION
# START_FUNCTION_CONTRACT: F-M-NORMALIZE-TODAY-FIXTURE.normalize_file
# purpose: Perform deterministic normalization on a fixture file.
# inputs: file_path - Path object; check_only - bool.
# returns: int - exit code (0 if clean, 1 if drifted, other non-zero on error).
# side_effects: reads file, writes normalized file if not check_only.
# emitted_logs: none.
# error_behavior: none (exceptions are caught and returned as error codes).
# END_FUNCTION_CONTRACT: F-M-NORMALIZE-TODAY-FIXTURE.normalize_file
def normalize_file(file_path: Path, check_only: bool) -> int:
    if not file_path.is_file():
        print(f"Error: {file_path} is not a file", file=sys.stderr)
        return 2

    try:
        raw_text = file_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}", file=sys.stderr)
        return 3
    except OSError as e:
        print(f"IO Error reading file: {e}", file=sys.stderr)
        return 4

    try:
        # strict validation via TodayPayload
        model = TodayPayload.model_validate(data)
    except ValidationError as e:
        print("Pydantic Validation Error:", file=sys.stderr)
        # Sanitized error printing without leaking raw input or PII
        for err in e.errors(include_input=False, include_url=False):
            loc = " -> ".join(str(x) for x in err.get("loc", []))
            err_type = err.get("type", "unknown")
            msg = err.get("msg", "no message")
            print(f"  [{loc}] ({err_type}): {msg}", file=sys.stderr)
        return 5

    # Dump using deterministic aliases and CamelModel settings
    dumped = model.model_dump(
        mode="json",
        by_alias=True,
        exclude_unset=True,
    )

    # Render with sorted keys and indent
    normalized_text = json.dumps(
        dumped,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    ) + "\n"

    if check_only:
        if raw_text == normalized_text:
            print(f"Check passed: {file_path} is normalized.")
            return 0
        else:
            print(f"Drift detected in {file_path}.", file=sys.stderr)
            print("Please run: pnpm contracts:fixture:normalize", file=sys.stderr)
            return 1
    else:
        # Atomic write
        temp_path = file_path.with_suffix(".tmp")
        try:
            temp_path.write_text(normalized_text, encoding="utf-8")
            temp_path.replace(file_path)
            print(f"Successfully normalized: {file_path}")
            return 0
        except OSError as e:
            print(f"IO Error writing file: {e}", file=sys.stderr)
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            return 6


# START_FUNCTION_CONTRACT: F-M-NORMALIZE-TODAY-FIXTURE.main
# purpose: CLI entrypoint parser for normalize_today_fixture.py.
# inputs: none (reads sys.argv).
# returns: None (exits process).
# side_effects: exits process.
# emitted_logs: none.
# error_behavior: exits non-zero on failure.
# END_FUNCTION_CONTRACT: F-M-NORMALIZE-TODAY-FIXTURE.main
def main():
    parser = argparse.ArgumentParser(description="Normalize today fixture JSON")
    parser.add_argument("path", type=str, help="Path to JSON fixture file")
    parser.add_argument("--check", action="store_true", help="Only check for normalization drift")
    args = parser.parse_args()

    file_path = Path(args.path)
    exit_code = normalize_file(file_path, args.check)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
# END_BLOCK: FIXTURE_NORMALIZATION
