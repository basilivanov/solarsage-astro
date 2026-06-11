
# ############################################################################
# AI_HEADER: MODULE_SCHEMAS_TRANSITS
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Sidecar calculation — apps/solarsage/solarsage/schemas/transits.py
# owns:
#   - apps/solarsage/solarsage/schemas/transits.py
# inputs: varies
# outputs: varies
# dependencies: local modules
# side_effects: varies
# emitted_logs: n/a
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

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
