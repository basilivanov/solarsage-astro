# AI_HEADER
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
# consumes: schemas._base.CamelModel, schemas.access (none directly today —
#           ContentAccessState is local because it differs from AccessSummary).
# END_MODULE_CONTRACT

# START_MODULE_MAP: M-CONTRACTS.today
# - DayStatus: Literal alias.
# - ContentAccessState: per-day/per-reading access object.
# - TopFlag, TopFlagHint: highlight cards for the day.
# - WhyParagraph, WhyBullets, WhyBlock, WhySection: "why this happens" body.
# - WeekStripDay: 7-day strip item.
# - MicrocopyItem, YesterdayEcho: ancillary blocks.
# - DayQuality, TodayMeta, TodayAction, ReadingBody, WhyThisHappens: helpers.
# - TodayPayload: top-level response.
# END_MODULE_MAP

# START_BLOCK: TODAY_PRIMITIVES
from __future__ import annotations

from typing import Literal

from pydantic import Field

from ._base import CamelModel

DayStatus = Literal["supportive", "steady", "tense"]

ContentAccessReason = Literal[
    "active_referral_days",
    "active_subscription",
    "expired_access",
    "outside_access_window",
]


class ContentAccessState(CamelModel):
    state: Literal["full", "preview", "locked"]
    reason: ContentAccessReason | None = None
    referral_days_left: int | None = None
    subscription_active: bool | None = None
    access_until: str | None = None


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

# START_BLOCK: TODAY_PAYLOAD
class TodayMeta(CamelModel):
    schema_version: Literal["today/v1"]
    contract_version: int
    calculation_version: int
    normalization_version: int
    scoring_version: int
    prompt_version: int
    content_version: int
    generated_at: str


class TodayPayload(CamelModel):
    meta: TodayMeta
    date: str
    title: str
    subtitle: str | None = None
    headline: str
    access: ContentAccessState
    day_status: DayStatus
    day_quality: DayQuality | None = None
    top_flags: list[TopFlag]
    reading: ReadingBody
    why_this_happens: WhyThisHappens
    week_strip: list[WeekStripDay]
    microcopy: list[MicrocopyItem]
    yesterday_echo: YesterdayEcho | None = None
    actions: list[TodayAction] | None = None
# END_BLOCK: TODAY_PAYLOAD
