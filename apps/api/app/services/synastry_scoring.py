# ############################################################################
# AI_HEADER: MODULE_SYNASTRY_SCORING
# ROLE: Pure scoring engine for synastry calculations (tone mapping, scores 0..100, counters, precision invariants)
# DEPENDENCIES: dataclasses, typing
# GRACE_ANCHORS: []
# ############################################################################

# START_MODULE_CONTRACT: M-SYNASTRY-SCORING
# purpose: Pure deterministic synastry scoring engine.
# owns:
#   - apps/api/app/services/synastry_scoring.py
# inputs: Raw aspect data, partner time precision
# outputs: Scored aspects, overall score (0..100), status, counters, spheres, precision flags
# dependencies: none (pure Python)
# side_effects: none
# emitted_logs: none
# invariants:
#   - Pure deterministic calculations (no LLM, no DB, no network)
#   - Unknown birth time forces partner Moon/ASC weight=0 and report_precision=approximate
# failure_policy: None (returns score 50 on empty aspect list)
# END_MODULE_CONTRACT: M-SYNASTRY-SCORING

# START_MODULE_MAP: M-SYNASTRY-SCORING
# public_entrypoints:
#   - SynastryScoringEngine
#   - RawAspectInput
#   - ScoredAspect
#   - ScoredSphere
#   - SynastryScoringResult
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_synastry_scoring.py
# END_MODULE_MAP: M-SYNASTRY-SCORING

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class RawAspectInput:
    """Raw aspect input item from calculation engine / sidecar."""

    owner_planet: str
    partner_planet: str
    aspect_type: str
    orb_degrees: float
    applying: bool | None = None


@dataclass
class ScoredAspect:
    """Scored aspect output item."""

    id: str
    owner_planet: str
    partner_planet: str
    aspect: str
    orb_degrees: float
    tone: Literal["good", "mid", "bad", "supportive", "mixed", "tense"]
    confidence: Literal["high", "medium", "low"]
    weight: float
    tech_signature: str


@dataclass
class ScoredSphere:
    """Scored sphere breakdown item."""

    id: str
    title: str
    score: int
    tone: Literal["supportive", "mixed", "tense"]


@dataclass
class SynastryScoringResult:
    """Overall scoring result payload."""

    score: int
    status: Literal["good", "mid", "bad"]
    counters: dict[str, int]
    aspects: list[ScoredAspect]
    spheres: list[ScoredSphere]
    precision_flags: dict[str, Any]


