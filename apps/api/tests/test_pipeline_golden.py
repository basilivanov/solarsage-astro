# AI_HEADER
# module: M-TEST-PIPELINE-GOLDEN
# wave: W-PHASE-3
# purpose: Golden-state tests — verify stable pipeline outputs (natal house assignments,
#          house system, sphere score thresholds) match pre-computed golden files.
#          Regenerate golden files with: python tests/fixtures/regenerate_golden.py --all

import asyncio
import json
import os
from datetime import date

import httpx
import pytest

from app.services.normalization_service import NormalizationService
from app.services.scoring_service import ScoringService
from app.services.astro_utils import find_house

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

PROFILES = [
    pytest.param("moscow", id="moscow"),
    pytest.param("murmansk", id="murmansk"),
]

BIRTH = "1990-01-15"
BIRTH_TIME = "12:00"


def _load_golden(name: str) -> dict:
    path = os.path.join(FIXTURES_DIR, f"golden_{name}.json")
    if not os.path.exists(path):
        pytest.skip(f"Golden file not found: {path} (run regenerate_golden.py --all)")
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", params=PROFILES)
async def golden_and_live(request):
    """Load golden file and run pipeline for comparison."""
    name = request.param
    golden = _load_golden(name)
    prof = golden["profile"]

    async with httpx.AsyncClient() as client:
        nr = await client.post("http://127.0.0.1:18091/v1/natal", json={
            "birth_date": BIRTH, "birth_time": BIRTH_TIME,
            "birth_lat": prof["lat"], "birth_lon": prof["lon"], "birth_tz": prof["tz"],
        }, timeout=30)
        natal = nr.json()

        tr = await client.post("http://127.0.0.1:18091/v1/transits", json={
            "birth_date": BIRTH, "birth_time": BIRTH_TIME,
            "birth_lat": prof["lat"], "birth_lon": prof["lon"], "birth_tz": prof["tz"],
            "target_date": str(date.today()), "target_time": "12:00", "target_tz": prof["tz"],
        }, timeout=30)
        transits = tr.json()

    ns = NormalizationService()
    signals = ns.normalize(natal, transits)
    ss = ScoringService()
    scoring = ss.score(signals)

    # Compute live natal house assignments
    live_houses = {}
    natal_planets = natal.get("planets", [])
    natal_houses_list = natal.get("houses", [])
    for p in natal_planets:
        h = find_house(p["longitude"], natal_houses_list)
        live_houses[p["name"]] = h

    return {
        "name": name,
        "golden": golden,
        "natal": natal,
        "live_houses": live_houses,
        "scoring": scoring,
    }


# ══════════════════════════════════════════════════════════════════════
# Golden test 1: Natal planets in correct houses
# ══════════════════════════════════════════════════════════════════════

def test_natal_houses_match_golden(golden_and_live):
    expected = golden_and_live["golden"]["natal_houses"]
    actual = golden_and_live["live_houses"]
    name = golden_and_live["name"]

    for planet, house in expected.items():
        live = actual.get(planet)
        assert live == house, (
            f"[{name}] Natal {planet} → golden={house}, live={live}\n"
            f"Full golden: {expected}\nFull live: {actual}"
        )


# ══════════════════════════════════════════════════════════════════════
# Golden test 2: House system matches
# ══════════════════════════════════════════════════════════════════════

def test_house_system_matches_golden(golden_and_live):
    expected = golden_and_live["golden"]["house_system"]
    actual = golden_and_live["natal"].get("house_system", "?")
    name = golden_and_live["name"]
    assert actual == expected, (
        f"[{name}] house_system: golden={expected}, live={actual}"
    )


# ══════════════════════════════════════════════════════════════════════
# Golden test 3: Sphere scores above golden thresholds
# ══════════════════════════════════════════════════════════════════════

def test_sphere_scores_above_golden_threshold(golden_and_live):
    thresholds = golden_and_live["golden"].get("sphere_scores_min", {})
    actual = golden_and_live["scoring"]["sphere_scores"]
    name = golden_and_live["name"]

    for sphere, min_score in thresholds.items():
        live = actual.get(sphere, 0)
        assert live >= min_score, (
            f"[{name}] Sphere '{sphere}' score {live} below golden threshold {min_score}\n"
            f"All scores: {actual}"
        )
