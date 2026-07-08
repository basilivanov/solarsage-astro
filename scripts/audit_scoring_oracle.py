#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: MODULE_AUDIT_SCORING_ORACLE — independent day scoring oracle.
# ROLE: Recomputes day scoring from canon YAML and exported signal traces without
#       importing production ScoringService.
# ############################################################################

# START_MODULE_CONTRACT: M-AUDIT-SCORING-ORACLE
# purpose: Recompute sphere_scores, top_signals, and day_status from
#          grace/canon/*.yml plus a signal_trace.csv artifact.
# owns:
#   - scripts/audit_scoring_oracle.py
# inputs: canon dir, signal_trace.csv, optional production scoring/payload JSON.
# outputs: oracle JSON/CSV files and pass/fail comparison with production output.
# dependencies: yaml, stdlib csv/json/argparse.
# side_effects: writes files under --out.
# emitted_logs: none.
# invariants:
#   - Does not import app.services.scoring_service or any app.* production module.
#   - Uses only day-scored rows from signal_trace.csv.
# failure_policy: raises SystemExit/FileNotFoundError on missing required inputs.
# END_MODULE_CONTRACT: M-AUDIT-SCORING-ORACLE

# START_MODULE_MAP: M-AUDIT-SCORING-ORACLE
# public_entrypoints:
#   - run_scoring_oracle
#   - main
# semantic_blocks:
#   - CANON_LOAD: YAML loading and helpers
#   - SIGNAL_LOAD: signal_trace.csv parsing
#   - SCORE_RECALC: independent score/top/day recomputation
#   - COMPARISON: production-vs-oracle tolerance checks
# owned_tests:
#   - scripts/test_audit_scoring_oracle.py
# END_MODULE_MAP: M-AUDIT-SCORING-ORACLE

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import yaml

POSITIVE_ASPECTS = {"trine", "sextile"}
NEGATIVE_ASPECTS = {"square", "opposition"}
MAJOR_ASPECTS = {"CONJUNCTION", "OPPOSITION", "TRINE", "SQUARE"}
TOLERANCE = 0.02


# START_BLOCK: CANON_LOAD
def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_canon(canon_dir: Path) -> dict[str, dict[str, Any]]:
    return {
        "spheres": load_yaml(canon_dir / "spheres.v1.yml"),
        "aspect_rules": load_yaml(canon_dir / "aspect_rules.v1.yml"),
    }


def base_planet_name(name: str | None) -> str:
    if not name:
        return ""
    value = str(name).upper()
    if value.startswith("TRANSIT_"):
        return value.removeprefix("TRANSIT_")
    if value.startswith("NATAL_"):
        return value.removeprefix("NATAL_")
    return value


def aspect_weight(aspect_rules: dict[str, Any], aspect_type: str | None) -> float:
    if not aspect_type:
        return 0.5
    raw = aspect_rules.get("aspect_weights", {}).get(aspect_type.upper())
    return float(raw) if raw is not None else 0.5


def is_major(aspect_type: str | None) -> bool:
    return (aspect_type or "").upper() in MAJOR_ASPECTS


def aspect_threshold(aspect_rules: dict[str, Any], aspect_type: str | None) -> float:
    key = "major" if is_major(aspect_type) else "minor"
    return float(aspect_rules.get("aspect_threshold", {}).get(key, 0.35))


def convergence_curve(aspect_rules: dict[str, Any], n: int) -> float:
    values = aspect_rules.get("convergence_curve", {}).get(
        "values", {2: 0.4, 3: 0.65, 4: 0.8, 5: 0.9}
    )
    if n >= 5:
        return float(values.get(5, values.get("5", 0.9)))
    return float(values.get(n, values.get(str(n), 0.0)))
# END_BLOCK: CANON_LOAD


# START_BLOCK: SIGNAL_LOAD
def _to_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(float(value))