class SynastryScoringEngine:
    """Pure scoring engine for synastry aspect analysis and score synthesis."""

    PLANET_WEIGHTS: dict[str, float] = {
        "sun": 1.0,
        "moon": 1.0,
        "venus": 1.0,
        "mars": 1.0,
        "ascendant": 1.0,
        "asc": 1.0,
        "midheaven": 0.8,
        "mc": 0.8,
        "mercury": 0.8,
        "jupiter": 0.8,
        "saturn": 0.8,
        "uranus": 0.6,
        "neptune": 0.6,
        "pluto": 0.6,
        "northnode": 0.5,
    }

    SPHERE_DEFINITIONS: list[tuple[str, str, set[str]]] = [
        ("intimacy", "Близость", {"sun", "moon", "venus", "mars", "pluto"}),
        ("communication", "Общение", {"mercury", "sun", "moon", "jupiter"}),
        ("daily_life", "Быт", {"moon", "saturn", "venus", "ascendant", "asc"}),
        ("finance", "Дела и деньги", {"saturn", "jupiter", "venus", "sun", "mars"}),
    ]

    @classmethod
    def determine_tone(
        cls, owner_planet: str, partner_planet: str, aspect_type: str
    ) -> Literal["supportive", "mixed", "tense"]:
        op = owner_planet.lower()
        pp = partner_planet.lower()
        asp = aspect_type.lower()

        malefics = {"saturn", "pluto", "mars"}
        benefics = {"venus", "jupiter", "sun", "moon"}
        outers = {"uranus", "neptune"}

        if asp in ("trine", "sextile"):
            if op in malefics and pp in malefics:
                return "mixed"
            return "supportive"

        if asp in ("square", "opposition"):
            if op in benefics and pp in benefics and asp == "opposition":
                return "mixed"
            return "tense"

        if asp in ("conjunction", "conjunct"):
            if (op in malefics or pp in malefics) and (
                op in {"moon", "sun", "venus", "mars", "saturn", "pluto"}
                or pp in {"moon", "sun", "venus", "mars", "saturn", "pluto"}
            ):
                if op in {"saturn", "pluto"} or pp in {"saturn", "pluto"}:
                    return "tense"
                return "mixed"
            if op in outers or pp in outers:
                return "mixed"
            return "supportive"

        return "mixed"

    @classmethod
    def calculate_score(
        cls,
        aspects: list[RawAspectInput],
        partner_time_precision: str = "exact",
    ) -> SynastryScoringResult:
        is_approximate = partner_time_precision in ("approximate", "unknown")

        precision_flags = {
            "houses_available": not is_approximate,
            "asc_available": not is_approximate,
            "moon_precision": "approximate" if is_approximate else "exact",
            "report_precision": "approximate" if is_approximate else "exact",
        }

        scored_aspects: list[ScoredAspect] = []
        raw_weighted_sum = 0.0
        total_weight = 0.0
        counters = {"good": 0, "mid": 0, "bad": 0}

        for idx, raw in enumerate(aspects):
            op = raw.owner_planet.lower()
            pp = raw.partner_planet.lower()
            asp = raw.aspect_type.lower()

            tone = cls.determine_tone(raw.owner_planet, raw.partner_planet, raw.aspect_type)

            # Precision rule: partner Moon / ASC has weight = 0 when time is approximate
            partner_time_dependent = pp in ("moon", "ascendant", "asc")
            if is_approximate and partner_time_dependent:
                effective_weight = 0.0
                confidence = "low"
            else:
                w1 = cls.PLANET_WEIGHTS.get(op, 0.7)
                w2 = cls.PLANET_WEIGHTS.get(pp, 0.7)
                effective_weight = (w1 + w2) / 2.0
                if raw.orb_degrees <= 3.0:
                    confidence = "high"
                elif raw.orb_degrees <= 6.0:
                    confidence = "medium"
                else:
                    confidence = "low"

            orb_decay = max(0.2, 1.0 - (raw.orb_degrees / 8.0))
            tone_value = 1.0 if tone == "supportive" else (-1.0 if tone == "tense" else 0.0)

            if effective_weight > 0:
                weighted_contrib = tone_value * effective_weight * orb_decay
                raw_weighted_sum += weighted_contrib
                total_weight += effective_weight * orb_decay

                if tone == "supportive":
                    counters["good"] += 1
                elif tone == "tense":
                    counters["bad"] += 1
                else:
                    counters["mid"] += 1

            aspect_id = f"{op}_{asp}_{pp}_{idx}"
            tech_sig = f"{raw.owner_planet} {raw.aspect_type} {raw.partner_planet} ({raw.orb_degrees:.1f}°)"

            scored_aspects.append(
                ScoredAspect(
                    id=aspect_id,
                    owner_planet=raw.owner_planet,
                    partner_planet=raw.partner_planet,
                    aspect=raw.aspect_type,
                    orb_degrees=raw.orb_degrees,
                    tone=tone,
                    confidence=confidence, # type: ignore[arg-type]
                    weight=effective_weight,
                    tech_signature=tech_sig,
                )
            )

        if total_weight > 0:
            ratio = raw_weighted_sum / total_weight
            final_score = int(round(50.0 + (ratio * 40.0)))
        else:
            final_score = 50

        final_score = max(0, min(100, final_score))

        if final_score >= 78:
            status: Literal["good", "mid", "bad"] = "good"
        elif final_score >= 45:
            status = "mid"
        else:
            status = "bad"

        # Spheres calculation
        scored_spheres: list[ScoredSphere] = []
        for sphere_id, sphere_title, relevant_planets in cls.SPHERE_DEFINITIONS:
            sphere_sum = 0.0
            sphere_weight = 0.0
            for sa in scored_aspects:
                if sa.weight <= 0:
                    continue
                if (
                    sa.owner_planet.lower() in relevant_planets
                    or sa.partner_planet.lower() in relevant_planets
                ):
                    sa_tone_val = 1.0 if sa.tone == "supportive" else (-1.0 if sa.tone == "tense" else 0.0)
                    sa_decay = max(0.2, 1.0 - (sa.orb_degrees / 8.0))
                    sphere_sum += sa_tone_val * sa.weight * sa_decay
                    sphere_weight += sa.weight * sa_decay

            if sphere_weight > 0:
                s_ratio = sphere_sum / sphere_weight
                s_score = int(round(50.0 + (s_ratio * 40.0)))
            else:
                s_score = final_score

            s_score = max(0, min(100, s_score))
            s_tone: Literal["supportive", "mixed", "tense"] = (
                "supportive" if s_score >= 75 else ("tense" if s_score < 45 else "mixed")
            )

            scored_spheres.append(
                ScoredSphere(
                    id=sphere_id,
                    title=sphere_title,
                    score=s_score,
                    tone=s_tone,
                )
            )

        return SynastryScoringResult(
            score=final_score,
            status=status,
            counters=counters,
            aspects=scored_aspects,
            spheres=scored_spheres,
            precision_flags=precision_flags,
        )
