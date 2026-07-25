# ############################################################################
# AI_HEADER: MODULE_SCHEMAS_SYNASTRY
# ROLE: Sidecar calculation schemas for synastry requests and responses
# DEPENDENCIES: pydantic
# GRACE_ANCHORS: []
# ############################################################################

# START_MODULE_CONTRACT: M-SIDECAR-SCHEMAS-SYNASTRY
# purpose: Request and response models for /v1/synastry sidecar calculation endpoint.
# owns:
#   - apps/solarsage/solarsage/schemas/synastry.py
# inputs: request parameters
# outputs: validated Pydantic models
# dependencies: pydantic
# side_effects: none
# emitted_logs: none
# invariants:
#   - Additive only: no modifications to natal/transits schemas
# failure_policy: Pydantic ValidationError
# END_MODULE_CONTRACT: M-SIDECAR-SCHEMAS-SYNASTRY

# START_MODULE_MAP: M-SIDECAR-SCHEMAS-SYNASTRY
# public_entrypoints:
#   - SynastryRequest
#   - CrossAspect
#   - SynastryResponse
# semantic_blocks: none
# owned_tests: none
# END_MODULE_MAP: M-SIDECAR-SCHEMAS-SYNASTRY

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class SynastryRequest(BaseModel):
    """Sidecar synastry calculation request payload."""

    owner_birth_date: str = Field(..., description="Owner birth date in YYYY-MM-DD format")
    owner_birth_time: str = Field(..., description="Owner birth time in HH:MM format")
    owner_birth_lat: float = Field(..., description="Owner birth latitude in degrees")
    owner_birth_lon: float = Field(..., description="Owner birth longitude in degrees")
    owner_birth_tz: str = Field(..., description="Owner birth timezone string")

    partner_birth_date: str = Field(..., description="Partner birth date in YYYY-MM-DD format")
    partner_birth_time: str | None = Field(default=None, description="Partner birth time in HH:MM format")
    partner_birth_lat: float | None = Field(default=None, description="Partner birth latitude in degrees")
    partner_birth_lon: float | None = Field(default=None, description="Partner birth longitude in degrees")
    partner_birth_tz: str | None = Field(default=None, description="Partner birth timezone string")
    partner_birth_time_precision: str = Field(
        default="exact", description="Partner birth time precision (exact, approximate, unknown)"
    )


class CrossAspect(BaseModel):
    """Cross-chart aspect between owner planet and partner planet."""

    owner_planet: str
    partner_planet: str
    aspect_type: str
    orb_degrees: float
    applying: bool | None = None


class SynastryResponse(BaseModel):
    """Sidecar synastry calculation response payload."""

    owner_planets: list[dict[str, Any]]
    partner_planets: list[dict[str, Any]]
    partner_houses: list[dict[str, Any]] | None = None
    partner_special_points: list[dict[str, Any]] | None = None
    cross_aspects: list[CrossAspect]
    precision_flags: dict[str, Any]
