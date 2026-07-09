#!/usr/bin/env python3
# START_MODULE_CONTRACT: M-V2-PERFORMANCE-BUDGETS-CHECK
# purpose: Verify that local V2 scoring and semantic block building run under 50ms.
# owns:
#   - scripts/check_v2_performance_budgets.py
# inputs: apps/api/tests/fixtures/golden/performance_case.json
# outputs: sys.exit(0) on success, sys.exit(1) on failure
# dependencies: app.services.scoring_v2_service, app.services.semantic_v2_service
# side_effects: runs scoring and semantic loops
# emitted_logs: system.performance_budgets_passed, system.performance_budgets_failed
# invariants: none
# failure_policy: log and raise
# END_MODULE_CONTRACT: M-V2-PERFORMANCE-BUDGETS-CHECK

# START_MODULE_MAP: M-V2-PERFORMANCE-BUDGETS-CHECK
# public_entrypoints:
#   - main
# semantic_blocks:
#   - BUDGET_CHECK: runs p95 performance loops
# END_MODULE_MAP: M-V2-PERFORMANCE-BUDGETS-CHECK

# ############################################################################
# AI_HEADER: TOOL_V2_PERFORMANCE_BUDGETS_CHECK
# ROLE: Lightweight local/CI gate to assert p95 scoring/semantic budget limits.
# DEPENDENCIES: stdlib, app.services
# ############################################################################

from __future__ import annotations

import json
import time
import sys
import os
from pathlib import Path

# Bootstrap re-exec block for virtualenv portability
# Uses sys.prefix comparison to avoid false-negative when venv python is a symlink.
RE_EXEC_GUARD = "SOLARSAGE_PERF_RE_EXEC"
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

# Add app to path dynamically
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "apps" / "api"))

from app.schemas.activation import ActivationLayer
from app.services.semantic_v2_service import SemanticV2Service
from app.services.scoring_v2_service import ScoringV2Service
from app.schemas.normalization import AstroSignal


def log_event(event: str, level: str, msg: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-V2-PERFORMANCE-BUDGETS-CHECK.log_event
    # purpose: Emit a structured JSON log to stdout.
    # inputs: event (str), level (str), msg (str)
    # returns: None
    # side_effects: writes to stdout
    # END_FUNCTION_CONTRACT: F-M-V2-PERFORMANCE-BUDGETS-CHECK.log_event
    from datetime import datetime, UTC
    print(json.dumps({
        "ts": datetime.now(UTC).isoformat() + "Z",
        "level": level,
        "event": event,
        "msg": msg,
        "service": "performance-tool",
        "slice": "W7",
        "module": "M-V2-PERFORMANCE-BUDGETS-CHECK",
        "block": "PERFORMANCE_RUN",
    }))


def main() -> None:
    # START_FUNCTION_CONTRACT: F-M-V2-PERFORMANCE-BUDGETS-CHECK.main
    # purpose: Main entry point for performance budget check.
    # inputs: none
    # returns: None
    # side_effects: exits process
    # END_FUNCTION_CONTRACT: F-M-V2-PERFORMANCE-BUDGETS-CHECK.main
    print("=== Running V2 Performance Budgets Check ===")
    print("mode: fixture")

    golden_inputs_dir = repo_root / "apps" / "api" / "tests" / "fixtures" / "golden"
    case_path = golden_inputs_dir / "performance_case.json"
    if not case_path.exists():
        print(f"Error: Performance case fixture not found at {case_path}")
        sys.exit(1)

    # 1. Load data
    case_data = json.loads(case_path.read_text(encoding="utf-8"))
    day_signals_raw = case_data.pop("day_signals", [])
    activation_layer = ActivationLayer.model_validate(case_data)

    # Load signals
    day_signals = [
        AstroSignal(
            type=s["type"],
            planet=s["planet"],
            target_planet=s.get("target_planet"),
            aspect_type=s.get("aspect_type"),
            orb=s.get("orb"),
            strength=s.get("strength", 0.0),
        )
        for s in day_signals_raw
    ]

    scoring_v2_service = ScoringV2Service()
    semantic_v2_service = SemanticV2Service()

    # 2. Measure Scoring V2 Performance
    scoring_times = []
    for _ in range(50):
        t0 = time.perf_counter()
        _res = scoring_v2_service.score_day(day_signals, activation_layer)
        t1 = time.perf_counter()
        scoring_times.append((t1 - t0) * 1000.0)

    scoring_times.sort()
    p95_scoring = scoring_times[int(len(scoring_times) * 0.95)]
    print(f"Scoring V2 p95: {p95_scoring:.2f} ms")

    # 3. Measure Semantic V2 Performance
    semantic_times = []
    res_scoring = scoring_v2_service.score_day(day_signals, activation_layer)
    for _ in range(50):
        t0 = time.perf_counter()
        semantic_v2_service.build_v2_block(
            activation_layer=activation_layer,
            scoring_result=res_scoring
        )
        t1 = time.perf_counter()
        semantic_times.append((t1 - t0) * 1000.0)

    semantic_times.sort()
    p95_semantic = semantic_times[int(len(semantic_times) * 0.95)]
    print(f"Semantic V2 p95: {p95_semantic:.2f} ms")

    # Budgets check
    BUDGET_SCORING_MS = 50.0
    BUDGET_SEMANTIC_MS = 50.0

    success = True
    if p95_scoring > BUDGET_SCORING_MS:
        print(f"ERROR: Scoring V2 p95 ({p95_scoring:.2f} ms) exceeded budget of {BUDGET_SCORING_MS} ms")
        success = False
    if p95_semantic > BUDGET_SEMANTIC_MS:
        print(f"ERROR: Semantic V2 p95 ({p95_semantic:.2f} ms) exceeded budget of {BUDGET_SEMANTIC_MS} ms")
        success = False

    if not success:
        log_event("system.performance_budgets_failed", "error", "Performance budget check failed")
        print("Performance budget check: FAILED")
        sys.exit(1)

    log_event("system.performance_budgets_passed", "info", "Performance budget check passed")
    print("Performance budget check: PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
