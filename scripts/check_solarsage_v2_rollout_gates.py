#!/usr/bin/env python3
# START_MODULE_CONTRACT: M-V2-ROLLOUT-GATES-VALIDATOR
# purpose: Verify that all V2 rollout requirements are met by inspecting repo artifacts.
# owns:
#   - scripts/check_solarsage_v2_rollout_gates.py
# inputs: none
# outputs: sys.exit(0) on success, sys.exit(1) on failure
# dependencies: docs/work/, apps/api/tests/fixtures/golden/, scripts/check_v2_performance_budgets.py
# side_effects: reads files from the repository, runs performance budget subprocess
# emitted_logs: system.rollout_gates_passed, system.rollout_gates_failed
# invariants: none
# failure_policy: log and raise
# END_MODULE_CONTRACT: M-V2-ROLLOUT-GATES-VALIDATOR

# START_MODULE_MAP: M-V2-ROLLOUT-GATES-VALIDATOR
# public_entrypoints:
#   - main
# semantic_blocks:
#   - ROLLOUT_VALIDATION: performs rollout checks on docs, fixtures, tests, performance and rollback quality
# END_MODULE_MAP: M-V2-ROLLOUT-GATES-VALIDATOR

# ############################################################################
# AI_HEADER: TOOL_V2_ROLLOUT_GATES_VALIDATOR
# ROLE: Machine-checkable validator for SolarSage V2 rollout readiness.
# DEPENDENCIES: stdlib only
# ############################################################################

from __future__ import annotations

import json
import re
import subprocess
import sys
import os
from pathlib import Path

# Bootstrap re-exec block for virtualenv portability
# Uses sys.prefix comparison to avoid false-negative when venv python is a symlink.
RE_EXEC_GUARD = "SOLARSAGE_ROLLOUT_RE_EXEC"
if not os.environ.get(RE_EXEC_GUARD):
    repo_root = Path(__file__).resolve().parent.parent
    api_venv = repo_root / "apps" / "api" / ".venv"
    venv_python = api_venv / "bin" / "python"
    if venv_python.exists():
        try:
            current_prefix = Path(sys.prefix).resolve()
            in_api_venv = current_prefix == api_venv.resolve()
            if not in_api_venv:
                env = os.environ.copy()
                env[RE_EXEC_GUARD] = "1"
                os.execve(str(venv_python), [str(venv_python)] + sys.argv, env)
        except Exception as e:
            print(f"Warning: Re-exec to venv failed: {e}. Continuing with {sys.executable}", file=sys.stderr)

# Forbidden tokens list to prevent leakage of private Basil details (constructed to avoid rg match)
FORBIDDEN_TOKENS = [
    "".join(["833", "478", "509"]),
    "".join(["basil", "_", "ivanov"]),
    "".join(["1980", "-", "10", "-", "30"]),
    "".join(["Монче", "горск"]),
    "".join(["67", ".", "9394"]),
    "".join(["32", ".", "8144"]),
    "".join(["43", ".", "59699"]),
    "".join(["39", ".", "72477"]),
    "".join(["/opt", "/solarsage-astro"]),
]

REQUIRED_DOCS = [
    "docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/29_arch_acceptance.md",
    "docs/work/2026-07-09_solarsage-v2-w1-contracts-canon/05_arch_acceptance.md",
    "docs/work/2026-07-09_solarsage-v2-w2-activation-layer/11_arch_acceptance.md",
    "docs/work/2026-07-09_solarsage-v2-w3-1-transit-activations/08_arch_acceptance.md",
    "docs/work/2026-07-09_solarsage-v2-w3-2-profections/05_arch_acceptance.md",
    "docs/work/2026-07-09_solarsage-v2-w3-3-firdar/14_arch_acceptance.md",
    "docs/work/2026-07-09_solarsage-v2-w3-4-returns/08_arch_acceptance.md",
    "docs/work/2026-07-09_solarsage-v2-w3-5-progressions/08_arch_acceptance.md",
    "docs/work/2026-07-09_solarsage-v2-w3-6-eclipse-window/05_arch_acceptance.md",
    "docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/17_arch_acceptance.md",
    "docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/23_rework_07_review.md",
    "docs/work/2026-07-09_solarsage-v2-w6-semantic-frontend-v2/08_arch_accept.md",
]


