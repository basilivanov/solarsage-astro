#!/usr/bin/env python3
"""Audit script for W4 Scoring V2.

Loads day-scored signals CSV and activation layer JSON, runs V1 and V2
scoring, writes result and diff artifacts.

Usage:
    apps/api/.venv/bin/python scripts/audit_scoring_v2.py \\
        --signals artifacts/audit/2026-07-08/04_day_scored_signals_after_filter.csv \\
        --activation-layer artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json \\
        --out-result artifacts/audit/2026-07-08/22_scoring_v2_result.json \\
        --out-diff artifacts/audit/2026-07-08/23_scoring_v2_diff.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


def _load_signals(csv_path: str) -> list[dict]:
    """Load day-scored signals from CSV."""
    signals = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.strip(): v.strip() for k, v in row.items()}
            signal: dict[str, Any] = {}
            # Map CSV columns to AstroSignal-like dict
            signal["type"] = row.get("type", row.get("signal_type", "aspect"))
            signal["planet"] = row.get("planet", "")
            signal["target_planet"] = row.get("target_planet", row.get("target_planet", ""))
            raw_aspect = row.get("aspect_type", row.get("aspect", ""))
            signal["aspect_type"] = raw_aspect if raw_aspect in ("conjunction", "sextile", "square", "trine", "opposition") else None
            signal["house"] = int(row["house"]) if row.get("house") else None
            signal["strength"] = float(row.get("strength", 0))
            signal["orb"] = float(row["orb"]) if row.get("orb") else 0.0
            signal["delta_kind"] = row.get("delta_kind", row.get("delta_kind", ""))
            # Required for validation
            signal["kind"] = row.get("kind", signal["type"])
            signal["polarity"] = "neutral"
            signal["source"] = "day"
            signals.append(signal)
    return signals


def main() -> None:
    parser = argparse.ArgumentParser(description="Scoring V2 audit")
    parser.add_argument("--signals", required=True, help="CSV with day-scored signals")
    parser.add_argument("--activation-layer", required=True, help="Activation layer JSON path")
    parser.add_argument("--out-result", required=True, help="Output path for V2 result JSON")
    parser.add_argument("--out-diff", required=True, help="Output path for V1/V2 diff JSON")
    args = parser.parse_args()

    # Load signals
    signals = _load_signals(args.signals)
    from app.schemas.normalization import AstroSignal
    day_signals = [AstroSignal(**s) for s in signals]

    # Load activation layer and strip audit metadata
    with open(args.activation_layer) as f:
        activation_data = json.load(f)
    activation_data.pop("_audit_meta", None)

    # Run V1
    from app.services.scoring_service import ScoringService
    v1_result = ScoringService().score_day(day_signals)
    v1_sphere_scores = v1_result.get("sphere_scores", {})
    v1_day_status = v1_result.get("day_status", "unknown")

    # Run V2
    from app.services.scoring_v2_service import ScoringV2Service
    from app.schemas.activation import ActivationLayer
    activation_layer = ActivationLayer.model_validate(activation_data)
    v2_result = ScoringV2Service().score_day(day_signals, activation_layer)

    # Write V2 result
    result_path = Path(args.out_result)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with open(result_path, "w") as f:
        json.dump(json.loads(v2_result.model_dump_json(by_alias=True)), f, indent=2)
    print(f"Wrote V2 result to {result_path}")

    # Build diff
    sphere_diffs: dict[str, dict] = {}
    for skey in set(list(v1_sphere_scores.keys()) + list(v2_result.sphere_scores.keys())):
        v1_val = round(float(v1_sphere_scores.get(skey, 0)), 4)
        v2_ss = v2_result.sphere_scores.get(skey)
        v2_val = round(v2_ss.final_score, 4) if v2_ss else 0.0
        delta = round(v2_val - v1_val, 4)

        # Top new evidence from activation contributions
        top_new = []
        if v2_ss:
            for c in v2_ss.contributions:
                if c.source == "activation" and c.amount > 0:
                    top_new.append(c.source_id)
                    if len(top_new) >= 3:
                        break

        sphere_diffs[skey] = {
            "v1": v1_val,
            "v2": v2_val,
            "delta": delta,
            "top_new_evidence": top_new,
        }

    diff = {
        "v1_day_status": v1_day_status,
        "v2_day_status": v2_result.day_status,
        "sphere_diffs": sphere_diffs,
    }

    diff_path = Path(args.out_diff)
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    with open(diff_path, "w") as f:
        json.dump(diff, f, indent=2)
    print(f"Wrote V1/V2 diff to {diff_path}")
    print(f"  V1 status: {v1_day_status}")
    print(f"  V2 status: {v2_result.day_status}")
    print(f"  Spheres: {len(sphere_diffs)}")


if __name__ == "__main__":
    main()
