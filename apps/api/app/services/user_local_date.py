# ############################################################################
# AI_HEADER: MODULE_USER_LOCAL_DATE — resolve a user's current local calendar date.
# ROLE: Pure timezone-aware date resolver for future day/calendar consumers.
# ############################################################################

# START_MODULE_CONTRACT: M-USER-LOCAL-DATE
# purpose: Convert an aware instant to the user's local calendar date using
#   current_tz, then birth_tz, then UTC.
# owns:
#   - apps/api/app/services/user_local_date.py
# inputs: User-like object with optional profile.current_tz/profile.birth_tz and
#   a timezone-aware datetime.
# outputs: A date in the selected IANA timezone.
# dependencies: datetime and zoneinfo from the Python standard library only.
# side_effects: none; does not read clocks, mutate profiles, or log values.
# emitted_logs: none
# invariants:
#   - naive datetimes fail closed with a stable domain error;
#   - an invalid selected timezone never falls back to UTC;
#   - timezone selection priority is current_tz → birth_tz → UTC.
# failure_policy: raises UserLocalDateError with a safe stable code.
# END_MODULE_CONTRACT: M-USER-LOCAL-DATE

# START_MODULE_MAP: M-USER-LOCAL-DATE
# public_entrypoints:
#   - UserLocalDateError
#   - resolve_user_local_date
# semantic_blocks:
#   - USER_LOCAL_DATE_RESOLUTION: timezone selection and aware conversion
# owned_tests:
#   - apps/api/tests/test_user_local_date.py
# END_MODULE_MAP: M-USER-LOCAL-DATE

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class _ProfileLike(Protocol):
    current_tz: str | None
    birth_tz: str | None


class _UserLike(Protocol):
    profile: _ProfileLike | None


class UserLocalDateError(ValueError):
    """Stable, safe domain error for local-date resolution failures."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


# START_BLOCK: USER_LOCAL_DATE_RESOLUTION
def _selected_timezone(user: _UserLike) -> str:
    # START_FUNCTION_CONTRACT: F-M-USER-LOCAL-DATE.selected_timezone
    # purpose: Select the profile timezone according to the canonical priority.
    # inputs: user — object with optional profile and timezone fields.
    # returns: A non-empty timezone key, defaulting to UTC.
    # side_effects: none; reads profile fields only.
    # emitted_logs: none
    # error_behavior: Invalid non-empty keys are returned for caller validation.
    # END_FUNCTION_CONTRACT: F-M-USER-LOCAL-DATE.selected_timezone
    profile = user.profile
    if profile is None:
        return "UTC"
    return profile.current_tz or profile.birth_tz or "UTC"


def resolve_user_local_date(user: _UserLike, now: datetime) -> date:
    # START_FUNCTION_CONTRACT: F-M-USER-LOCAL-DATE.resolve_user_local_date
    # purpose: Resolve the current calendar date in the user's selected timezone.
    # inputs: user — profile timezone source; now — timezone-aware instant.
    # returns: date corresponding to now in current_tz, birth_tz, or UTC.
    # side_effects: none; does not read system clocks, mutate user, or log.
    # emitted_logs: none
    # error_behavior: Raises UserLocalDateError for naive now or invalid timezone.
    # END_FUNCTION_CONTRACT: F-M-USER-LOCAL-DATE.resolve_user_local_date
    if now.tzinfo is None or now.utcoffset() is None:
        raise UserLocalDateError("now_must_be_aware")

    timezone_key = _selected_timezone(user)
    try:
        selected_zone = ZoneInfo(timezone_key)
    except (TypeError, ValueError, ZoneInfoNotFoundError):
        raise UserLocalDateError("invalid_timezone") from None

    return now.astimezone(selected_zone).date()
# END_BLOCK: USER_LOCAL_DATE_RESOLUTION
