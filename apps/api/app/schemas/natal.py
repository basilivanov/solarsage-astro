# AI_HEADER
# module: M-CONTRACTS.natal
# canon: docs/GRACE_CANON.md §6; docs/06_*.md; docs/work/2026-06-10_natal_full_report_cache_TZ.md
# wave: W-1.1B, W-NATAL-FULL
# purpose: Natal payload schemas — preview, full report, blocks, context.
#          Block list is deliberately tolerant on the frontend, but on the
#          server we keep the discriminated union strict — unknown blocks
#          are a server bug.

# START_MODULE_CONTRACT: M-CONTRACTS.natal
# purpose: Define all natal-related schemas:
#   - Block variants: paragraph, lead, heading, list, callout, pros_cons,
#     quote, divider, highlights, bullets.
#   - NatalSection: titled section containing blocks.
#   - NatalPayload: legacy full reading response.
#   - NatalPreviewRead: preview endpoint response.
#   - NatalReportRead: full report endpoint response.
#   - NatalReportSectionRead: single section of a report.
#   - NatalContextData: deterministic chart context for LLM input.
#   - Sidecar validation schemas.
# invariants:
#   - meta.schema_version is "natal/v1".
#   - The TS side keeps a tolerant `{ type: string; [k: string]: unknown }`
#     fallback for forward-compat; the Python side does NOT — it must
#     refuse to emit any block not listed here. New block types require
#     a wave + contract_version bump.
#   - Natal report sections use the 8 required section ids:
#     portrait, ascendant, rulers, aspects, spheres, planets, shadow, synthesis.
# emits: nothing.
# consumes: schemas._base.CamelModel.
# END_MODULE_CONTRACT: M-CONTRACTS.natal

# START_BLOCK: NATAL_BLOCKS
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from ._base import CamelModel


class ParagraphBlock(CamelModel):
    type: Literal["paragraph"]
    text: str


class LeadBlock(CamelModel):
    type: Literal["lead"]
    text: str


class HeadingBlock(CamelModel):
    type: Literal["heading"]
    text: str
    level: int = 2  # 1-6, default 2


class ListBlock(CamelModel):
    type: Literal["list"]
    items: list[str]
    ordered: bool = False


class CalloutBlock(CamelModel):
    type: Literal["callout"]
    title: str | None = None
    text: str
    tone: Literal["info", "warning", "insight", "positive"] = "info"


class ProsConsItem(CamelModel):
    title: str
    text: str


class ProsConsBlock(CamelModel):
    type: Literal["pros_cons"]
    pros_label: str = "Сильные стороны"
    cons_label: str = "Зоны роста"
    pros: list[ProsConsItem] = []
    cons: list[ProsConsItem] = []


class QuoteBlock(CamelModel):
    type: Literal["quote"]
    text: str
    source: str | None = None


class DividerBlock(CamelModel):
    type: Literal["divider"]


class HighlightItem(CamelModel):
    id: str
    title: str
    text: str
    tone: str | None = None


class HighlightsBlock(CamelModel):
    type: Literal["highlights"]
    items: list[HighlightItem]


class BulletsBlock(CamelModel):
    type: Literal["bullets"]
    items: list[str]


# Closed discriminated union — the server MUST NOT emit blocks not listed here.
NatalBlock = Annotated[
    ParagraphBlock
    | LeadBlock
    | HeadingBlock
    | ListBlock
    | CalloutBlock
    | ProsConsBlock
    | QuoteBlock
    | DividerBlock
    | HighlightsBlock
    | BulletsBlock,
    Field(discriminator="type"),
]
# END_BLOCK: NATAL_BLOCKS

# START_BLOCK: NATAL_PAYLOAD
class NatalSection(CamelModel):
    id: str
    title: str
    summary: str | None = None
    icon_name: str | None = None
    blocks: list[NatalBlock]


class PersonBirth(CamelModel):
    date: str
    time: str | None = None
    place: str | None = None


class Person(CamelModel):
    name: str | None = None
    birth: PersonBirth | None = None


