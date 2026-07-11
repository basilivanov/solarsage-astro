# ############################################################################
# AI_HEADER: MODULE_SIDECAR_SCHEMAS_ACTIVATION — sidecar activation schemas.
# ROLE: Pydantic schemas for sidecar activation layer calculation.
#       W1: contract-only. No endpoint exposed.
# ############################################################################

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ActivationTargetType = Literal["planet", "house", "lot", "angle", "sphere"]
ActivationPolarity = Literal["supportive", "tense", "mixed", "neutral"]
ActivationPhase = Literal["applying", "exact", "separating", "background", "period"]


class ActivationEvidence(BaseModel):
    """Single activation evidence entry (sidecar calculation output)."""

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


class ActivationLayer(BaseModel):
    """Full activation layer output from sidecar."""

    schema_version: str = "activation-layer.v1"
    activation_layer_version: str = "al-1.1"
    calculation_version: str
    target_date: str
    target_time: str
    target_tz: str
    house_system: str
    activations: list[ActivationEvidence]
    by_planet: dict[str, list[str]]
    by_house: dict[str, list[str]]
    by_lot: dict[str, list[str]]
    by_angle: dict[str, list[str]]
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_index_references(self) -> "ActivationLayer":
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
