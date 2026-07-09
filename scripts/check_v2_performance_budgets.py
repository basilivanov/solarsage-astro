#!/usr/bin/env python3
# START_MODULE_CONTRACT: M-V2-PERFORMANCE-BUDGETS-CHECK
# purpose: Verify that local V2 scoring and semantic block building run under 50ms.
# owns:
#   - scripts/check_v2_performance_budgets.py
# inputs: artifacts/audit/2026-07-08/ raw signals and activations
# outputs: sys.exit(0) on success, sys.exit(1) on failure
# dependencies: app.services.scoring_v2_service, app.services.semantic_v2_service
# side_effects: runs scoring and semantic loops
# emitted_logs: system.performance_budgets_passed, system.performance_budgets_failed
# END_MODULE_CONTRACT: M-V2-PERFORMANCE-BUDGETS-CHECK

# ############################################################################
# AI_HEADER: TOOL_V2_PERFORMANCE_BUDGETS_CHECK
# ROLE: Lightweight local/CI gate to assert p95 scoring/semantic budget limits.
# DEPENDENCIES: stdlib, app.services
# ############################################################################

import json
import time
import sys
from pathlib import Path

# Add app to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "apps" / "api"))

from app.schemas.activation import ActivationLayer
from app.services.semantic_v2_service import SemanticV2Service
from app.services.scoring_v2_service import ScoringV2Service
from app.schemas.normalization import AstroSignal

def log_event(event: str, level: str, msg: str):
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

def main():
    print("=== Running V2 Performance Budgets Check ===")
    print("mode: fixture")

    repo_root = Path(__file__).resolve().parent.parent
    golden_inputs_dir = repo_root / "apps" / "api" / "tests" / "fixtures" / "golden" / "inputs"
    if not golden_inputs_dir.exists():
        print("Error: Golden inputs directory not found.")
        sys.exit(1)

    # 1. Load data
    raw_activations = json.loads((golden_inputs_dir / "raw_activations.json").read_text(encoding="utf-8"))
    activation_layer = ActivationLayer.model_validate(raw_activations)

    # Load signals
    signals_data = (golden_inputs_dir / "raw_signals.csv").read_text(encoding="utf-8").splitlines()
    day_signals = []
    for line in signals_data[1:]:
        if not line.strip():
            continue
        parts = line.split(",")
        if len(parts) >= 10:
            day_signals.append(
                AstroSignal(
                    type=parts[2].strip(),
                    planet=parts[3].strip(),
                    target_planet=parts[5].strip() if parts[5].strip() else None,
                    aspect_type=parts[7].strip() if parts[7].strip() else None,
                    orb=float(parts[8].strip()) if parts[8].strip() else None,
                    strength=float(parts[9].strip()) if parts[9].strip() else 0.0,
                )
            )

    scoring_v2_service = ScoringV2Service()
    semantic_v2_service = SemanticV2Service()

    # 2. Measure Scoring V2 Performance
    scoring_times = []
    for _ in range(50):
        t0 = time.perf_counter()
        res = scoring_v2_service.score_day(day_signals, activation_layer)
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
