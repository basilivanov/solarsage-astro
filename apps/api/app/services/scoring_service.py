# AI_HEADER
# module: M-SCORING-SERVICE
# wave: W-4.2, W-4.3
# purpose: Scoring layer v2 — canon-based sphere_scores from grace/canon/*.yml

import os
from pathlib import Path

import yaml

from app.schemas.normalization import AstroSignal

# ── Load canon (cached at module level) ────────────────────────

_CANON_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "grace" / "canon"

def _load_canon(name: str) -> dict:
    path = _CANON_DIR / f"{name}.v1.yml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

_SPHERES = _load_canon("spheres")
_ASPECTS = _load_canon("aspect_rules")
_DIGNITIES = _load_canon("dignities")

# ── Aspect helpers ─────────────────────────────────────────────

_POSITIVE = {"trine", "sextile"}
_NEGATIVE = {"square", "opposition"}

def _aspect_weight(aspect_type: str) -> float:
    w = _ASPECTS.get("aspect_weights", {}).get(aspect_type.upper())
    return float(w) if w else 0.5

def _aspect_threshold(is_major: bool) -> float:
    key = "major" if is_major else "minor"
    return float(_ASPECTS.get("aspect_threshold", {}).get(key, 0.35))

def _is_major(aspect_type: str) -> bool:
    return aspect_type.upper() in {"CONJUNCTION", "OPPOSITION", "TRINE", "SQUARE"}

# ── Dignity helpers ────────────────────────────────────────────

def _condition_factor(planet: str, sign: str | None, retrograde: bool = False) -> float:
    """Compute condition_factor for a planet in a sign. Range [0.45, 1.35]."""
    cf = 1.0
    bounds = _DIGNITIES.get("condition_factor", {}).get("bounds", [0.45, 1.35])
    
    for m in _DIGNITIES.get("condition_factor", {}).get("modifiers", []):
        if m.get("planet") == planet.upper() and m.get("sign") == (sign or "").upper():
            cf += float(m.get("delta", 0))
    
    if retrograde:
        penalty = _DIGNITIES.get("condition_factor", {}).get("retrograde_penalty", {})
        cf += float(penalty.get(planet.upper(), 0))
    
    return max(bounds[0], min(bounds[1], cf))

# ── Main scoring class ─────────────────────────────────────────

class ScoringService:

    def score(self, signals: list[AstroSignal]) -> dict:
        """Score signals v2 — canon-based with aspect weights, dignities, spheres."""
        sphere_scores = self._calculate_sphere_scores(signals)
        day_status = self._calculate_day_status(signals)
        top_signals = self._get_top_signals(signals, limit=5)
        return {"day_status": day_status, "sphere_scores": sphere_scores, "top_signals": top_signals}

    def _calculate_sphere_scores(self, signals: list[AstroSignal]) -> dict:
        """Canon-based sphere scores with aspect weights, dignities, house rulers."""
        sphere_list = _SPHERES.get("spheres", {})
        scores: dict[str, float] = {}

        # Only process aspect signals
        aspects = [s for s in signals if s.type == "aspect"]
        houses = [s for s in signals if s.type == "planet_in_house"]

        for key, sphere in sphere_list.items():
            total = 0.0

            # 1. Aspect signals → score per sphere based on planet weights
            for s in aspects:
                planet_weight = sphere.get("planets", {}).get(s.planet.upper(), 0)
                if planet_weight > 0:
                    aw = _aspect_weight(s.aspect_type or "")
                    # benefic softening
                    softening = _ASPECTS.get("benefic_softening", {})
                    tension_mod = 0.0
                    if s.aspect_type in _NEGATIVE and s.target_planet and s.target_planet.upper() in {"JUPITER", "VENUS"}:
                        tension_mod = float(softening.get("square_or_opposition_with_benefic", {}).get("tension_delta", 0))
                    elif s.aspect_type in _POSITIVE and s.target_planet and s.target_planet.upper() in {"SATURN", "MARS"}:
                        tension_mod = float(softening.get("trine_or_sextile_with_malefic", {}).get("ease_delta", 0))

                    threshold = _aspect_threshold(_is_major(s.aspect_type or ""))
                    base = aw * planet_weight * s.strength
                    if base < threshold:
                        continue
                    total += base + tension_mod

            # 2. Planet-in-house signals → score per sphere
            for s in houses:
                house_key = s.house
                if house_key and house_key in sphere.get("houses", []):
                    planet_weight = sphere.get("planets", {}).get(s.planet.upper(), 0.1)
                    angular_bonus = sphere.get("weight_multipliers", {}).get("angular_house_bonus", 1.0)
                    if house_key in {1, 4, 7, 10}:
                        planet_weight *= angular_bonus
                    total += planet_weight * s.strength

            scores[key] = round(total, 2)

        return scores

    def _calculate_day_status(self, signals: list[AstroSignal]) -> str:
        """Canon-based day_status with aspect weights."""
        aspects = [s for s in signals if s.type == "aspect"]
        positive_score = 0.0
        negative_score = 0.0

        for s in aspects:
            aw = _aspect_weight(s.aspect_type or "")
            threshold = _aspect_threshold(_is_major(s.aspect_type or ""))
            base = aw * s.strength
            if base < threshold:
                continue

            if s.aspect_type in _POSITIVE:
                positive_score += base
            elif s.aspect_type in _NEGATIVE:
                negative_score += base
            else:
                # conjunction — counts 50/50
                positive_score += base * 0.5
                negative_score += base * 0.5

        if positive_score > negative_score * 1.3 and positive_score >= 1.0:
            return "supportive"
        elif negative_score > positive_score * 1.3 and negative_score >= 1.0:
            return "tense"
        return "steady"

    def _get_top_signals(self, signals: list[AstroSignal], limit: int = 5) -> list[AstroSignal]:
        return sorted(signals, key=lambda s: s.strength, reverse=True)[:limit]
