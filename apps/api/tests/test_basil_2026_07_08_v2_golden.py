"""Tests: Basil 2026-07-08 V2 golden — runs audit script and validates output."""
import json
import subprocess
import sys
from pathlib import Path

import pytest
from app.schemas.scoring_v2 import ScoringV2Result


def test_basil_v2_golden(tmp_path):
    """Run audit_scoring_v2.py on Basil 2026-07-08 inputs, validate output in tmp_path."""
    script = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "audit_scoring_v2.py"
    artifacts_dir = Path(__file__).resolve().parent.parent.parent.parent / "artifacts" / "audit" / "2026-07-08"

    signals_path = artifacts_dir / "04_day_scored_signals_after_filter.csv"
    activation_path = artifacts_dir / "21_sidecar_activation_layer_w3_5_progressions.json"
    result_path = tmp_path / "22_scoring_v2_result.json"
    diff_path = tmp_path / "23_scoring_v2_diff.json"

    assert signals_path.exists(), f"Missing signals: {signals_path}"
    assert activation_path.exists(), f"Missing activation: {activation_path}"

    # Run audit script
    cmd = [
        sys.executable, str(script),
        "--signals", str(signals_path),
        "--activation-layer", str(activation_path),
        "--out-result", str(result_path),
        "--out-diff", str(diff_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, f"Script failed: {proc.stderr}"

    # Validate result (snake_case)
    assert result_path.exists(), "Result not written"
    result_data = json.loads(result_path.read_text())
    ScoringV2Result.model_validate(result_data)
    assert result_data["scoring_version"] == "ss-scoring-2.0"

    sphere_scores = result_data["sphere_scores"]
    assert sphere_scores, "No sphere scores"

    any_activation = any(v["activation_score"] > 0 for v in sphere_scores.values())
    assert any_activation, "No sphere has activation_score > 0"

    any_convergence = any(v["convergence_bonus"] > 0 for v in sphere_scores.values())
    assert any_convergence, "No sphere has convergence_bonus > 0"

    # Validate diff
    assert diff_path.exists(), "Diff not written"
    diff_data = json.loads(diff_path.read_text())
    assert "sphere_diffs" in diff_data
    assert diff_data["sphere_diffs"]

    print("Basil V2 golden test passed")
