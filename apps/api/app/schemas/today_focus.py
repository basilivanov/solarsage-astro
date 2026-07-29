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
# outputs: TodayFocusEvent, TodayFeaturedSphere, TodayFocusFactor, TodayConvergence, TodayFocus
# dependencies: app.schemas._base.CamelModel
# side_effects: none (pure schema)
# emitted_logs: none
# failure_policy: Pydantic ValidationError on schema mismatch
# END_MODULE_CONTRACT: M-SCHEMAS-TODAY-FOCUS

# START_MODULE_MAP: M-SCHEMAS-TODAY-FOCUS
# public_entrypoints:
#   - TodayFocusEvent
#   - TodayFeaturedSphere
#   - TodayFocusFactor
#   - TodayConvergence
#   - TodayFocus
#   - FocusEventPlanetSide
#   - FocusEventNumber
#   - FocusEventDrilldown
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_today_focus_contract.py
#   - apps/api/tests/test_focus_event_drilldown.py
# END_MODULE_MAP: M-SCHEMAS-TODAY-FOCUS

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from pydantic import Field, model_validator

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


class TodayFocusFactor(CamelModel):
    """Non-event convergence factor for the technical disclosure."""

    id: str = Field(..., description="Deterministic factor identity")
    role: Literal["anchor_today", "supporting", "background", "unrelated"] = Field(
        ..., description="Temporal role relative to the user's day"
    )
    human_title: str = Field(..., description="Human-first factor title without jargon")
    technical_title: str | None = Field(
        default=None, description="Optional technical disclosure title"
    )
    source_activation_ids: list[str] = Field(
        default_factory=list, description="IDs of underlying activations"
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
    background_factors: list[TodayFocusFactor] = Field(
        default_factory=list,
        description="Non-event factors with human titles and temporal roles",
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

    @model_validator(mode="after")
    def validate_focus_invariants(self) -> TodayFocus:
        # 1. State x ContentState matrix validation (§4.3 doc 29)
        allowed_content_states: dict[str, set[str]] = {
            "convergence_today": {"ready", "pending", "unavailable"},
            "single_impulses": {"ready", "pending", "unavailable"},
            "background_only": {"not_needed"},
            "no_accent": {"not_needed"},
            "unavailable": {"unavailable"},
        }
        allowed = allowed_content_states.get(self.state, set())
        if self.content_state not in allowed:
            raise ValueError(
                f"Invalid content_state '{self.content_state}' for focus state '{self.state}'. Allowed: {allowed}"
            )

        # 2. Caps validation (doc 29 §4.3)
        if len(self.events) > 3:
            raise ValueError(f"events count {len(self.events)} exceeds cap of 3")
        if len(self.featured_spheres) > 3:
            raise ValueError(f"featured_spheres count {len(self.featured_spheres)} exceeds cap of 3")

        # 3. Duplicate public event IDs and empty IDs validation (doc 29 §4.3)
        event_ids = [e.id for e in self.events]
        for ev_id in event_ids:
            if not ev_id or not ev_id.strip():
                raise ValueError("event.id cannot be empty")
        if len(event_ids) != len(set(event_ids)):
            raise ValueError(f"duplicate public event IDs found: {event_ids}")

        return self


class FocusEventPlanetSide(CamelModel):
    """Source or target side representation for a focus event drilldown."""

    planet_key: str = Field(..., description="Planet or lot key e.g. MOON, PLUTO, NECESSITY")
    label: str = Field(..., description="Human label e.g. Луна, Жребий")
    frame_label: str = Field(..., description="Frame origin label e.g. транзитная, твой натальный, твой жребий")
    function_text: str = Field(..., description="Human function text e.g. эмоции и привычки")


class FocusEventNumber(CamelModel):
    """Key numerical metric for focus event drilldown."""

    label: str = Field(..., description="Metric label e.g. Орб, Точное время, Окно действия")
    value: str = Field(..., description="Formatted metric value e.g. 0°19′, 13:31 · Europe/Moscow")


class FocusEventDrilldown(CamelModel):
    """Complete response payload for GET /api/day/{date_str}/focus-event/{event_id} (E1)."""

    event_id: str = Field(..., description="Public event identity string")
    human_title: str = Field(..., description="Human event title")
    technical_title: str | None = Field(default=None, description="Technical event title")
    kind: str = Field(..., description="Timing kind: exact|starts|peak|building|separating")
    kind_label: str = Field(..., description="Human kind label e.g. точный пик, начинается")
    occurs_at: datetime | None = Field(default=None, description="UTC ISO instant timestamp")
    local_time: str | None = Field(default=None, description="Local HH:MM format in user timezone")
    timezone: str = Field(..., description="User IANA timezone")
    meaning: str | None = Field(default=None, description="Validated narrative text from payload")
    technique_label: str = Field(..., description="Technique description e.g. Транзит к твоей натальной карте")
    source: FocusEventPlanetSide | None = Field(default=None, description="Source side details")
    target: FocusEventPlanetSide | None = Field(default=None, description="Target side details")
    aspect_label: str | None = Field(default=None, description="Russian aspect name e.g. Квадратура")
    aspect_symbol: str | None = Field(default=None, description="Aspect Unicode symbol e.g. □")
    aspect_tone: str | None = Field(default=None, description="Aspect polarity e.g. supportive|tense|mixed|neutral")
    aspect_mechanics: str | None = Field(default=None, description="Explanation of astrological aspect mechanics")
    numbers: list[FocusEventNumber] = Field(default_factory=list, description="Key numerical metrics")
    source_activation_ids: list[str] = Field(default_factory=list, description="IDs of underlying activations")
