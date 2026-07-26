# ############################################################################
# AI_HEADER: MODULE_SCHEMAS_SYNASTRY
# ROLE: Pydantic schemas for synastry (compatibility) endpoints
# DEPENDENCIES: pydantic, app.schemas._base.CamelModel
# GRACE_ANCHORS: []
# ############################################################################

# START_MODULE_CONTRACT: M-SCHEMAS-SYNASTRY
# purpose: Pydantic schemas for synastry capabilities, partners, reports, aspect details, and feedback.
# owns:
#   - apps/api/app/schemas/synastry.py
# inputs: request payload dicts / query params
# outputs: validated models in camelCase wire format
# dependencies: app.schemas._base.CamelModel
# side_effects: none (pure schemas)
# emitted_logs: none
# invariants:
#   - All public schemas subclass CamelModel for camelCase wire format
# failure_policy: Pydantic ValidationError on invalid data
# END_MODULE_CONTRACT: M-SCHEMAS-SYNASTRY

# START_MODULE_MAP: M-SCHEMAS-SYNASTRY
# public_entrypoints:
#   - SynastryCapabilitiesRead
#   - PartnerCreate
#   - SynastryPartnerItem
#   - SynastryListRead
#   - SynastryGenerationRead
#   - SynastryAspect
#   - AspectDrilldown
#   - SynastrySphere
#   - SynastryReport
#   - SynastryFeedbackWrite
#   - SynastryFeedbackRead
# semantic_blocks: none
# owned_tests: none
# END_MODULE_MAP: M-SCHEMAS-SYNASTRY

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
import uuid
from typing import Any, Literal

from pydantic import Field

from app.schemas._base import CamelModel


class SynastryCapabilitiesRead(CamelModel):
    """Capabilities status for synastry feature."""

    can_calculate: bool = Field(..., description="Whether user can calculate new synastry report")
    active_partner_count: int = Field(..., description="Current count of active partners")
    max_partners: int = Field(default=20, description="Maximum allowed active partners per user")
    has_unlocked_access: bool = Field(..., description="Whether user has unlocked synastry access")
    credit_balance: int = Field(default=0, description="Available credit balance")


class PartnerCreate(CamelModel):
    """Request payload to create a new synastry partner."""

    name: str = Field(..., min_length=1, max_length=120, description="Partner name or nickname")
    relation: str = Field(default="romantic", description="Relation type (romantic, friend, business, family)")
    birth_date: date = Field(..., description="Birth date (YYYY-MM-DD)")
    birth_time: time | None = Field(default=None, description="Birth time (HH:MM:SS or HH:MM)")
    birth_city: str | None = Field(default=None, description="Birth city name")
    birth_lat: Decimal | float | None = Field(default=None, ge=-90, le=90, description="Birth latitude")
    birth_lon: Decimal | float | None = Field(default=None, ge=-180, le=180, description="Birth longitude")
    birth_tz: str | None = Field(default=None, description="Birth IANA timezone string")
    birth_time_precision: Literal["exact", "approximate"] = Field(
        default="exact", description="Birth time precision: exact or approximate"
    )
    idempotency_key: str | None = Field(default=None, max_length=80, description="Idempotency key")


class SynastryPartnerItem(CamelModel):
    """Summary item for a partner in the synastry list."""

    id: uuid.UUID = Field(..., description="Partner UUID")
    name: str = Field(..., description="Partner name")
    relation_type: str = Field(..., description="Relation type")
    birth_date: date = Field(..., description="Birth date")
    precision: str = Field(..., description="Birth time precision (exact/approximate)")
    score: int | None = Field(default=None, description="Overall compatibility score (0..100)")
    status: Literal["good", "mid", "bad"] | None = Field(default=None, description="Valence status")
    summary: str | None = Field(default=None, description="Short summary verdict")
    counters: dict[str, int] | None = Field(default=None, description="Counts of good, mid, bad aspects")
    report_state: str | None = Field(default=None, description="Report calculation state (pending, calculating, ready, failed)")
    created_at: datetime = Field(..., description="Partner creation timestamp")


class SynastryListRead(CamelModel):
    """List response of user's synastry partners."""

    partners: list[SynastryPartnerItem] = Field(default_factory=list, description="List of partner items")


