# AI_HEADER: MODULE_CONTRACTS_TODAY
# module: M-CONTRACTS.today
# canon: docs/GRACE_CANON.md §6; docs/05_API_contracts_и_TodayPayload.md
# wave: W-1.1B
# purpose: TodayPayload and every nested type. Source of truth that
#          generates the today.* portion of packages/contracts/openapi.json
#          and, downstream, packages/contracts/*.ts.

# START_MODULE_CONTRACT: M-CONTRACTS.today
# purpose: Mirror the pre-W-1.1B handwritten TS exactly so the wire format
#          stays byte-identical (INV-CONTRACT-STABLE).
# invariants:
#   - meta.schema_version is the literal "today/v1".
#   - dates and timestamps are ISO-8601 strings.
#   - dayStatus literal set: supportive | steady | tense.
#   - WhyBlock is a discriminated union on `kind`.
#   - meta.contract_version is an int monotonically bumped on breaking
#     changes; never silently changed.
# emits: nothing.
# consumes: schemas._base.CamelModel and canonical per-content access types
#           re-exported from schemas.access.
# END_MODULE_CONTRACT: M-CONTRACTS.today

# START_MODULE_MAP: M-CONTRACTS.today
# - DayStatus: Literal alias.
# - ContentAccessReason, ContentAccessState: canonical re-exports from schemas.access.
# - TopFlag, TopFlagHint: highlight cards for the day.
# - WhyParagraph, WhyBullets, WhyBlock, WhySection: "why this happens" body.
# - WeekStripDay: 7-day strip item.
# - MicrocopyItem, YesterdayEcho: ancillary blocks.
# - DayQuality, TodayMeta, TodayAction, ReadingBody, WhyThisHappens: helpers.
# - TodayPayload: top-level response.
# END_MODULE_MAP: M-CONTRACTS.today

# START_BLOCK: TODAY_PRIMITIVES
from __future__ import annotations

from typing import Annotated, Literal, Any

from pydantic import Field, model_validator

from app.core.versions import (
    PREVIOUS_V2_FRONTEND_PAYLOAD_VERSION,
    TODAY_V2_COMPATIBLE_PAYLOAD_VERSIONS,
    TODAY_V2_PAYLOAD_VERSION,
    TODAY_V2_PREVIOUS_PAYLOAD_VERSION,
    V2_COMPATIBLE_FRONTEND_PAYLOAD_VERSIONS,
    V2_FRONTEND_PAYLOAD_VERSION,
)
from ._base import CamelModel
from .access import ContentAccessReason as ContentAccessReason
from .access import ContentAccessState as ContentAccessState
from .activation import ActivationEvidence
from .day import RelativeDayStatusRead
from .day_valence import DayStatusBreakdown, SphereValenceRead
from .scoring_v2 import SphereScoreV2
from .today_horizons import TodayV2HorizonsBlock, validate_horizons_against_evidence

DayStatus = Literal["supportive", "steady", "tense"]

class TopFlagHint(CamelModel):
    why_today: str | None = None
    how_it_feels: str | None = None


class TopFlag(CamelModel):
    icon_name: str
    title: str
    summary: str
    hint: TopFlagHint | None = None
# END_BLOCK: TODAY_PRIMITIVES

# START_BLOCK: WHY_BLOCKS
class WhyParagraph(CamelModel):
    kind: Literal["paragraph"]
    text: str


class WhyBullets(CamelModel):
    kind: Literal["bullets"]
    items: list[str]


# Discriminated union: TS emits `WhyParagraph | WhyBullets`.
WhyBlock = WhyParagraph | WhyBullets


class WhySection(CamelModel):
    id: str
    title: str
    icon_name: str | None = None
    blocks: list[WhyBlock] = Field(..., discriminator=None)

    # W-4.0: layer metadata for convergence evidence
    layer: Literal[
        "main_theme",
        "daily_layer",
        "personal_activation",
        "period_background",
        "amplifiers",
        "softeners",
        "manifestation_zones",
        "astrological_meaning",
        "practical_meaning",
    ] | None = None

    # W-4.0: astrological details for this section
    planets: list[str] | None = None
    houses: list[int] | None = None
    aspects: list[str] | None = None
    techniques: list[str] | None = None


