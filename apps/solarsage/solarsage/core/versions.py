# ############################################################################
# AI_HEADER: MODULE_SIDECAR_VERSIONS — sidecar-local version identity facade.
# ROLE: Re-export shared activation-layer version constants for sidecar consumers.
# ############################################################################

# START_MODULE_CONTRACT: M-SIDECAR-VERSIONS
# purpose: Preserve sidecar-local import surface for shared activation-layer versions.
# owns:
#   - apps/solarsage/solarsage/core/versions.py
# inputs: solarsage_contracts.versions.
# outputs: CALCULATION_VERSION, ACTIVATION_LAYER_VERSION.
# dependencies: solarsage_contracts.versions.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Wire literals are defined only in the shared package.
#   - Sidecar consumers keep importing from solarsage.core.versions.
# failure_policy: Import errors propagate during startup/tests.
# END_MODULE_CONTRACT: M-SIDECAR-VERSIONS

# START_MODULE_MAP: M-SIDECAR-VERSIONS
# public_entrypoints:
#   - CALCULATION_VERSION
#   - ACTIVATION_LAYER_VERSION
# semantic_blocks:
#   - VERSION_REEXPORTS: sidecar facade over shared constants
# owned_tests:
#   - packages/py-contracts/tests/test_versions.py
# END_MODULE_MAP: M-SIDECAR-VERSIONS

from __future__ import annotations

# START_BLOCK: VERSION_REEXPORTS
from solarsage_contracts.versions import (
    ACTIVATION_LAYER_VERSION,
    CALCULATION_VERSION,
)

__all__ = [
    "CALCULATION_VERSION",
    "ACTIVATION_LAYER_VERSION",
]
# END_BLOCK: VERSION_REEXPORTS
