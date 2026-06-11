# AI_HEADER: MODULE_CONTRACTS_CALENDAR
# module: M-CONTRACTS.calendar
# canon: docs/GRACE_CANON.md §6
# wave: W-1.1B
# purpose: Calendar payload. Mirrors packages/contracts/calendar.ts.

# START_MODULE_CONTRACT: M-CONTRACTS.calendar
# purpose: Define CalendarDay and CalendarPayload as wire-stable schemas.
# invariants:
#   - month is YYYY-MM string.
#   - allowedRange.from/to are ISO date strings.
#   - day.date is ISO date string.
#   - meta.schema_version is "calendar/v1".
# emits: nothing.
# consumes: schemas._base.CamelModel, schemas.today.{DayStatus,ContentAccessState}.
# END_MODULE_CONTRACT: M-CONTRACTS.calendar

# START_MODULE_MAP: M-CONTRACTS.calendar
# - CalendarDay: per-cell data.
# - CalendarMeta: schema versioning header.
# - AllowedRange: from/to date pair.
# - CalendarPayload: top-level response.
# END_MODULE_MAP: M-CONTRACTS.calendar

# START_BLOCK: CALENDAR_TYPES
from __future__ import annotations

from typing import Literal

from ._base import CamelModel
from .today import ContentAccessState, DayStatus


class CalendarDay(CamelModel):
    date: str
    day_number: int
    is_current_month: bool
    is_today: bool
    disabled: bool
    day_status: DayStatus | None = None
    access: ContentAccessState | None = None


class CalendarMeta(CamelModel):
    schema_version: Literal["calendar/v1"]
    contract_version: int
    generated_at: str


class AllowedRange(CamelModel):
    from_: str  # serialized as "from" via alias_generator (to_camel('from_') == 'from_'),
    # so we override explicitly below.
    to: str

    model_config = {
        **CamelModel.model_config,
        # Force the wire name "from" without the trailing underscore.
    }


# pydantic v2 alias for the reserved keyword
AllowedRange.model_fields["from_"].alias = "from"
AllowedRange.model_fields["from_"].validation_alias = "from"
AllowedRange.model_fields["from_"].serialization_alias = "from"
AllowedRange.model_rebuild(force=True)


class CalendarPayload(CamelModel):
    meta: CalendarMeta
    month: str
    title: str
    allowed_range: AllowedRange
    days: list[CalendarDay]
# END_BLOCK: CALENDAR_TYPES