def load_day_signals(signal_trace_path: Path) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    with signal_trace_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if not _to_bool(row.get("included_in_day_scoring", "true")):
                continue
            signals.append(
                {
                    "type": row.get("type") or "",
                    "planet": row.get("planet") or "",
                    "target_planet": row.get("target_planet") or "",
                    "aspect_type": row.get("aspect_type") or "",
                    "orb": _to_float(row.get("orb")),
                    "strength": float(row.get("strength") or 0.0),
                    "house": _to_int(row.get("house")),
                    "sign": row.get("sign") or "",
                    "daily_salience": _to_float(row.get("daily_salience")),
                    "technique": row.get("technique") or "",
                    "technique_family": row.get("technique_family") or "",
                    "delta_kind": row.get("delta_kind") or "",
                    "phase": row.get("phase") or "",
                }
            )
    return signals
# END_BLOCK: SIGNAL_LOAD


# START_BLOCK: SCORE_RECALC
def signal_family(signal: dict[str, Any], aspect_rules: dict[str, Any]) -> str:
    if signal.get("technique_family"):
        return str(signal["technique_family"])
    technique = signal.get("technique")
    if technique:
        for family, members in aspect_rules.get("technique_families", {}).items():
            if isinstance(members, list) and technique in members:
                return str(family)
        return str(technique)
    if signal.get("type") in {"aspect", "planet_in_house", "planet_in_sign"}:
        return "transit"
    return str(signal.get("type") or "unknown")


def compute_convergence(
    signals: list[dict[str, Any]], aspect_rules: dict[str, Any]
) -> dict[str, dict[str, int]]:
    by_planet: dict[str, set[str]] = {}
    by_house: dict[str, set[str]] = {}
    for signal in signals:
        family = signal_family(signal, aspect_rules)
        if signal.get("type") == "aspect" and signal.get("target_planet"):
            by_planet.setdefault(str(signal["target_planet"]).upper(), set()).add(family)
        if signal.get("type") == "planet_in_house" and signal.get("house"):
            by_house.setdefault(str(signal["house"]), set()).add(family)
            if signal.get("planet"):
                by_planet.setdefault(str(signal["planet"]).upper(), set()).add(family)
    return {
        "by_planet": {planet: len(families) for planet, families in by_planet.items()},
        "by_house": {house: len(families) for house, families in by_house.items()},
    }


