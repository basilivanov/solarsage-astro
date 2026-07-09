#!/usr/bin/env python3
"""Audit script for sidecar W3.1 activation layer.

Calls the sidecar activation builder directly for Basil profile
and writes the resulting activation layer as a deterministic artifact.

Usage (from repo root):
    python3 scripts/audit_sidecar_activation.py \\
        --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 \\
        --date 2026-07-08 \\
        --out artifacts/audit/2026-07-08/17_sidecar_activation_layer.json
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _ensure_imports() -> None:
    """Set up PYTHONPATH and, if needed, re-exec into sidecar venv."""
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    sidecar_root = project_root / "apps" / "solarsage"
    sidecar_python = sidecar_root / "venv" / "bin" / "python"

    # Ensure PYTHONPATH includes sidecar root for solarsage imports
    sidecar_str = str(sidecar_root)
    if sidecar_str not in sys.path:
        sys.path.insert(0, sidecar_str)

    # Check if we're in the right venv (swisseph available)
    try:
        import swisseph  # noqa: F401
        return  # All good
    except ImportError:
        pass

    # Re-exec into sidecar venv
    if sidecar_python.exists():
        env = os.environ.copy()
        existing_pp = env.get("PYTHONPATH", "")
        pp_entries = [p for p in existing_pp.split(":") if p] if existing_pp else []
        if sidecar_str not in pp_entries:
            pp_entries.insert(0, sidecar_str)
        env["PYTHONPATH"] = ":".join(pp_entries)
        os.execve(str(sidecar_python), [str(sidecar_python)] + sys.argv, env)
    else:
        print(f"ERROR: swisseph not found and sidecar venv not at {sidecar_python}", file=sys.stderr)
        sys.exit(1)


_ensure_imports()

import argparse
import json
from pathlib import Path

from solarsage.services.activation_builder import build_activation_layer


def main() -> None:
    parser = argparse.ArgumentParser(description="Sidecar activation layer audit")
    parser.add_argument("--user-id", required=True, help="User UUID (for audit metadata)")
    parser.add_argument("--date", required=True, help="Target date YYYY-MM-DD")
    parser.add_argument(
        "--out",
        required=True,
        help="Output path (e.g., artifacts/audit/2026-07-08/17_sidecar_activation_layer.json)",
    )
    parser.add_argument(
        "--techniques",
        default=None,
        help="Comma-separated technique list (default: all supported)",
    )
    args = parser.parse_args()

    # Basil profile birth data (hard-coded from audit 00_input_profile.json)
    birth_date = "1980-10-30"
    birth_time = "19:50"
    birth_lat = 67.9394
    birth_lon = 32.8144
    birth_tz = "Europe/Moscow"

    target_date = args.date
    target_time = "12:00"
    target_tz = "Europe/Moscow"

    techniques = None
    if args.techniques:
        techniques = [t.strip() for t in args.techniques.split(",")]

    layer = build_activation_layer(
        birth_date=birth_date,
        birth_time=birth_time,
        birth_lat=birth_lat,
        birth_lon=birth_lon,
        birth_tz=birth_tz,
        target_date=target_date,
        target_time=target_time,
        target_tz=target_tz,
        house_system="PLACIDUS",
        techniques=techniques,
    )

    # Serialize
    output = layer.model_dump(mode="json", by_alias=True)
    output["_audit_meta"] = {
        "user_id": args.user_id,
        "birth": {
            "date": birth_date,
            "time": birth_time,
            "lat": birth_lat,
            "lon": birth_lon,
            "tz": birth_tz,
        },
        "target": {
            "date": target_date,
            "time": target_time,
            "tz": target_tz,
        },
        "script": "audit_sidecar_activation.py",
        "wave": (
            "W3.6" if techniques is None or "eclipse_window" in techniques
            else "W3.5" if "solar_arc" in techniques or "secondary_progression" in techniques
            else "W3.4" if "solar_return" in techniques or "lunar_return" in techniques
            else "W3.3" if "firdar_major" in techniques or "firdar_minor" in techniques
            else "W3.2" if "annual_profection" in techniques or "monthly_profection" in techniques
            else "W3.1"
        ),
        "techniques": techniques,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Wrote sidecar activation layer to {out_path}")
    print(f"  Activations: {len(layer.activations)}")
    print(f"  by_planet: {list(layer.by_planet.keys())}")
    print(f"  by_house: {list(layer.by_house.keys())}")
    print(f"  by_lot: {list(layer.by_lot.keys())}")
    print(f"  by_angle: {list(layer.by_angle.keys())}")
    print(f"  Warnings: {layer.warnings}")


if __name__ == "__main__":
    main()
