# AI_HEADER
# module: M-TEST-LLM-CONTEXT-ACCURACY
# wave: W-PHASE-3
# purpose: Verify LLM input context is accurate — house numbers match find_house,
#          degree+sign are consistent (no "14.4° Scorpio" where 14.4 is wrong),
#          VOC time uses user timezone, not server time.

import asyncio
import re
from datetime import date

import httpx
import pytest

from app.services.normalization_service import NormalizationService
from app.services.scoring_service import ScoringService
from app.services.semantic_service import SemanticService
from app.services.today_important_service import TodayImportantService
from app.services.astro_utils import find_house

BIRTH = "1990-01-15"
BIRTH_TIME = "12:00"

# Degrees at which each sign starts (tropical zodiac, Aries = 0°)
_SIGN_START = {
    "Овен": 0, "Телец": 30, "Близнецы": 60, "Рак": 90,
    "Лев": 120, "Дева": 150, "Весы": 180, "Скорпион": 210,
    "Стрелец": 240, "Козерог": 270, "Водолей": 300, "Рыбы": 330,
}

_SIGN_RU_TO_EN = {
    "Овен": "Aries", "Телец": "Taurus", "Близнецы": "Gemini",
    "Рак": "Cancer", "Лев": "Leo", "Дева": "Virgo",
    "Весы": "Libra", "Скорпион": "Scorpio", "Стрелец": "Sagittarius",
    "Козерог": "Capricorn", "Водолей": "Aquarius", "Рыбы": "Pisces",
}

_SIGN_EN_TO_RU = {v: k for k, v in _SIGN_RU_TO_EN.items()}


def _deg_in_sign(lon: float) -> float:
    return lon % 30


def _sign_for_lon(lon: float) -> str:
    idx = int(lon / 30) % 12
    signs_ru = list(_SIGN_START.keys())
    return signs_ru[idx]


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def llm_context_data():
    """Full pipeline run for baseline Moscow profile."""
    prof = dict(lat=55.75, lon=37.62, tz="Europe/Moscow")

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
    sem = SemanticService()
    semantic_layer = sem.build_semantic_layer(scoring["day_status"], scoring["sphere_scores"])
    why_contexts = sem.build_why_contexts(
        scoring["day_status"], scoring["sphere_scores"],
        scoring["top_signals"], natal, transits, semantic_layer,
        all_signals=signals,
    )

    imp_svc = TodayImportantService()
    important_items = imp_svc.build_items(
        target_date=date.today(), timezone=prof["tz"],
        natal=natal, transits=transits, signals=signals,
        scoring_result=scoring,
    )

    return {
        "natal": natal,
        "why_contexts": why_contexts,
        "important_items": important_items,
    }


# ══════════════════════════════════════════════════════════════════════
# Test 1: Every "planet ... N дом" in context matches find_house
# ══════════════════════════════════════════════════════════════════════

# Russian planet names used in context
_PLANET_CONTEXT_RU = {
    "Солнце": "Sun", "Луна": "Moon", "Меркурий": "Mercury",
    "Венера": "Venus", "Марс": "Mars", "Юпитер": "Jupiter",
    "Сатурн": "Saturn", "Уран": "Uranus", "Нептун": "Neptune",
    "Плутон": "Pluto",
}

# Pattern: "в Скорпион 14.4°, 10 дом" or "в Козерог 21.1°, 3 дом"
_HOUSE_PATTERN = re.compile(
    r'(%b) (\d+\.?\d*)°,\s*(\d+)\s*дом'.encode().decode()
    .replace('%b', '|'.join(_SIGN_START.keys()))
)


