#!/usr/bin/env python3
"""Audit script for sidecar W3.1 activation layer.

Calls the sidecar activation builder directly for Basil profile
and writes the resulting activation layer as a deterministic artifact.

Usage:
    apps/solarsage/venv/bin/python scripts/audit_sidecar_activation.py \\
        --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 \\
        --date 2026-07-08 \\
        --out artifacts/audit/2026-07-08/17_sidecar_activation_layer.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Sidecar activation layer audit")
    parser.add_argument("--user-id", required=True, help="User UUID (for audit metadata)")
    parser.add_argument("--date", required=True, help="Target date YYYY-MM-DD")
    parser.add_argument(
        "--out",
        required=True,
        help="Output path (e.g., artifacts/audit/2026-07-08/17_sidecar_activation_layer.json)",
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

    # Add sidecar to path
    sidecar_root = Path(__file__).resolve().parent.parent / "apps" / "solarsage"
    sys.path.insert(0, str(sidecar_root))
    from solarsage.services.activation_builder import build_activation_layer

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
        techniques=None,  # All supported transit techniques
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
        "wave": "W3.1",
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
