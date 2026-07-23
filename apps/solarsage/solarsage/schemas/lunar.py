# ############################################################################
# AI_HEADER: MODULE_SCHEMAS_LUNAR
# ROLE: Sidecar schemas for lunar window calculations
# DEPENDENCIES: pydantic
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ######################################### START_MODULE_CONTRACT
# purpose: Pydantic schemas for /v1/lunar-window endpoint
# owns:
#   - apps/solarsage/solarsage/schemas/lunar.py
# inputs: date strings
# outputs: validated requests/responses
# dependencies: pydantic
# side_effects: none
# emitted_logs: n/a (pure)
# failure_policy: validation error
# END_MODULE_CONTRACT

from __future__ import annotations

from datetime import date
from typing import Literal
from pydantic import BaseModel, Field


class LunarWindowRequest(BaseModel):
    from_date: date = Field(..., description="Start date (inclusive)")
    to_date: date = Field(..., description="End date (inclusive)")


class VocInterval(BaseModel):
    start: str = Field(..., description="Start timestamp ISO UTC")
    end: str = Field(..., description="End timestamp ISO UTC")


class LunarDayInfo(BaseModel):
    date: str = Field(..., description="Date YYYY-MM-DD")
    moon_sign: Literal[
        "aries", "taurus", "gemini", "cancer", "leo", "virgo",
        "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"
    ]
    moon_sign_ru: str
    moon_lon_noon: float
    phase_angle: float
    waxing: bool
    illumination: float
    is_voc_noon: bool
    voc_intervals: list[VocInterval]
    voc_fraction: float
    sign_ingress: str | None = None
    mercury_retro: bool


class LunarWindowResponse(BaseModel):
    days: list[LunarDayInfo]
