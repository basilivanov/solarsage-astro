#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: MODULE_AUDIT_SCORING_V2 — Scoring V2 audit artifact generator.
# ROLE: Loads day-scored signals CSV and activation layer JSON, runs V1 and V2
#       scoring, writes V2 result (snake_case) and V1/V2 diff artifacts.
#       Self-reexecutes into the API venv if needed so the documented repo-root
#       command 'python3 scripts/audit_scoring_v2.py ...' works.
# ############################################################################

# START_MODULE_CONTRACT: M-AUDIT-SCORING-V2
# purpose: Generate reproducible V2 scoring artifacts for audit.
#          Self-reexecutes into apps/api/.venv/bin/python if the current
#          interpreter cannot import the API runtime. This is a local process
#          bootstrap, not an external service call.
# inputs: --signals CSV, --activation-layer JSON paths
# outputs: --out-result (ScoringV2Result snake_case), --out-diff (V1/V2 diff)
# dependencies: app.services.scoring_service, app.services.scoring_v2_service,
#               apps/api/.venv/bin/python for runtime bootstrap
# side_effects: writes JSON files; may re-exec into API venv
# failure_policy: exits non-zero on missing inputs, validation failures, or
#                 missing API venv
# END_MODULE_CONTRACT: M-AUDIT-SCORING-V2

# START_MODULE_MAP: M-AUDIT-SCORING-V2
# public_entrypoints:
#   - main
# semantic_blocks:
#   - REEXEC_BOOTSTRAP: detect API venv and re-exec if needed
#   - SIGNAL_LOADING: CSV to AstroSignal
#   - V1_SCORE: ScoringService.score_day
#   - V2_SCORE: ScoringV2Service.score_day
#   - DIFF_BUILD: sphere-by-sphere diff
# END_MODULE_MAP: M-AUDIT-SCORING-V2

from __future__ import annotations

import os
import sys
from pathlib import Path


def _ensure_api_runtime() -> None:
    """Re-exec into the API venv if the current interpreter cannot run the
    API runtime correctly. Uses the unresolved .venv/bin/python entry path
    to preserve virtualenv activation. Uses sys.prefix comparison as the
    infinite-loop guard.
    """
    api_root = (Path(__file__).resolve().parent.parent / "apps" / "api").resolve()
    venv_root = api_root / ".venv"
    venv_python = venv_root / "bin" / "python"
    venv_prefix = venv_root.resolve()

    # Loop guard: if already in the API venv, do not re-exec
    in_api_venv = Path(sys.prefix).resolve() == venv_prefix
    already_reexeced = os.environ.get("AUDIT_EXEC_REEXECED") == "1"

    if already_reexeced or in_api_venv:
        # If we're already in the venv or have already tried, test imports
        # and let any failure propagate normally (no silent continue)
        try:
            import app  # noqa: F401
            from app.schemas.normalization import AstroSignal  # noqa: F401
        except Exception:
            raise  # Re-raise to fail visibly if venv is broken
        return

    # Test a real API import
    try:
        import app  # noqa: F401
        from app.schemas.normalization import AstroSignal  # noqa: F401
        return  # All good
    except Exception:
        pass  # Will re-exec below

    if not venv_python.exists():
        print(
            f"ERROR: API venv not found at {venv_python}. "
            f"Create it with: cd apps/api && python3 -m venv .venv && source .venv/bin/activate && pip install -e .",
            file=sys.stderr,
        )
        sys.exit(1)

    # Re-exec into API venv — keep the unresolved symlink so pyvenv.cfg is found
    env = os.environ.copy()
    env["AUDIT_EXEC_REEXECED"] = "1"
    existing_pp = env.get("PYTHONPATH", "")
    pp_entries = [p for p in existing_pp.split(":") if p] if existing_pp else []
    if str(api_root) not in pp_entries:
        pp_entries.insert(0, str(api_root))
    env["PYTHONPATH"] = ":".join(pp_entries)
    os.execve(str(venv_python), [str(venv_python), *sys.argv], env)


