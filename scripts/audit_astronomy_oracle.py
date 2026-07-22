#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: MODULE_AUDIT_ASTRONOMY_ORACLE — independent astronomy oracle.
# ROLE: Recomputes day astronomy with direct pyswisseph calls and compares it
#       with exported SolarSage/API artifacts.
# ############################################################################

# START_MODULE_CONTRACT: M-AUDIT-ASTRONOMY-ORACLE
# purpose: Verify transit longitudes, retrograde flags, Moon phase, Moon-Pluto
#          opposition, and transit house placement without importing sidecar code.
# owns:
#   - scripts/audit_astronomy_oracle.py
# inputs: input_profile.json, raw_transits.json, raw_natal_context.json,
#         final_today_payload.json, date/time/timezone.
# outputs: astronomy_oracle.csv, house_placements_oracle.csv,
#          astronomy_oracle_summary.json.
# dependencies: swisseph, stdlib.
# side_effects: writes files under --out.
# emitted_logs: none.
# invariants:
#   - Does not import solarsage.* or app.* code.
#   - Uses direct Swiss Ephemeris calls as the oracle implementation.
# failure_policy: raises on missing required artifacts or swisseph failures.
# END_MODULE_CONTRACT: M-AUDIT-ASTRONOMY-ORACLE

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import swisseph as swe

PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
}

SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

LONGITUDE_TOLERANCE_DEG = 0.01
HOUSE_TOLERANCE_DEG = 0.05


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sign_for(longitude: float) -> str:
    return SIGNS[int(longitude / 30.0) % 12]


def shortest_delta(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def angular_distance(a: float, b: float) -> float:
    delta = abs(a - b)
    return 360.0 - delta if delta > 180.0 else delta


def julian_day(date_str: str, time_str: str, tz_name: str) -> float:
    local = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").replace(
        tzinfo=ZoneInfo(tz_name)
    )
    utc = local.astimezone(ZoneInfo("UTC"))
    return swe.julday(
        utc.year,
        utc.month,
        utc.day,
        utc.hour + utc.minute / 60.0 + utc.second / 3600.0,
    )


def planet_positions(jd: float) -> dict[str, dict[str, Any]]:
    result = {}
    for name, planet_id in PLANETS.items():
        values, _flags = swe.calc_ut(jd, planet_id)
        lon, lat, dist, speed_lon, speed_lat, speed_dist = values
        result[name] = {
            "name": name,
            "longitude": float(lon),
            "latitude": float(lat),
            "speed": float(speed_lon),
            "retrograde": bool(speed_lon < 0),
            "sign": sign_for(float(lon)),
        }
    return result


def normalize_house_system(raw: str | None, birth_lat: float) -> bytes:
    value = (raw or "").upper()
    if "WHOLE" in value or abs(birth_lat) >= 60:
        return b"W"
    return b"P"


def calculate_houses_from_birth(profile: dict[str, Any], house_system_raw: str | None) -> list[dict[str, Any]]:
    birth = profile["birth"]
    jd = julian_day(birth["date"], birth["time"], birth["tz"])
    lat = float(birth["lat"])
    lon = float(birth["lon"])
    house_system = normalize_house_system(house_system_raw, lat)
    cusps, _ascmc = swe.houses(jd, lat, lon, house_system)
    return [
        {"number": index, "longitude": float(cusp), "sign": sign_for(float(cusp))}
        for index, cusp in enumerate(cusps, start=1)
    ]


def house_cusp(house: dict[str, Any]) -> float:
    return float(house.get("longitude", house.get("cusp", 0.0)) or 0.0)


def find_house(longitude: float, houses: list[dict[str, Any]]) -> int | None:
    if not houses:
        return None
    sorted_houses = sorted(houses, key=house_cusp)
    for index, house in enumerate(sorted_houses):
        next_house = sorted_houses[(index + 1) % len(sorted_houses)]
        cusp = house_cusp(house)
        next_cusp = house_cusp(next_house)
        if next_cusp > cusp:
            if cusp <= longitude < next_cusp:
                return int(house["number"])
        else:
            if longitude >= cusp or longitude < next_cusp:
                return int(house["number"])
    return int(sorted_houses[0]["number"])


