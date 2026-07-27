# ############################################################################
# AI_HEADER: MODULE_SCHEMAS_TODAY_FOCUS
# ROLE: Pydantic schemas for TodayFocus public API contract (§5 of parent TZ).
# DEPENDENCIES: pydantic, datetime, app.schemas._base.CamelModel
# ############################################################################

# START_MODULE_CONTRACT: M-SCHEMAS-TODAY-FOCUS
# purpose: Typed Pydantic schemas for TodayFocus, events, convergence, and featured spheres (W4-C1).
# owns:
#   - apps/api/app/schemas/today_focus.py
# inputs: none (schema-only)
# outputs: TodayFocusEvent, TodayFeaturedSphere, TodayConvergence, TodayFocus
# dependencies: app.schemas._base.CamelModel
# side_effects: none (pure schema)
# emitted_logs: none
# failure_policy: Pydantic ValidationError on schema mismatch
# END_MODULE_CONTRACT: M-SCHEMAS-TODAY-FOCUS

# START_MODULE_MAP: M-SCHEMAS-TODAY-FOCUS
# public_entrypoints:
#   - TodayFocusEvent
#   - TodayFeaturedSphere
#   - TodayConvergence
#   - TodayFocus
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_today_focus_contract.py
# END_MODULE_MAP: M-SCHEMAS-TODAY-FOCUS

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from pydantic import Field

from app.schemas._base import CamelModel


class TodayFocusEvent(CamelModel):
    """Public event calculated for a user's date (§5)."""

    id: str = Field(..., description="Deterministic event identity")
    kind: Literal["exact", "starts", "peak", "building", "separating"] = Field(
        ..., description="Event timing kind"
    )
    occurs_at: datetime | None = Field(
        default=None, description="UTC ISO instant timestamp"
    )
    local_date: date = Field(..., description="User local date")
    timezone: str = Field(..., description="IANA timezone name used for classification")
    precision: Literal["minute", "date", "window"] = Field(
        ..., description="Time precision level"
    )
    human_title: str = Field(..., description="Human-first event title without jargon")
    technical_title: str | None = Field(
        default=None, description="Optional technical disclosure title"
    )
    meaning: str | None = Field(
        default=None, description="Validated narrative meaning (LLM-owned)"
    )
    source_activation_ids: list[str] = Field(
        default_factory=list, description="IDs of underlying activations"
    )


class TodayFeaturedSphere(CamelModel):
    """Featured sphere recommendation card for convergence (§5)."""

    key: str = Field(..., description="Product sphere key e.g. work, money")
    relevance_rank: int = Field(..., description="Relevance rank 1..3")
    state: Literal["convergence_today"] = Field(
        default="convergence_today", description="Featured sphere state"
    )
    summary: str | None = Field(
        default=None, description="LLM-generated featured summary"
    )
    action: str | None = Field(
        default=None, description="LLM-generated imperative action phrase"
    )
    convergence_id: str = Field(..., description="Associated convergence ID")
    source_event_ids: list[str] = Field(
        default_factory=list, description="IDs of supporting events"
    )
    source_activation_ids: list[str] = Field(
        default_factory=list, description="IDs of supporting activations"
    )


class TodayConvergence(CamelModel):
    """Calculated theme convergence summary (§5)."""

    id: str = Field(..., description="Convergence cluster identity")
    theme_key: str = Field(..., description="Primary theme or target key")
    title: str = Field(..., description="Convergence section title")
    summary: str | None = Field(
        default=None, description="LLM-generated convergence summary"
    )
    independent_factor_count: int = Field(
        ..., description="Count of distinct physical factors"
    )
    technique_families: list[str] = Field(
        default_factory=list, description="List of technique family names"
    )
    source_activation_ids: list[str] = Field(
        default_factory=list, description="IDs of all contributing activations"
    )


class TodayFocus(CamelModel):
    """Root focus block for 'What converged today' (§5)."""

    state: Literal[
        "convergence_today",
        "single_impulses",
        "background_only",
        "no_accent",
        "unavailable",
    ] = Field(..., description="Product focus state")
    convergence: TodayConvergence | None = Field(
        default=None, description="Convergence detail if state is convergence_today"
    )
    events: list[TodayFocusEvent] = Field(
        default_factory=list, description="0..3 public calculated events"
    )
    featured_spheres: list[TodayFeaturedSphere] = Field(
        default_factory=list, description="0..3 featured sphere cards"
    )
    content_state: Literal["ready", "pending", "unavailable", "not_needed"] = Field(
        default="not_needed", description="LLM content generation status"
    )