def compute_sphere_scores(
    signals: list[dict[str, Any]],
    canon: dict[str, dict[str, Any]],
) -> tuple[dict[str, float], list[dict[str, Any]], dict[str, dict[str, int]]]:
    spheres = canon["spheres"].get("spheres", {})
    aspect_rules = canon["aspect_rules"]
    scores: dict[str, float] = {}
    rows: list[dict[str, Any]] = []

    aspects = [signal for signal in signals if signal.get("type") == "aspect"]
    houses = [signal for signal in signals if signal.get("type") == "planet_in_house"]

    for sphere_key, sphere in spheres.items():
        total = 0.0

        for signal in aspects:
            planet_weight = float(
                sphere.get("planets", {}).get(base_planet_name(signal.get("planet")), 0)
            )
            if planet_weight <= 0:
                continue
            weight = aspect_weight(aspect_rules, signal.get("aspect_type"))
            threshold = aspect_threshold(aspect_rules, signal.get("aspect_type"))
            base = weight * planet_weight * float(signal.get("strength") or 0.0)
            tension_mod = 0.0
            aspect = signal.get("aspect_type")
            target = str(signal.get("target_planet") or "").upper()
            softening = aspect_rules.get("benefic_softening", {})
            if aspect in NEGATIVE_ASPECTS and target in {"JUPITER", "VENUS"}:
                tension_mod = float(
                    softening.get("square_or_opposition_with_benefic", {}).get(
                        "tension_delta", 0
                    )
                )
            elif aspect in POSITIVE_ASPECTS and target in {"SATURN", "MARS"}:
                tension_mod = float(
                    softening.get("trine_or_sextile_with_malefic", {}).get(
                        "ease_delta", 0
                    )
                )

            passed = base >= threshold
            contribution = base + tension_mod if passed else 0.0
            total += contribution
            rows.append(
                {
                    "signal_type": signal.get("type"),
                    "planet": signal.get("planet"),
                    "target_planet": signal.get("target_planet"),
                    "aspect_type": aspect,
                    "house": "",
                    "sphere": sphere_key,
                    "planet_weight": planet_weight,
                    "aspect_weight": weight,
                    "strength": signal.get("strength"),
                    "threshold": threshold,
                    "base": round(base, 6),
                    "modifier": round(tension_mod, 6),
                    "contribution": round(contribution, 6),
                    "passed_threshold": passed,
                    "source": "aspect",
                }
            )

        for signal in houses:
            house = signal.get("house")
            if not house or house not in sphere.get("houses", []):
                continue
            planet_weight = float(
                sphere.get("planets", {}).get(base_planet_name(signal.get("planet")), 0.1)
            )
            angular_bonus = float(
                sphere.get("weight_multipliers", {}).get("angular_house_bonus", 1.0)
            )
            if house in {1, 4, 7, 10}:
                planet_weight *= angular_bonus
            contribution = planet_weight * float(signal.get("strength") or 0.0)
            total += contribution
            rows.append(
                {
                    "signal_type": signal.get("type"),
                    "planet": signal.get("planet"),
                    "target_planet": "",
                    "aspect_type": "",
                    "house": house,
                    "sphere": sphere_key,
                    "planet_weight": round(planet_weight, 6),
                    "aspect_weight": "",
                    "strength": signal.get("strength"),
                    "threshold": "",
                    "base": round(contribution, 6),
                    "modifier": 0.0,
                    "contribution": round(contribution, 6),
                    "passed_threshold": True,
                    "source": "planet_in_house",
                }
            )

        scores[sphere_key] = round(total, 2)

    convergence = compute_convergence(signals, aspect_rules)
    scores = apply_convergence(scores, convergence, canon)
    return scores, rows, convergence


def apply_convergence(
    sphere_scores: dict[str, float],
    convergence: dict[str, dict[str, int]],
    canon: dict[str, dict[str, Any]],
) -> dict[str, float]:
    result = dict(sphere_scores)
    spheres = canon["spheres"].get("spheres", {})
    aspect_rules = canon["aspect_rules"]
    by_planet = convergence.get("by_planet", {})
    by_house = convergence.get("by_house", {})

    for sphere_key, sphere in spheres.items():
        bonus = 0.0
        for planet, weight in sphere.get("planets", {}).items():
            n = by_planet.get(str(planet), 0)
            if n >= 2:
                bonus += convergence_curve(aspect_rules, n) * float(weight)
        for house in sphere.get("houses", []):
            n = by_house.get(str(house), 0)
            if n >= 2:
                bonus += convergence_curve(aspect_rules, n) * 0.3
        result[sphere_key] = round(result.get(sphere_key, 0.0) + bonus, 2)

    total = sum(value for value in result.values() if value > 0)
    cap_pct = float(aspect_rules.get("dominance_cap", {}).get("threshold", 0.65))
    for sphere_key, value in list(result.items()):
        if total > 0 and value > cap_pct * total:
            result[sphere_key] = round(cap_pct * total, 2)
    return result


def compute_day_status(signals: list[dict[str, Any]], aspect_rules: dict[str, Any]) -> str:
    positive_score = 0.0
    negative_score = 0.0
    for signal in signals:
        if signal.get("type") != "aspect":
            continue
        weight = aspect_weight(aspect_rules, signal.get("aspect_type"))
        base = weight * float(signal.get("strength") or 0.0)
        if base < aspect_threshold(aspect_rules, signal.get("aspect_type")):
            continue
        aspect = signal.get("aspect_type")
        if aspect in POSITIVE_ASPECTS:
            positive_score += base
        elif aspect in NEGATIVE_ASPECTS:
            negative_score += base
        else:
            positive_score += base * 0.5
            negative_score += base * 0.5

    if positive_score > negative_score * 1.3 and positive_score >= 1.0:
        return "supportive"
    if negative_score > positive_score * 1.3 and negative_score >= 1.0:
        return "tense"
    return "steady"