class SynastryGenerationRead(CamelModel):
    """Status read model for async report calculation generation."""

    report_id: uuid.UUID = Field(..., description="Report UUID")
    partner_id: uuid.UUID = Field(..., description="Partner UUID")
    state: Literal["pending", "calculating", "narrative_generating", "ready", "failed", "invalidated"] = Field(
        ..., description="Current calculation state"
    )
    stage: str | None = Field(default=None, description="Human-readable processing stage")
    attempt_count: int = Field(default=0, description="Current calculation attempt count")
    error_code: str | None = Field(default=None, description="Error code if state is failed")
    error_message: str | None = Field(default=None, description="Public error message if failed")


class SynastryPlanetPoint(CamelModel):
    """Planet point for synastry interaction wheel geometry."""

    id: str = Field(..., description="Unique point ID e.g. owner_sun, partner_moon")
    owner: Literal["user", "partner"] = Field(..., description="Point owner: user or partner")
    planet: str = Field(..., description="Planet name e.g. Sun, Moon, Venus")
    longitude: float = Field(..., description="Ecliptic longitude in degrees (0..360)")
    sign: str | None = Field(default=None, description="Zodiac sign name")
    retrograde: bool = Field(default=False, description="Whether planet is in retrograde motion")
    house: int | None = Field(default=None, description="House number (1..12) if calculated and reliable")
    house_reliable: bool = Field(default=False, description="Whether house calculation is reliable")


class SynastryAspect(CamelModel):
    """Synastry aspect entry for interactive wheel and list."""

    id: str = Field(..., description="Aspect ID e.g. sun_trine_moon")
    title: str = Field(..., description="Human aspect title e.g. Солнце трин Луна")
    tone: Literal["good", "mid", "bad", "harmony", "tension", "neutral", "supportive", "mixed", "tense"] = Field(..., description="Aspect tone/valence")
    score: int | None = Field(default=None, description="Aspect impact score")
    description: str | None = Field(default=None, description="Short interpretation snippet")
    tech_signature: str | None = Field(default=None, description="Technical aspect signature")
    owner_planet_key: str | None = Field(default=None, description="Point ID for owner planet e.g. owner_sun")
    partner_planet_key: str | None = Field(default=None, description="Point ID for partner planet e.g. partner_moon")
    aspect_symbol: str | None = Field(default=None, description="Aspect symbol e.g. △, □, ☌, ☍, ⚹")
    orb_degrees: float | None = Field(default=None, description="Orb value in degrees")
    orb_label: str | None = Field(default=None, description="Formatted orb string e.g. 1°12′")


class PlanetInfo(CamelModel):
    """Planet metadata for drill-down cards."""

    key: str = Field(..., description="Planet key e.g. Sun, Moon, Venus")
    label: str = Field(..., description="Localized planet name e.g. Меркурий")
    glyph: str = Field(..., description="Planet symbol glyph e.g. ☿")
    meaning: str = Field(..., description="Planet function in relationships")


class AspectDrilldownScene(CamelModel):
    """Life scene card for aspect drill-down."""

    title: str = Field(..., description="Scene title e.g. В споре")
    text: str = Field(..., description="Scene description")


class AspectDrilldown(CamelModel):
    """Detailed drill-down interpretation for a single synastry aspect."""

    aspect_id: str = Field(..., description="Aspect ID")
    title: str = Field(..., description="Aspect title")
    tone: Literal["good", "mid", "bad", "harmony", "tension", "neutral", "supportive", "mixed", "tense"] = Field(..., description="Aspect tone")
    tech_signature: str | None = Field(default=None, description="Technical astrological signature")
    aspect_symbol: str | None = Field(default=None, description="Aspect symbol e.g. □, △, ☌, ☍, ⚹")
    aspect_kind_label: str | None = Field(default=None, description="Localized aspect kind name e.g. Квадрат, Тригон")
    orb_text: str | None = Field(default=None, description="Formatted orb string e.g. орб 1°05′")
    headline: str | None = Field(default=None, description="Human headline for aspect interaction")
    owner_planet: PlanetInfo | None = Field(default=None, description="Owner planet information")
    partner_planet: PlanetInfo | None = Field(default=None, description="Partner planet information")
    aspect_mechanics: str | None = Field(default=None, description="Aspect type astrological mechanics explanation")
    explanation: str = Field(..., description="Deep psychological and dynamic explanation")
    scenes: list[AspectDrilldownScene] = Field(default_factory=list, description="Life interaction scenes (3-5 items)")
    repairs: list[str] = Field(default_factory=list, description="Numbered repair actions (3-5 items)")
    not_means: list[str] = Field(default_factory=list, description="Protection from fatalism ('This does NOT mean...') (3 items)")
    scenario: str | None = Field(default=None, description="Legacy flat scenario fallback")
    advice: str | None = Field(default=None, description="Legacy flat advice fallback")


