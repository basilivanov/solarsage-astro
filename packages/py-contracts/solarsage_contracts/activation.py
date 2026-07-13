# ############################################################################
# AI_HEADER: MODULE_SOLARSAGE_CONTRACTS_ACTIVATION — shared activation contracts.
# ROLE: Owns activation-layer fields, literals, defaults, constraints, and index validation.
# ############################################################################

# START_MODULE_CONTRACT: M-SOLARSAGE-CONTRACTS-ACTIVATION
# purpose: Define boundary-neutral activation evidence and layer contract models once.
# owns:
#   - packages/py-contracts/solarsage_contracts/activation.py
# inputs: Pydantic validation input from API/sidecar boundary wrappers.
# outputs: ActivationEvidenceContract and generic ActivationLayerContract.
# dependencies: pydantic, solarsage_contracts.base, solarsage_contracts.versions.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Field names, order, defaults, default factories, requiredness, and constraints are canonical.
#   - Boundary wrappers own casing; shared contracts define no alias generator.
#   - Index maps may only reference ids present in activations.
# failure_policy: Pydantic ValidationError for invalid fields or dangling index refs.
# END_MODULE_CONTRACT: M-SOLARSAGE-CONTRACTS-ACTIVATION

# START_MODULE_MAP: M-SOLARSAGE-CONTRACTS-ACTIVATION
# public_entrypoints:
#   - ActivationTargetType
#   - ActivationPolarity
#   - ActivationPhase
#   - ActivationEvidenceContract
#   - ActivationLayerContract
# semantic_blocks:
#   - ACTIVATION_LITERAL_TYPES: canonical literal aliases
#   - ACTIVATION_EVIDENCE_CONTRACT: canonical activation evidence fields
#   - ACTIVATION_LAYER_CONTRACT: canonical layer fields and index validator
# owned_tests:
#   - packages/py-contracts/tests/test_activation_contract.py
#   - packages/py-contracts/tests/test_boundary_configs.py
# END_MODULE_MAP: M-SOLARSAGE-CONTRACTS-ACTIVATION

from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import Field, model_validator

from .base import StrictContractModel
from .versions import ACTIVATION_LAYER_VERSION, ACTIVATION_SCHEMA_VERSION


# START_BLOCK: ACTIVATION_LITERAL_TYPES
ActivationTargetType = Literal["planet", "house", "lot", "angle", "sphere"]
ActivationPolarity = Literal["supportive", "tense", "mixed", "neutral"]
ActivationPhase = Literal[
    "applying",
    "exact",
    "separating",
    "background",
    "period",
]
# END_BLOCK: ACTIVATION_LITERAL_TYPES


# START_BLOCK: ACTIVATION_EVIDENCE_CONTRACT
class ActivationEvidenceContract(StrictContractModel):
    id: str
    technique: str
    technique_family: str
    target_type: ActivationTargetType
    target_key: str
    kind: str
    active: bool = True
    source_planet: str | None = None
    source_frame: str | None = None
    target_planet: str | None = None
    target_frame: str | None = None
    aspect: str | None = None
    orb: float | None = None
    applying: bool | None = None
    active_from: str | None = None
    exact_at: str | None = None
    active_until: str | None = None
    phase: ActivationPhase = "background"
    house: int | None = None
    lot: str | None = None
    angle: str | None = None
    strength: float = Field(ge=0.0, le=1.0)
    polarity: ActivationPolarity = "neutral"
    weight_hint: float | None = None
    evidence: str
    debug: dict[str, Any] = Field(default_factory=dict)
# END_BLOCK: ACTIVATION_EVIDENCE_CONTRACT


EvidenceT = TypeVar("EvidenceT", bound=ActivationEvidenceContract)


# START_BLOCK: ACTIVATION_LAYER_CONTRACT
class ActivationLayerContract(StrictContractModel, Generic[EvidenceT]):
    schema_version: str = ACTIVATION_SCHEMA_VERSION
    activation_layer_version: str = ACTIVATION_LAYER_VERSION
    calculation_version: str
    target_date: str
    target_time: str
    target_tz: str
    house_system: str
    activations: list[EvidenceT]
    by_planet: dict[str, list[str]]
    by_house: dict[str, list[str]]
    by_lot: dict[str, list[str]]
    by_angle: dict[str, list[str]]
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_index_references(self) -> "ActivationLayerContract[EvidenceT]":
        # START_FUNCTION_CONTRACT: F-M-SOLARSAGE-CONTRACTS-ACTIVATION.validate_index_references
        # purpose: Reject by_* index ids that do not exist in activations.
        # inputs: self — validated activation layer instance.
        # returns: self when all refs point to known activation ids.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: Raises ValueError with the preserved legacy message for dangling refs.
        # END_FUNCTION_CONTRACT: F-M-SOLARSAGE-CONTRACTS-ACTIVATION.validate_index_references
        valid_ids = {ev.id for ev in self.activations}
        index_maps = [
            ("by_planet", self.by_planet),
            ("by_house", self.by_house),
            ("by_lot", self.by_lot),
            ("by_angle", self.by_angle),
        ]
        for map_name, index_map in index_maps:
            if not index_map:
                continue
            for key, refs in index_map.items():
                for ref_id in refs:
                    if ref_id not in valid_ids:
                        raise ValueError(
                            f"{map_name}[{key}] references '{ref_id}' "
                            f"which is not present in activations"
                        )
        return self
# END_BLOCK: ACTIVATION_LAYER_CONTRACT


__all__ = [
    "ActivationTargetType",
    "ActivationPolarity",
    "ActivationPhase",
    "ActivationEvidenceContract",
    "ActivationLayerContract",
]
