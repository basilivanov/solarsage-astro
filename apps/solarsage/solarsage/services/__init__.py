
# ############################################################################
# AI_HEADER: MODULE_SERVICES__INIT__
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ######################################### START_MODULE_CONTRACT
# purpose: Module: __init__.py
# owns:
#   - apps/solarsage/solarsage/services/__init__.py
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
# module: M-SOLARSAGE-SERVICES-INIT
# wave: W-3.2, W-SOLARSAGE-SVC
# purpose: Services package exports

from .natal import NatalService
from .transits import TransitsService

__all__ = ['NatalService', 'TransitsService']
