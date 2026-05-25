# AI_HEADER
# module: M-CONTRACTS
# canon: docs/GRACE_CANON.md §6
# wave: W-1.1B (Option B — Pydantic is source of truth)
# purpose: Public re-export surface for all wire schemas. This is what
#          FastAPI handlers and the openapi-export script import from.

# START_MODULE_CONTRACT: M-CONTRACTS
# purpose: Single import point for every public schema. Anything not
#          re-exported here is internal to apps/api/app/schemas/* and must
#          not be referenced by routes, services, or the export script.
# invariants:
#   - Adding a new public schema requires (a) a model in this package and
#     (b) an export here. Forgetting (b) means the model never reaches
#     openapi.json, which CI's contracts:check will catch.
#   - This module re-exports types only. No runtime side effects.
# emits: nothing.
# consumes: schemas.access, schemas.today, schemas.calendar, schemas.natal.
# END_MODULE_CONTRACT

# START_MODULE_MAP: M-CONTRACTS
# - access: UserAccessState, AccessSummary
# - today: TodayPayload + every nested model and Literal alias
# - calendar: CalendarPayload, CalendarDay, CalendarMeta, AllowedRange
# - natal: NatalPayload, NatalSection, every block variant
# END_MODULE_MAP

# START_BLOCK: SCHEMAS_REEXPORTS
from __future__ import annotations

from .access import AccessSummary, UserAccessState
from .auth import AuthError, AuthSession, TelegramAuthRequest
from .calendar import AllowedRange, CalendarDay, CalendarMeta, CalendarPayload
from .profile import BirthData, ProfileRead, ProfileWrite
from .natal import (
    BulletsBlock,
    HighlightItem,
    HighlightsBlock,
    NatalBlock,
    NatalMeta,
    NatalPayload,
    NatalSection,
    ParagraphBlock,
    Person,
    PersonBirth,
    QuoteBlock,
)
from .today import (
    ContentAccessReason,
    ContentAccessState,
    DayQuality,
    DayStatus,
    MicrocopyItem,
    MicrocopyScope,
    MicrocopyTone,
    ReadingBody,
    TodayAction,
    TodayMeta,
    TodayPayload,
    TopFlag,
    TopFlagHint,
    WeekStripDay,
    WhyBlock,
    WhyBullets,
    WhyParagraph,
    WhySection,
    WhyThisHappens,
    YesterdayEcho,
    YesterdayTransition,
)

__all__ = [
    # access
    "AccessSummary",
    "UserAccessState",
    # auth (W-1.2)
    "AuthError",
    "AuthSession",
    "TelegramAuthRequest",
    # profile (W-1.2)
    "BirthData",
    "ProfileRead",
    "ProfileWrite",
    # today
    "ContentAccessReason",
    "ContentAccessState",
    "DayQuality",
    "DayStatus",
    "MicrocopyItem",
    "MicrocopyScope",
    "MicrocopyTone",
    "ReadingBody",
    "TodayAction",
    "TodayMeta",
    "TodayPayload",
    "TopFlag",
    "TopFlagHint",
    "WeekStripDay",
    "WhyBlock",
    "WhyBullets",
    "WhyParagraph",
    "WhySection",
    "WhyThisHappens",
    "YesterdayEcho",
    "YesterdayTransition",
    # calendar
    "AllowedRange",
    "CalendarDay",
    "CalendarMeta",
    "CalendarPayload",
    # natal
    "BulletsBlock",
    "HighlightItem",
    "HighlightsBlock",
    "NatalBlock",
    "NatalMeta",
    "NatalPayload",
    "NatalSection",
    "ParagraphBlock",
    "Person",
    "PersonBirth",
    "QuoteBlock",
]
# END_BLOCK: SCHEMAS_REEXPORTS
