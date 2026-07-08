# ############################################################################
# AI_HEADER: MODULE_CONTRACTS_ACTIVATION — canonical activation schemas.
# ROLE: Typed contracts for SolarSage V2 activation layer.
#       W1: contract-only. Not populated by TodayService until W2+.
# ############################################################################

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from ._base import CamelModel

ActivationTargetType = Literal["planet", "house", "lot", "angle", "sphere"]
ActivationPolarity = Literal["supportive", "tense", "mixed", "neutral"]
ActivationPhase = Literal["applying", "exact", "separating", "background", "period"]


class ActivationEvidence(CamelModel):
    """Single activation evidence entry for a transit/technique interaction."""

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
    exact_at: str | None = None
    phase: ActivationPhase = "background"
    house: int | None = None
    lot: str | None = None
    angle: str | None = None
    strength: float = Field(ge=0.0, le=1.0)
    polarity: ActivationPolarity = "neutral"
    weight_hint: float | None = None
    evidence: str
    debug: dict[str, Any] = Field(default_factory=dict)


class ActivationLayer(CamelModel):
    """Full activation layer output for a given target date."""

    schema_version: str = "activation-layer.v1"
    activation_layer_version: str = "al-1.0"
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