class WhyThisHappens(CamelModel):
    sections: list[WhySection]
# END_BLOCK: WHY_BLOCKS

# START_BLOCK: TODAY_AUX
class WeekStripDay(CamelModel):
    date: str
    day_status: DayStatus
    is_today: bool


MicrocopyTone = Literal["bold", "supportive", "gentle", "warning"]
MicrocopyScope = Literal["today", "morning", "evening"]


class MicrocopyItem(CamelModel):
    id: str
    text_short: str
    text_long: str
    tone: list[MicrocopyTone]
    scope: MicrocopyScope


YesterdayTransition = Literal["released", "intensified", "shifted", "continued"]


class YesterdayEcho(CamelModel):
    had_checkin: bool
    mood: Literal[1, 2, 3, 4, 5] | None = None
    accuracy: Literal[1, 2, 3, 4, 5] | None = None
    closure_text: str
    transition: YesterdayTransition


class DayQuality(CamelModel):
    support_score: float
    friction_score: float
    intensity_score: float


class TodayAction(CamelModel):
    id: str
    label: str
    href: str | None = None


class ReadingBody(CamelModel):
    paragraphs: list[str]
# END_BLOCK: TODAY_AUX


# START_BLOCK: TODAY_READ_MODELS
class DayChartHouse(CamelModel):
    number: int
    cusp_longitude: float
    sign: str | None = None


class DayChartTransitPlanet(CamelModel):
    name: str
    longitude: float
    sign: str | None = None
    retrograde: bool | None = None
    speed: float | None = None
    motion: Literal["direct", "retrograde", "stationary"] | None = None
    house: int | None = None
    interpretation: str | None = None


class DayChartAspect(CamelModel):
    planet: str
    target_planet: str
    aspect_type: str
    orb: float | None = None
    strength: float | None = None


class DayChart(CamelModel):
    source: Literal["solarsage"]
    houses: list[DayChartHouse]
    transit_planets: list[DayChartTransitPlanet]
    aspects: list[DayChartAspect]


class PlanetInfluence(CamelModel):
    name: str
    score: float
    rank: int


class SphereScore(CamelModel):
    key: str
    score: float
    rank: int
# END_BLOCK: TODAY_READ_MODELS

# START_BLOCK: CONVERGENCE_EVIDENCE
# AI_HEADER
# wave: W-4.0
# purpose: Convergence evidence — доказательство, что несколько техник указывают
#          на одну планету/дом/сферу. Показывает силу активации через количество
#          независимых техник.
class ConvergenceEvidence(CamelModel):
    """Convergence: несколько техник указывают на одну планету/дом/сферу"""

    theme: str  # "thinking_speech_learning" или "MERCURY" или "house_3"
    convergence_level: Literal["double", "triple", "quad", "peak"]  # 2, 3, 4, 5+ техник
    techniques: list[str]  # ["annual_profection", "transit_to_natal", "solar_arc"]
    summary: str  # "Меркурий подсвечен через 3 независимые техники"
# END_BLOCK: CONVERGENCE_EVIDENCE

# START_BLOCK: MANIFESTATION_ZONES
# AI_HEADER
# wave: W-4.0
# purpose: Manifestation zones — где это проявится в жизни (дома).
#          Показывает конкретные сферы жизни, где активация будет видна.
class ManifestationZone(CamelModel):
    """Где это проявится в жизни"""

    house: int  # 3
    theme: str  # "общение, учёба, ближний круг"
    intensity: Literal["background", "active", "peak"]
    description: str  # "Основная зона проявления сегодня"
# END_BLOCK: MANIFESTATION_ZONES

# START_BLOCK: PERIOD_CONTEXT
# AI_HEADER
# wave: W-4.0
# purpose: Period context — почему это важно именно сейчас (фон периода).
#          Показывает долгосрочные техники (профекция, фирдар, соляр), которые
#          создают контекст для сегодняшних активаций.
class PeriodContext(CamelModel):
    """Почему это важно именно сейчас (фон периода)"""

    year_theme: str | None = None  # "3-й дом года (профекция)"
    year_ruler: str | None = None  # "Меркурий"
    active_period: str | None = None  # "Фирдар Меркурия"
    solar_return_emphasis: str | None = None  # "Марс в 3-м доме SR"
    long_term_transit: str | None = None  # "Сатурн квадрат натальный Меркурий (весь год)"