def signal_daily_salience(signal: dict[str, Any], aspect_rules: dict[str, Any]) -> float:
    if signal.get("daily_salience") is not None:
        return float(signal["daily_salience"])
    velocity_class = aspect_rules.get("planet_velocity_class", {})
    velocity_factor = aspect_rules.get(
        "velocity_factor", {"fast": 1.0, "medium": 0.7, "slow": 0.45}
    )
    planet = base_planet_name(signal.get("planet"))
    if planet in set(velocity_class.get("fast", ["MOON", "SUN", "MERCURY", "VENUS"])):
        factor = float(velocity_factor.get("fast", 1.0))
    elif planet in set(velocity_class.get("medium", ["MARS", "JUPITER", "SATURN"])):
        factor = float(velocity_factor.get("medium", 0.7))
    elif planet in set(velocity_class.get("slow", ["URANUS", "NEPTUNE", "PLUTO"])):
        factor = float(velocity_factor.get("slow", 0.45))
    else:
        factor = 0.5
    return float(signal.get("strength") or 0.0) * factor


def compute_top_signals(
    signals: list[dict[str, Any]], aspect_rules: dict[str, Any], limit: int = 5
) -> list[dict[str, Any]]:
    ranked = sorted(
        signals,
        key=lambda signal: signal_daily_salience(signal, aspect_rules),
        reverse=True,
    )[:limit]
    has_moon = any("Moon" in str(signal.get("planet") or "") for signal in ranked)
    if ranked and not has_moon:
        moon_signals = [signal for signal in signals if "Moon" in str(signal.get("planet") or "")]
        if moon_signals:
            ranked[-1] = max(moon_signals, key=lambda signal: float(signal.get("strength") or 0.0))
    return ranked
# END_BLOCK: SCORE_RECALC


# START_BLOCK: COMPARISON
def signal_identity(signal: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": signal.get("type"),
        "planet": signal.get("planet"),
        "target_planet": signal.get("target_planet") or None,
        "aspect_type": signal.get("aspect_type") or None,
        "house": signal.get("house") or None,
    }


