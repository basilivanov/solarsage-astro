
# ############################################################################
# AI_HEADER: MODULE_MODELS_POSITION
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Sidecar calculation — apps/solarsage/solarsage/models/position.py
# owns:
#   - apps/solarsage/solarsage/models/position.py
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
