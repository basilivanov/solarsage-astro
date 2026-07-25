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
# dependencies: none
# side_effects: none
# emitted_logs: none
# invariants: none
# failure_policy: none
# END_MODULE_CONTRACT: M-SCHEMAS-ELECTION

# START_MODULE_MAP: M-SCHEMAS-ELECTION
# public_entrypoints:
#   - ElectionDayNote
#   - ElectionSearchCreateRequest
#   - ElectionSearchRead
# semantic_blocks: none
# owned_tests: none
# END_MODULE_MAP: M-SCHEMAS-ELECTION

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
    fallback_notes: dict[str, str] | None = None,
) -> ElectionNarrative:
    # START_FUNCTION_CONTRACT: F-M-SCHEMAS-ELECTION.validate_election_narrative
    # purpose: Validate LLM output against ElectionNarrative schema and dates alignment.
    # inputs: narrative_data (dict), expected_best_dates (list[str]),
    #   expected_avoid_dates (list[str]), fallback_notes (dict date->note from
    #   engine facts, used to fill dates a weak model omitted — never fabricated).
    # returns: ElectionNarrative with notes aligned to expected dates in expected order.
    # error_behavior: raises ValueError on schema error or unknown dates in notes.
    # END_FUNCTION_CONTRACT: F-M-SCHEMAS-ELECTION.validate_election_narrative
    try:
        parsed = ElectionNarrative.model_validate(narrative_data)
    except Exception as exc:
        raise ValueError(f"Election narrative schema validation failed: {exc}") from exc

    def _align(notes: list[ElectionDayNote], expected: list[str], kind: str) -> list[ElectionDayNote]:
        unknown = [n.date for n in notes if n.date not in expected]
        if unknown:
            raise ValueError(f"Election {kind} contain unknown dates {unknown}, expected {expected}")
        by_date = {n.date: n for n in notes}
        aligned: list[ElectionDayNote] = []
        for d in expected:
            if d in by_date:
                aligned.append(by_date[d])
            elif fallback_notes and d in fallback_notes:
                aligned.append(ElectionDayNote(date=d, note=fallback_notes[d]))
            else:
                raise ValueError(f"Election {kind} missing required date {d}")
        return aligned

    return ElectionNarrative(
        hero_reason=parsed.hero_reason,
        hero_personal=parsed.hero_personal,
        hero_plain=parsed.hero_plain,
        hero_hours=parsed.hero_hours,
        day_notes=_align(parsed.day_notes, expected_best_dates, "day_notes"),
        avoid_notes=_align(parsed.avoid_notes, expected_avoid_dates, "avoid_notes"),
    )


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
