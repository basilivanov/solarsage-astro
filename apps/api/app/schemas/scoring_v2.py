# ############################################################################
# AI_HEADER: MODULE_CONTRACTS_SCORING_V2 — scoring v2 contract schemas.
# ROLE: Typed contracts for SolarSage V2 scoring.
#       W1: contract-only. Not populated by ScoringService until W4+.
# ############################################################################

# START_MODULE_CONTRACT: M-SCHEMAS-SCORING-V2
# purpose: Typed contracts for SolarSage V2 scoring.
# owns:
#   - apps/api/app/schemas/scoring_v2.py
# inputs: none (schema-only)
# outputs: validated models
# dependencies: none
# side_effects: none
# emitted_logs: none
# invariants: none
# failure_policy: none
# END_MODULE_CONTRACT: M-SCHEMAS-SCORING-V2

# START_MODULE_MAP: M-SCHEMAS-SCORING-V2
# public_entrypoints:
#   - SphereContribution
#   - SphereScoreV2
# semantic_blocks: none
# owned_tests: none
# END_MODULE_MAP: M-SCHEMAS-SCORING-V2

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from ._base import CamelModel
from .activation import ActivationEvidence


class SphereContribution(CamelModel):
    """One contribution line in a sphere score breakdown."""

    sphere: str
    source: Literal["base_signal", "activation", "convergence", "cap"]
    source_id: str
    amount: float
    before: float | None = None
    after: float | None = None
    evidence: str


class SphereScoreV2(CamelModel):
    """Per-sphere score with full V2 breakdown."""

    key: str
    title: str
    base_score: float
    activation_score: float
    convergence_bonus: float
    raw_score: float
    final_score: float
    normalized_score: float | None = None
    dominance_capped: bool = False
    contributions: list[SphereContribution]


class ScoringV2Result(CamelModel):
    """Full V2 scoring result. Contract-only until W4."""

    scoring_version: str = "ss-scoring-2.0"
    canon_versions: dict[str, str]
    day_status: str
    status_breakdown: dict[str, Any]
    sphere_scores: dict[str, SphereScoreV2]
    top_signals: list[dict[str, Any]]
    top_activations: list[ActivationEvidence]
    debug: dict[str, Any] = Field(default_factory=dict)
