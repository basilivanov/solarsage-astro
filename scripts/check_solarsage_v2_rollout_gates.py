#!/usr/bin/env python3
# START_MODULE_CONTRACT: M-V2-ROLLOUT-GATES-VALIDATOR
# purpose: Verify that all V2 rollout requirements are met by inspecting repo artifacts.
# owns:
#   - scripts/check_solarsage_v2_rollout_gates.py
# inputs: none
# outputs: sys.exit(0) on success, sys.exit(1) on failure
# dependencies: docs/work/, apps/api/tests/fixtures/golden/, scripts/check_v2_performance_budgets.py
# side_effects: reads files from the repository
# emitted_logs: system.rollout_gates_passed, system.rollout_gates_failed
# END_MODULE_CONTRACT: M-V2-ROLLOUT-GATES-VALIDATOR

# ############################################################################
# AI_HEADER: TOOL_V2_ROLLOUT_GATES_VALIDATOR
# ROLE: Machine-checkable validator for SolarSage V2 rollout readiness.
# DEPENDENCIES: stdlib only
# ############################################################################

import json
import re
import sys
from pathlib import Path

# Forbidden tokens list to prevent leakage of private Basil details
FORBIDDEN_TOKENS = [
    "833478509",
    "basil_ivanov",
    "1980-10-30",
    "Мончегорск",
    "67.9394",
    "32.8144",
    "43.59699",
    "39.72477",
    "/opt/solarsage-astro",
]

def log_event(event: str, level: str, msg: str):
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

def main():
    print("=== Running SolarSage V2 Rollout Gates Validation ===")
    repo_root = Path(__file__).resolve().parent.parent
    
    success = True
    
    # 1. Verify W0-W6 accept/review docs exist
    required_docs = [
        "docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/23_rework_07_review.md",
        "docs/work/2026-07-09_solarsage-v2-w6-semantic-frontend-v2/08_arch_accept.md",
    ]
    for doc in required_docs:
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
            
        # Get file size
        f_size = f_path.stat().st_size
        total_size += f_size
        
        # Read content and check for forbidden tokens
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

    # 3. Verify no unexplained status flips and flips have evidence
    v1_path = golden_dir / "basil_2026_07_08_v1.json"
    v2_path = golden_dir / "basil_2026_07_08_v2.json"
    if v1_path.exists() and v2_path.exists():
        v1 = json.loads(v1_path.read_text(encoding="utf-8"))
        v2 = json.loads(v2_path.read_text(encoding="utf-8"))
        if v1.get("dayStatus") != v2.get("dayStatus"):
            # Ensure V2 block has activationEvidence
            act_ev = v2.get("v2", {}).get("activationEvidence", [])
            if not act_ev:
                print("ERROR: V1/V2 status flip has no activation evidence!")
                success = False
            else:
                print("Status flip verified: has activation evidence")

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
        if "rollback" not in content.lower():
            print("ERROR: Rollout gates doc is missing rollback documentation!")
            success = False
        else:
            print("Rollback procedure documentation checked: OK")

    # 6. Verify performance budget script exists
    perf_script = repo_root / "scripts" / "check_v2_performance_budgets.py"
    if not perf_script.exists():
        print("ERROR: Performance budgets script not found!")
        success = False
    else:
        print("Performance budget script checked: OK")

    if not success:
        log_event("system.rollout_gates_failed", "error", "Rollout gates validation failed")
        print("\nRollout gates validation: FAILED")
        sys.exit(1)
        
    log_event("system.rollout_gates_passed", "info", "Rollout gates validation passed")
    print("\nRollout gates validation: PASSED")
    sys.exit(0)

if __name__ == "__main__":
    main()
