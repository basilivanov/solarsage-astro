# ############################################################################
# AI_HEADER: MODULE_TESTS_USER_LOCAL_DATE
# ROLE: Unit tests for the pure user local-date resolver.
# DEPENDENCIES: pytest, datetime, app.services.user_local_date
# GRACE_ANCHORS: [USER_LOCAL_DATE_TESTS]
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-USER-LOCAL-DATE
# purpose: Prove timezone priority, aware datetime conversion, DST boundaries,
#   and fail-closed behavior for the user local-date resolver.
# owns:
#   - apps/api/tests/test_user_local_date.py
# inputs: SimpleNamespace user/profile doubles and aware datetime values.
# outputs: Pytest assertions over resolved dates and stable domain errors.
# dependencies:
#   - app.services.user_local_date
# side_effects: none
# emitted_logs: none
# invariants:
#   - Tests never use system clocks or mutate a profile.
# failure_policy: assertion failures propagate through pytest.
# END_MODULE_CONTRACT: M-TESTS-USER-LOCAL-DATE

# START_MODULE_MAP: M-TESTS-USER-LOCAL-DATE
# public_entrypoints:
#   - test_west_of_utc_resolves_previous_local_date
#   - test_east_of_utc_resolves_next_local_date
#   - test_current_timezone_wins_over_birth_timezone
#   - test_birth_timezone_is_used_without_current_timezone
#   - test_utc_is_used_without_profile_timezones
#   - test_dst_transition_keeps_local_date_deterministic
#   - test_dst_date_local_midnight_boundary
#   - test_aware_non_utc_offset_is_normalized
#   - test_naive_now_fails_closed
#   - test_invalid_timezone_fails_closed_without_leaking_profile_value
# semantic_blocks:
#   - USER_LOCAL_DATE_TESTS: resolver behavior and failure contract
# owned_tests:
#   - apps/api/tests/test_user_local_date.py
# END_MODULE_MAP: M-TESTS-USER-LOCAL-DATE

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services.user_local_date import (
    UserLocalDateError,
    resolve_user_local_date,
)


def _user(*, current_tz: str | None = None, birth_tz: str | None = None):
    return SimpleNamespace(
        profile=SimpleNamespace(current_tz=current_tz, birth_tz=birth_tz)
    )


# START_BLOCK: USER_LOCAL_DATE_TESTS
def test_west_of_utc_resolves_previous_local_date() -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.west_of_utc
    # purpose: Prove a UTC instant maps to the previous date west of UTC.
    # inputs: Aware UTC instant and America/Los_Angeles profile timezone.
    # returns: None; assertions prove the resolved date.
    # side_effects: none
    # emitted_logs: none
    # error_behavior: Fails through pytest if date conversion is incorrect.
    # END_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.west_of_utc
    now = datetime(2026, 7, 29, 0, 30, tzinfo=timezone.utc)

    assert resolve_user_local_date(_user(current_tz="America/Los_Angeles"), now) == date(
        2026, 7, 28
    )


def test_east_of_utc_resolves_next_local_date() -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.east_of_utc
    # purpose: Prove a UTC instant maps to the next date east of UTC.
    # inputs: Aware UTC instant and Asia/Tokyo profile timezone.
    # returns: None; assertions prove the resolved date.
    # side_effects: none
    # emitted_logs: none
    # error_behavior: Fails through pytest if date conversion is incorrect.
    # END_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.east_of_utc
    now = datetime(2026, 7, 28, 23, 30, tzinfo=timezone.utc)

    assert resolve_user_local_date(_user(current_tz="Asia/Tokyo"), now) == date(
        2026, 7, 29
    )


def test_current_timezone_wins_over_birth_timezone() -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.current_priority
    # purpose: Prove current_tz wins when it conflicts with birth_tz.
    # inputs: Aware UTC instant and conflicting profile timezones.
    # returns: None; assertions prove current_tz is selected.
    # side_effects: none
    # emitted_logs: none
    # error_behavior: Fails through pytest if priority is incorrect.
    # END_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.current_priority
    now = datetime(2026, 7, 29, 0, 30, tzinfo=timezone.utc)

    assert resolve_user_local_date(
        _user(current_tz="America/Los_Angeles", birth_tz="Asia/Tokyo"), now
    ) == date(2026, 7, 28)


def test_birth_timezone_is_used_without_current_timezone() -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.birth_fallback
    # purpose: Prove birth_tz is selected when current_tz is absent.
    # inputs: Aware UTC instant and birth-only profile timezone.
    # returns: None; assertions prove birth_tz is selected.
    # side_effects: none
    # emitted_logs: none
    # error_behavior: Fails through pytest if fallback priority is incorrect.
    # END_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.birth_fallback
    now = datetime(2026, 7, 28, 23, 30, tzinfo=timezone.utc)

    assert resolve_user_local_date(_user(birth_tz="Asia/Tokyo"), now) == date(
        2026, 7, 29
    )


