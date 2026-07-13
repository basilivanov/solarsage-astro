# ############################################################################
# AI_HEADER: MODULE_SIDECAR_SCHEMAS_ACTIVATION — sidecar activation facades.
# ROLE: Sidecar snake_case boundary wrappers over shared SolarSage activation contracts.
# ############################################################################

# START_MODULE_CONTRACT: M-SIDECAR-SCHEMAS-ACTIVATION
# purpose: Expose sidecar-local schema names while reusing shared activation fields.
# owns:
#   - apps/solarsage/solarsage/schemas/activation.py
# inputs: Shared activation contracts.
# outputs: ActivationEvidence and ActivationLayer sidecar Pydantic wrappers.
# dependencies: solarsage_contracts.activation.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Field definitions, defaults, constraints, and validators live only in shared contracts.
#   - Sidecar JSON casing remains snake_case; no camel alias generator is defined here.
#   - No API imports are introduced.
# failure_policy: Pydantic ValidationError from shared boundary-neutral contract config.
# END_MODULE_CONTRACT: M-SIDECAR-SCHEMAS-ACTIVATION

# START_MODULE_MAP: M-SIDECAR-SCHEMAS-ACTIVATION
# public_entrypoints:
#   - ActivationEvidence
#   - ActivationLayer
#   - ActivationTargetType
#   - ActivationPolarity
#   - ActivationPhase
# semantic_blocks:
#   - SIDECAR_ACTIVATION_FACADES: thin sidecar wrappers over shared contracts
# owned_tests:
#   - apps/solarsage/tests/test_activation_schema.py
#   - packages/py-contracts/tests/test_boundary_configs.py
# END_MODULE_MAP: M-SIDECAR-SCHEMAS-ACTIVATION

from __future__ import annotations

from solarsage_contracts.activation import (
    ActivationEvidenceContract,
    ActivationLayerContract,
    ActivationPhase,
    ActivationPolarity,
    ActivationTargetType,
)


# START_BLOCK: SIDECAR_ACTIVATION_FACADES
class ActivationEvidence(ActivationEvidenceContract):
    """Single activation evidence entry (sidecar calculation output)."""


class ActivationLayer(ActivationLayerContract[ActivationEvidence]):
    """Full activation layer output from sidecar."""
# END_BLOCK: SIDECAR_ACTIVATION_FACADES


__all__ = [
    "ActivationTargetType",
    "ActivationPolarity",
    "ActivationPhase",
    "ActivationEvidence",
    "ActivationLayer",
]
