#!/usr/bin/env python3
"""Regenerate golden fixture files for pipeline tests.

Usage:
    cd apps/api && source .venv/bin/activate
    python tests/fixtures/regenerate_golden.py moscow
    python tests/fixtures/regenerate_golden.py murmansk
    python tests/fixtures/regenerate_golden.py --all

Golden files contain stable pipeline output (house assignments, sphere thresholds).
They do NOT contain:
  - Full planet longitudes (SolarSage's job)
  - LLM-generated text (changes every run)
  - Daily transit aspect lists (change with date)
"""

import asyncio, json, os, sys
from datetime import date, datetime

import httpx

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.services.normalization_service import NormalizationService
from app.services.scoring_service import ScoringService
from app.services.astro_utils import find_house

PROFILES = {
    "moscow": {
        "name": "moscow",
        "birth": "1990-01-15", "time": "12:00",
        "lat": 55.75, "lon": 37.62, "tz": "Europe/Moscow",
    },
    "murmansk": {
        "name": "murmansk",
        "birth": "1990-01-15", "time": "12:00",
        "lat": 67.94, "lon": 32.92, "tz": "Europe/Moscow",
    },
}

FIXTURES_DIR = os.path.dirname(__file__)


async def regenerate(prof_name: str):
    prof = PROFILES[prof_name]

    async with httpx.AsyncClient() as client:
        nr = await client.post("http://127.0.0.1:18091/v1/natal", json={
            "birth_date": prof["birth"], "birth_time": prof["time"],
            "birth_lat": prof["lat"], "birth_lon": prof["lon"], "birth_tz": prof["tz"],
        }, timeout=30)
        natal = nr.json()

        tr = await client.post("http://127.0.0.1:18091/v1/transits", json={
            "birth_date": prof["birth"], "birth_time": prof["time"],
            "birth_lat": prof["lat"], "birth_lon": prof["lon"], "birth_tz": prof["tz"],
            "target_date": str(date.today()), "target_time": "12:00", "target_tz": prof["tz"],
        }, timeout=30)
        transits = tr.json()

    ns = NormalizationService()
    signals = ns.normalize(natal, transits)
    ss = ScoringService()
    scoring = ss.score(signals)

    natal_houses = {}
    natal_planets = natal.get("planets", [])
    natal_houses_list = natal.get("houses", [])
    for p in natal_planets:
        h = find_house(p["longitude"], natal_houses_list)
        natal_houses[p["name"]] = h

    golden = {
        "profile": prof,
        "generated_at": datetime.now().isoformat(),
        "transit_date": str(date.today()),
        "house_system": natal.get("house_system", "?"),
        "natal_houses": natal_houses,
        "sphere_scores_min": {
            k: round(v * 0.5, 2) for k, v in scoring["sphere_scores"].items() if v > 0
        },
    }

    fname = os.path.join(FIXTURES_DIR, f"golden_{prof_name}.json")
    with open(fname, "w") as f:
        json.dump(golden, f, ensure_ascii=False, indent=2)
    print(f"Regenerated: {fname}")
    print(f"  house_system: {golden['house_system']}")
    print(f"  natal_houses: {golden['natal_houses']}")
    print(f"  sphere_scores_min: {golden['sphere_scores_min']}")


if __name__ == "__main__":
    if "--all" in sys.argv:
        for name in PROFILES:
            asyncio.run(regenerate(name))
    elif len(sys.argv) > 1 and sys.argv[1] in PROFILES:
        asyncio.run(regenerate(sys.argv[1]))
    else:
        print(f"Usage: {sys.argv[0]} <name|--all>  (names: {', '.join(PROFILES)})")
        sys.exit(1)
