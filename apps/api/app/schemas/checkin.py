# ############################################################################
# AI_HEADER: MODULE_SCHEMAS_CHECKIN
# ROLE: Pydantic schemas for checkin endpoints.
# DEPENDENCIES: pydantic, app.schemas._base
# ############################################################################

# START_MODULE_CONTRACT: M-SCHEMAS-CHECKIN
# purpose: Request and response models for /api/checkin routes.
# owns:
#   - apps/api/app/schemas/checkin.py
# inputs: request dicts
# outputs: validated models
# dependencies: none
# side_effects: none
# emitted_logs: none
# invariants: none
# failure_policy: none
# END_MODULE_CONTRACT: M-SCHEMAS-CHECKIN

# START_MODULE_MAP: M-SCHEMAS-CHECKIN
# public_entrypoints:
#   - CheckinCreate
#   - CheckinResponse
# semantic_blocks: none
# owned_tests: none
# END_MODULE_MAP: M-SCHEMAS-CHECKIN

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.schemas._base import CamelModel


CheckinMood = Literal[1, 2, 3, 4, 5]
CheckinAccuracy = Literal[1, 2, 3]
CheckinEnergy = Literal[1, 2, 3, 4, 5]


class CheckinCreate(CamelModel):
    target_date: date
    mood: CheckinMood
    accuracy: CheckinAccuracy | None = None
    energy: CheckinEnergy | None = None
    tags: list[str] = Field(default_factory=list)
    note: str | None = Field(None, max_length=500)


class CheckinResponse(CamelModel):
    id: int
    target_date: date
    mood: int = Field(ge=1, le=5)
    accuracy: int | None = Field(None, ge=1, le=3)
    energy: int | None = Field(None, ge=1, le=5)
    tags: list[str]
    note: str | None
    streak: int = Field(ge=1)
    filled_at: datetime | None
    created_at: datetime


class YesterdayCheckinResponse(CamelModel):
    had_checkin: bool
    checkin: CheckinResponse | None


class CheckinMetrics(CamelModel):
    total_checkins: int = Field(ge=0)
    current_streak: int = Field(ge=0)
    longest_streak: int = Field(ge=0)
    average_mood: float
    average_energy: float | None
    average_accuracy: float | None
    mood_distribution: dict[str, int]
    accuracy_distribution: dict[str, int]
    tag_frequency: dict[str, int]
