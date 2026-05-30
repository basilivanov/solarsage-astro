# AI_HEADER
# module: M-SIDECAR-SCHEMA-TRANSITS
# wave: W-3.3
# purpose: Transits request/response schemas

from pydantic import BaseModel, Field

from .natal import Planet  # Reuse Planet schema


class TransitsRequest(BaseModel):
    """Transits calculation request."""
    target_date: str = Field(..., description="Target date in YYYY-MM-DD format")
    target_time: str = Field(..., description="Target time in HH:MM format")
    target_tz: str = Field(..., description="Target timezone (e.g., Europe/Moscow)")


class TransitsResponse(BaseModel):
    """Transits calculation response."""
    planets: list[Planet]
    target_jd: float  # Julian Day for reference
