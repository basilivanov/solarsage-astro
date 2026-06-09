# ############################################################################
# AI_HEADER: MODULE_HORARY_ANALYSIS_SCHEMA
# ROLE: Pydantic v2 models for structured horary analysis.
# DEPENDENCIES: pydantic
# GRACE_ANCHORS: [HORARY_ANALYSIS]
# ############################################################################

# START_MODULE_CONTRACT: M-CONTRACTS.horary_analysis
# purpose: Define structured evidence items, timing info and full horary
#          analysis object produced by HoraryEngine.analyze().
# owns:
#   - apps/api/app/schemas/horary_analysis.py
# inputs:
#   - none (schema definitions only)
# outputs:
#   - EvidenceItem, TimingInfo, HoraryAnalysis
# invariants:
#   - Every EvidenceItem.source is "computed" (LLM must not invent evidence).
#   - confidence_score is integer 0..100, confidence_label is low/medium/high.
# END_MODULE_CONTRACT: M-CONTRACTS.horary_analysis

# START_MODULE_MAP: M-CONTRACTS.horary_analysis
# public_entrypoints:
#   - EvidenceItem
#   - TimingInfo
#   - HoraryAnalysis
# END_MODULE_MAP: M-CONTRACTS.horary_analysis

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


EvidenceType = Literal[
    "main_aspect",
    "moon_testimony",
    "combustion",
    "category_modifier",
    "chart_weakness",
    "timeframe_hint",
    "neutral",
]


class EvidenceItem(BaseModel):
    type: EvidenceType
    title: str
    explanation: str
    weight: float = Field(..., ge=-1.0, le=1.0)
    planets_involved: list[str] = Field(default_factory=list)
    aspect_type: str | None = None
    orb: float | None = None
    applying: bool | None = None
    source: Literal["computed"] = "computed"


TimingStatus = Literal["known", "unclear", "not_enough_evidence"]


class TimingInfo(BaseModel):
    status: TimingStatus
    time_range: str | None = None
    text: str
    basis: str | None = None


ConfidenceLabel = Literal["low", "medium", "high"]


class HoraryAnalysis(BaseModel):
    verdict: Literal["yes", "no", "maybe"]
    confidence_score: int = Field(..., ge=0, le=100)
    confidence_label: ConfidenceLabel
    confidence_explanation: str
    involved_planets: list[str] = Field(default_factory=list)
    testimonies_for: list[EvidenceItem] = Field(default_factory=list)
    testimonies_against: list[EvidenceItem] = Field(default_factory=list)
    neutral_factors: list[EvidenceItem] = Field(default_factory=list)
    timing: TimingInfo
    calculation_warnings: list[str] = Field(default_factory=list)
