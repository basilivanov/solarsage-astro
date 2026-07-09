#!/usr/bin/env python3
import re
import sys
from pathlib import Path

REQUIRED_GATES = [
    "W0_to_W6_accept_docs_exist",
    "dual_run_evidence_exists",
    "no_unexplained_status_flips",
    "status_flips_have_activation_evidence",
    "frontend_compatibility_tests_exist",
    "rollback_procedure_documented",
    "performance_budget_check_passes",
]

def main():
    print("=== Running SolarSage V2 Rollout Gates Validation ===")
    gates_file = Path(__file__).resolve().parent.parent / "docs" / "rollout" / "solarsage_v2_rollout_gates.md"

    if not gates_file.exists():
        print(f"Error: Rollout gates file not found at {gates_file}")
        sys.exit(1)

    content = gates_file.read_text(encoding="utf-8")

    success = True
    found_gates = {}

    # Match pattern like: - [x] gate_name: true
    pattern = re.compile(r"-\s+\[x\]\s+([\w_]+):\s*(true|false)", re.IGNORECASE)
    for match in pattern.finditer(content):
        name, val = match.groups()
        found_gates[name] = val.lower() == "true"

    for gate in REQUIRED_GATES:
        if gate not in found_gates:
            print(f"ERROR: Missing gate check: {gate}")
            success = False
        elif not found_gates[gate]:
            print(f"ERROR: Rollout gate not ready: {gate} (is false)")
            success = False
        else:
            print(f"Gate ready: {gate}")

    if not success:
        print("\nRollout gates validation: FAILED")
        sys.exit(1)

    print("\nRollout gates validation: PASSED")
    sys.exit(0)

if __name__ == "__main__":
    main()
