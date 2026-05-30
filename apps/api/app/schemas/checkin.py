# ############################################################################
# AI_HEADER
# module: M-CHECKIN-SCHEMA
# wave: W-8.1
# purpose: Evening checkin schemas
# ############################################################################

from pydantic import BaseModel
from datetime import date


class CheckinCreate(BaseModel):
    """Create evening checkin."""
    target_date: date
    mood: str  # "great", "good", "neutral", "bad"
    notes: str | None = None


class CheckinResponse(BaseModel):
    """Evening checkin response."""
    id: int
    target_date: date
    mood: str
    notes: str | None
    created_at: str