def test_utc_is_used_without_profile_timezones() -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.utc_fallback
    # purpose: Prove UTC is selected when both profile timezones are absent.
    # inputs: Aware UTC instant and empty profile timezone fields.
    # returns: None; assertions prove UTC fallback.
    # side_effects: none
    # emitted_logs: none
    # error_behavior: Fails through pytest if UTC fallback is incorrect.
    # END_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.utc_fallback
    now = datetime(2026, 7, 28, 23, 30, tzinfo=timezone.utc)

    assert resolve_user_local_date(_user(), now) == date(2026, 7, 28)


def test_dst_transition_keeps_local_date_deterministic() -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.dst_transition
    # purpose: Prove conversion across Berlin's 2026 DST jump remains date-correct.
    # inputs: Aware UTC instants immediately before and after the DST jump.
    # returns: None; assertions prove both instants resolve to the transition date.
    # side_effects: none
    # emitted_logs: none
    # error_behavior: Fails through pytest if zoneinfo conversion mishandles DST.
    # END_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.dst_transition
    before_jump = datetime(2026, 3, 29, 0, 59, tzinfo=timezone.utc)
    after_jump = datetime(2026, 3, 29, 1, 1, tzinfo=timezone.utc)

    assert resolve_user_local_date(_user(current_tz="Europe/Berlin"), before_jump) == date(
        2026, 3, 29
    )
    assert resolve_user_local_date(_user(current_tz="Europe/Berlin"), after_jump) == date(
        2026, 3, 29
    )


def test_dst_date_local_midnight_boundary() -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.dst_midnight
    # purpose: Prove UTC instants around local midnight on the DST transition date.
    # inputs: Aware UTC instants on either side of Europe/Berlin local midnight.
    # returns: None; assertions prove the local date boundary.
    # side_effects: none
    # emitted_logs: none
    # error_behavior: Fails through pytest if local-midnight conversion is incorrect.
    # END_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.dst_midnight
    before_midnight = datetime(2026, 3, 28, 22, 59, tzinfo=timezone.utc)
    after_midnight = datetime(2026, 3, 28, 23, 1, tzinfo=timezone.utc)

    assert resolve_user_local_date(_user(current_tz="Europe/Berlin"), before_midnight) == date(
        2026, 3, 28
    )
    assert resolve_user_local_date(_user(current_tz="Europe/Berlin"), after_midnight) == date(
        2026, 3, 29
    )


def test_aware_non_utc_offset_is_normalized() -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.aware_offset
    # purpose: Prove an aware non-UTC offset is normalized before date extraction.
    # inputs: Aware +05:30 datetime and UTC profile timezone.
    # returns: None; assertions prove the UTC-normalized date.
    # side_effects: none
    # emitted_logs: none
    # error_behavior: Fails through pytest if non-UTC aware input is mishandled.
    # END_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.aware_offset
    now = datetime(
        2026,
        7,
        29,
        0,
        30,
        tzinfo=timezone(timedelta(hours=5, minutes=30)),
    )

    assert resolve_user_local_date(_user(current_tz="UTC"), now) == date(2026, 7, 28)


def test_naive_now_fails_closed() -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.naive_now
    # purpose: Prove naive datetimes are rejected instead of using server local time.
    # inputs: Naive datetime and otherwise valid profile timezone.
    # returns: None; assertions prove the stable domain error.
    # side_effects: none
    # emitted_logs: none
    # error_behavior: Expects UserLocalDateError with now_must_be_aware code.
    # END_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.naive_now
    with pytest.raises(UserLocalDateError) as exc_info:
        resolve_user_local_date(
            _user(current_tz="Europe/Moscow"), datetime(2026, 7, 29, 0, 30)
        )

    assert exc_info.value.code == "now_must_be_aware"
    assert str(exc_info.value) == "now_must_be_aware"


def test_invalid_timezone_fails_closed_without_leaking_profile_value() -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.invalid_timezone
    # purpose: Prove invalid selected timezone fails without UTC fallback or leakage.
    # inputs: Invalid current_tz, valid birth_tz, and aware UTC instant.
    # returns: None; assertions prove stable safe error behavior.
    # side_effects: none
    # emitted_logs: none
    # error_behavior: Expects UserLocalDateError with invalid_timezone code.
    # END_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE.invalid_timezone
    invalid_timezone = "Not/A-Timezone-Secret"

    with pytest.raises(UserLocalDateError) as exc_info:
        resolve_user_local_date(
            _user(current_tz=invalid_timezone, birth_tz="Asia/Tokyo"),
            datetime(2026, 7, 29, 0, 30, tzinfo=timezone.utc),
        )

    assert exc_info.value.code == "invalid_timezone"
    assert str(exc_info.value) == "invalid_timezone"
    assert invalid_timezone not in str(exc_info.value)
# END_BLOCK: USER_LOCAL_DATE_TESTS