class SynastrySphere(CamelModel):
    """Synastry breakdown sphere (Intimacy, Communication, Daily Life, Work & Money)."""

    id: str = Field(..., description="Sphere identifier e.g. intimacy, communication, daily_life, finance")
    title: str = Field(..., description="Display title e.g. Близость")
    score: int = Field(..., ge=0, le=100, description="Sphere compatibility score (0..100)")
    description: str | None = Field(default=None, description="Detailed sphere explanation")


class SynastryTranslation(CamelModel):
    """Human translation item connecting astrological factors to real-life dynamics."""

    tone: Literal["good", "mid", "bad", "supportive", "mixed", "tense"] | None = Field(
        default=None, description="Tone/valence of translation"
    )
    title: str = Field(..., description="Card title (up to 42 chars)")
    aspect_id: str | None = Field(default=None, description="Matched aspect ID for drill-down link")
    tech: str | None = Field(default=None, description="Technical aspect signature text")
    text: str | None = Field(default=None, description="Main translation text")
    scene: str | None = Field(default=None, description="Real life scene description")


class SynastryReport(CamelModel):
    """Full synastry report data model."""

    id: uuid.UUID = Field(..., description="Report UUID")
    owner_id: uuid.UUID = Field(..., description="Owner user UUID")
    partner_id: uuid.UUID = Field(..., description="Partner UUID")
    partner_name: str = Field(..., description="Partner name")
    partner_birth_date: date | None = Field(default=None, description="Partner birth date")
    partner_birth_time: str | None = Field(default=None, description="Partner birth time HH:MM if known")
    partner_birth_city: str | None = Field(default=None, description="Partner birth city")
    relation_type: str = Field(..., description="Relation type")
    precision: str = Field(..., description="Birth time precision (exact/approximate)")
    score: int = Field(..., ge=0, le=100, description="Overall compatibility score (0..100)")
    status: Literal["good", "mid", "bad"] = Field(..., description="Overall compatibility valence status")
    verdict: str = Field(..., description="One-line verdict headline")
    summary: str = Field(..., description="Paragraph executive summary")
    hero_title: str | None = Field(default=None, description="Hero section headline")
    hero_description: str | None = Field(default=None, description="Hero section subtitle")
    counters: dict[str, int] = Field(default_factory=dict, description="Counts of good, mid, bad aspects")
    owner_planets: list[SynastryPlanetPoint] = Field(default_factory=list, description="Owner chart planet points for SVG wheel")
    partner_planets: list[SynastryPlanetPoint] = Field(default_factory=list, description="Partner chart planet points for SVG wheel")
    aspects: list[SynastryAspect] = Field(default_factory=list, description="Key synastry aspects list")
    house_overlays: list[dict[str, Any]] = Field(default_factory=list, description="House overlay interpretations")
    spheres: list[SynastrySphere] = Field(default_factory=list, description="Spheres breakdown")
    translations: list[SynastryTranslation] = Field(default_factory=list, description="Human translation cards")
    user_feedback: str | None = Field(default=None, description="Current user reality feedback value")
    created_at: datetime = Field(..., description="Report creation timestamp")


class SynastryFeedbackWrite(CamelModel):
    """Request payload to submit reality check feedback."""

    value: str = Field(..., min_length=1, max_length=30, description="Feedback choice (accurate, partial, inaccurate)")


class SynastryFeedbackRead(CamelModel):
    """Response payload for submitted feedback."""

    report_id: uuid.UUID = Field(..., description="Report UUID")
    value: str = Field(..., description="Feedback value")
    updated_at: datetime = Field(..., description="Submission timestamp")
