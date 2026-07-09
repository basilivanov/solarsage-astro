# ############################################################################
# AI_HEADER: MODULE_NORMALIZATION_SCHEMA
# ROLE: AstroSignal schema
# DEPENDENCIES: pydantic, typing, enum
# GRACE_ANCHORS: [ASTRO_SIGNAL, ASPECT_TYPE]
# WAVE: W-4.1
# ############################################################################

# START_MODULE_CONTRACT: M-NORMALIZATION-SCHEMA
# purpose: Define AstroSignal and AspectType used throughout the scoring pipeline.
# owns:
#   - apps/api/app/schemas/normalization.py
# inputs:
#   - none (type definitions)
# outputs:
#   - AstroSignal, AspectType
# dependencies:
#   - pydantic.BaseModel
#   - enum
# side_effects:
#   - none (type-only module)
# END_MODULE_CONTRACT: M-NORMALIZATION-SCHEMA

# START_MODULE_MAP: M-NORMALIZATION-SCHEMA
# public_entrypoints:
#   - AstroSignal
#   - AspectType
# semantic_blocks:
#   - ASTRO_SIGNAL: signal data model
#   - ASPECT_TYPE: aspect enum
# END_MODULE_MAP: M-NORMALIZATION-SCHEMA

from typing import Literal
from datetime import datetime
from pydantic import BaseModel, Field


SignalType = Literal[
    "planet_in_house",
    "planet_in_sign",
    "aspect",
    "dignity",
]

AspectType = Literal[
    "conjunction",
    "sextile",
    "square",
    "trine",
    "opposition",
]

DeltaKind = Literal[
    "new_today", "exact_today", "peak_today",
    "entering_today", "leaving_today",
    "stronger_than_yesterday", "weaker_than_yesterday",
    "background",
]

PhaseKind = Literal[
    "entering", "applying", "exact", "separating", "leaving", "background",
]


class AstroSignal(BaseModel):
    """Normalized astrological signal."""
    type: SignalType
    planet: str
    house: int | None = None
    sign: str | None = None
    aspect_type: AspectType | None = None
    target_planet: str | None = None
    orb: float | None = None
    strength: float = Field(..., ge=0.0, le=1.0, description="Signal strength (0.0-1.0)")

    # Wave 2+: technique tracking
    technique: str | None = Field(default=None, description="Signal source technique")
    technique_family: str | None = Field(default=None, description="Technique family for convergence counting")

    # Wave 3+: temporal state
    delta_kind: DeltaKind | None = Field(default=None, description="How this signal changed from yesterday")
    phase: PhaseKind | None = Field(default=None, description="Phase of the aspect (applying/exact/separating)")
    daily_salience: float | None = Field(default=None, description="Velocity + delta weighted salience")


def normalize_top_signals(top_signals: list) -> list[AstroSignal]:
    if not top_signals:
        return []
    if isinstance(top_signals[0], AstroSignal):
        return top_signals

    normalized = []
    for s in top_signals:
        if isinstance(s, dict):
            sig_type = s.get("type") or s.get("type_")
            sig_planet = s.get("planet")
            if not sig_type or not sig_planet:
                continue

            raw_strength = s.get("strength")
            try:
                strength = float(raw_strength) if raw_strength is not None else 0.0
            except (ValueError, TypeError):
                strength = 0.0

            normalized.append(
                AstroSignal(
                    type=sig_type,
                    planet=sig_planet,
                    target_planet=s.get("target_planet") or s.get("targetPlanet"),
                    aspect_type=s.get("aspect_type") or s.get("aspectType"),
                    orb=float(s["orb"]) if s.get("orb") is not None else None,
                    strength=strength,
                    house=int(s["house"]) if s.get("house") is not None else None,
                    sign=s.get("sign"),
                    technique=s.get("technique"),
                    technique_family=s.get("technique_family") or s.get("techniqueFamily"),
                    delta_kind=s.get("delta_kind") or s.get("deltaKind"),
                    phase=s.get("phase"),
                    daily_salience=float(s["daily_salience"]) if s.get("daily_salience") is not None else None,
                )
            )
    return normalized
