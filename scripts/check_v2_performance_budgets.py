#!/usr/bin/env python3
import json
import time
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, "/opt/solarsage-astro/apps/api")

from app.schemas.activation import ActivationLayer
from app.services.semantic_v2_service import SemanticV2Service
from app.services.scoring_v2_service import ScoringV2Service
from app.services.day_scoring_signals import filter_day_scored_signals
from app.schemas.normalization import AstroSignal

def main():
    print("=== Running V2 Performance Budgets Check ===")
    print("mode: fixture")

    audit_dir = Path("/opt/solarsage-astro/artifacts/audit/2026-07-08")
    if not audit_dir.exists():
        print("Error: Audit artifacts not found. Run make audit-day or populate artifacts.")
        sys.exit(1)

    # 1. Load data
    raw_activations = json.loads((audit_dir / "21_sidecar_activation_layer_w3_5_progressions.json").read_text(encoding="utf-8"))
    if "_audit_meta" in raw_activations:
        raw_activations.pop("_audit_meta")
    activation_layer = ActivationLayer.model_validate(raw_activations)

    # Load signals
    signals_data = (audit_dir / "04_day_scored_signals_after_filter.csv").read_text(encoding="utf-8").splitlines()
    # Parse signals (skip header)
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
        scoring_times.append((t1 - t0) * 1000.0) # in ms

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
        semantic_times.append((t1 - t0) * 1000.0) # in ms

    semantic_times.sort()
    p95_semantic = semantic_times[int(len(semantic_times) * 0.95)]
    print(f"Semantic V2 p95: {p95_semantic:.2f} ms")

    # Budgets check: p95 targets under local execution should be extremely fast (e.g. < 50ms)
    # This prevents any high-CPU regression in scoring/semantic builder loop.
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
        print("Performance budget check: FAILED")
        sys.exit(1)

    print("Performance budget check: PASSED")
    sys.exit(0)

if __name__ == "__main__":
    main()