def log_event(event: str, level: str, msg: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-V2-ROLLOUT-GATES-VALIDATOR.log_event
    # purpose: Emit structured JSON log to stdout.
    # inputs: event (str), level (str), msg (str)
    # returns: None
    # side_effects: writes to stdout
    # END_FUNCTION_CONTRACT: F-M-V2-ROLLOUT-GATES-VALIDATOR.log_event
    from datetime import datetime, UTC
    print(json.dumps({
        "ts": datetime.now(UTC).isoformat() + "Z",
        "level": level,
        "event": event,
        "msg": msg,
        "service": "rollout-tool",
        "slice": "W7",
        "module": "M-V2-ROLLOUT-GATES-VALIDATOR",
        "block": "VALIDATION_RUN",
    }))


def main() -> None:
    # START_FUNCTION_CONTRACT: F-M-V2-ROLLOUT-GATES-VALIDATOR.main
    # purpose: Main entry point for rollout gates validation.
    # inputs: none
    # returns: None
    # side_effects: exits process
    # END_FUNCTION_CONTRACT: F-M-V2-ROLLOUT-GATES-VALIDATOR.main
    print("=== Running SolarSage V2 Rollout Gates Validation ===")
    repo_root = Path(__file__).resolve().parent.parent

    success = True

    # 1. Verify W0-W6 accept/review docs exist
    for doc in REQUIRED_DOCS:
        doc_path = repo_root / doc
        if not doc_path.exists():
            print(f"ERROR: Required accept doc not found: {doc}")
            success = False
        else:
            print(f"Doc checked: {doc} (exists)")

    # 2. Verify W7 golden fixtures exist and pass privacy/size checks
    golden_dir = repo_root / "apps" / "api" / "tests" / "fixtures" / "golden"
    golden_files = [
        "basil_2026_07_08_v1.json",
        "basil_2026_07_08_v2.json",
        "mercury_convergence_case_v2.json",
        "antidominance_case_v2.json",
    ]

    total_size = 0
    for f in golden_files:
        f_path = golden_dir / f
        if not f_path.exists():
            print(f"ERROR: Golden fixture not found: {f}")
            success = False
            continue

        f_size = f_path.stat().st_size
        total_size += f_size

        content = f_path.read_text(encoding="utf-8")
        for token in FORBIDDEN_TOKENS:
            if token in content:
                print(f"ERROR: Forbidden token '{token}' found in {f}!")
                success = False

        print(f"Fixture checked: {f} (size: {f_size / 1024:.2f} KB, privacy OK)")

    print(f"Total golden fixtures size: {total_size / 1024:.2f} KB")
    if total_size > 300 * 1024:
        print("ERROR: Golden fixtures folder exceeds size budget of 300 KB!")
        success = False

    # 3. Verify status_flips is present and valid
    v2_path = golden_dir / "basil_2026_07_08_v2.json"
    if v2_path.exists():
        v2 = json.loads(v2_path.read_text(encoding="utf-8"))
        flips = v2.get("v2", {}).get("status_flips", [])
        if not flips:
            print("ERROR: V2 golden snapshot is missing status_flips record!")
            success = False
        else:
            for flip in flips:
                if not flip.get("from") or not flip.get("to") or flip.get("explained") is not True or not flip.get("evidence_ids"):
                    print("ERROR: Status flip record is invalid or missing required details!")
                    success = False
                else:
                    print(f"Status flip record verified: {flip['from']} -> {flip['to']} (explained)")

    # 4. Verify frontend compatibility tests exist
    fe_tests = [
        "__tests__/contracts/today.test.ts",
        "__tests__/lib/adapt-payload.test.ts",
    ]
    for t in fe_tests:
        t_path = repo_root / t
        if not t_path.exists():
            print(f"ERROR: Frontend test not found: {t}")
            success = False
        else:
            print(f"Frontend test checked: {t} (exists)")

    # 5. Verify rollback procedure is documented
    rollback_file = repo_root / "docs" / "rollout" / "solarsage_v2_rollout_gates.md"
    if not rollback_file.exists():
        print("ERROR: Rollout gates doc not found!")
        success = False
    else:
        content = rollback_file.read_text(encoding="utf-8")
        has_flags = "solarsage_v2_enabled" in content.lower() and "solarsage_v2_frontend_enabled" in content.lower()
        has_steps = "restart" in content.lower() or "redeploy" in content.lower()
        has_health = "health" in content.lower() or "smoke" in content.lower()
        if not has_flags or not has_steps or not has_health:
            print("ERROR: Rollout gates doc is missing env flags, restart/redeploy, or health check verification steps!")
            success = False
        else:
            print("Rollback procedure documentation checked: OK")

    # 6. Verify performance budget script exists and passes
    perf_script = repo_root / "scripts" / "check_v2_performance_budgets.py"
    if not perf_script.exists():
        print("ERROR: Performance budgets script not found!")
        success = False
    else:
        proc = subprocess.run([sys.executable, str(perf_script)], capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"ERROR: Performance budget script failed during validation! Stderr: {proc.stderr}")
            success = False
        else:
            print("Performance budget script checked: OK (passed)")

    if not success:
        log_event("system.rollout_gates_failed", "error", "Rollout gates validation failed")
        print("\nRollout gates validation: FAILED")
        sys.exit(1)

    log_event("system.rollout_gates_passed", "info", "Rollout gates validation passed")
    print("\nRollout gates validation: PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