class NatalMeta(CamelModel):
    schema_version: Literal["natal/v1"]
    contract_version: int
    title: str
    subtitle: str | None = None
    generated_at: str
    calculation_version: int | None = None
    interpretation_version: int | None = None
    person: Person | None = None


class NatalPayload(CamelModel):
    meta: NatalMeta
    sections: list[NatalSection]


class NatalCalculationStats(CamelModel):
    planets_count: int = 0
    houses_count: int = 0
    aspects_count: int = 0
    spheres_count: int = 0
    special_points_count: int = 0
    scoring_factors_count: int = 0
    dignity_factors_count: int = 0
    total_factors_count: int = 0
    display_label: str = ""


class NatalHighlight(CamelModel):
    id: str
    title: str
    value: str
    description: str | None = None


class NatalSpherePreview(CamelModel):
    id: str
    title: str
    score: float
    rank: int
    description: str


class NatalPlanetPreview(CamelModel):
    id: str
    name: str
    sign: str | None = None
    house: int | str | None = None
    score: float | None = None
    description: str


class NatalChapterPreview(CamelModel):
    id: str
    eyebrow: str
    title: str
    locked: bool = True
    description: str


class NatalPreviewMeta(CamelModel):
    name: str | None = None
    birth_date: str
    birth_time: str | None = None
    birth_city: str | None = None
    house_system: str | None = None
    asc_sign: str | None = None
    asc_degree: float | None = None
    gender: Literal["male", "female"]


class NatalPreviewRead(CamelModel):
    meta: NatalPreviewMeta
    highlights: list[NatalHighlight] = []
    spheres: list[NatalSpherePreview] = []
    planets: list[NatalPlanetPreview] = []
    chapters: list[NatalChapterPreview] = []
    personal_hook: str = ""
    calculation_stats: NatalCalculationStats
    sales_bullets: list[str] = []
    full_report_available: bool = False
    full_report_price_kopecks: int = 99900
# END_BLOCK: NATAL_PAYLOAD

# START_BLOCK: NATAL_REPORT_SCHEMAS
class NatalReportMeta(CamelModel):
    """Metadata for a persisted full natal report."""
    user_name: str | None = None
    birth_date: str | None = None
    birth_time: str | None = None
    birth_place: str | None = None
    house_system: str = "Placidus"
    context_hash: str | None = None
    prompt_version: str = "1"


class NatalReportSectionRead(CamelModel):
    """One section of a persisted full natal report."""
    id: str
    title: str
    summary: str | None = None
    blocks: list[NatalBlock]


class NatalReportRead(CamelModel):
    """Full natal report response — the main read model for GET /api/natal/report/{id}."""
    id: str
    status: Literal["PENDING", "GENERATING", "READY", "FAILED_RETRYABLE", "FAILED_PERMANENT"]
    access_state: Literal["FREE_PREVIEW", "UNLOCKED", "INTERNAL_TEST", "BLOCKED"] = "FREE_PREVIEW"
    meta: NatalReportMeta
    sections: list[NatalReportSectionRead] = []
    error_code: str | None = None
    error_message: str | None = None
    created_at: str | None = None
    completed_at: str | None = None


class NatalGenerateRequest(CamelModel):
    """Request body for POST /api/natal/generate."""
    force_regenerate: bool = False


class NatalGenerateResponse(CamelModel):
    """Response body for POST /api/natal/generate."""
    report_id: str
    status: Literal["PENDING", "GENERATING", "READY", "FAILED_RETRYABLE", "FAILED_PERMANENT"]
    sections_available: bool = False
    error_code: str | None = None
    error_message: str | None = None
# END_BLOCK: NATAL_REPORT_SCHEMAS

# START_BLOCK: NATAL_CONTEXT_SCHEMAS
class NatalChartPlanet(CamelModel):
    """Planet position in natal chart."""
    name: str
    sign: str
    degree: float
    house: int | None = None
    retrograde: bool = False
    longitude: float


class NatalChartAngle(CamelModel):
    """Angle in natal chart (ASC, MC, etc.)."""
    name: str
    sign: str
    degree: float
    longitude: float