# END_BLOCK: PERIOD_CONTEXT

# START_BLOCK: TODAY_PAYLOAD
class TodayMeta(CamelModel):
    schema_version: Literal["today/v1"]
    contract_version: int
    calculation_version: int | str
    normalization_version: int
    scoring_version: int | str
    prompt_version: int
    content_version: int
    generated_at: str
    cached: bool = False  # W-5.2: true if returned from cache

    # W-4.0: legacy canon/activation version fields (int, for backward compat)
    scoring_canon_version: int | None = None
    activation_layer_version: int | str | None = None

    # W1+: V2 string version fields
    canon_versions: dict[str, str] | None = None
    audit_trace_id: str | None = None
    payload_version: Literal["today.v1", "today.v2", "today.v2.1", "today.v2.2"] = "today.v1"
    frontend_payload_version: int = 1


# START_BLOCK: TODAY_IMPORTANT_EVENTS
ImportantTodayKind = Literal[
    "void_moon",
    "new_moon",
    "full_moon",
    "solar_eclipse",
    "lunar_eclipse",
    "mercury_retrograde",
    "mercury_station",
    "moon_quarter",
    "sun_ingress",
    "fast_planet_aspect",
]

ImportantTodayTone = Literal["supportive", "caution", "neutral_shift"]


class TodayImportantEvent(CamelModel):
    """Today Important block event."""

    id: str
    kind: ImportantTodayKind
    tone: ImportantTodayTone
    title: str
    summary: str
    starts_at: str | None = None
    ends_at: str | None = None
    exact_at: str | None = None
    local_time_label: str | None = None
    timezone: str
    priority: int = 5
# END_BLOCK: TODAY_IMPORTANT_EVENTS


# START_BLOCK: CONCRETE_ADVICE_SCHEMAS
ConcreteAdviceVerdict = Literal["good", "caution", "avoid", "neutral"]
ConcreteAdviceConfidence = Literal["high", "medium", "low"]
ConcreteAdviceEvidenceKind = Literal[
    "sphere_score",
    "aspect",
    "planet_in_house",
    "day_status",
    "lunar",
    "important_today",
    "activation",
    "score_contribution",
]

class ConcreteAdviceEvidence(CamelModel):
    kind: ConcreteAdviceEvidenceKind
    title: str
    weight: float | None = None
    planet: str | None = None
    target_planet: str | None = None
    aspect_type: str | None = None
    orb: float | None = None
    strength: float | None = None
    sphere_key: str | None = None
    house: int | None = None
    sign: str | None = None
    activation_id: str | None = None
    technique: str | None = None
    technique_family: str | None = None
    source_frame: str | None = None
    target_frame: str | None = None
    contribution_source_id: str | None = None

class ConcreteAdviceDetails(CamelModel):
    """Structured personal drilldown breakdown for a single product sphere."""
    story: str = Field(..., description="2-3 sentences about the person and their day in this sphere")
    why: list[str] = Field(default_factory=list, description="1-2 human background lines grounded in evidence")
    advice: str = Field(..., description="Short concrete advice string")

class ConcreteAdviceRow(CamelModel):
    key: Literal[
        "work",
        "money",
        "documents",
        "relationships",
        "sport",
        "communication",
        "health",
        "decisions",
        "travel",
        "creativity",
        "study",
        "shopping",
    ]
    label: str
    icon_name: str
    rank: int
    verdict: ConcreteAdviceVerdict
    confidence: ConcreteAdviceConfidence
    text: str
    evidence: list[ConcreteAdviceEvidence]
    details: ConcreteAdviceDetails | None = None
    assessment: SphereValenceRead | None = None

class ConcreteAdviceCounts(CamelModel):
    good: int
    caution: int
    avoid: int
    neutral: int

class ConcreteAdviceBlock(CamelModel):
    rows: list[ConcreteAdviceRow]
    counts: ConcreteAdviceCounts
# END_BLOCK: CONCRETE_ADVICE_SCHEMAS

