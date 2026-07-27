# AI_HEADER: MODULE_CONTRACTS
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
# END_MODULE_CONTRACT: M-CONTRACTS

# START_MODULE_MAP: M-CONTRACTS
# - access: UserAccessState, AccessSummary
# - today: TodayPayload + every nested model and Literal alias
# - calendar: CalendarPayload, CalendarDay, CalendarMeta, AllowedRange
# - natal: NatalPayload, NatalSection, every block variant
# END_MODULE_MAP: M-CONTRACTS

# START_BLOCK: SCHEMAS_REEXPORTS
from __future__ import annotations

from .access import AccessSummary, UserAccessState
from .auth import AuthError, AuthSession, TelegramAuthRequest
from .calendar import (
    AllowedRange as AllowedRange,
    CalendarDay as CalendarDay,
    CalendarMeta as CalendarMeta,
    CalendarPayload as CalendarPayload,
)
from .checkin import (
    CheckinCreate,
    CheckinMetrics,
    CheckinResponse,
    YesterdayCheckinResponse,
)
from .day import RelativeDayStatusRead, RelativeStatusBaseline
from .profile import BirthData, LocationData, ProfileRead, ProfileWrite
from .horary import (
    HoraryQuestionCreate,
    HoraryQuestionRead,
    HoraryAnswerRead,
    HoraryQuotaRead,
)
from .natal import (
    BulletsBlock as BulletsBlock,
    HighlightItem as HighlightItem,
    HighlightsBlock as HighlightsBlock,
    NatalBlock as NatalBlock,
    NatalMeta as NatalMeta,
    NatalPayload as NatalPayload,
    NatalSection as NatalSection,
    ParagraphBlock as ParagraphBlock,
    Person as Person,
    PersonBirth as PersonBirth,
    QuoteBlock as QuoteBlock,
)
from .today import (
    ConcreteAdviceDetails,
    ContentAccessReason,
    ContentAccessState,
    ConvergenceEvidence,
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
    TodayImportantEvent,
)
from .today_horizons import (
    TodayV2ClaimKind,
    TodayV2GroundedItem,
    TodayV2GuidanceMode,
    TodayV2Horizon,
    TodayV2HorizonActions,
    TodayV2HorizonId,
    TodayV2HorizonIntro,
    TodayV2HorizonTiming,
    TodayV2HorizonTone,
    TodayV2HorizonsBlock,
    TodayV2Manifestation,
    TodayV2ProductSphereKey,
    TodayV2Provenance,
    TodayV2TechniqueExplanation,
    TodayV2TimingPrecision,
    TodayV2TimingState,
)
from .activation import (
    ActivationEvidence,
    ActivationLayer,
    ActivationTargetType,
    ActivationPolarity,
    ActivationPhase,
)
from .scoring_v2 import (
    ScoringV2Result,
    SphereScoreV2,
    SphereContribution,
)

__all__ = [
    # access
    "AccessSummary",
    "UserAccessState",
    # auth (W-1.2)
    "AuthError",
    "AuthSession",
    "TelegramAuthRequest",
    # check-in
    "CheckinCreate",
    "CheckinMetrics",
    "CheckinResponse",
    "YesterdayCheckinResponse",
    # relative day status
    "RelativeDayStatusRead",
    "RelativeStatusBaseline",
    # profile (W-1.2)
    "BirthData",
    "LocationData",
    "ProfileRead",
    "ProfileWrite",
    # horary (W-HORARY)
    "HoraryQuestionCreate",
    "HoraryQuestionRead",
    "HoraryAnswerRead",
    "HoraryQuotaRead",
    # today
    "ConcreteAdviceDetails",
    "ContentAccessReason",
    "ContentAccessState",
    "ConvergenceEvidence",
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
    "TodayImportantEvent",
    "TodayV2ClaimKind",
    "TodayV2GroundedItem",
    "TodayV2GuidanceMode",
    "TodayV2Horizon",
    "TodayV2HorizonActions",
    "TodayV2HorizonId",
    "TodayV2HorizonIntro",
    "TodayV2HorizonTiming",
    "TodayV2HorizonTone",
    "TodayV2HorizonsBlock",
    "TodayV2Manifestation",
    "TodayV2ProductSphereKey",
    "TodayV2Provenance",
    "TodayV2TechniqueExplanation",
    "TodayV2TimingPrecision",
    "TodayV2TimingState",
    # activation (W1)
    "ActivationEvidence",
    "ActivationLayer",
    "ActivationTargetType",
    "ActivationPolarity",
    "ActivationPhase",
    # scoring v2 (W1 contract skeleton)
    "ScoringV2Result",
    "SphereScoreV2",
    "SphereContribution",
]
# END_BLOCK: SCHEMAS_REEXPORTS
