
# ############################################################################
# AI_HEADER: MODULE_SCHEMAS_HEALTH
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Sidecar calculation — apps/solarsage/solarsage/schemas/health.py
# owns:
#   - apps/solarsage/solarsage/schemas/health.py
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
# module: M-SIDECAR-SCHEMA-HEALTH
# wave: W-3.1
# purpose: Health response schema

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response."""
    ok: bool
    version: str
    ephemeris_path: str
    calculation_version: str
