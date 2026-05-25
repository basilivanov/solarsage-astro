#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

PLANETS = [
    "SUN",
    "MOON",
    "MERCURY",
    "VENUS",
    "MARS",
    "JUPITER",
    "SATURN",
    "URANUS",
    "NEPTUNE",
    "PLUTO",
    "CHIRON",
    "NORTH_NODE_TRUE",
    "SOUTH_NODE",
    "LILITH_MEAN",
    "LILITH_TRUE",
]
CORE = ["SUN", "MOON", "MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO"]
TRADITIONAL_PLANETS = ["SUN", "MOON", "MERCURY", "VENUS", "MARS", "JUPITER", "SATURN"]
HELIACAL_PLANETS = ["MERCURY", "VENUS", "MARS", "JUPITER", "SATURN"]
DEFAULT_VARGAS = ["D1", "D7", "D9", "D10", "D12"]
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
WESTERN_ASPECTS = {"CONJUNCTION", "SEXTILE", "SQUARE", "TRINE", "OPPOSITION"}
WESTERN_ASPECT_LIST = ["CONJUNCTION", "SEXTILE", "SQUARE", "TRINE", "OPPOSITION"]
MAJOR_ASPECT_DEFS = {
    "CONJUNCTION": {"angle": 0.0, "orb": 8.0},
    "OPPOSITION": {"angle": 180.0, "orb": 8.0},
    "TRINE": {"angle": 120.0, "orb": 7.0},
    "SQUARE": {"angle": 90.0, "orb": 7.0},
    "SEXTILE": {"angle": 60.0, "orb": 5.0},
}
PLANET_ORBS = {
    "SUN": 15.0,
    "MOON": 12.0,
    "JUPITER": 9.0,
    "SATURN": 9.0,
    "MERCURY": 7.5,
    "VENUS": 7.5,
    "MARS": 7.5,
    "URANUS": 5.0,
    "NEPTUNE": 5.0,
    "PLUTO": 5.0,
    "CHIRON": 5.0,
    "NORTH_NODE_TRUE": 5.0,
    "SOUTH_NODE": 5.0,
    "LILITH_MEAN": 5.0,
    "LILITH_TRUE": 5.0,
}
ASPECT_DEFS = [
    ("CONJUNCTION", 0.0, 1.0),
    ("OPPOSITION", 180.0, 1.0),
    ("TRINE", 120.0, 0.875),
    ("SQUARE", 90.0, 0.875),
    ("SEXTILE", 60.0, 0.625),
    ("SEMI_SEXTILE", 30.0, 2.0),
    ("SEMI_SQUARE", 45.0, 2.0),
    ("SESQUIQUADRATE", 135.0, 2.0),
    ("QUINCUNX", 150.0, 2.0),
]
ANGLE_POINTS = {
    "ASC": "asc",
    "MC": "mc",
    "DSC": "dsc",
    "IC": "ic",
}
SWISSEPH_SPECIAL_POINTS = ["VERTEX", "ANTI_VERTEX", "EAST_POINT"]
SIGN_ELEMENTS = {
    "Aries": "Fire",
    "Leo": "Fire",
    "Sagittarius": "Fire",
    "Taurus": "Earth",
    "Virgo": "Earth",
    "Capricorn": "Earth",
    "Gemini": "Air",
    "Libra": "Air",
    "Aquarius": "Air",
    "Cancer": "Water",
    "Scorpio": "Water",
    "Pisces": "Water",
}
SIGN_MODALITIES = {
    "Aries": "Cardinal",
    "Cancer": "Cardinal",
    "Libra": "Cardinal",
    "Capricorn": "Cardinal",
    "Taurus": "Fixed",
    "Leo": "Fixed",
    "Scorpio": "Fixed",
    "Aquarius": "Fixed",
    "Gemini": "Mutable",
    "Virgo": "Mutable",
    "Sagittarius": "Mutable",
    "Pisces": "Mutable",
}
SIGN_RULERS = {
    "Aries": "MARS",
    "Taurus": "VENUS",
    "Gemini": "MERCURY",
    "Cancer": "MOON",
    "Leo": "SUN",
    "Virgo": "MERCURY",
    "Libra": "VENUS",
    "Scorpio": "MARS",
    "Sagittarius": "JUPITER",
    "Capricorn": "SATURN",
    "Aquarius": "SATURN",
    "Pisces": "JUPITER",
}
PLANET_RU = {
    "SUN": "Солнце",
    "MOON": "Луна",
    "MERCURY": "Меркурий",
    "VENUS": "Венера",
    "MARS": "Марс",
    "JUPITER": "Юпитер",
    "SATURN": "Сатурн",
    "URANUS": "Уран",
    "NEPTUNE": "Нептун",
    "PLUTO": "Плутон",
    "CHIRON": "Хирон",
    "NORTH_NODE_TRUE": "Северный узел",
    "SOUTH_NODE": "Южный узел",
    "LILITH_MEAN": "Лилит mean",
    "LILITH_TRUE": "Лилит true",
    "SELENA": "Селена",
}
SPECIAL_POINT_RU = {
    "ASC": "ASC",
    "MC": "MC",
    "DSC": "DSC",
    "IC": "IC",
    "VERTEX": "Вертекс",
    "ANTI_VERTEX": "Анти-Вертекс",
    "EAST_POINT": "East Point",
    "SELENA": "Селена",
}
SPHERES = {
    "identity_entry": {"houses": {1}, "planets": {"SUN", "MOON"}, "lots": set()},
    "money_resources": {"houses": {2, 8, 11}, "planets": {"VENUS", "JUPITER", "SATURN"}, "lots": {"Lot of Fortune"}},
    "thinking_speech_learning": {"houses": {3}, "planets": {"MERCURY", "JUPITER", "SATURN"}, "lots": set()},
    "home_roots_safety": {"houses": {4}, "planets": {"MOON", "SATURN", "VENUS"}, "lots": set()},
    "love_pleasure_creativity": {"houses": {5, 7}, "planets": {"VENUS", "MOON", "MARS"}, "lots": {"Lot of Eros"}},
    "work_routine_health": {"houses": {6}, "planets": {"MARS", "SATURN", "MERCURY"}, "lots": set()},
    "relationships_marriage": {"houses": {7}, "planets": {"VENUS", "MOON", "SATURN"}, "lots": {"Lot of Marriage (M)", "Lot of Marriage (W)"}},
    "crisis_intimacy_control": {"houses": {8}, "planets": {"MARS", "SATURN", "PLUTO"}, "lots": set()},
    "career_status_role": {"houses": {10}, "planets": {"SUN", "SATURN", "JUPITER"}, "lots": {"Lot of Fortune", "Lot of Spirit"}},
    "meaning_faith_vector": {"houses": {9, 12}, "planets": {"JUPITER", "SUN", "MOON"}, "lots": set()},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect a deep SolarSage JSON package.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--date", required=True, help="Birth date, YYYY-MM-DD")
    parser.add_argument("--time", required=True, help="Birth time, HH:MM")
    parser.add_argument("--timezone", required=True, help="IANA timezone, e.g. Asia/Yekaterinburg")
    parser.add_argument("--location", required=True)
    parser.add_argument("--lat", required=True, type=float)
    parser.add_argument("--lon", required=True, type=float)
    parser.add_argument("--out", required=True)
    parser.add_argument("--base-url", default=os.environ.get("SOLARSAGE_BASE_URL", "http://127.0.0.1:18091"))
    parser.add_argument("--api-key", default=os.environ.get("SOLARSAGE_API_KEY", "basil-solarsage-local"))
    parser.add_argument("--house-system", choices=["auto", "placidus", "whole_sign", "PLACIDUS", "WHOLE_SIGN"], default="auto")
    parser.add_argument("--high-lat-threshold", type=float, default=60.0)
    parser.add_argument("--fixed-stars-orb", type=float, default=1.5)
    parser.add_argument("--antiscia-orb", type=float, default=1.0)
    parser.add_argument("--midpoints-orb", type=float, default=1.0)
    parser.add_argument("--target-date", default="2026-04-16", help="Forecast/direction date, YYYY-MM-DD.")
    parser.add_argument("--target-time", default="00:00", help="Forecast/direction local time, HH:MM or HH:MM:SS.")
    parser.add_argument("--target-timezone", default=None, help="IANA timezone for target date; defaults to birth timezone.")
    parser.add_argument("--target-year", type=int, default=2026)
    parser.add_argument("--target-month", type=int, default=4)
    parser.add_argument("--direction-max-age", type=float, default=100.0)
    parser.add_argument("--wheel-radius", type=float, default=240.0)
    parser.add_argument("--ayanamsa", default="LAHIRI")
    parser.add_argument("--vargas", nargs="+", default=DEFAULT_VARGAS)
    parser.add_argument("--heliacal-altitude", type=float, default=0.0)
    parser.add_argument("--include-non-western", action="store_true", help="Include sidereal/divisional/Vedic raw layers.")
    return parser.parse_args()


def resolve_house_system(latitude: float, requested: str, threshold: float) -> tuple[str, str]:
    normalized = requested.lower()
    if normalized in {"placidus", "plac"}:
        return "PLACIDUS", "requested"
    if normalized in {"whole_sign", "wholesign", "whole-sign"}:
        return "WHOLE_SIGN", "requested"
    if abs(latitude) >= threshold:
        return "WHOLE_SIGN", f"auto_high_latitude_abs_lat_ge_{threshold:g}"
    return "PLACIDUS", f"auto_normal_latitude_abs_lat_lt_{threshold:g}"


def julian_day_ut(dt_utc: datetime) -> float:
    year = dt_utc.year
    month = dt_utc.month
    day = dt_utc.day + (dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600 + dt_utc.microsecond / 3_600_000_000) / 24
    if month <= 2:
        year -= 1
        month += 12
    a = math.floor(year / 100)
    b = 2 - a + math.floor(a / 4)
    return math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + b - 1524.5


def parse_local_datetime(date_value: str, time_value: str, timezone_name: str) -> datetime:
    time_part = time_value if time_value.count(":") == 2 else f"{time_value}:00"
    return datetime.fromisoformat(f"{date_value}T{time_part}").replace(tzinfo=ZoneInfo(timezone_name))


def date_time_to_jd(date_value: str, time_value: str, timezone_name: str) -> tuple[datetime, datetime, float]:
    local_dt = parse_local_datetime(date_value, time_value, timezone_name)
    utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
    return local_dt, utc_dt, julian_day_ut(utc_dt)


def year_bounds_jd(year: int) -> tuple[float, float]:
    start = datetime(year, 1, 1, 0, 0, 0, tzinfo=ZoneInfo("UTC"))
    end = datetime(year, 12, 31, 23, 59, 59, tzinfo=ZoneInfo("UTC"))
    return julian_day_ut(start), julian_day_ut(end)


def month_start_jd(year: int, month: int) -> float:
    return julian_day_ut(datetime(year, month, 1, 0, 0, 0, tzinfo=ZoneInfo("UTC")))


def age_on_date(birth_dt: datetime, target_dt: datetime) -> int:
    age = target_dt.year - birth_dt.year
    if (target_dt.month, target_dt.day) < (birth_dt.month, birth_dt.day):
        age -= 1
    return age


def post(base_url: str, api_key: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode())


def safe(base_url: str, api_key: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return {"ok": True, "value": post(base_url, api_key, path, payload), "request": {"path": path, "payload": payload}}
    except urllib.error.HTTPError as exc:
        return {
            "ok": False,
            "error": f"HTTP {exc.code}",
            "body": exc.read().decode(errors="replace"),
            "request": {"path": path, "payload": payload},
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "request": {"path": path, "payload": payload}}


def aspect_exactness(orb: float) -> float:
    return max(0.0, min(1.0, 1.0 - (orb / 8.0)))


def nearest_house_from_cusps(longitude: float, cusps: list[float]) -> int | None:
    if len(cusps) != 12:
        return None
    lon = longitude % 360
    for index in range(12):
        start = cusps[index] % 360
        end = cusps[(index + 1) % 12] % 360
        if start <= end:
            inside = start <= lon < end
        else:
            inside = lon >= start or lon < end
        if inside:
            return index + 1
    return None


def normalize_degrees(value: float) -> float:
    return float(value) % 360.0


def sign_name_from_longitude(longitude: float) -> str:
    return SIGNS[int(normalize_degrees(longitude) // 30) % 12]


def whole_sign_house(longitude: float, asc: float | None) -> int | None:
    if asc is None:
        return None
    return int(((math.floor(normalize_degrees(longitude) / 30) - math.floor(normalize_degrees(asc) / 30)) % 12) + 1)


def point_entry(point_id: str, longitude: float, houses: list[float], angles: dict[str, Any], source: str) -> dict[str, Any]:
    lon = normalize_degrees(longitude)
    asc = angles.get("asc")
    return {
        "point_id": point_id,
        "name": point_id,
        "ru_name": SPECIAL_POINT_RU.get(point_id, point_id),
        "longitude": lon,
        "sign": sign_name_from_longitude(lon),
        "sign_degree": lon % 30,
        "placidus_house": nearest_house_from_cusps(lon, houses),
        "whole_sign_house": whole_sign_house(lon, float(asc)) if isinstance(asc, (int, float)) else None,
        "source": source,
    }


def angular_distance(a: float, b: float) -> float:
    diff = abs(normalize_degrees(a) - normalize_degrees(b))
    return min(diff, 360.0 - diff)


def moiety_orb(point_a: str, point_b: str, aspect_type: str) -> float:
    orb_a = PLANET_ORBS.get(point_a.upper(), 5.0)
    orb_b = PLANET_ORBS.get(point_b.upper(), 5.0)
    moiety = (orb_a + orb_b) / 2.0
    return moiety


def aspect_exactness_dynamic(orb: float, max_orb: float, p1: str, p2: str) -> float:
    exactness = max(0.0, min(1.0, 1.0 - (orb / max_orb)))
    important_ids = {"SUN", "MOON", "MERCURY", "VENUS", "MARS", "JUPITER", "SATURN"}
    base = 1.0 if p1 in important_ids and p2 in important_ids else 0.75
    return base * exactness


def check_aspect(p1: str, p1_lon: float, p2: str, p2_lon: float) -> dict[str, Any] | None:
    diff = angular_distance(p1_lon, p2_lon)
    best: dict[str, Any] | None = None
    for name, angle, val in ASPECT_DEFS:
        if name in {"CONJUNCTION", "OPPOSITION", "TRINE", "SQUARE", "SEXTILE"}:
            max_orb = moiety_orb(p1, p2, name) * val
        else:
            max_orb = val  # fixed orb for minor aspects
        orb = abs(diff - angle)
        if orb <= max_orb and (best is None or orb < best["orb"]):
            best = {
                "planet_a": p1,
                "planet_b": p2,
                "aspect_type": name.title().replace("_", "-"),
                "aspect_angle": angle,
                "actual_angle": diff,
                "orb": orb,
                "max_orb": max_orb,
                "score_hint": round(aspect_exactness_dynamic(orb, max_orb, p1, p2), 4),
            }
    return best


def get_raw_exactness(aspect: dict[str, Any]) -> float:
    orb = float(aspect.get("orb", 0.0))
    max_orb = float(aspect.get("max_orb", 8.0))
    return max(0.0, min(1.0, 1.0 - (orb / max_orb)))


def check_special_point_aspect(point_id: str, point_lon: float, planet_id: str, planet_lon: float) -> dict[str, Any] | None:
    diff = angular_distance(point_lon, planet_lon)
    best: dict[str, Any] | None = None
    for name, angle, val in ASPECT_DEFS:
        if name in {"CONJUNCTION", "OPPOSITION", "TRINE", "SQUARE", "SEXTILE"}:
            max_orb = moiety_orb(point_id, planet_id, name) * val
        else:
            max_orb = val
        orb = abs(diff - angle)
        if orb <= max_orb and (best is None or orb < best["orb"]):
            best = {
                "aspect_type": name.title().replace("_", "-"),
                "aspect_angle": angle,
                "actual_angle": diff,
                "orb": orb,
                "max_orb": max_orb,
                "score_hint": round(aspect_exactness_dynamic(orb, max_orb, point_id, planet_id), 4),
                "point_id": point_id,
                "planet_id": planet_id,
                "point_longitude": point_lon,
                "planet_longitude": planet_lon,
            }
    return best


def collect_special_point_aspects(special_points: dict[str, dict[str, Any]], planets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aspects: list[dict[str, Any]] = []
    aspect_points = ["VERTEX", "ANTI_VERTEX", "EAST_POINT", "SELENA"]
    for point_id in aspect_points:
        point = special_points.get(point_id)
        if not point:
            continue
        for planet in planets:
            planet_id = planet.get("planet_id")
            if point_id == "SELENA" and planet_id == "LILITH_MEAN":
                continue
            longitude = planet.get("longitude")
            if not isinstance(longitude, (int, float)):
                continue
            match = check_special_point_aspect(point_id, point["longitude"], planet_id, float(longitude))
            if not match:
                continue
            aspects.append(match)
    aspects.sort(key=lambda item: (item["score_hint"], -item["orb"]), reverse=True)
    return aspects


def native_special_point_records(natal: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for key in ["special_points", "points"]:
        container = natal.get(key)
        if isinstance(container, list):
            for item in container:
                if isinstance(item, dict):
                    records.append(item)
        elif isinstance(container, dict):
            for point_id, value in container.items():
                if isinstance(value, dict):
                    records.append({"point_id": point_id, **value})
                else:
                    records.append({"point_id": point_id, "longitude": value})
    return records


def collect_native_special_points(natal: dict[str, Any], houses: list[float], angles: dict[str, Any]) -> dict[str, dict[str, Any]]:
    points: dict[str, dict[str, Any]] = {}
    for record in native_special_point_records(natal):
        point_id = record.get("point_id") or record.get("id") or record.get("name")
        longitude = record.get("longitude")
        if point_id and isinstance(longitude, (int, float)):
            points[str(point_id).upper()] = point_entry(str(point_id).upper(), float(longitude), houses, angles, "solarsage_rest_native")
    return points


def calc_swisseph_special_points(latitude: float, longitude: float, jd_ut: float, house_system: str) -> dict[str, Any]:
    repo = Path(os.environ.get("SOLARSAGE_REPO", "/opt/solarsage"))
    swe_dir = Path(os.environ.get("SOLARSAGE_SWISSEPH_DIR", str(repo / "third_party" / "swisseph")))
    ephe_dir = Path(os.environ.get("SWISSEPH_EPHE_PATH") or os.environ.get("SE_EPHE_PATH") or str(swe_dir / "ephe"))
    lib_path = swe_dir / "libswe.a"
    cc = shutil.which("cc") or shutil.which("gcc")
    hsys_chars = {
        "PLACIDUS": "P",
        "WHOLE_SIGN": "W",
        "KOCH": "K",
        "EQUAL": "E",
        "CAMPANUS": "C",
        "REGIOMONTANUS": "R",
        "PORPHYRY": "O",
        "MORINUS": "M",
        "TOPOCENTRIC": "T",
        "ALCABITIUS": "B",
        "MERIDIAN": "X",
    }
    if not cc:
        return {"ok": False, "error": "C compiler not found"}
    if not swe_dir.exists() or not lib_path.exists():
        return {"ok": False, "error": f"SolarSage Swiss Ephemeris library not found under {swe_dir}"}
    if not ephe_dir.exists():
        return {"ok": False, "error": f"Swiss Ephemeris data directory not found: {ephe_dir}"}
    hsys = hsys_chars.get(house_system.upper(), "P")
    source = r'''
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include "swephexp.h"

static double norm360(double value) {
    double result = fmod(value, 360.0);
    return result < 0 ? result + 360.0 : result;
}

int main(int argc, char **argv) {
    if (argc != 6) {
        fprintf(stderr, "usage: helper LAT LON JD_UT HOUSE_CHAR EPHE_PATH\n");
        return 2;
    }
    double lat = atof(argv[1]);
    double lon = atof(argv[2]);
    double jd_ut = atof(argv[3]);
    int hsys = argv[4][0];
    swe_set_ephe_path(argv[5]);

    double cusps[13];
    double ascmc[10];
    int rc = swe_houses(jd_ut, lat, lon, hsys, cusps, ascmc);
    if (rc < 0) {
        fprintf(stderr, "swe_houses failed\n");
        return 1;
    }

    printf("{\"VERTEX\":%.12f,\"ANTI_VERTEX\":%.12f,\"EAST_POINT\":%.12f}\n",
        norm360(ascmc[3]), norm360(ascmc[3] + 180.0), norm360(ascmc[4]));
    swe_close();
    return 0;
}
'''
    with tempfile.TemporaryDirectory(prefix="solarsage-swe-") as tmp:
        tmp_path = Path(tmp)
        src = tmp_path / "special_points.c"
        binary = tmp_path / "special_points"
        src.write_text(source, encoding="utf-8")
        compile_cmd = [cc, "-O2", "-I", str(swe_dir), str(src), str(lib_path), "-lm", "-o", str(binary)]
        compiled = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=60)
        if compiled.returncode != 0:
            return {"ok": False, "error": compiled.stderr.strip() or compiled.stdout.strip() or "helper compile failed"}
        run_cmd = [str(binary), str(latitude), str(longitude), f"{jd_ut:.12f}", hsys, str(ephe_dir)]
        completed = subprocess.run(run_cmd, capture_output=True, text=True, timeout=30)
        if completed.returncode != 0:
            return {"ok": False, "error": completed.stderr.strip() or completed.stdout.strip() or "helper run failed"}
        try:
            return {
                "ok": True,
                "source": "solarsage_vendored_swisseph",
                "points": json.loads(completed.stdout),
            }
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": f"helper returned invalid JSON: {exc}"}


def collect_special_points(
    natal: dict[str, Any],
    planet_by_id: dict[str, dict[str, Any]],
    houses: list[float],
    angles: dict[str, Any],
    latitude: float,
    longitude: float,
    jd_ut: float,
    house_system: str,
) -> dict[str, Any]:
    points: dict[str, dict[str, Any]] = {}
    for point_id, angle_key in ANGLE_POINTS.items():
        angle = angles.get(angle_key)
        if isinstance(angle, (int, float)):
            points[point_id] = point_entry(point_id, float(angle), houses, angles, "solarsage_rest_angles")

    points.update(collect_native_special_points(natal, houses, angles))

    helper_status = calc_swisseph_special_points(latitude, longitude, jd_ut, house_system)
    if helper_status.get("ok"):
        for point_id, point_longitude in dict(helper_status.get("points") or {}).items():
            if isinstance(point_longitude, (int, float)):
                points[str(point_id)] = point_entry(str(point_id), float(point_longitude), houses, angles, helper_status["source"])

    lilith = planet_by_id.get("LILITH_MEAN")
    lilith_longitude = lilith.get("longitude") if lilith else None
    if isinstance(lilith_longitude, (int, float)):
        points["SELENA"] = point_entry("SELENA", float(lilith_longitude) + 180.0, houses, angles, "derived_from_solarsage_lilith_mean_plus_180")

    missing = [point_id for point_id in [*ANGLE_POINTS.keys(), *SWISSEPH_SPECIAL_POINTS, "SELENA"] if point_id not in points]
    return {
        "points": points,
        "missing": missing,
        "helper_status": helper_status,
    }


def chain_for(planet_id: str, planet_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    chain: list[dict[str, Any]] = []
    seen: set[str] = set()
    current = planet_id
    for _ in range(12):
        planet = planet_by_id.get(current)
        if not planet:
            break
        ruler = SIGN_RULERS[planet["sign"]]
        chain.append({"planet": current, "sign": planet["sign"], "dispositor": ruler})
        if ruler == current:
            return {"chain": chain, "final": ruler, "type": "domicile_final"}
        if ruler in seen:
            chain.append({"planet": ruler, "cycle": True})
            return {"chain": chain, "final": ruler, "type": "cycle"}
        seen.add(current)
        current = ruler
    return {"chain": chain, "final": current, "type": "open"}


def condition_factor(planet_id: str, planet_by_id: dict[str, dict[str, Any]]) -> float:
    planet = planet_by_id.get(planet_id)
    if not planet:
        return 1.0
    factor = 1.0
    house = int(planet["house"])
    sign = planet["sign"]
    if planet.get("is_retrograde"):
        factor -= 0.15
    if planet_id in {"VENUS", "JUPITER"} and house in {1, 4, 7, 10}:
        factor += 0.15
    if planet_id == "JUPITER" and sign == "Cancer":
        factor += 0.25
    if planet_id == "VENUS" and sign in {"Taurus", "Libra"}:
        factor += 0.25
    if planet_id == "MERCURY" and sign in {"Virgo", "Gemini"}:
        factor += 0.20
    if planet_id == "SATURN" and sign == "Libra":
        factor += 0.20
    if planet_id == "SATURN" and sign == "Leo":
        factor -= 0.15
    if planet_id == "MERCURY" and planet.get("is_retrograde"):
        factor -= 0.10
    return max(0.45, min(1.35, factor))


def collect(args: argparse.Namespace) -> dict[str, Any]:
    house_system, house_policy = resolve_house_system(args.lat, args.house_system, args.high_lat_threshold)
    local_dt, utc_dt, jd_ut = date_time_to_jd(args.date, args.time, args.timezone)
    target_timezone = args.target_timezone or args.timezone
    target_local_dt, target_utc_dt, target_jd_ut = date_time_to_jd(args.target_date, args.target_time, target_timezone)
    target_age = age_on_date(local_dt, target_local_dt)
    year_start_jd, year_end_jd = year_bounds_jd(args.target_year)
    month_search_jd = month_start_jd(args.target_year, args.target_month)
    base_payload = {"latitude": args.lat, "longitude": args.lon, "jd_ut": jd_ut, "house_system": house_system}
    chart_payload = {**base_payload, "planets": PLANETS}
    core_payload = {**base_payload, "planets": CORE}
    target_label = args.target_date.replace("-", "_")

    raw = {
        "natal": safe(args.base_url, args.api_key, "/api/v1/chart/natal", chart_payload),
        "natal_whole_sign": safe(args.base_url, args.api_key, "/api/v1/chart/natal", {**base_payload, "planets": PLANETS, "house_system": "WHOLE_SIGN"}),
        "natal_placidus": safe(args.base_url, args.api_key, "/api/v1/chart/natal", {**base_payload, "planets": PLANETS, "house_system": "PLACIDUS"}),
        "chart_wheel": safe(args.base_url, args.api_key, "/api/v1/chart/wheel", {**core_payload, "radius": args.wheel_radius}),
        "dignity": safe(args.base_url, args.api_key, "/api/v1/dignity", core_payload),
        "bonification": safe(args.base_url, args.api_key, "/api/v1/bonification", core_payload),
        "dispositors_modern": safe(args.base_url, args.api_key, "/api/v1/dispositors", {**core_payload, "traditional": False}),
        "dispositors_traditional": safe(args.base_url, args.api_key, "/api/v1/dispositors", {**core_payload, "traditional": True}),
        "profection": safe(args.base_url, args.api_key, "/api/v1/profection", {**base_payload, "natal_jd_ut": jd_ut, "age": target_age, "include_monthly": True}),
        "lots": safe(args.base_url, args.api_key, "/api/v1/lots", base_payload),
        "bounds": safe(args.base_url, args.api_key, "/api/v1/bounds", base_payload),
        "antiscia": safe(args.base_url, args.api_key, "/api/v1/antiscia", {**core_payload, "orb": args.antiscia_orb}),
        "planetary_hours": safe(args.base_url, args.api_key, "/api/v1/planetary-hours", {"latitude": args.lat, "longitude": args.lon, "jd_ut": jd_ut}),
        "heliacal": safe(args.base_url, args.api_key, "/api/v1/heliacal", {
            "latitude": args.lat,
            "longitude": args.lon,
            "altitude": args.heliacal_altitude,
            "start_jd_ut": year_start_jd,
            "end_jd_ut": year_end_jd,
            "planets": HELIACAL_PLANETS,
        }),
        "fixed_stars": safe(args.base_url, args.api_key, "/api/v1/fixed-stars", {**core_payload, "orb": args.fixed_stars_orb}),
        "midpoints": safe(args.base_url, args.api_key, "/api/v1/midpoints", {**core_payload, "orb": args.midpoints_orb}),
        "aspect_patterns": safe(args.base_url, args.api_key, "/api/v1/aspects/patterns", core_payload),
        f"transit_{target_label}": safe(args.base_url, args.api_key, "/api/v1/transit", {
            "natal_latitude": args.lat,
            "natal_longitude": args.lon,
            "natal_jd_ut": jd_ut,
            "natal_planets": CORE,
            "transit_latitude": args.lat,
            "transit_longitude": args.lon,
            "start_jd_ut": target_jd_ut,
            "end_jd_ut": target_jd_ut + 1.0,
            "transit_planets": CORE,
            "house_system": house_system,
            "timezone": target_timezone,
        }),
        f"progressions_{target_label}": safe(args.base_url, args.api_key, "/api/v1/progressions", {
            "natal_jd_ut": jd_ut,
            "transit_jd_ut": target_jd_ut,
            "planets": CORE,
        }),
        f"solar_arc_{target_label}": safe(args.base_url, args.api_key, "/api/v1/solar-arc", {
            "natal_jd_ut": jd_ut,
            "transit_jd_ut": target_jd_ut,
            "planets": CORE,
        }),
        "primary_directions": safe(args.base_url, args.api_key, "/api/v1/primary-directions", {
            "latitude": args.lat,
            "longitude": args.lon,
            "natal_jd_ut": jd_ut,
            "planets": TRADITIONAL_PLANETS,
            "aspects": WESTERN_ASPECT_LIST,
            "direction_key": "NAIBOD",
            "max_age": args.direction_max_age,
            "house_system": house_system,
        }),
        f"symbolic_directions_age_{target_age}": safe(args.base_url, args.api_key, "/api/v1/symbolic-directions", {
            "latitude": args.lat,
            "longitude": args.lon,
            "natal_jd_ut": jd_ut,
            "age": target_age,
            "planets": CORE,
            "house_system": house_system,
        }),
        f"solar_return_{args.target_year}": safe(args.base_url, args.api_key, "/api/v1/solar-return", {
            "natal_latitude": args.lat,
            "natal_longitude": args.lon,
            "natal_jd_ut": jd_ut,
            "search_jd_ut": year_start_jd,
            "planets": CORE,
            "house_system": house_system,
        }),
        f"lunar_return_{args.target_year}_{args.target_month:02d}": safe(args.base_url, args.api_key, "/api/v1/lunar-return", {
            "natal_latitude": args.lat,
            "natal_longitude": args.lon,
            "natal_jd_ut": jd_ut,
            "search_jd_ut": month_search_jd,
            "planets": CORE,
            "house_system": house_system,
        }),
        "lunar_phase_birth": safe(args.base_url, args.api_key, "/api/v1/lunar/phase", {"jd_ut": jd_ut}),
        f"lunar_phase_{target_label}": safe(args.base_url, args.api_key, "/api/v1/lunar/phase", {"jd_ut": target_jd_ut}),
        f"lunar_phases_{args.target_year}": safe(args.base_url, args.api_key, "/api/v1/lunar/phases", {"start_jd_ut": year_start_jd, "end_jd_ut": year_end_jd}),
        f"eclipses_{args.target_year}": safe(args.base_url, args.api_key, "/api/v1/lunar/eclipses", {"start_jd_ut": year_start_jd, "end_jd_ut": year_end_jd}),
        "natal_report": safe(args.base_url, args.api_key, "/api/v1/report/natal", {"latitude": args.lat, "longitude": args.lon, "jd_ut": jd_ut}),
    }
    is_day_birth = bool(raw.get("dignity", {}).get("value", {}).get("is_day_chart", True)) if raw.get("dignity", {}).get("ok") else True
    raw["firdaria"] = safe(args.base_url, args.api_key, "/api/v1/firdaria", {"is_day_birth": is_day_birth, "age": float(target_age)})
    if args.include_non_western:
        raw["sidereal_lahiri"] = safe(args.base_url, args.api_key, "/api/v1/chart/sidereal", {
            "latitude": args.lat,
            "longitude": args.lon,
            "jd_ut": jd_ut,
            "ayanamsa": args.ayanamsa,
        })
        for varga in args.vargas:
            raw[f"divisional_{varga.lower()}"] = safe(args.base_url, args.api_key, "/api/v1/chart/divisional", {
                "latitude": args.lat,
                "longitude": args.lon,
                "jd_ut": jd_ut,
                "varga": varga,
                "ayanamsa": args.ayanamsa,
            })
        raw["vedic_dasha"] = safe(args.base_url, args.api_key, "/api/v1/vedic/dasha", {"latitude": args.lat, "longitude": args.lon, "jd_ut": jd_ut, "ayanamsa": args.ayanamsa})
        raw["vedic_ashtakavarga"] = safe(args.base_url, args.api_key, "/api/v1/vedic/ashtakavarga", {"latitude": args.lat, "longitude": args.lon, "jd_ut": jd_ut, "ayanamsa": args.ayanamsa})
        raw["vedic_yogas"] = safe(args.base_url, args.api_key, "/api/v1/vedic/yogas", {"latitude": args.lat, "longitude": args.lon, "jd_ut": jd_ut, "ayanamsa": args.ayanamsa})
    if not raw["natal"]["ok"]:
        raise RuntimeError(json.dumps(raw["natal"], ensure_ascii=False, indent=2))

    natal = raw["natal"]["value"]
    planets = list(natal.get("planets") or [])
    planet_by_id = {planet["planet_id"]: planet for planet in planets}
    houses = list(natal.get("houses") or [])
    angles = dict(natal.get("angles") or {})
    aspects = list(natal.get("aspects") or [])

    elements: Counter[str] = Counter()
    modalities: Counter[str] = Counter()
    houses_count: Counter[str] = Counter()
    hemisphere: Counter[str] = Counter()
    quadrants: Counter[str] = Counter()
    angular: list[str] = []
    for planet_id in CORE:
        planet = planet_by_id[planet_id]
        elements[SIGN_ELEMENTS[planet["sign"]]] += 1
        modalities[SIGN_MODALITIES[planet["sign"]]] += 1
        house = int(planet["house"])
        houses_count[str(house)] += 1
        hemisphere["above_horizon" if house in {7, 8, 9, 10, 11, 12} else "below_horizon"] += 1
        hemisphere["eastern_self-directed" if house in {1, 2, 3, 10, 11, 12} else "western_other-facing"] += 1
        if house in {1, 2, 3}:
            quadrants["Q1_identity"] += 1
        elif house in {4, 5, 6}:
            quadrants["Q2_inner_creative"] += 1
        elif house in {7, 8, 9}:
            quadrants["Q3_relational_meaning"] += 1
        else:
            quadrants["Q4_public_social"] += 1
        if house in {1, 4, 7, 10}:
            angular.append(planet_id)

    inferred_chains = {planet_id: chain_for(planet_id, planet_by_id) for planet_id in CORE}
    final_counter = Counter(value["final"] for value in inferred_chains.values())

    calculated_aspects = []
    for i in range(len(PLANETS)):
        p1 = PLANETS[i]
        p1_data = planet_by_id.get(p1)
        if not p1_data:
            continue
        p1_lon = float(p1_data["longitude"])
        for j in range(i + 1, len(PLANETS)):
            p2 = PLANETS[j]
            p2_data = planet_by_id.get(p2)
            if not p2_data:
                continue
            p2_lon = float(p2_data["longitude"])
            aspect_res = check_aspect(p1, p1_lon, p2, p2_lon)
            if aspect_res:
                calculated_aspects.append(aspect_res)

    all_ranked_aspects = sorted(calculated_aspects, key=lambda item: (item["score_hint"], -float(item.get("orb", 0))), reverse=True)
    major_aspects = [
        asp for asp in calculated_aspects
        if asp["aspect_type"].upper().replace("-", "_") in {"CONJUNCTION", "SEXTILE", "SQUARE", "TRINE", "OPPOSITION"}
    ]
    major_aspects.sort(key=lambda item: (item["score_hint"], -float(item.get("orb", 0))), reverse=True)

    lots = list(raw.get("lots", {}).get("value", {}).get("lots") or []) if raw.get("lots", {}).get("ok") else []
    for lot in lots:
        longitude = lot.get("longitude")
        if longitude is None:
            continue
        lot["placidus_house"] = nearest_house_from_cusps(float(longitude), houses)
        if angles.get("asc") is not None:
            lot["whole_sign_house"] = int(((math.floor(float(longitude) / 30) - math.floor(float(angles["asc"]) / 30)) % 12) + 1)

    special_points = collect_special_points(natal, planet_by_id, houses, angles, args.lat, args.lon, jd_ut, house_system)
    special_point_aspects = collect_special_point_aspects(special_points["points"], planets)

    def soft_cap(raw_value: float, scale: float) -> float:
        if scale <= 0.0:
            return 0.0
        return round(10.0 * math.tanh(max(0.0, raw_value) / scale), 2)

    sphere_scores: dict[str, dict[str, Any]] = {}
    for key, spec in SPHERES.items():
        salience = 0.0
        ease = 0.0
        tension = 0.0
        expression = 0.0
        evidence: list[str] = []

        # 1. House Placements
        for planet_id in CORE:
            planet = planet_by_id[planet_id]
            house = int(planet["house"])
            if house in spec["houses"]:
                weight = 0.85 * condition_factor(planet_id, planet_by_id)
                salience += weight
                expression += weight * (1.2 if house in {1, 4, 7, 10} else 0.9)
                evidence.append(f"{planet_id} in house {house}")
                if planet_id in {"VENUS", "JUPITER"} or (planet_id == "MERCURY" and planet["sign"] == "Virgo"):
                    ease += 0.45 * weight
                if planet_id in {"MARS", "SATURN", "PLUTO"} or planet.get("is_retrograde"):
                    tension += 0.35 * weight

            # 2. Planetary affinities
            if planet_id in spec["planets"]:
                relevance = 0.6
                weight = relevance * condition_factor(planet_id, planet_by_id)
                salience += 0.18 * weight
                if int(planet_by_id[planet_id]["house"]) in {1, 4, 7, 10}:
                    expression += 0.12 * weight

        # 3. House Rulers Integration
        for h in spec["houses"]:
            if len(houses) >= h:
                cusp_lon = houses[h-1]
                sign_cusp = sign_name_from_longitude(cusp_lon)
                ruler_id = SIGN_RULERS.get(sign_cusp)
                if ruler_id:
                    factor = condition_factor(ruler_id, planet_by_id)
                    salience += 0.3 * factor
                    if ruler_id in {"VENUS", "JUPITER"}:
                        ease += 0.15 * factor
                    elif ruler_id in {"SATURN", "MARS", "PLUTO"}:
                        tension += 0.15 * factor
                    else:
                        expression += 0.10 * factor
                    evidence.append(f"House {h} ruler {ruler_id} (cond: {factor:.2f})")

        # 4. Aspect Influences (Dynamic Benefic/Malefic logic)
        for aspect in major_aspects[:40]:
            planet_a = aspect["planet_a"]
            planet_b = aspect["planet_b"]
            if planet_a in spec["planets"] or planet_b in spec["planets"]:
                exact = get_raw_exactness(aspect)
                aspect_type = aspect["aspect_type"]
                salience += 0.25 * exact

                aspecting_planets = []
                if planet_a in spec["planets"]:
                    aspecting_planets.append(planet_b)
                if planet_b in spec["planets"]:
                    aspecting_planets.append(planet_a)

                benefic_count = sum(1 for p in aspecting_planets if p in {"JUPITER", "VENUS"})
                malefic_count = sum(1 for p in aspecting_planets if p in {"SATURN", "MARS", "PLUTO"})

                if aspect_type in {"Trine", "Sextile"}:
                    if malefic_count > 0:
                        ease += 0.20 * exact
                        tension += 0.15 * exact
                    else:
                        ease += 0.30 * exact
                elif aspect_type in {"Square", "Opposition"}:
                    if benefic_count > 0 and malefic_count == 0:
                        tension += 0.20 * exact
                        ease += 0.15 * exact
                    else:
                        tension += 0.40 * exact
                elif aspect_type == "Conjunction":
                    if malefic_count > 0:
                        tension += 0.30 * exact
                    elif benefic_count > 0:
                        ease += 0.30 * exact
                    else:
                        expression += 0.20 * exact

                evidence.append(f'{planet_a}-{planet_b} {aspect_type} orb {float(aspect.get("orb", 0)):.3f}')

        # 5. Arabic Lots with diminishing returns
        lot_contributions = []
        for lot in lots:
            lot_name = lot.get("name")
            lot_house = lot.get("placidus_house") or lot.get("whole_sign_house")
            if lot_name in spec["lots"] or lot_house in spec["houses"]:
                weight = 0.25 if lot_name in {"Lot of Fortune", "Lot of Spirit"} else 0.08
                lot_contributions.append((weight, f'{lot_name} house {lot_house}'))
        
        lot_contributions.sort(reverse=True, key=lambda x: x[0])
        for idx, (w, ev_str) in enumerate(lot_contributions):
            decay_mult = 1.0 if idx == 0 else 0.5 if idx == 1 else 0.25
            salience += w * decay_mult
            expression += 0.6 * w * decay_mult
            evidence.append(ev_str)

        # 6. Soft Capping (Hyperbolic Tangent)
        sphere_scores[key] = {
            "salience": soft_cap(salience, 6.0),
            "ease": soft_cap(ease, 4.0),
            "tension": soft_cap(tension, 3.5),
            "expression": soft_cap(expression, 4.5),
            "shadow_risk": soft_cap(tension * 1.2 + max(0.0, salience - ease) * 0.35, 5.0),
            "evidence": evidence[:14],
        }

    return {
        "metadata": {
            "engine": "SolarSage REST sidecar",
            "mode": "western_deep_with_vasiliy_max_raw_layers",
            "name": args.name,
            "birth": {
                "date": args.date,
                "time": args.time,
                "timezone": args.timezone,
                "utc": utc_dt.isoformat().replace("+00:00", "Z"),
                "jd_ut": jd_ut,
            },
            "target": {
                "date": args.target_date,
                "time": args.target_time,
                "timezone": target_timezone,
                "utc": target_utc_dt.isoformat().replace("+00:00", "Z"),
                "jd_ut": target_jd_ut,
                "age": target_age,
                "year": args.target_year,
                "month": args.target_month,
                "year_start_jd_ut": year_start_jd,
                "year_end_jd_ut": year_end_jd,
            },
            "location": {"name": args.location, "latitude": args.lat, "longitude": args.lon},
            "house_system": house_system,
            "house_system_policy": house_policy,
            "high_lat_threshold_abs_degrees": args.high_lat_threshold,
            "non_western_layers_enabled": args.include_non_western,
            "raw_layer_origin": "superset of tmp/collect_vasiliy_solarsage_max.py with generic inputs",
        },
        "raw": raw,
        "derived": {
            "element_balance": dict(elements),
            "modality_balance": dict(modalities),
            "house_emphasis": dict(houses_count),
            "hemisphere_balance": dict(hemisphere),
            "quadrant_balance": dict(quadrants),
            "angular_planets": angular,
            "traditional_dispositor_chains_inferred": inferred_chains,
            "final_dispositor_frequency_inferred": dict(final_counter),
            "major_aspects_ranked": major_aspects,
            "all_aspects_ranked": all_ranked_aspects,
            "planets_ru_labels": PLANET_RU,
            "special_points": special_points["points"],
            "special_points_missing": special_points["missing"],
            "special_points_helper_status": special_points["helper_status"],
            "special_point_major_aspects": special_point_aspects,
            "sphere_scores": sphere_scores,
            "lots": lots,
            "aspect_patterns": raw.get("aspect_patterns", {}).get("value"),
            "antiscia_points": raw.get("antiscia", {}).get("value", {}).get("antiscia_points"),
            "antiscia_pairs": raw.get("antiscia", {}).get("value", {}).get("antiscia_pairs"),
            "dignities": raw.get("dignity", {}).get("value", {}).get("dignities"),
            "mutual_receptions": raw.get("dignity", {}).get("value", {}).get("mutual_receptions"),
            "sect": raw.get("dignity", {}).get("value", {}).get("sect"),
            "is_day_chart": raw.get("dignity", {}).get("value", {}).get("is_day_chart"),
            "bonification": raw.get("bonification", {}).get("value"),
            "faces": raw.get("bounds", {}).get("value", {}).get("faces"),
            "planetary_hours": raw.get("planetary_hours", {}).get("value"),
            "heliacal_events": raw.get("heliacal", {}).get("value", {}).get("events"),
            "fixed_star_conjunctions": raw.get("fixed_stars", {}).get("value", {}).get("conjunctions"),
            "midpoints": raw.get("midpoints", {}).get("value"),
            "dispositors_modern": raw.get("dispositors_modern", {}).get("value"),
            "dispositors_traditional": raw.get("dispositors_traditional", {}).get("value"),
        },
        "calculation_notes": {
            "timezone_rule": "Birth time is interpreted with the supplied IANA timezone and converted to UTC before JD calculation.",
            "julian_day": "JD UT is calculated locally from timezone-aware UTC datetime and passed to SolarSage.",
            "house_system": "Auto policy uses Placidus below the latitude threshold and Whole Sign at/above the threshold unless overridden.",
            "special_points": "ASC/MC/DSC/IC come from SolarSage REST angles. Vertex/AntiVertex/EastPoint are calculated with SolarSage's vendored Swiss Ephemeris helper when the REST natal response does not expose them. Selena is derived as LILITH_MEAN + 180 degrees.",
            "raw_layers": "The raw block includes the previous Vasiliy max collector coverage plus generic target-date parameters; non-western raw layers can be included with --include-non-western.",
            "scoring": "Sphere scores are transparent heuristic helpers for LLM interpretation, not SolarSage-native astrology verdicts.",
        },
    }


def main() -> None:
    args = parse_args()
    package = collect(args)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "output": str(out),
        "house_system": package["metadata"]["house_system"],
        "house_system_policy": package["metadata"]["house_system_policy"],
        "utc": package["metadata"]["birth"]["utc"],
        "jd_ut": package["metadata"]["birth"]["jd_ut"],
        "target_utc": package["metadata"]["target"]["utc"],
        "target_age": package["metadata"]["target"]["age"],
        "raw_layers_total": len(package["raw"]),
        "raw_layers_failed": [key for key, value in package["raw"].items() if not value.get("ok")],
        "special_points_missing": package["derived"]["special_points_missing"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
