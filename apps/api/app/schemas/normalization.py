# AI_HEADER
# module: M-NORMALIZATION-SCHEMA
# wave: W-4.1
# purpose: AstroSignal schema

from typing import Literal
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