# START_BLOCK: DAY_SUMMARY_SCHEMAS
DaySummaryFactKind = Literal[
    "top_planet",
    "lunar_phase",
    "void_moon",
    "top_flag",
]

class DaySummaryFact(CamelModel):
    kind: DaySummaryFactKind
    icon_name: str
    title: str
    summary: str | None = None

class DaySummaryBlock(CamelModel):
    status_label: str
    status_line: str
    facts: list[DaySummaryFact]
    main_advice: str | None = None
# END_BLOCK: DAY_SUMMARY_SCHEMAS


# START_BLOCK: TODAY_V2_SCHEMAS
class TodayV2HorizonPipelineAuditBuilt(CamelModel):
    model_config = {**CamelModel.model_config, "hide_input_in_errors": True}

    schema_version: Literal["today-horizon-pipeline-audit.v1"] = "today-horizon-pipeline-audit.v1"
    status: Literal["built"]
    reason: Literal["selected"]
    selected_count: Literal[3]


TodayV2UnavailableHorizonSelectionReason = Literal[
    "invalid_target_clock",
    "missing_long",
    "missing_medium",
    "missing_fast",
    "no_coherent_triple",
]


class TodayV2HorizonPipelineAuditUnavailable(CamelModel):
    model_config = {**CamelModel.model_config, "hide_input_in_errors": True}

    schema_version: Literal["today-horizon-pipeline-audit.v1"] = "today-horizon-pipeline-audit.v1"
    status: Literal["unavailable"]
    reason: TodayV2UnavailableHorizonSelectionReason
    selected_count: Literal[0]


TodayV2HorizonPipelineAudit = Annotated[
    TodayV2HorizonPipelineAuditBuilt | TodayV2HorizonPipelineAuditUnavailable,
    Field(discriminator="status"),
]


class TodayV2ActivatedTarget(CamelModel):
    target_type: Literal["planet", "house", "lot", "angle", "sphere"]
    target_key: str
    label: str
    family_count: int
    techniques: list[str]
    spheres: list[str]
    activation_ids: list[str]


class TodayV2ActivationSummary(CamelModel):
    headline: str
    top_activated_targets: list[TodayV2ActivatedTarget]


class TodayV2WhyTodayItem(CamelModel):
    id: str
    title: str
    body: str
    activation_ids: list[str]
    techniques: list[str]


class TodayV2Audit(CamelModel):
    trace_id: str | None = None
    available: bool = False
    payload_version: str
    calculation_version: str | int
    scoring_version: str | int
    activation_layer_version: str | int | None = None
    valence_version: str | None = None
    canon_versions: dict[str, str] = Field(default_factory=dict)
    v1_v2_diff: dict[str, Any] | None = None
    day_status_breakdown: DayStatusBreakdown | None = None
    horizon_pipeline: TodayV2HorizonPipelineAudit | None = None


class TodayV2Block(CamelModel):
    model_config = {**CamelModel.model_config, "hide_input_in_errors": True}

    activation_summary: TodayV2ActivationSummary
    activation_evidence: list[ActivationEvidence]
    score_breakdown: dict[str, SphereScoreV2]
    why_today: list[TodayV2WhyTodayItem]
    audit: TodayV2Audit
    horizons: TodayV2HorizonsBlock | None = None

    @model_validator(mode="after")
    def validate_optional_horizons(self) -> "TodayV2Block":
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS.today.TodayV2Block.validate_optional_horizons
        # purpose: Enforce audit-to-horizons alignment plus horizons activation/timing cross-reference integrity.
        # inputs: self - validated TodayV2Block candidate.
        # returns: the same V2 block when audit status, horizons presence, and cross-references are valid.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError with structural text for audit/horizons or cross-reference violations.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS.today.TodayV2Block.validate_optional_horizons
        if self.audit.horizon_pipeline is not None:
            if self.audit.horizon_pipeline.status == "built" and self.horizons is None:
                raise ValueError("TodayV2Block: built horizon pipeline requires horizons")
            if self.audit.horizon_pipeline.status == "unavailable" and self.horizons is not None:
                raise ValueError("TodayV2Block: unavailable horizon pipeline requires null horizons")
        if self.horizons is None:
            return self
        validate_horizons_against_evidence(self.horizons, self.activation_evidence)
        return self