class NatalChartHouse(CamelModel):
    """House cusp in natal chart."""
    number: int
    sign: str
    degree: float
    longitude: float


class NatalChartAspect(CamelModel):
    """Aspect between two chart points."""
    planet_a: str
    planet_b: str
    aspect_type: str
    orb: float
    applying: bool | None = None


class NatalChartSpecialPoint(CamelModel):
    """Special point in natal chart (North Node, Lilith, etc.)."""
    name: str
    sign: str
    degree: float
    longitude: float
    house: int | None = None


class ElementsBalance(CamelModel):
    """Element/modalities balance in the chart."""
    fire: float = 0.0
    earth: float = 0.0
    air: float = 0.0
    water: float = 0.0


class ModalitiesBalance(CamelModel):
    """Modalities balance in the chart."""
    cardinal: float = 0.0
    fixed: float = 0.0
    mutable: float = 0.0


class NatalContextData(CamelModel):
    """Deterministic chart context — the single source of truth for preview/day/report.
    This is what gets persisted in NatalChartCache.normalized_context_json."""
    angles: list[NatalChartAngle] = []
    planets: list[NatalChartPlanet] = []
    houses: list[NatalChartHouse] = []
    aspects: list[NatalChartAspect] = []
    special_points: list[NatalChartSpecialPoint] = []
    elements_balance: ElementsBalance = ElementsBalance()
    modalities_balance: ModalitiesBalance = ModalitiesBalance()
    house_system: str = "Placidus"
    sphere_scores: dict[str, float] = {}
    top_signals: list[dict] = []
    dominants: list[str] = []
# END_BLOCK: NATAL_CONTEXT_SCHEMAS

# START_BLOCK: SIDECAR_VALIDATION_SCHEMAS
from pydantic import model_validator


class SolarSagePlanetPosition(CamelModel):
    """Pydantic schema for a single planet in SolarSage natal response."""
    name: str
    longitude: float
    sign: str
    house: int | None = None
    retrograde: bool = False
    speed: float | None = None
    latitude: float | None = None


class SolarSageHouseCusp(CamelModel):
    """Pydantic schema for a house cusp in SolarSage natal response."""
    number: int
    longitude: float = Field(..., alias="cusp")
    sign: str


class SolarSageSpecialPoint(CamelModel):
    """Pydantic schema for a special point in SolarSage natal response."""
    name: str
    longitude: float
    sign: str
    house: int | None = None


class SolarSageNatalResponse(CamelModel):
    """Pydantic schema for the full SolarSage /v1/natal response.
    Validates raw sidecar output before it enters business logic.

    planets and houses are required and must be non-empty — a natal chart
    without planets or houses is invalid, not just empty.
    special_points is optional (some house systems may not return extra points).
    """
    house_system: str = "Placidus"
    planets: list[SolarSagePlanetPosition]
    houses: list[SolarSageHouseCusp]
    special_points: list[SolarSageSpecialPoint] = []

    @model_validator(mode="after")
    def _validate_non_empty(self) -> "SolarSageNatalResponse":
        """Reject empty planets/houses — these indicate a broken sidecar response."""
        if not self.planets:
            raise ValueError("SolarSage natal response must contain at least one planet")
        if not self.houses:
            raise ValueError("SolarSage natal response must contain at least one house cusp")
        return self


class SolarSageTransitPlanet(CamelModel):
    """Pydantic schema for a single transit planet."""
    name: str
    longitude: float
    sign: str
    retrograde: bool = False
    speed: float | None = None
    latitude: float | None = None


class SolarSageTransitsResponse(CamelModel):
    """Pydantic schema for the full SolarSage /v1/transits response.

    planets is required and must be non-empty — transit data without
    any planets is invalid.
    """
    target_jd: float | None = None
    planets: list[SolarSageTransitPlanet]

    @model_validator(mode="after")
    def _validate_non_empty(self) -> "SolarSageTransitsResponse":
        """Reject empty transit planets — indicates a broken sidecar response."""
        if not self.planets:
            raise ValueError("SolarSage transits response must contain at least one planet")
        return self
# END_BLOCK: SIDECAR_VALIDATION_SCHEMAS
