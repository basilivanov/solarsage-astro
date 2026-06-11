
# ############################################################################
# AI_HEADER: MODULE_MODELS_POSITION
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ######################################### START_MODULE_CONTRACT
# purpose: Module: position.py
# owns:
#   - apps/solarsage/solarsage/models/position.py
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
# module: M-SOLARSAGE-POSITION-MODELS
# wave: W-SOLARSAGE-SVC
# purpose: Position data models

from dataclasses import dataclass


@dataclass
class PlanetPosition:
    """Planet position data."""
    name: str
    longitude: float
    latitude: float
    speed: float
    sign: str
