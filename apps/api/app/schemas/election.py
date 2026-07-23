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
from pydantic import Field

from app.schemas._base import CamelModel


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