def moon_phase_percent(sun_lon: float, moon_lon: float) -> float:
    elongation = math.radians((moon_lon - sun_lon) % 360.0)
    return (1.0 - math.cos(elongation)) / 2.0 * 100.0


def production_lunar_percent(payload: dict[str, Any]) -> int | None:
    for fact in (payload.get("day_summary") or {}).get("facts", []):
        if fact.get("kind") == "lunar_phase":
            match = re.search(r"(\d+)\s*%", fact.get("title") or "")
            if match:
                return int(match.group(1))
    return None


def planet_by_name(planets: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    return next((planet for planet in planets if planet.get("name") == name), None)


def final_chart_planet(payload: dict[str, Any], name: str) -> dict[str, Any] | None:
    # The oracle's final payload may be the debug (snake_case) dump or the
    # root (camelCase) wire payload — both carry the same day chart.
    chart = payload.get("dayChart") or payload.get("day_chart") or {}
    planets = chart.get("transitPlanets") or chart.get("transit_planets") or []
    return next((p for p in planets if p.get("name") == name), None)


def run_astronomy_oracle(
    *,
    input_profile_path: Path,
    raw_transits_path: Path,
    raw_natal_context_path: Path,
    final_payload_path: Path,
    target_date: str,
    target_time: str,
    target_tz: str | None,
    out_dir: Path,
    ephemeris_path: str | None = None,
) -> dict[str, Any]:
    # START_FUNCTION_CONTRACT: F-M-AUDIT-ASTRONOMY-ORACLE.run_astronomy_oracle
    # purpose: Run direct Swiss Ephemeris verification and write audit artifacts.
    # inputs: artifact paths, target date/time/timezone, output dir.
    # returns: summary dict with pass/fail aggregates.
    # side_effects: writes CSV/JSON artifacts.
    # emitted_logs: none.
    # error_behavior: propagates file/swisseph errors.
    # END_FUNCTION_CONTRACT: F-M-AUDIT-ASTRONOMY-ORACLE.run_astronomy_oracle
    if ephemeris_path:
        swe.set_ephe_path(ephemeris_path)
    elif os.getenv("SWEPH_PATH"):
        swe.set_ephe_path(os.environ["SWEPH_PATH"])

    profile = load_json(input_profile_path)
    raw_transits = load_json(raw_transits_path)
    natal_context = load_json(raw_natal_context_path)
    payload = load_json(final_payload_path)
    tz_name = target_tz or profile.get("current", {}).get("tz") or profile["birth"]["tz"]

    jd = julian_day(target_date, target_time, tz_name)
    oracle_positions = planet_positions(jd)
    production_planets = raw_transits.get("planets", [])

    rows: list[dict[str, Any]] = []
    for name in PLANETS:
        prod = planet_by_name(production_planets, name) or {}
        oracle = oracle_positions[name]
        prod_lon = float(prod.get("longitude", 0.0))
        delta = shortest_delta(oracle["longitude"], prod_lon)
        prod_speed = prod.get("speed")
        speed_delta = (
            abs(oracle["speed"] - float(prod_speed)) if prod_speed is not None else None
        )
        prod_retro = prod.get("retrograde")
        final_planet = final_chart_planet(payload, name) or {}
        rows.append(
            {
                "check": "transit_planet",
                "planet": name,
                "oracle_longitude": round(oracle["longitude"], 8),
                "production_longitude": round(prod_lon, 8),
                "longitude_delta_deg": round(delta, 8),
                "longitude_pass": delta <= LONGITUDE_TOLERANCE_DEG,
                "oracle_sign": oracle["sign"],
                "production_sign": prod.get("sign"),
                "sign_pass": oracle["sign"] == prod.get("sign"),
                "oracle_speed": round(oracle["speed"], 8),
                "production_speed": prod_speed,
                "speed_delta": round(speed_delta, 8) if speed_delta is not None else "",
                "oracle_retrograde": oracle["retrograde"],
                "production_retrograde": prod_retro,
                "retrograde_flag_pass": prod_retro == oracle["retrograde"],
                "final_motion": final_planet.get("motion"),
            }
        )

    sun = oracle_positions["Sun"]
    moon = oracle_positions["Moon"]
    moon_phase = moon_phase_percent(sun["longitude"], moon["longitude"])
    prod_phase = production_lunar_percent(payload)

    transit_pluto = oracle_positions["Pluto"]
    transit_moon_pluto_orb = abs(angular_distance(moon["longitude"], transit_pluto["longitude"]) - 180.0)
    natal_pluto = planet_by_name(natal_context.get("planets", []), "Pluto")
    natal_moon_pluto_orb = None
    if natal_pluto:
        natal_moon_pluto_orb = abs(
            angular_distance(moon["longitude"], float(natal_pluto["longitude"])) - 180.0
        )

    house_system = natal_context.get("house_system")
    oracle_houses = calculate_houses_from_birth(profile, house_system)
    house_rows: list[dict[str, Any]] = []
    for name in PLANETS:
        oracle = oracle_positions[name]
        oracle_house = find_house(oracle["longitude"], oracle_houses)
        final_planet = final_chart_planet(payload, name) or {}
        house_rows.append(
            {
                "planet": name,
                "oracle_longitude": round(oracle["longitude"], 8),
                "oracle_house": oracle_house,
                "production_house": final_planet.get("house"),
                "house_pass": oracle_house == final_planet.get("house"),
                "final_sign": final_planet.get("sign"),
                "oracle_sign": oracle["sign"],
            }
        )

    # START_BLOCK: FINAL_CHART_PROOF
    # The FINAL serialized dayChart must equal the independent Swiss result:
    # transit longitudes/signs/retrograde+motion and the serialized house
    # list (number/order/cusp/sign). Raw transit proof above is necessary but
    # NOT sufficient — the payload itself is the money boundary.
    final_chart = payload.get("dayChart") or payload.get("day_chart") or {}
    final_planets = final_chart.get("transitPlanets") or final_chart.get("transit_planets") or []
    final_rows: list[dict[str, Any]] = []
    for name in PLANETS:
        oracle = oracle_positions[name]
        final_planet = next((p for p in final_planets if p.get("name") == name), None) or {}
        final_lon = final_planet.get("longitude")
        final_delta = shortest_delta(oracle["longitude"], float(final_lon)) if isinstance(final_lon, (int, float)) else None
        final_motion = final_planet.get("motion")
        # Mirror the payload's own motion derivation: stationary beats
        # retrograde when |speed| < 0.01, retrograde on negative speed or the
        # retrograde flag, else direct.
        oracle_speed = float(oracle["speed"])
        if abs(oracle_speed) < 0.01:
            expected_motion = "stationary"
        elif oracle_speed < 0 or oracle["retrograde"]:
            expected_motion = "retrograde"
        else:
            expected_motion = "direct"
        final_rows.append(
            {
                "planet": name,
                "oracle_longitude": round(oracle["longitude"], 8),
                "final_longitude": final_lon,
                "final_longitude_delta_deg": round(final_delta, 8) if final_delta is not None else "",
                "final_longitude_pass": final_delta is not None and final_delta <= LONGITUDE_TOLERANCE_DEG,
                "oracle_sign": oracle["sign"],
                "final_sign": final_planet.get("sign"),
                "final_sign_pass": final_planet.get("sign") == oracle["sign"],
                "oracle_speed": round(oracle_speed, 8),
                "oracle_retrograde": oracle["retrograde"],
                "final_motion": final_motion,
                "expected_motion": expected_motion,
                "final_motion_pass": final_motion == expected_motion,
            }
        )
    final_houses = final_chart.get("houses") or []
    final_house_rows: list[dict[str, Any]] = []
    if len(final_houses) != len(oracle_houses):
        final_house_rows.append(
            {
                "number": None,
                "oracle_cusp": "",
                "final_cusp": "",
                "final_house_pass": False,
                "reason": f"house count mismatch: oracle {len(oracle_houses)} vs final {len(final_houses)}",
            }
        )
    for idx, oracle_house in enumerate(oracle_houses):
        final_house = final_houses[idx] if idx < len(final_houses) else {}
        oracle_cusp = float(oracle_house["longitude"])
        final_cusp = (
            final_house["cuspLongitude"]
            if "cuspLongitude" in final_house
            else final_house.get("cusp_longitude")
        )
        final_house_rows.append(
            {
                "number": oracle_house["number"],
                "oracle_cusp": round(oracle_cusp, 8),
                "final_cusp": final_cusp,
                "final_cusp_pass": (
                    final_house.get("number") == oracle_house["number"]
                    and isinstance(final_cusp, (int, float))
                    and shortest_delta(oracle_cusp, float(final_cusp)) <= LONGITUDE_TOLERANCE_DEG
                ),
                "oracle_sign": oracle_house["sign"],
                "final_sign": final_house.get("sign"),
                "final_house_sign_pass": final_house.get("sign") == oracle_house["sign"],
            }
        )
    # END_BLOCK: FINAL_CHART_PROOF

    summary = {
        "target": {"date": target_date, "time": target_time, "timezone": tz_name, "jd": jd},
        "longitude_pass": all(row["longitude_pass"] for row in rows),
        "sign_pass": all(row["sign_pass"] for row in rows),
        "retrograde_flag_pass": all(row["retrograde_flag_pass"] for row in rows),
        "house_pass": all(row["house_pass"] for row in house_rows),
        "final_transit_longitude_pass": all(row["final_longitude_pass"] for row in final_rows),
        "final_transit_sign_pass": all(row["final_sign_pass"] for row in final_rows),
        "final_motion_pass": all(row["final_motion_pass"] for row in final_rows),
        "final_house_cusp_pass": all(row["final_cusp_pass"] for row in final_house_rows),
        "final_house_sign_pass": all(row["final_house_sign_pass"] for row in final_house_rows),
        "moon_phase": {
            "oracle_percent": round(moon_phase, 4),
            "production_percent": prod_phase,
            "delta_percent": round(moon_phase - prod_phase, 4) if prod_phase is not None else None,
            "pass": abs(moon_phase - prod_phase) <= 0.5 if prod_phase is not None else None,
        },
        "moon_opposite_pluto": {
            "transit_moon_to_transit_pluto_orb": round(transit_moon_pluto_orb, 4),
            "transit_moon_to_transit_pluto_pass": transit_moon_pluto_orb <= 8.0,
            "transit_moon_to_natal_pluto_orb": (
                round(natal_moon_pluto_orb, 4) if natal_moon_pluto_orb is not None else None
            ),
            "transit_moon_to_natal_pluto_pass": (
                natal_moon_pluto_orb <= 8.0 if natal_moon_pluto_orb is not None else None
            ),
        },
        "house_system": house_system,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "astronomy_oracle.csv", rows)
    write_csv(out_dir / "house_placements_oracle.csv", house_rows)
    write_csv(out_dir / "final_transit_oracle.csv", final_rows)
    write_csv(out_dir / "final_houses_oracle.csv", final_house_rows)
    write_json(out_dir / "astronomy_oracle_summary.json", summary)
    write_json(out_dir / "astronomy_oracle_positions.json", oracle_positions)
    write_json(out_dir / "astronomy_oracle_houses.json", oracle_houses)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Independent SolarSage astronomy oracle")
    parser.add_argument("--input-profile", type=Path, required=True)
    parser.add_argument("--raw-transits", type=Path, required=True)
    parser.add_argument("--raw-natal-context", type=Path, required=True)
    parser.add_argument("--final-payload", type=Path, required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--time", default="12:00")
    parser.add_argument("--tz", default=None)
    parser.add_argument("--ephemeris-path", default="/opt/sweph/ephe")
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_astronomy_oracle(
        input_profile_path=args.input_profile,
        raw_transits_path=args.raw_transits,
        raw_natal_context_path=args.raw_natal_context,
        final_payload_path=args.final_payload,
        target_date=args.date,
        target_time=args.time,
        target_tz=args.tz,
        out_dir=args.out,
        ephemeris_path=args.ephemeris_path,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    # Propagate failures
    has_failed = (
        not summary["longitude_pass"]
        or not summary["sign_pass"]
        or not summary["retrograde_flag_pass"]
        or not summary["house_pass"]
        or not summary["final_transit_longitude_pass"]
        or not summary["final_transit_sign_pass"]
        or not summary["final_motion_pass"]
        or not summary["final_house_cusp_pass"]
        or not summary["final_house_sign_pass"]
    )
    if summary["moon_phase"]["pass"] is False:
        has_failed = True

    if has_failed:
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