def load_json_if_present(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def sphere_scores_from_payload(payload: dict[str, Any] | None) -> dict[str, float]:
    if not payload:
        return {}
    rows = payload.get("sphere_scores") or payload.get("sphereScores") or []
    return {row["key"]: float(row["score"]) for row in rows if "key" in row}


def compare_outputs(
    oracle: dict[str, Any],
    production_scoring: dict[str, Any] | None,
    production_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    prod_day_status = None
    prod_scores: dict[str, float] = {}
    prod_top: list[dict[str, Any]] = []
    has_prod = False
    if production_scoring:
        has_prod = True
        prod_day_status = production_scoring.get("day_status")
        prod_scores = {
            key: float(value)
            for key, value in (production_scoring.get("sphere_scores") or {}).items()
        }
        prod_top = production_scoring.get("top_signals") or []
    if production_payload:
        has_prod = True
        prod_day_status = prod_day_status or production_payload.get("day_status")
        prod_scores = prod_scores or sphere_scores_from_payload(production_payload)

    sphere_comparison = {}
    all_keys = sorted(set(oracle["sphere_scores"]) | set(prod_scores))
    for key in all_keys:
        oracle_value = float(oracle["sphere_scores"].get(key, 0.0))
        prod_value = float(prod_scores.get(key, 0.0)) if key in prod_scores else None

        passed = True
        if prod_value is not None:
            passed = math.isclose(oracle_value, prod_value, abs_tol=TOLERANCE)

        delta = round(oracle_value - prod_value, 6) if prod_value is not None else None
        sphere_comparison[key] = {
            "oracle": oracle_value,
            "production": prod_value,
            "delta": delta,
            "pass": passed,
        }

    oracle_top = [signal_identity(signal) for signal in oracle.get("top_signals", [])]
    prod_top_identity = [signal_identity(signal) for signal in prod_top]

    day_status_pass = True
    if has_prod and prod_day_status is not None:
        day_status_pass = (oracle["day_status"] == prod_day_status)

    top_signals_pass = True
    if has_prod and prod_top_identity:
        top_signals_pass = (oracle_top == prod_top_identity)

    return {
        "day_status": {
            "oracle": oracle["day_status"],
            "production": prod_day_status,
            "pass": day_status_pass,
        },
        "sphere_scores": sphere_comparison,
        "top_signals": {
            "oracle": oracle_top,
            "production": prod_top_identity,
            "pass": top_signals_pass,
        },
    }
# END_BLOCK: COMPARISON


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_scoring_oracle(
    *,
    canon_dir: Path,
    signal_trace_path: Path,
    production_scoring_path: Path | None,
    production_payload_path: Path | None,
    out_dir: Path,
) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-AUDIT-SCORING-ORACLE.run_scoring_oracle
    # purpose: Run independent day scoring recomputation and write artifacts.
    # inputs: canon_dir, signal_trace_path, optional production JSON paths, out_dir.
    # returns: dict with oracle and comparison payloads.
    # side_effects: writes scoring_oracle*.json/csv and scoring_intermediate_table.csv.
    # emitted_logs: none.
    # error_behavior: propagates file/parse errors.
    # END_FUNCTION_CONTRACT: F-M-AUDIT-SCORING-ORACLE.run_scoring_oracle
    canon = load_canon(canon_dir)
    signals = load_day_signals(signal_trace_path)
    scores, intermediate_rows, convergence = compute_sphere_scores(signals, canon)
    day_status = compute_day_status(signals, canon["aspect_rules"])
    top_signals = compute_top_signals(signals, canon["aspect_rules"])

    oracle = {
        "day_status": day_status,
        "sphere_scores": scores,
        "top_signals": top_signals,
        "convergence": convergence,
    }
    production_scoring = load_json_if_present(production_scoring_path)
    production_payload = load_json_if_present(production_payload_path)
    comparison = compare_outputs(oracle, production_scoring, production_payload)
    result = {"oracle": oracle, "comparison": comparison}

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "scoring_oracle_result.json", oracle)
    write_json(out_dir / "scoring_oracle_comparison.json", result)
    write_csv(out_dir / "scoring_intermediate_table.csv", intermediate_rows)
    write_csv(
        out_dir / "sphere_scores_oracle.csv",
        [
            {"key": key, "score": value, "rank": index}
            for index, (key, value) in enumerate(
                sorted(scores.items(), key=lambda item: (-item[1], item[0])),
                start=1,
            )
        ],
    )
    write_csv(
        out_dir / "top_signals_oracle.csv",
        [
            {
                **signal_identity(signal),
                "strength": signal.get("strength"),
                "orb": signal.get("orb"),
                "daily_salience": signal_daily_salience(signal, canon["aspect_rules"]),
            }
            for signal in top_signals
        ],
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Independent SolarSage day scoring oracle")
    parser.add_argument("--canon-dir", type=Path, default=Path("grace/canon"))
    parser.add_argument("--signals", type=Path, required=True, help="Path to signal_trace.csv")
    parser.add_argument("--production-scoring", type=Path, default=None)
    parser.add_argument("--production-payload", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_scoring_oracle(
        canon_dir=args.canon_dir,
        signal_trace_path=args.signals,
        production_scoring_path=args.production_scoring,
        production_payload_path=args.production_payload,
        out_dir=args.out,
    )
    comp = result["comparison"]
    print(json.dumps(comp, ensure_ascii=False, indent=2))

    # Propagate failures
    has_failed = not comp["day_status"]["pass"] or not comp["top_signals"]["pass"]
    for key, val in comp["sphere_scores"].items():
        if not val["pass"]:
            has_failed = True

    if has_failed:
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
