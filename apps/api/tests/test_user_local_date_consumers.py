# ############################################################################
# AI_HEADER: MODULE_TESTS_USER_LOCAL_DATE_CONSUMERS
# ROLE: Focused acceptance tests for Day/Calendar local-date wiring.
# DEPENDENCIES: pytest, app.api.day, app.api.calendar, app.services.calendar_service
# GRACE_ANCHORS: [DAY_CALENDAR_LOCAL_DATE_WIRING]
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-USER-LOCAL-DATE-CONSUMERS
# purpose: Prove Day and Calendar consume the pure local-date resolver exactly
#   at their date-classification boundaries without changing wire payloads.
# owns:
#   - apps/api/tests/test_user_local_date_consumers.py
# inputs: Authenticated user doubles, aware frozen UTC instants, and mocked
#   heavy downstream service boundaries.
# outputs: Assertions over resolved dates, safe HTTP errors, cache selection,
#   Calendar allowed range, and isToday classification.
# dependencies:
#   - M-DAY-SERVICE.api
#   - M-CALENDAR-API
#   - M-CALENDAR-SERVICE
#   - M-USER-LOCAL-DATE
# side_effects: none beyond test database fixtures.
# emitted_logs: none
# invariants:
#   - west/east and DST acceptance uses the real resolver, never a resolver mock;
#   - only system time and heavy downstream boundaries are patched.
# failure_policy: assertion failures propagate through pytest.
# END_MODULE_CONTRACT: M-TESTS-USER-LOCAL-DATE-CONSUMERS

# START_MODULE_MAP: M-TESTS-USER-LOCAL-DATE-CONSUMERS
# public_entrypoints:
#   - test_day_today_uses_previous_western_local_date
#   - test_day_today_uses_next_eastern_local_date
#   - test_day_explicit_date_is_not_resolved_or_shifted
#   - test_focus_event_today_uses_resolved_local_date_for_cache
#   - test_calendar_api_uses_local_year_and_passes_one_resolved_date
#   - test_calendar_service_uses_explicit_today_for_range_and_is_today
#   - test_day_invalid_timezone_is_privacy_safe_422
#   - test_calendar_invalid_timezone_is_privacy_safe_422
# semantic_blocks:
#   - DAY_WIRING: Day today and focus-event date selection
#   - CALENDAR_WIRING: Calendar API/service date propagation
#   - ERROR_MAPPING: invalid timezone HTTP surface
# owned_tests:
#   - apps/api/tests/test_user_local_date_consumers.py
# END_MODULE_MAP: M-TESTS-USER-LOCAL-DATE-CONSUMERS

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

from app.api import calendar as calendar_api
from app.api import day as day_api
from app.db.models import TodayPayloadCache, User, UserProfile
from app.schemas.access import ContentAccessState
from app.services.calendar_service import CalendarService


class _FrozenDateTime(datetime):
    frozen: datetime

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls.frozen.replace(tzinfo=None)
        return cls.frozen.astimezone(tz)


def _user(*, current_tz: str | None, birth_tz: str | None = "UTC"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tg_user_id=991001,
        tg_username=None,
        profile=SimpleNamespace(
            current_tz=current_tz,
            birth_tz=birth_tz,
            birth_lat=55.75,
            birth_lon=37.62,
            is_onboarded=True,
        ),
    )


def _request():
    return SimpleNamespace(headers={}, client=None)


def _patch_day_downstream(monkeypatch: pytest.MonkeyPatch):
    access = Mock()
    access.can_access_day = AsyncMock(
        return_value=ContentAccessState(
            state="full",
            reason="active_subscription",
            referral_days_left=None,
            subscription_active=True,
            access_until=None,
        )
    )
    today_service = Mock()
    today_service.get_today_payload = AsyncMock(return_value=object())
    monkeypatch.setattr(day_api, "AccessService", lambda _db: access)
    monkeypatch.setattr(day_api, "TodayService", lambda _db: today_service)
    return access, today_service


