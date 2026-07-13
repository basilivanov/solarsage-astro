# ############################################################################
# AI_HEADER: MODULE_CONTRACTS_ACTIVATION — API activation contract facades.
# ROLE: Public camelCase boundary wrappers over shared SolarSage activation contracts.
# ############################################################################

# START_MODULE_CONTRACT: M-CONTRACTS-ACTIVATION
# purpose: Expose API-owned public schema names while reusing shared activation fields.
# owns:
#   - apps/api/app/schemas/activation.py
# inputs: Shared activation contracts and API CamelModel boundary config.
# outputs: ActivationEvidence and ActivationLayer public Pydantic wrappers.
# dependencies: solarsage_contracts.activation, app.schemas._base.CamelModel.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Field definitions, defaults, constraints, and validators live only in shared contracts.
#   - API wrappers remain CamelModel subclasses for OpenAPI generation.
#   - Public wire casing remains camelCase and accepts snake_case by field name.
# failure_policy: Pydantic ValidationError from shared/base boundary config.
# END_MODULE_CONTRACT: M-CONTRACTS-ACTIVATION

# START_MODULE_MAP: M-CONTRACTS-ACTIVATION
# public_entrypoints:
#   - ActivationEvidence
#   - ActivationLayer
#   - ActivationTargetType
#   - ActivationPolarity
#   - ActivationPhase
# semantic_blocks:
#   - API_ACTIVATION_FACADES: thin public wrappers over shared contracts
# owned_tests:
#   - apps/api/tests/test_activation_contracts.py
#   - packages/py-contracts/tests/test_boundary_configs.py
# END_MODULE_MAP: M-CONTRACTS-ACTIVATION

from __future__ import annotations

from solarsage_contracts.activation import (
    ActivationEvidenceContract,
    ActivationLayerContract,
    ActivationPhase,
    ActivationPolarity,
    ActivationTargetType,
)

from ._base import CamelModel


# START_BLOCK: API_ACTIVATION_FACADES
class ActivationEvidence(ActivationEvidenceContract, CamelModel):
    """Single activation evidence entry for a transit/technique interaction."""


class ActivationLayer(
    ActivationLayerContract[ActivationEvidence],
    CamelModel,
):
    """Full activation layer output for a given target date."""
# END_BLOCK: API_ACTIVATION_FACADES


__all__ = [
    "ActivationTargetType",
    "ActivationPolarity",
    "ActivationPhase",
    "ActivationEvidence",
    "ActivationLayer",
]
