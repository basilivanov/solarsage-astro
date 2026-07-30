# ############################################################################
# AI_HEADER: MODULE_SOLARSAGE_CONTRACTS_VERSIONS — shared wire version constants.
# ROLE: Single product-code source for activation-layer wire identity values.
# ############################################################################

# START_MODULE_CONTRACT: M-SOLARSAGE-CONTRACTS-VERSIONS
# purpose: Define activation-layer wire versions used by API and sidecar facades.
# owns:
#   - packages/py-contracts/solarsage_contracts/versions.py
# inputs: none.
# outputs: ACTIVATION_SCHEMA_VERSION, ACTIVATION_LAYER_VERSION, CALCULATION_VERSION.
# dependencies: none.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Wire versions are independent from package distribution version.
#   - Values must remain byte-identical during shared-model refactors.
# failure_policy: n/a (pure constants).
# END_MODULE_CONTRACT: M-SOLARSAGE-CONTRACTS-VERSIONS

# START_MODULE_MAP: M-SOLARSAGE-CONTRACTS-VERSIONS
# public_entrypoints:
#   - ACTIVATION_SCHEMA_VERSION
#   - ACTIVATION_LAYER_VERSION
#   - CALCULATION_VERSION
# semantic_blocks:
#   - WIRE_VERSION_CONSTANTS: canonical activation wire identity values
# owned_tests:
#   - packages/py-contracts/tests/test_versions.py
# END_MODULE_MAP: M-SOLARSAGE-CONTRACTS-VERSIONS

from __future__ import annotations

# START_BLOCK: WIRE_VERSION_CONSTANTS
ACTIVATION_SCHEMA_VERSION = "activation-layer.v1"
ACTIVATION_LAYER_VERSION = "al-1.1"
CALCULATION_VERSION = "ss-calc-1.3.0"

__all__ = [
    "ACTIVATION_SCHEMA_VERSION",
    "ACTIVATION_LAYER_VERSION",
    "CALCULATION_VERSION",
]
# END_BLOCK: WIRE_VERSION_CONSTANTS