# START_BLOCK: DAY_WIRING
@pytest.mark.asyncio
async def test_day_today_uses_previous_western_local_date(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE-CONSUMERS.day_west
    # purpose: Prove Day today uses the prior local date west of UTC.
    # inputs: Frozen aware UTC instant and America/Los_Angeles profile.
    # returns: None; asserts the downstream target date.
    # side_effects: none beyond mocked downstream calls.
    # emitted_logs: none
    # error_behavior: assertion failure on UTC-date or server-date fallback.
    # END_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE-CONSUMERS.day_west
    _FrozenDateTime.frozen = datetime(2026, 7, 29, 0, 30, tzinfo=UTC)
    monkeypatch.setattr(day_api, "datetime", _FrozenDateTime)
    _, today_service = _patch_day_downstream(monkeypatch)

    await day_api.get_day("today", _request(), _user(current_tz="America/Los_Angeles"), object())

    assert today_service.get_today_payload.await_args.kwargs["target_date"] == date(2026, 7, 28)


@pytest.mark.asyncio
async def test_day_today_uses_next_eastern_local_date(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE-CONSUMERS.day_east
    # purpose: Prove Day today uses the next local date east of UTC.
    # inputs: Frozen aware UTC instant and Asia/Tokyo profile.
    # returns: None; asserts the downstream target date.
    # side_effects: none beyond mocked downstream calls.
    # emitted_logs: none
    # error_behavior: assertion failure on UTC-date or server-date fallback.
    # END_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE-CONSUMERS.day_east
    _FrozenDateTime.frozen = datetime(2026, 7, 28, 23, 30, tzinfo=UTC)
    monkeypatch.setattr(day_api, "datetime", _FrozenDateTime)
    _, today_service = _patch_day_downstream(monkeypatch)

    await day_api.get_day("today", _request(), _user(current_tz="Asia/Tokyo"), object())

    assert today_service.get_today_payload.await_args.kwargs["target_date"] == date(2026, 7, 29)


@pytest.mark.asyncio
async def test_day_explicit_date_is_not_resolved_or_shifted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE-CONSUMERS.day_explicit
    # purpose: Prove explicit ISO dates bypass the local-date resolver.
    # inputs: Explicit ISO date and a conflicting profile timezone.
    # returns: None; asserts the exact downstream date.
    # side_effects: none beyond mocked downstream calls.
    # emitted_logs: none
    # error_behavior: resolver invocation fails the test.
    # END_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE-CONSUMERS.day_explicit
    resolver = Mock(side_effect=AssertionError("explicit date must not resolve"))
    monkeypatch.setattr(day_api, "resolve_user_local_date", resolver)
    _, today_service = _patch_day_downstream(monkeypatch)

    await day_api.get_day(
        "2026-07-28", _request(), _user(current_tz="Asia/Tokyo"), object()
    )

    resolver.assert_not_called()
    assert today_service.get_today_payload.await_args.kwargs["target_date"] == date(2026, 7, 28)


@pytest.mark.asyncio
async def test_focus_event_today_uses_resolved_local_date_for_cache(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE-CONSUMERS.focus_today
    # purpose: Prove focus-event today reads the cache at resolved local date.
    # inputs: Real ORM user/profile, frozen UTC instant, and matching cache row.
    # returns: None; patched builder sentinel proves the cache row was found.
    # side_effects: test database insert only.
    # emitted_logs: none
    # error_behavior: 404 or wrong sentinel indicates incorrect date wiring.
    # END_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE-CONSUMERS.focus_today
    _FrozenDateTime.frozen = datetime(2026, 7, 29, 0, 30, tzinfo=UTC)
    monkeypatch.setattr(day_api, "datetime", _FrozenDateTime)
    user = User(tg_user_id=991002)
    profile = UserProfile(
        user=user,
        current_tz="America/Los_Angeles",
        birth_tz="Asia/Tokyo",
    )
    db_session.add_all([user, profile])
    await db_session.flush()
    db_session.add(
        TodayPayloadCache(
            user_id=user.id,
            target_date=date(2026, 7, 28),
            profile_hash="test-profile",
            payload_json=json.dumps(
                {
                    "focus": {"events": [{"id": "event-1", "sourceActivationIds": []}]},
                    "v2": {"activationEvidence": []},
                }
            ),
        )
    )
    await db_session.commit()
    sentinel = object()

    with patch(
        "app.services.focus_event_drilldown_builder.build_focus_event_drilldown",
        return_value=sentinel,
    ):
        result = await day_api.get_focus_event_drilldown(
            "today", "event-1", db_session, user
        )

    assert result is sentinel
# END_BLOCK: DAY_WIRING


# START_BLOCK: CALENDAR_WIRING
@pytest.mark.asyncio
async def test_calendar_api_uses_local_year_and_passes_one_resolved_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE-CONSUMERS.calendar_api
    # purpose: Prove Calendar validates range from local year and forwards today.
    # inputs: Frozen UTC instant crossing into 2027 in Asia/Tokyo.
    # returns: None; asserts the exact service call.
    # side_effects: none beyond mocked service call.
    # emitted_logs: none
    # error_behavior: 400 or wrong today indicates UTC/server-date fallback.
    # END_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE-CONSUMERS.calendar_api
    _FrozenDateTime.frozen = datetime(2026, 12, 31, 23, 30, tzinfo=UTC)
    monkeypatch.setattr(calendar_api, "datetime", _FrozenDateTime)
    service = Mock()
    service.get_calendar = AsyncMock(return_value=object())
    monkeypatch.setattr(calendar_api, "CalendarService", lambda _db: service)

    user = _user(current_tz="Asia/Tokyo")
    await calendar_api.get_calendar("2029-01", user, object())

    assert service.get_calendar.await_args.kwargs == {
        "user_id": user.id,
        "month": "2029-01",
        "today": date(2027, 1, 1),
    }


@pytest.mark.asyncio
async def test_calendar_service_uses_explicit_today_for_range_and_is_today(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE-CONSUMERS.calendar_service
    # purpose: Prove service date classification and range use passed today only.
    # inputs: Explicit 2027-01-01 today and December 2026 calendar request.
    # returns: None; asserts local-year range and one matching day.
    # side_effects: mocked DB/downstream boundaries only.
    # emitted_logs: none
    # error_behavior: wrong range or count indicates internal UTC fallback.
    # END_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE-CONSUMERS.calendar_service
    service = CalendarService(db_session)
    service._prepare_request_context = AsyncMock()
    service._get_day_status = AsyncMock(return_value=None)
    access = Mock()
    access.can_access_day = AsyncMock(
        return_value=ContentAccessState(state="locked", reason="outside_access_window")
    )
    monkeypatch.setattr(
        "app.services.calendar_service.AccessService", lambda _db: access
    )

    payload = await service.get_calendar(
        uuid.uuid4(), "2026-12", today=date(2027, 1, 1)
    )

    assert payload.allowed_range.from_ == "2025-01-01"
    assert payload.allowed_range.to == "2029-12-31"
    today_days = [day for day in payload.days if day.is_today]
    assert len(today_days) == 1
    assert today_days[0].date == "2027-01-01"
# END_BLOCK: CALENDAR_WIRING


# START_BLOCK: ERROR_MAPPING
@pytest.mark.asyncio
async def test_day_invalid_timezone_is_privacy_safe_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE-CONSUMERS.day_error
    # purpose: Prove Day maps invalid timezone to stable safe HTTP 422.
    # inputs: Invalid selected current_tz and frozen aware instant.
    # returns: None; asserts code/reason contain no profile value.
    # side_effects: none.
    # emitted_logs: none
    # error_behavior: Expects HTTPException 422.
    # END_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE-CONSUMERS.day_error
    _FrozenDateTime.frozen = datetime(2026, 7, 29, 0, 30, tzinfo=UTC)
    monkeypatch.setattr(day_api, "datetime", _FrozenDateTime)
    invalid_timezone = "Not/A-Secret-Timezone"

    with pytest.raises(HTTPException) as exc_info:
        await day_api.get_day(
            "today", _request(), _user(current_tz=invalid_timezone), object()
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == {
        "code": "INVALID_USER_TIMEZONE",
        "reason": "invalid_timezone",
    }
    assert invalid_timezone not in repr(exc_info.value.detail)


@pytest.mark.asyncio
async def test_calendar_invalid_timezone_is_privacy_safe_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE-CONSUMERS.calendar_error
    # purpose: Prove Calendar maps invalid timezone to stable safe HTTP 422.
    # inputs: Invalid selected birth_tz and frozen aware instant.
    # returns: None; asserts code/reason contain no profile value.
    # side_effects: none.
    # emitted_logs: none
    # error_behavior: Expects HTTPException 422.
    # END_FUNCTION_CONTRACT: F-M-TESTS-USER-LOCAL-DATE-CONSUMERS.calendar_error
    _FrozenDateTime.frozen = datetime(2026, 7, 29, 0, 30, tzinfo=UTC)
    monkeypatch.setattr(calendar_api, "datetime", _FrozenDateTime)
    invalid_timezone = "Not/A-Secret-Timezone"

    with pytest.raises(HTTPException) as exc_info:
        await calendar_api.get_calendar(
            "2026-08", _user(current_tz=None, birth_tz=invalid_timezone), object()
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == {
        "code": "INVALID_USER_TIMEZONE",
        "reason": "invalid_timezone",
    }
    assert invalid_timezone not in repr(exc_info.value.detail)
# END_BLOCK: ERROR_MAPPING