# END_BLOCK: TODAY_V2_SCHEMAS


class TodayPayload(CamelModel):
    meta: TodayMeta
    date: str
    title: str
    subtitle: str | None = None
    headline: str
    access: ContentAccessState
    day_status: DayStatus
    day_summary: DaySummaryBlock
    concrete_advice: ConcreteAdviceBlock
    day_quality: DayQuality | None = None
    top_flags: list[TopFlag]
    reading: ReadingBody
    notes: str | None = None
    why_this_happens: WhyThisHappens
    week_strip: list[WeekStripDay]
    microcopy: list[MicrocopyItem]
    yesterday_echo: YesterdayEcho | None = None
    actions: list[TodayAction] | None = None
    day_chart: DayChart | None = None
    planet_influences: list[PlanetInfluence] | None = None
    sphere_scores: list[SphereScore] | None = None

    # W-4.0: convergence evidence
    activation_evidence: list[ConvergenceEvidence] | None = None

    # W-4.0: manifestation zones
    manifestation_zones: list[ManifestationZone] | None = None

    # W-4.0: period context
    period_context: PeriodContext | None = None

    # W-PHASE-2: today important items
    important_today: list[TodayImportantEvent] = []

    # W-DAY: relative status (z-score against 14-day personal baseline)
    relative_status: RelativeDayStatusRead | None = None

    # W-6: optional V2 block
    v2: TodayV2Block | None = None

    @model_validator(mode="after")
    def validate_v2_identity_requires_body(self) -> "TodayPayload":
        # START_FUNCTION_CONTRACT: F-M-CONTRACTS.today.TodayPayload.validate_v2_identity_requires_body
        # purpose: Enforce public V2 identity/body compatibility for current and previous payload pairs.
        # inputs: self - validated TodayPayload candidate with meta and optional v2 block.
        # returns: self when V1/null, previous V2/frontend=2, or current V2.1/frontend=3 identity is coherent.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for missing V2 body, contradictory current pair,
        # missing pipeline audit, or audit payload mismatch.
        # END_FUNCTION_CONTRACT: F-M-CONTRACTS.today.TodayPayload.validate_v2_identity_requires_body
        """Reject explicit V2 wire identity without a V2 body.

        V1 payloads (and legacy rows without explicit V2 identity) may keep v2=None.
        Known V2 payload/frontend identities require a non-null V2 body.
        """
        payload_version = getattr(self.meta, "payload_version", None)
        frontend_version = getattr(self.meta, "frontend_payload_version", None)
        if payload_version in TODAY_V2_COMPATIBLE_PAYLOAD_VERSIONS and self.v2 is None:
            if payload_version == TODAY_V2_PREVIOUS_PAYLOAD_VERSION:
                raise ValueError("today.v2 payload requires v2 block")
            raise ValueError("current V2 payload identity requires v2 block")
        if frontend_version in V2_COMPATIBLE_FRONTEND_PAYLOAD_VERSIONS and self.v2 is None:
            if frontend_version == PREVIOUS_V2_FRONTEND_PAYLOAD_VERSION:
                raise ValueError("frontend payload v2 requires v2 block")
            raise ValueError("current frontend V2 identity requires v2 block")
        if payload_version == TODAY_V2_PAYLOAD_VERSION or frontend_version == V2_FRONTEND_PAYLOAD_VERSION:
            if payload_version != TODAY_V2_PAYLOAD_VERSION or frontend_version != V2_FRONTEND_PAYLOAD_VERSION:
                raise ValueError("current V2 identity requires exact payload/frontend version pair")
            if self.v2 is None or self.v2.audit.horizon_pipeline is None:
                raise ValueError("current V2 identity requires horizon pipeline audit")
            if self.v2.audit.payload_version != payload_version:
                raise ValueError("current V2 audit payload version must match meta")
        if payload_version == TODAY_V2_PREVIOUS_PAYLOAD_VERSION and frontend_version == PREVIOUS_V2_FRONTEND_PAYLOAD_VERSION:
            return self
        return self
# END_BLOCK: TODAY_PAYLOAD
