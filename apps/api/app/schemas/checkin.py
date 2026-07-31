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
# dependencies: M-SCHEMAS-TODAY-CONVERGENCE (CanonicalSphere)
# side_effects: none
# emitted_logs: none
# invariants: observed_spheres is null or a unique list of at most 12 canonical spheres.
# failure_policy: none
# END_MODULE_CONTRACT: M-SCHEMAS-CHECKIN

# START_MODULE_MAP: M-SCHEMAS-CHECKIN
# public_entrypoints:
#   - CheckinCreate
#   - CheckinResponse
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_checkin.py
#   - apps/api/tests/test_checkin_endpoints.py
#   - apps/api/tests/test_checkin_snapshot_lineage.py
# END_MODULE_MAP: M-SCHEMAS-CHECKIN

from __future__ import annotations

from datetime import date, datetime
import uuid
from typing import Literal

from pydantic import Field, model_validator

from app.schemas._base import CamelModel
from app.schemas.today_convergence import CanonicalSphere


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
    observed_spheres: list[CanonicalSphere] | None = Field(None, max_length=12)

    # START_BLOCK: CHECKIN_OBSERVED_SPHERES
    @model_validator(mode="after")
    def validate_observed_spheres(self) -> "CheckinCreate":
        # START_FUNCTION_CONTRACT: F-M-SCHEMAS-CHECKIN.validate_observed_spheres
        # purpose: Reject duplicate canonical observed sphere answers.
        # inputs: self.observed_spheres — optional canonical sphere list.
        # returns: CheckinCreate — unchanged validated model.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: raises ValueError for duplicate values.
        # END_FUNCTION_CONTRACT: F-M-SCHEMAS-CHECKIN.validate_observed_spheres
        if self.observed_spheres is not None and len(self.observed_spheres) != len(set(self.observed_spheres)):
            raise ValueError("observed_spheres must contain unique canonical spheres")
        return self
    # END_BLOCK: CHECKIN_OBSERVED_SPHERES


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
    observed_spheres: list[CanonicalSphere] | None = None
    forecast_snapshot_id: uuid.UUID | None = None
    prediction_seen_at: datetime | None = None
    prediction_seen_surface: Literal["day", "lookahead"] | None = None


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
