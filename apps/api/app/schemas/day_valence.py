# ############################################################################
# AI_HEADER: MODULE_SCHEMAS_DAY_VALENCE
# ROLE: Pydantic schemas for day valence factor ledger, sphere assessment, and status breakdown.
# DEPENDENCIES: pydantic, app.schemas._base.CamelModel
# ############################################################################

# START_MODULE_CONTRACT: M-SCHEMAS-DAY-VALENCE
# purpose: Typed schemas for day valence factor ledger, product sphere assessments, and global status breakdown (W2-VALENCE).
# owns:
#   - apps/api/app/schemas/day_valence.py
# inputs: none (schema-only)
# outputs: DayValenceFactor, ProductSphereAssessment, SphereValenceRead, DayStatusBreakdown
# dependencies: app.schemas._base.CamelModel
# side_effects: none (pure schema)
# emitted_logs: none
# failure_policy: Pydantic ValidationError on schema mismatch
# END_MODULE_CONTRACT: M-SCHEMAS-DAY-VALENCE

# START_MODULE_MAP: M-SCHEMAS-DAY-VALENCE
# public_entrypoints:
#   - DayValenceFactor
#   - ProductSphereAssessment
#   - SphereValenceRead
#   - DayStatusBreakdown
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_day_valence_schemas.py
# END_MODULE_MAP: M-SCHEMAS-DAY-VALENCE

from __future__ import annotations

from typing import Literal
from pydantic import Field

from app.schemas._base import CamelModel


class DayValenceFactor(CamelModel):
    """Canonical factor entry in the day factor ledger (§5.1)."""

    factor_id: str = Field(..., description="Unique deterministic factor identity")
    semantic_key: str = Field(..., description="Normalized factor key for cross-source deduplication")
    source: Literal["activation", "day_signal"] = Field(..., description="Origin layer: activation or day_signal")
    technique: str = Field(..., description="Astrological technique key")
    technique_family: str = Field(..., description="Astrological technique family")
    polarity: Literal["supportive", "tense", "mixed", "neutral"] = Field(..., description="Valence polarity")
    strength: float = Field(..., description="Raw factor strength (0..1)")
    technical_spheres: list[str] = Field(default_factory=list, description="Mapped technical sphere keys")
    source_planet: str | None = Field(default=None, description="Normalized source planet name")
    target_type: str = Field(..., description="Target entity type (e.g. natal_planet, house, lot, angle)")
    target_key: str = Field(..., description="Normalized target entity key")
    aspect_type: str | None = Field(default=None, description="Aspect type if aspect factor")


class ProductSphereAssessment(CamelModel):
    """Assessment summary for one product sphere (§6.6)."""

    key: str = Field(..., description="Product sphere key e.g. work, money")
    salience_score: float = Field(..., description="Max final_score across mapped technical spheres")
    support_score: float = Field(..., description="Effective support valence score")
    tension_score: float = Field(..., description="Effective tension valence score")
    balance: float = Field(..., description="Normalized balance (-1..1)")
    verdict: Literal["good", "neutral", "caution", "avoid"] = Field(..., description="Product sphere verdict")
    confidence: Literal["low", "medium", "high"] = Field(..., description="Assessment confidence level")
    verdict_rule: Literal[
        "avoid_tension_2x",
        "caution_tension_1_3x",
        "good_support_1_3x",
        "neutral_low_evidence",
        "neutral_balanced",
    ] = Field(..., description="Rule code that determined the verdict")
    factor_count: int = Field(..., description="Total factors touching this sphere")
    effective_factor_count: int = Field(..., description="Effective factors contributing after family decay")
    independent_family_count: int = Field(..., description="Number of distinct technique families")
    primary_factor_id: str | None = Field(default=None, description="ID of primary driving factor")


class SphereValenceRead(CamelModel):
    """Public/read representation for one product sphere's valence."""

    sphere: str
    assessment: ProductSphereAssessment
    primary_factor: DayValenceFactor | None = None


class DayStatusBreakdown(CamelModel):
    """Global day status calculation breakdown (§6.7)."""

    support_score: float = Field(..., description="Global support valence score")
    tension_score: float = Field(..., description="Global tension valence score")
    ratio: float | None = Field(default=None, description="Support/tension or tension/support ratio")
    rule: str = Field(..., description="Day status decision rule name")
    factor_count: int = Field(..., description="Total canonical factors in day ledger")
    effective_factor_count: int = Field(..., description="Factors contributing after global family decay")
    family_counts: dict[str, int] = Field(default_factory=dict, description="Factor count per technique family")
    duplicate_factor_count: int = Field(default=0, description="Number of deduplicated/merged factors")


class FactorLedger(CamelModel):
    """Container for built factor ledger and deduplication counters."""

    factors: list[DayValenceFactor] = Field(default_factory=list)
    duplicate_count: int = Field(default=0, description="Count of duplicate factors excluded during ledger build")
    invalid_count: int = Field(default=0, description="Count of invalid factors excluded due to missing required fields")
