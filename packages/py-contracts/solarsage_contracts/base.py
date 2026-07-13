# ############################################################################
# AI_HEADER: MODULE_SOLARSAGE_CONTRACTS_BASE — shared strict Pydantic base.
# ROLE: Provides boundary-neutral Pydantic config for shared SolarSage contracts.
# ############################################################################

# START_MODULE_CONTRACT: M-SOLARSAGE-CONTRACTS-BASE
# purpose: Define StrictContractModel without boundary-specific alias casing.
# owns:
#   - packages/py-contracts/solarsage_contracts/base.py
# inputs: Pydantic BaseModel and ConfigDict.
# outputs: StrictContractModel base class for shared contract definitions.
# dependencies: pydantic.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - No alias_generator is defined in shared contracts.
#   - Unknown fields are rejected.
#   - Ordinary Pydantic coercion semantics are preserved.
#   - Models remain mutable for current runtime behavior.
# failure_policy: Validation errors are raised by Pydantic callers.
# END_MODULE_CONTRACT: M-SOLARSAGE-CONTRACTS-BASE

# START_MODULE_MAP: M-SOLARSAGE-CONTRACTS-BASE
# public_entrypoints:
#   - StrictContractModel
# semantic_blocks:
#   - STRICT_CONTRACT_MODEL: shared Pydantic base config
# owned_tests:
#   - packages/py-contracts/tests/test_activation_contract.py
#   - packages/py-contracts/tests/test_boundary_configs.py
# END_MODULE_MAP: M-SOLARSAGE-CONTRACTS-BASE

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


# START_BLOCK: STRICT_CONTRACT_MODEL
class StrictContractModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=False,
        frozen=False,
    )
# END_BLOCK: STRICT_CONTRACT_MODEL
