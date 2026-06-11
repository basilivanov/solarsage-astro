
# ############################################################################
# AI_HEADER: MODULE_MODELS__INIT__
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Sidecar calculation — apps/solarsage/solarsage/models/__init__.py
# owns:
#   - apps/solarsage/solarsage/models/__init__.py
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
# module: M-SOLARSAGE-MODELS-INIT
# wave: W-SOLARSAGE-SVC
# purpose: Models package exports

from .chart import NatalChart, Transit
from .position import PlanetPosition

__all__ = ['NatalChart', 'Transit', 'PlanetPosition']