_ensure_api_runtime()

import argparse
import csv
import json
from typing import Any


def _load_signals(csv_path: str) -> list[dict]:
    # START_FUNCTION_CONTRACT: F-M-AUDIT-SCORING-V2._load_signals
    # purpose: Load day-scored signals from CSV to dicts for AstroSignal.
    # inputs: csv_path — path to CSV with signal columns
    # returns: list of dicts suitable for AstroSignal construction
    # side_effects: reads file
    # END_FUNCTION_CONTRACT: F-M-AUDIT-SCORING-V2._load_signals
    """Load day-scored signals from CSV."""
    signals = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.strip(): v.strip() for k, v in row.items()}
            signal: dict[str, Any] = {}
            signal["type"] = row.get("type", row.get("signal_type", "aspect"))
            signal["planet"] = row.get("planet", "")
            signal["target_planet"] = row.get("target_planet", "")
            raw_aspect = row.get("aspect_type", row.get("aspect", ""))
            signal["aspect_type"] = raw_aspect if raw_aspect in ("conjunction", "sextile", "square", "trine", "opposition") else None
            signal["house"] = int(row["house"]) if row.get("house") else None
            signal["strength"] = float(row.get("strength", 0))
            signal["orb"] = float(row["orb"]) if row.get("orb") else 0.0
            signal["delta_kind"] = row.get("delta_kind", "")
            signal["kind"] = row.get("kind", signal["type"])
            signal["polarity"] = "neutral"
            signal["source"] = "day"
            signals.append(signal)
    return signals


def main() -> None:
    # START_FUNCTION_CONTRACT: F-M-AUDIT-SCORING-V2.main
    # purpose: CLI entry point. Loads signals + activation layer, runs V1/V2,
    #          writes snake_case V2 result and diff.
    # side_effects: writes --out-result and --out-diff JSON files
    # END_FUNCTION_CONTRACT: F-M-AUDIT-SCORING-V2.main
    parser = argparse.ArgumentParser(description="Scoring V2 audit")
    parser.add_argument("--signals", required=True, help="CSV with day-scored signals")
    parser.add_argument("--activation-layer", required=True, help="Activation layer JSON path")
    parser.add_argument("--out-result", required=True, help="Output path for V2 result JSON")
    parser.add_argument("--out-diff", required=True, help="Output path for V1/V2 diff JSON")
    args = parser.parse_args()

    from app.schemas.normalization import AstroSignal
    from app.schemas.activation import ActivationLayer
    from app.services.scoring_service import ScoringService
    from app.services.scoring_v2_service import ScoringV2Service

    signals = _load_signals(args.signals)
    day_signals = [AstroSignal(**s) for s in signals]

    with open(args.activation_layer) as f:
        activation_data = json.load(f)
    activation_data.pop("_audit_meta", None)
    activation_layer = ActivationLayer.model_validate(activation_data)

    # V1
    v1_result = ScoringService().score_day(day_signals)
    v1_sphere_scores = v1_result.get("sphere_scores", {})
    v1_day_status = v1_result.get("day_status", "unknown")

    # V2
    v2_result = ScoringV2Service().score_day(day_signals, activation_layer)

    # Write V2 result (snake_case for W4 verification command)
    result_path = Path(args.out_result)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with open(result_path, "w") as f:
        json.dump(v2_result.model_dump(mode="json", by_alias=False), f, indent=2)
    print(f"Wrote V2 result to {result_path}")

    # Build diff
    sphere_diffs: dict[str, dict] = {}
    all_keys = set(list(v1_sphere_scores.keys()) + list(v2_result.sphere_scores.keys()))
    for skey in sorted(all_keys):
        v1_val = round(float(v1_sphere_scores.get(skey, 0)), 4)
        v2_ss = v2_result.sphere_scores.get(skey)
        v2_val = round(v2_ss.final_score, 4) if v2_ss else 0.0
        delta = round(v2_val - v1_val, 4)
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
