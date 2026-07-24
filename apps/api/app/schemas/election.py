# ############################################################################
# AI_HEADER: MODULE_SCHEMAS_ELECTION
# ROLE: Pydantic schemas for election endpoints
# DEPENDENCIES: pydantic, app.schemas.camel
# GRACE_ANCHORS: []
# ############################################################################

# START_MODULE_CONTRACT: M-SCHEMAS-ELECTION
# purpose: Request and response models for /api/election routes.
# owns:
#   - apps/api/app/schemas/election.py
# inputs: request dicts
# outputs: validated models
# END_MODULE_CONTRACT: M-SCHEMAS-ELECTION

from __future__ import annotations

from datetime import date, datetime
import uuid
from typing import Any, Literal
from pydantic import BaseModel, Field

from app.schemas._base import CamelModel


class ElectionDayNote(BaseModel):
    date: str
    note: str


class ElectionNarrative(BaseModel):
    hero_reason: str
    hero_personal: str
    hero_plain: str
    hero_hours: str
    day_notes: list[ElectionDayNote]
    avoid_notes: list[ElectionDayNote]


def validate_election_narrative(
    narrative_data: dict[str, Any],
    expected_best_dates: list[str],
    expected_avoid_dates: list[str],
) -> ElectionNarrative:
    # START_FUNCTION_CONTRACT: F-M-SCHEMAS-ELECTION.validate_election_narrative
    # purpose: Validate LLM output against ElectionNarrative schema and dates alignment.
    # inputs: narrative_data (dict), expected_best_dates (list[str]), expected_avoid_dates (list[str])
    # returns: ElectionNarrative
    # error_behavior: raises ValueError on validation error or date mismatch
    # END_FUNCTION_CONTRACT: F-M-SCHEMAS-ELECTION.validate_election_narrative
    try:
        parsed = ElectionNarrative.model_validate(narrative_data)
    except Exception as exc:
        raise ValueError(f"Election narrative schema validation failed: {exc}") from exc

    best_dates_in_narrative = [item.date for item in parsed.day_notes]
    if best_dates_in_narrative != expected_best_dates:
        raise ValueError(
            f"Election day_notes dates {best_dates_in_narrative} do not match expected best_days {expected_best_dates}"
        )

    avoid_dates_in_narrative = [item.date for item in parsed.avoid_notes]
    if avoid_dates_in_narrative != expected_avoid_dates:
        raise ValueError(
            f"Election avoid_notes dates {avoid_dates_in_narrative} do not match expected avoid_days {expected_avoid_dates}"
        )

    return parsed


class ElectionSearchCreateRequest(CamelModel):
    event_type: str = Field(..., description="Event type identifier")
    window_from: date = Field(..., description="Start date (inclusive)")
    window_to: date = Field(..., description="End date (inclusive)")
    idempotency_key: str = Field(..., max_length=80, description="Idempotency key")
    client_timezone: str | None = Field(None, description="Client timezone string")


class ElectionDayReasonRead(CamelModel):
    date: date
    score: int
    label: Literal["great", "good", "ok", "avoid"]
    reasons: list[str]


class ElectionResultRead(CamelModel):
    event: str
    best_days: list[ElectionDayReasonRead]
    avoid_days: list[ElectionDayReasonRead]


class ElectionSearchRead(CamelModel):
    id: uuid.UUID
    event_type: str
    window_from: date
    window_to: date
    status: Literal["pending", "processing", "done", "failed", "refunded"]
    created_at: datetime
    result: dict[str, Any] | None = None
    public_error_code: str | None = None
    public_error_message: str | None = None
