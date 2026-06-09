# ############################################################################
# AI_HEADER: MODULE_PROFILE_SCHEMAS
# ROLE: Pydantic v2 schemas for /api/profile read + write surface (W-1.2).
# DEPENDENCIES: pydantic, app.schemas._base.CamelModel
# GRACE_ANCHORS: [BIRTH_DATA, PROFILE_READ, PROFILE_WRITE]
# ############################################################################

# START_MODULE_CONTRACT: M-PROFILE.schemas
# purpose: Wire-format contracts for GET /api/profile (response) and
#   PUT /api/profile (request body + response). Source of truth for the
#   profile surface; OpenAPI is generated from these.
# owns:
#   - apps/api/app/schemas/profile.py
# outputs:
#   - BirthData, ProfileRead, ProfileWrite
# invariants:
#   - all fields snake_case in Python, camelCase on the wire (CamelModel).
#   - birth_lat ∈ [-90, 90]; birth_lon ∈ [-180, 180].
#   - if either birth_lat or birth_lon is set, BOTH must be set (validator).
#   - birth_tz must be in zoneinfo.available_timezones() if provided.
#   - birthday >= 1900-01-01 if provided.
#   - ProfileRead never echoes tg_user_id, tokens, or other privacy keys.
# non_goals:
#   - no geocoding, no address validation
# END_MODULE_CONTRACT: M-PROFILE.schemas

# START_MODULE_MAP: M-PROFILE.schemas
# public_entrypoints:
#   - BirthData
#   - ProfileRead
#   - ProfileWrite
# semantic_blocks:
#   - BIRTH_DATA: BirthData
#   - PROFILE_READ: ProfileRead
#   - PROFILE_WRITE: ProfileWrite
# owned_tests:
#   - apps/api/tests/test_profile_endpoints.py
# END_MODULE_MAP: M-PROFILE.schemas

from __future__ import annotations

from datetime import date, time
from uuid import UUID
from zoneinfo import available_timezones

from pydantic import Field, field_validator, model_validator

from app.schemas._base import CamelModel

_MIN_BIRTHDAY: date = date(1900, 1, 1)


# START_BLOCK: LOCATION_DATA
class LocationData(CamelModel):
    city: str | None = Field(None, max_length=200)
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)
    tz: str | None = None

    @field_validator("tz")
    @classmethod
    def _validate_tz(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in available_timezones():
            raise ValueError(f"tz {v!r} is not an IANA timezone")
        return v

    @model_validator(mode="after")
    def _check_lat_lon_pair(self) -> "LocationData":
        if (self.lat is None) ^ (self.lon is None):
            raise ValueError("lat and lon must be set together")
        return self
# END_BLOCK: LOCATION_DATA


# START_BLOCK: BIRTH_DATA
class BirthData(CamelModel):
    """Birth-place + birth-time data. Every field is optional (incremental
    onboarding). Validators enforce per-field ranges and lat/lon co-presence.
    """

    birthday: date | None = None
    birth_time: time | None = None
    birth_city: str | None = Field(None, max_length=200)
    birth_lat: float | None = Field(None, ge=-90, le=90)
    birth_lon: float | None = Field(None, ge=-180, le=180)
    birth_tz: str | None = None

    @field_validator("birthday")
    @classmethod
    def _validate_birthday(cls, v: date | None) -> date | None:
        if v is not None and v < _MIN_BIRTHDAY:
            raise ValueError(f"birthday must be >= {_MIN_BIRTHDAY.isoformat()}")
        return v

    @field_validator("birth_tz")
    @classmethod
    def _validate_tz(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in available_timezones():
            raise ValueError(f"birth_tz {v!r} is not an IANA timezone")
        return v

    @model_validator(mode="after")
    def _check_lat_lon_pair(self) -> "BirthData":
        if (self.birth_lat is None) ^ (self.birth_lon is None):
            raise ValueError("birth_lat and birth_lon must be set together")
        return self
# END_BLOCK: BIRTH_DATA


# START_BLOCK: PROFILE_READ
class ProfileRead(CamelModel):
    """Response shape for GET /api/profile. Privacy: NO tg_user_id, NO tokens."""

    user_id: UUID
    first_name: str | None = None
    is_onboarded: bool = False
    birth: BirthData
    current_location: LocationData | None = None
    birthday_location: LocationData | None = None
# END_BLOCK: PROFILE_READ


# START_BLOCK: PROFILE_WRITE
class ProfileWrite(CamelModel):
    """Request body for PUT /api/profile.

    Field-level partial: omitted top-level fields are 'unchanged'. The
    `birth` block is itself a BirthData (also optional fields), so callers
    can update e.g. only `birthCity` by sending `{"birth": {"birthCity": "..."}}`.
    """

    first_name: str | None = Field(None, max_length=120)
    birth: BirthData = Field(default_factory=BirthData)
    current_location: LocationData | None = None
    birthday_location: LocationData | None = None
# END_BLOCK: PROFILE_WRITE
