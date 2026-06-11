
# ############################################################################
# AI_HEADER: MODULE_SCHEMAS_HEALTH
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ######################################### START_MODULE_CONTRACT
# purpose: Module: health.py
# owns:
#   - apps/solarsage/solarsage/schemas/health.py
# inputs: Function args
# outputs: Return values
# dependencies: local modules
# side_effects: n/a (pure)
# emitted_logs: n/a (pure)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
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
