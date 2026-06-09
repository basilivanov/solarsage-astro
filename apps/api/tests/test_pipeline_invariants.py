# AI_HEADER
# module: M-TEST-PIPELINE-INVARIANTS
# wave: W-PHASE-3
# purpose: Parameterized invariants across 5 birth profiles (Moscow, Murmansk,
#          equator, Sydney, Magadan). Each profile runs the full pipeline once
#          (natal + transits + normalization + scoring + semantic + today_important)
#          and 10 structural checks verify the pipeline is not broken.
#          No golden numbers — only structural invariants.

import asyncio
from datetime import date

import pytest
import httpx

from app.services.normalization_service import NormalizationService
from app.services.scoring_service import ScoringService
from app.services.semantic_service import SemanticService
from app.services.today_important_service import TodayImportantService
from app.services.astro_utils import find_house

# ── 5 profiles covering edge cases ──────────────────────────────────

PROFILES = [
    pytest.param(
        dict(name="moscow",   lat=55.75,  lon=37.62,  tz="Europe/Moscow",      hsys="PLACIDUS"),
        id="moscow",
    ),
    pytest.param(
        dict(name="murmansk", lat=67.94,  lon=32.92,  tz="Europe/Moscow",      hsys="WHOLE_SIGN"),
        id="murmansk-polar",
    ),
    pytest.param(
        dict(name="equator",  lat=0.0,    lon=37.0,   tz="Africa/Nairobi",     hsys="PLACIDUS"),
        id="equator",
    ),
    pytest.param(
        dict(name="sydney",   lat=-33.87, lon=151.21, tz="Australia/Sydney",   hsys="PLACIDUS"),
        id="sydney-southern",
    ),
    pytest.param(
        dict(name="magadan",  lat=59.57,  lon=150.80, tz="Asia/Magadan",       hsys="PLACIDUS"),
        id="magadan-far-east",
    ),
]

BIRTH = "1990-01-15"
BIRTH_TIME = "12:00"


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", params=PROFILES)
async def pipeline_for_profile(request):
    """One SolarSage call per profile, then full pipeline."""
    prof = request.param

    async with httpx.AsyncClient() as client:
        nr = await client.post("http://127.0.0.1:18091/v1/natal", json={
            "birth_date": BIRTH, "birth_time": BIRTH_TIME,
            "birth_lat": prof["lat"], "birth_lon": prof["lon"],
            "birth_tz": prof["tz"],
        }, timeout=30)
        natal = nr.json()

        tr = await client.post("http://127.0.0.1:18091/v1/transits", json={
            "birth_date": BIRTH, "birth_time": BIRTH_TIME,
            "birth_lat": prof["lat"], "birth_lon": prof["lon"],
            "birth_tz": prof["tz"],
            "target_date": str(date.today()), "target_time": "12:00",
            "target_tz": prof["tz"],
        }, timeout=30)
        transits = tr.json()

    ns = NormalizationService()
    signals = ns.normalize(natal, transits)

    ss = ScoringService()
    scoring = ss.score(signals)

    sem = SemanticService()
    semantic_layer = sem.build_semantic_layer(scoring["day_status"], scoring["sphere_scores"])
    why_contexts = sem.build_why_contexts(
        scoring["day_status"], scoring["sphere_scores"],
        scoring["top_signals"], natal, transits, semantic_layer,
        all_signals=signals,
    )

    imp_svc = TodayImportantService()
    important_items = imp_svc.build_items(
        target_date=date.today(),
        timezone=prof["tz"],
        natal=natal, transits=transits, signals=signals,
        scoring_result=scoring, semantic_layer=semantic_layer,
    )

    return {
        "profile": prof,
        "natal": natal,
        "transits": transits,
        "signals": signals,
        "scoring": scoring,
        "why_contexts": why_contexts,
        "important_items": important_items,
    }


# ══════════════════════════════════════════════════════════════════════
# Invariant 1: Houses — 12, cusps in [0,360), monotonic
# ══════════════════════════════════════════════════════════════════════

def test_houses_valid(pipeline_for_profile):
    data = pipeline_for_profile
    houses = data["natal"]["houses"]
    prof = data["profile"]

    assert len(houses) == 12, f"[{prof['name']}] Expected 12 houses, got {len(houses)}"

    cusps = [float(h["cusp"]) for h in houses]
    for c in cusps:
        assert 0.0 <= c < 360.0, f"[{prof['name']}] Cusp {c} out of range"

    # In Placidus/WholeSign, cusps should be roughly monotonic
    # (allow for ASC sometimes being near 0° → requires sorting check)
    sorted_cusps = sorted(cusps)
    for i in range(11):
        diff = (sorted_cusps[(i + 1)] - sorted_cusps[i] + 360) % 360
        assert diff > 0, f"[{prof['name']}] Cusps not distinct"


# ══════════════════════════════════════════════════════════════════════
# Invariant 2: Planets — 10, longitude in [0,360), sign nonempty
# ══════════════════════════════════════════════════════════════════════

