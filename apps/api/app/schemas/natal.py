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
# END_BLOCK: NATAL_PAYLOAD
