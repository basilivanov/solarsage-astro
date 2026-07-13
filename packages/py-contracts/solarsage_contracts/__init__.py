# ############################################################################
# AI_HEADER: MODULE_SOLARSAGE_CONTRACTS_INIT — shared Python contract exports.
# ROLE: Stable import surface for SolarSage shared wire contract models and versions.
# ############################################################################

# START_MODULE_CONTRACT: M-SOLARSAGE-CONTRACTS-INIT
# purpose: Re-export shared activation contracts, base model, and wire versions.
# owns:
#   - packages/py-contracts/solarsage_contracts/__init__.py
# inputs: solarsage_contracts.base, solarsage_contracts.activation, solarsage_contracts.versions.
# outputs: Public package-level names for product boundary facades and tests.
# dependencies: Local shared contract modules only.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Package root must not import API or sidecar app code.
#   - Wire version literals are re-exported, not redefined here.
# failure_policy: Import errors propagate during startup/tests.
# END_MODULE_CONTRACT: M-SOLARSAGE-CONTRACTS-INIT

# START_MODULE_MAP: M-SOLARSAGE-CONTRACTS-INIT
# public_entrypoints:
#   - StrictContractModel
#   - ActivationTargetType
#   - ActivationPolarity
#   - ActivationPhase
#   - ActivationEvidenceContract
#   - ActivationLayerContract
#   - ACTIVATION_SCHEMA_VERSION
#   - ACTIVATION_LAYER_VERSION
#   - CALCULATION_VERSION
# semantic_blocks:
#   - ROOT_REEXPORTS: package-level import surface
# owned_tests:
#   - packages/py-contracts/tests/test_versions.py
# END_MODULE_MAP: M-SOLARSAGE-CONTRACTS-INIT

from __future__ import annotations

# START_BLOCK: ROOT_REEXPORTS
from .activation import (
    ActivationEvidenceContract,
    ActivationLayerContract,
    ActivationPhase,
    ActivationPolarity,
    ActivationTargetType,
)
from .base import StrictContractModel
from .versions import (
    ACTIVATION_LAYER_VERSION,
    ACTIVATION_SCHEMA_VERSION,
    CALCULATION_VERSION,
)

__all__ = [
    "StrictContractModel",
    "ActivationTargetType",
    "ActivationPolarity",
    "ActivationPhase",
    "ActivationEvidenceContract",
    "ActivationLayerContract",
    "ACTIVATION_SCHEMA_VERSION",
    "ACTIVATION_LAYER_VERSION",
    "CALCULATION_VERSION",
]
# END_BLOCK: ROOT_REEXPORTS