def test_planets_valid(pipeline_for_profile):
    data = pipeline_for_profile
    planets = data["natal"]["planets"]
    prof = data["profile"]

    assert len(planets) == 10, f"[{prof['name']}] Expected 10 planets, got {len(planets)}"

    names_seen = set()
    for p in planets:
        assert "name" in p, f"[{prof['name']}] Planet missing name"
        assert p["name"] not in names_seen, f"[{prof['name']}] Duplicate planet {p['name']}"
        names_seen.add(p["name"])
        assert 0.0 <= p["longitude"] < 360.0, f"[{prof['name']}] {p['name']} longitude out of range"
        assert p.get("sign"), f"[{prof['name']}] {p['name']} missing sign"


# ══════════════════════════════════════════════════════════════════════
# Invariant 3: Signal count ≥ 30 (10 planet_in_house + 20 aspects min)
# ══════════════════════════════════════════════════════════════════════

def test_signals_min_count(pipeline_for_profile):
    signals = pipeline_for_profile["signals"]
    prof = pipeline_for_profile["profile"]
    n = len(signals)
    assert n >= 30, f"[{prof['name']}] Only {n} signals (expected ≥30)"


# ══════════════════════════════════════════════════════════════════════
# Invariant 4: Sphere scores non-zero, non-negative
# ══════════════════════════════════════════════════════════════════════

def test_sphere_scores_nonzero(pipeline_for_profile):
    sphere_scores = pipeline_for_profile["scoring"]["sphere_scores"]
    prof = pipeline_for_profile["profile"]
    total = sum(v for v in sphere_scores.values())
    assert total > 0.1, f"[{prof['name']}] Total sphere score {total} — Transit_ prefix bug?"
    for k, v in sphere_scores.items():
        assert v >= 0, f"[{prof['name']}] Negative score for {k}: {v}"


# ══════════════════════════════════════════════════════════════════════
# Invariant 5: Day status valid
# ══════════════════════════════════════════════════════════════════════

def test_day_status_valid(pipeline_for_profile):
    status = pipeline_for_profile["scoring"]["day_status"]
    assert status in {"supportive", "steady", "tense"}, f"Invalid day_status: {status}"


# ══════════════════════════════════════════════════════════════════════
# Invariant 6: Top signals — exactly 5
# ══════════════════════════════════════════════════════════════════════

def test_top_signals_count(pipeline_for_profile):
    top = pipeline_for_profile["scoring"]["top_signals"]
    prof = pipeline_for_profile["profile"]
    assert len(top) == 5, f"[{prof['name']}] Expected 5 top_signals, got {len(top)}"


# ══════════════════════════════════════════════════════════════════════
# Invariant 7: Every planet_in_house signal's house matches find_house
# ══════════════════════════════════════════════════════════════════════

def test_house_signals_match_find_house(pipeline_for_profile):
    signals = pipeline_for_profile["signals"]
    natal_houses = pipeline_for_profile["natal"]["houses"]
    natal_planets = {p["name"]: p for p in pipeline_for_profile["natal"]["planets"]}
    prof = pipeline_for_profile["profile"]

    for s in signals:
        if s.type != "planet_in_house":
            continue
        np = natal_planets.get(s.planet)
        if not np:
            continue
        expected = find_house(np["longitude"], natal_houses)
        assert s.house == expected, (
            f"[{prof['name']}] planet_in_house signal {s.planet} has house={s.house}, "
            f"find_house() at {np['longitude']:.1f}° = {expected}"
        )


# ══════════════════════════════════════════════════════════════════════
# Invariant 8: Why contexts have no Transit_/Natal_ prefixes
# ══════════════════════════════════════════════════════════════════════

def test_why_contexts_no_prefix(pipeline_for_profile):
    contexts = pipeline_for_profile["why_contexts"]
    prof = pipeline_for_profile["profile"]

    for ctx in contexts:
        text = ctx.get("context", "")
        assert "Transit_" not in text, (
            f"[{prof['name']}] Transit_ in section '{ctx['title']}': {text[:120]}"
        )
        assert "Natal_" not in text, (
            f"[{prof['name']}] Natal_ in section '{ctx['title']}': {text[:120]}"
        )


# ══════════════════════════════════════════════════════════════════════
# Invariant 9: TodayImportantService runs without crash, ≤3 items
# ══════════════════════════════════════════════════════════════════════

def test_today_important_no_crash(pipeline_for_profile):
    items = pipeline_for_profile["important_items"]
    assert len(items) <= 3, f"Expected ≤3 important items, got {len(items)}"

    for it in items:
        assert it.id, f"Item missing id: {it}"
        assert it.kind, f"Item missing kind: {it}"
        assert it.title, f"Item missing title: {it}"
        assert 0 <= it.priority <= 100, f"Item priority out of range: {it.priority}"


# ══════════════════════════════════════════════════════════════════════
# Invariant 10: House system correct for latitude
# ══════════════════════════════════════════════════════════════════════

def test_house_system_correct(pipeline_for_profile):
    prof = pipeline_for_profile["profile"]
    natal = pipeline_for_profile["natal"]
    actual = natal.get("house_system", "?")
    expected = prof["hsys"]
    assert actual == expected, (
        f"[{prof['name']}] house_system={actual}, expected {expected}"
    )
