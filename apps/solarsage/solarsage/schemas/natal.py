# AI_HEADER
# module: M-SIDECAR-SCHEMA-NATAL
# wave: W-3.2
# purpose: Natal request/response schemas

from pydantic import BaseModel, Field


class NatalRequest(BaseModel):
    """Natal chart calculation request."""
    birth_date: str = Field(..., description="Birth date in YYYY-MM-DD format")
    birth_time: str = Field(..., description="Birth time in HH:MM format")
    birth_lat: float = Field(..., description="Birth latitude in degrees")
    birth_lon: float = Field(..., description="Birth longitude in degrees")
    birth_tz: str = Field(..., description="Birth timezone (e.g., Europe/Moscow)")


class Planet(BaseModel):
    """Planet position."""
    name: str
    longitude: float  # degrees
    latitude: float   # degrees
    speed: float      # degrees per day
    sign: str         # zodiac sign


class House(BaseModel):
    """House cusp."""
    number: int
    cusp: float  # degrees
    sign: str


class SpecialPoint(BaseModel):
    """Special point (ASC, MC, etc)."""
    name: str
    longitude: float
    sign: str


class NatalResponse(BaseModel):
    """Natal chart calculation response."""
    planets: list[Planet]
    houses: list[House]
    special_points: list[SpecialPoint]
    house_system: str  # e.g., "PLACIDUS", "WHOLE_SIGN"
