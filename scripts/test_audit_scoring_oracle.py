from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from audit_scoring_oracle import run_scoring_oracle


def test_scoring_oracle_recomputes_scores_without_app_imports(tmp_path: Path) -> None:
    canon_dir = tmp_path / "canon"
    canon_dir.mkdir()
    (canon_dir / "spheres.v1.yml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "spheres.v1",
                "spheres": {
                    "work_status_achievement": {
                        "houses": [6],
                        "planets": {"MARS": 1.0, "SATURN": 0.5},
                        "weight_multipliers": {"angular_house_bonus": 1.0},
                    },
                    "relationships_partnership": {
                        "houses": [7],
                        "planets": {"VENUS": 1.0, "MOON": 0.6},
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    (canon_dir / "aspect_rules.v1.yml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "aspect_rules.v1",
                "aspect_weights": {"TRINE": 0.85, "SQUARE": 0.85},
                "aspect_threshold": {"major": 0.35, "minor": 0.55},
                "convergence_curve": {"values": {2: 0.4, 3: 0.65, 4: 0.8, 5: 0.9}},
                "dominance_cap": {"threshold": 1.0},
                "planet_velocity_class": {
                    "fast": ["MOON", "SUN", "MERCURY", "VENUS"],
                    "medium": ["MARS", "JUPITER", "SATURN"],
                    "slow": ["URANUS", "NEPTUNE", "PLUTO"],
                },
                "velocity_factor": {"fast": 1.0, "medium": 0.7, "slow": 0.45},
            }
        ),
        encoding="utf-8",
    )

    signals_path = tmp_path / "signal_trace.csv"
    with signals_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "included_in_day_scoring",
                "type",
                "planet",
                "target_planet",
                "aspect_type",
                "orb",
                "strength",
                "house",
                "sign",
                "daily_salience",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "included_in_day_scoring": "true",
                "type": "aspect",
                "planet": "Transit_Mars",
                "target_planet": "Saturn",
                "aspect_type": "trine",
                "orb": "0.1",
                "strength": "1.0",
                "house": "",
                "sign": "",
                "daily_salience": "",
            }
        )
        writer.writerow(
            {
                "included_in_day_scoring": "true",
                "type": "aspect",
                "planet": "Transit_Venus",
                "target_planet": "Moon",
                "aspect_type": "square",
                "orb": "6.5",
                "strength": "0.2",
                "house": "",
                "sign": "",
                "daily_salience": "",
            }
        )
        writer.writerow(
            {
                "included_in_day_scoring": "true",
                "type": "aspect",
                "planet": "Transit_Jupiter",
                "target_planet": "Mercury",
                "aspect_type": "trine",
                "orb": "0.2",
                "strength": "1.0",
                "house": "",
                "sign": "",
                "daily_salience": "",
            }
        )
        writer.writerow(
            {
                "included_in_day_scoring": "true",
                "type": "planet_in_house",
                "planet": "Transit_Mars",
                "target_planet": "",
                "aspect_type": "",
                "orb": "",
                "strength": "1.0",
                "house": "6",
                "sign": "Gemini",
                "daily_salience": "",
            }
        )

    production_scoring = tmp_path / "production_scoring_result.json"
    production_scoring.write_text(
        json.dumps({"day_status": "supportive", "sphere_scores": {}, "top_signals": []}),
        encoding="utf-8",
    )

    result = run_scoring_oracle(
        canon_dir=canon_dir,
        signal_trace_path=signals_path,
        production_scoring_path=production_scoring,
        production_payload_path=None,
        out_dir=tmp_path / "out",
    )

    assert result["oracle"]["day_status"] == "supportive"
    assert result["oracle"]["sphere_scores"]["work_status_achievement"] == 1.85
    assert result["oracle"]["sphere_scores"]["relationships_partnership"] == 0.0
    assert result["comparison"]["day_status"]["pass"] is True
