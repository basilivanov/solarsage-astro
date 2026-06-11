# ############################################################################
# AI_HEADER: MODULE_CHECKIN_SCHEMA
# ROLE: Evening checkin schemas
# DEPENDENCIES: pydantic, datetime
# GRACE_ANCHORS: [CHECKIN_SCHEMAS]
# WAVE: W-8.1
# ############################################################################

# START_MODULE_CONTRACT: M-CHECKIN-SCHEMA
# purpose: Define CheckinCreate and CheckinResponse Pydantic schemas.
# owns:
#   - apps/api/app/schemas/checkin.py
# inputs:
#   - none (type definitions)
# outputs:
#   - CheckinCreate, CheckinResponse
# dependencies:
#   - standard library: datetime, uuid
#   - pydantic.BaseModel
# side_effects:
#   - none (type-only module)
# END_MODULE_CONTRACT: M-CHECKIN-SCHEMA

# START_MODULE_MAP: M-CHECKIN-SCHEMA
# public_entrypoints:
#   - CheckinCreate
#   - CheckinResponse
# semantic_blocks:
#   - CHECKIN_SCHEMAS: Pydantic models for checkin endpoints
# END_MODULE_MAP: M-CHECKIN-SCHEMA
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
