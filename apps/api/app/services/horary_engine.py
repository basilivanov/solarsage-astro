# AI_HEADER
# module: M-HORARY-ENGINE
# wave: W-HORARY
# purpose: Computational engine for horary questions

from __future__ import annotations

import logging
from typing import Any
from app.schemas.normalization import AstroSignal

logger = logging.getLogger(__name__)

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

CATEGORY_SIGNIFICATORS = {
    "love": "Venus",
    "career": "Saturn",
    "money": "Jupiter",
    "health": "Mars",
    "travel": "Mercury",
    "other": "Moon",
}


class HoraryEngine:
    @staticmethod
    def get_significator(category: str | None) -> str:
        if not category:
            return "Moon"
        return CATEGORY_SIGNIFICATORS.get(category, "Moon")

    @staticmethod
    def compute_verdict(
        horary_chart: dict[str, Any], signals: list[AstroSignal], category: str | None
    ) -> tuple[str, float, list[str]]:
        """
        Compute horary verdict (yes/no/maybe), confidence score, and involved planets.
        """
        # 1. Resolve Ascendant and its ruler
        special_points = horary_chart.get("special_points", [])
        asc_point = next((sp for sp in special_points if sp["name"] == "ASC"), None)
        if asc_point:
            asc_lon = asc_point["longitude"]
            asc_sign = SIGNS[int(asc_lon / 30) % 12]
        else:
            asc_sign = "Aries"

        asc_ruler = SIGN_RULERS.get(asc_sign, "MARS").title()
        significator = HoraryEngine.get_significator(category)

        # 2. Main aspect score between ASC ruler and significator
        main_aspect_score = 0.5  # default neutral
        main_aspect_found = False

        for sig in signals:
            if sig.type == "aspect":
                p1 = sig.planet
                p2 = sig.target_planet
                # Normalize names (e.g. strip "Transit_" prefix if any, but they are natal aspects mostly)
                p1_clean = p1.replace("Transit_", "")
                p2_clean = p2.replace("Transit_", "") if p2 else ""

                if {p1_clean, p2_clean} == {asc_ruler, significator}:
                    main_aspect_found = True
                    if sig.aspect_type in ("trine", "sextile"):
                        main_aspect_score = 1.0
                    elif sig.aspect_type == "conjunction":
                        main_aspect_score = 0.8
                    elif sig.aspect_type == "square":
                        main_aspect_score = -0.5
                    elif sig.aspect_type == "opposition":
                        main_aspect_score = -0.8
                    break

        # 3. Moon score (check Moon aspects in signals)
        moon_has_good_aspect = False
        for sig in signals:
            if sig.type == "aspect":
                p1_clean = sig.planet.replace("Transit_", "")
                p2_clean = sig.target_planet.replace("Transit_", "") if sig.target_planet else ""
                if "Moon" in (p1_clean, p2_clean) and sig.aspect_type in ("trine", "sextile", "conjunction"):
                    moon_has_good_aspect = True
                    break

        moon_score = 0.5 if moon_has_good_aspect else 0.2

        # 4. Combustion (is ASC ruler close to Sun?)
        combustion = 0.0
        for sig in signals:
            if sig.type == "aspect":
                p1_clean = sig.planet.replace("Transit_", "")
                p2_clean = sig.target_planet.replace("Transit_", "") if sig.target_planet else ""
                if {p1_clean, p2_clean} == {asc_ruler, "Sun"} and sig.aspect_type == "conjunction":
                    combustion = -0.2
                    break

        # 5. Formal modifiers
        formal = 0.0
        if category == "love" and asc_sign in ("Libra", "Taurus"):
            formal = 0.1

        # 6. Final score computation
        score = 0.5 * main_aspect_score + 0.3 * moon_score + combustion + 0.1 * formal

        # Map to verdict
        if score >= 0.6:
            verdict = "yes"
        elif score <= 0.3:
            verdict = "no"
        else:
            verdict = "maybe"

        confidence = float(min(1.0, max(0.0, abs(score))))

        # Involved planets
        involved = list(set(filter(None, [asc_ruler, significator, "Moon"])))

        return verdict, confidence, involved
