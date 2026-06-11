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
