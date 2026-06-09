# AI_HEADER
# module: M-CONTRACTS.natal
# canon: docs/GRACE_CANON.md §6; docs/06_*.md
# wave: W-1.1B
# purpose: Natal payload. Mirrors packages/contracts/natal.ts. Block list is
#          deliberately tolerant on the frontend, but on the server we keep
#          the discriminated union strict — unknown blocks are a server bug.

# START_MODULE_CONTRACT: M-CONTRACTS.natal
# purpose: Define NatalSection and NatalPayload, plus the closed set of
#          block variants (paragraph | bullets | highlights | quote).
# invariants:
#   - meta.schema_version is "natal/v1".
#   - The TS side keeps a tolerant `{ type: string; [k: string]: unknown }`
#     fallback for forward-compat; the Python side does NOT — it must
#     refuse to emit any block not listed here. New block types require
#     a wave + contract_version bump.
# emits: nothing.
# consumes: schemas._base.CamelModel.
# END_MODULE_CONTRACT

# START_MODULE_MAP: M-CONTRACTS.natal
# - ParagraphBlock, BulletsBlock, HighlightItem, HighlightsBlock, QuoteBlock.
# - NatalBlock: closed union of the four block variants.
# - NatalSection: titled section containing blocks.
# - NatalMeta: schema versioning + person bio.
# - PersonBirth, Person.
# - NatalPayload: top-level response.
# END_MODULE_MAP

# START_BLOCK: NATAL_BLOCKS
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from ._base import CamelModel


class ParagraphBlock(CamelModel):
    type: Literal["paragraph"]
    text: str


class BulletsBlock(CamelModel):
    type: Literal["bullets"]
    items: list[str]


class HighlightItem(CamelModel):
    id: str
    title: str
    text: str
    tone: str | None = None


class HighlightsBlock(CamelModel):
    type: Literal["highlights"]
    items: list[HighlightItem]


class QuoteBlock(CamelModel):
    type: Literal["quote"]
    text: str
    source: str | None = None


NatalBlock = Annotated[
    ParagraphBlock | BulletsBlock | HighlightsBlock | QuoteBlock,
    Field(discriminator="type"),
]
# END_BLOCK: NATAL_BLOCKS

# START_BLOCK: NATAL_PAYLOAD
class NatalSection(CamelModel):
    id: str
    title: str
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