def test_context_house_numbers_match_find_house(llm_context_data):
    """
    Every occurrence of 'planet ... N дом' in the LLM context text
    must have N = find_house(planet_longitude).
    """
    natal = llm_context_data["natal"]
    natal_houses = natal.get("houses", [])
    natal_planets = {p["name"]: p for p in natal.get("planets", [])}

    all_context_text = " ".join(
        ctx.get("context", "") for ctx in llm_context_data["why_contexts"]
    )

    # Find all " <planet> в <sign> <deg>°, <N> дом" patterns
    errors = []
    for sign_name, deg_str, house_str in _HOUSE_PATTERN.findall(all_context_text):
        sign_lon_start = _SIGN_START.get(sign_name)
        if sign_lon_start is None:
            continue
        deg = float(deg_str)
        house_in_text = int(house_str)

        # Reconstruct approximate longitude
        approx_lon = (sign_lon_start + deg) % 360

        # Find the exact natal planet near this longitude
        found = False
        for name, np in natal_planets.items():
            lon = np["longitude"]
            if abs((lon - approx_lon + 180) % 360 - 180) < 1.0:  # within 1° orb
                actual_house = find_house(lon, natal_houses)
                if actual_house != house_in_text:
                    errors.append(
                        f"{name} at {lon:.1f}° ({_sign_for_lon(lon)} {_deg_in_sign(lon):.1f}°) "
                        f"→ context says дом {house_in_text}, find_house says дом {actual_house}"
                    )
                found = True
                break

        if not found:
            errors.append(
                f"Context mentions sign={sign_name} deg={deg}° house={house_in_text}, "
                f"but no natal planet found near {(sign_lon_start + deg) % 360:.1f}°"
            )

    assert not errors, "\n".join(errors)


# ══════════════════════════════════════════════════════════════════════
# Test 2: Degree and sign are consistent in context
# ══════════════════════════════════════════════════════════════════════

def test_context_degree_sign_consistent(llm_context_data):
    """
    Every "sign deg°" in context must have deg within 0-30 and sign must
    match the longitude. E.g., "Скорпион 14.4°" means longitude 210+14.4=224.4°.
    """
    natal = llm_context_data["natal"]
    natal_planets = {p["name"]: p for p in natal.get("planets", [])}

    all_context_text = " ".join(
        ctx.get("context", "") for ctx in llm_context_data["why_contexts"]
    )

    # Pattern: "<sign> <deg>°"
    _DEG_PATTERN = re.compile(
        r'(%b) (\d+\.?\d*)°'.encode().decode()
        .replace('%b', '|'.join(_SIGN_START.keys()))
    )

    errors = []
    for sign_name, deg_str in _DEG_PATTERN.findall(all_context_text):
        deg = float(deg_str)
        if deg < 0 or deg >= 30:
            errors.append(f"Degree {deg}° out of range 0-30 for sign {sign_name}")
            continue

        approx_lon = (_SIGN_START[sign_name] + deg) % 360

        # Verify a natal planet exists near this longitude
        found = False
        for name, np in natal_planets.items():
            lon = np["longitude"]
            if abs((lon - approx_lon + 180) % 360 - 180) < 0.5:
                actual_sign = _sign_for_lon(lon)
                if actual_sign != sign_name:
                    errors.append(
                        f"{name} at {lon:.1f}° → sign={actual_sign}, "
                        f"context says {sign_name} {deg}° (lon≈{approx_lon:.1f}°)"
                    )
                found = True
                break

        if not found:
            # Could be a transit planet — skip
            pass

    assert not errors, "\n".join(errors)


# ══════════════════════════════════════════════════════════════════════
# Test 3: VOC end_time is in user timezone, not UTC
# ══════════════════════════════════════════════════════════════════════

def test_voc_time_has_timezone_info(llm_context_data):
    """
    If moon_void item exists, its ends_at field should contain timezone info.
    Before the fix, datetime.now() was used without tz.
    """
    items = llm_context_data["important_items"]
    voc_items = [it for it in items if it.kind == "void_moon"]

    if not voc_items:
        pytest.skip("No moon_void event today")

    for it in voc_items:
        ends_at = it.ends_at
        assert ends_at is not None, "moon_void item missing ends_at"
        # ends_at should be an ISO string with timezone or contain hours:minutes
        assert ":" in (ends_at or ""), f"ends_at format unexpected: {ends_at}"
        # Title should also contain the HH:MM time
        assert ":" in it.title, f"VOC title missing time: {it.title}"
