# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_ERROR_TRACKING
# ROLE: Unit and integration tests for ErrorTrackingService and Bugsink envelope forwarding.
# DEPENDENCIES: pytest, unittest.mock, sentry_sdk, app.services.error_tracking, app.services.log_intake
# GRACE_ANCHORS: [TEST_ERROR_TRACKING]
# WAVE: W-PROD-ERROR-LOOP
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-ERROR-TRACKING
# purpose: Validate Sentry SDK initialization rules, frontend error envelope filtering, mapping to Sentry event dicts, fire-and-forget exception handling, and log intake integration.
# owns:
#   - apps/api/tests/services/test_error_tracking.py
# inputs: sample frontend log envelopes
# outputs: pytest execution assertions
# dependencies:
#   - app.services.error_tracking (init_error_tracking, capture_frontend_envelope, should_forward_envelope)
#   - app.services.log_intake (LogIntakeService)
# side_effects: none (mocks sentry_sdk)
# failure_policy: raise assertions
# END_MODULE_CONTRACT: M-TEST-ERROR-TRACKING

# START_MODULE_MAP: M-TEST-ERROR-TRACKING
# public_entrypoints:
#   - test_init_error_tracking_no_op_on_empty_dsn
#   - test_should_forward_envelope_filtering
#   - test_capture_frontend_envelope_mapping_and_sentry_event
#   - test_capture_frontend_envelope_fire_and_forget_swallows_exceptions
#   - test_log_intake_integration_forwards_frontend_errors
# owned_tests:
#   - apps/api/tests/services/test_error_tracking.py
# END_MODULE_MAP: M-TEST-ERROR-TRACKING

import unittest.mock
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.error_tracking import (
    capture_frontend_envelope,
    init_error_tracking,
    should_forward_envelope,
)
from app.services.log_intake import LogIntakeService


def test_init_error_tracking_no_op_on_empty_dsn() -> None:
    with unittest.mock.patch("sentry_sdk.init") as mock_init:
        init_error_tracking("", "sha123")
        init_error_tracking("   ", "sha123")
        assert not mock_init.called

    with unittest.mock.patch("sentry_sdk.init") as mock_init:
        init_error_tracking("http://key@bugsink:8000/1", "sha123")
        assert mock_init.called
        _, kwargs = mock_init.call_args
        assert kwargs.get("dsn") == "http://key@bugsink:8000/1"
        assert kwargs.get("release") == "sha123"
        assert kwargs.get("send_default_pii") is False


def test_should_forward_envelope_filtering() -> None:
    # Level error + frontend. prefix -> True
    assert should_forward_envelope({"level": "error", "event": "frontend.runtime_failed"}) is True
    assert should_forward_envelope({"level": "fatal", "event": "frontend.render_failed"}) is True

    # Level info -> False
    assert should_forward_envelope({"level": "info", "event": "frontend.runtime_failed"}) is False

    # Event prefix not frontend. -> False
    assert should_forward_envelope({"level": "error", "event": "auth.tg_login_failed"}) is False
    assert should_forward_envelope({"level": "error", "event": "ui.fetch_failed"}) is False
    assert should_forward_envelope({"level": "error", "event": "system.error"}) is False

    # Invalid types
    assert should_forward_envelope(None) is False
    assert should_forward_envelope("invalid") is False


def test_capture_frontend_envelope_mapping_and_sentry_event() -> None:
    envelope = {
        "ts": "2026-07-24T12:00:00.000Z",
        "level": "error",
        "env": "production",
        "service": "frontend",
        "service_version": "1.0.0",
        "slice": "W-1.7",
        "module": "M-LOG-CAPTURE-ERROR",
        "block": "CAPTURE_API",
        "event": "frontend.runtime_failed",
        "correlation_id": "h1_abc123",
        "error": {
            "kind": "TypeError",
            "code": "ERR_NULL_PTR",
            "source": "window.error",
            "fingerprint": "fp_12345",
            "stack_frames": [
                {"file": "app/main.tsx", "function": "renderApp", "line": 42, "column": 10}
            ],
        },
        "payload": {
            "route": "/profile",
        },
        "http": {
            "method": "GET",
            "route": "/profile",
            "status": 500,
        },
        "duration_ms": 12.5,
    }

    with unittest.mock.patch("sentry_sdk.capture_event") as mock_capture:
        capture_frontend_envelope(envelope)

        assert mock_capture.called
        event_dict = mock_capture.call_args[0][0]

        assert event_dict["message"] == "frontend.runtime_failed: TypeError"
        assert event_dict["fingerprint"] == ["fp_12345"]
        assert event_dict["level"] == "error"

        # Exception values
        exc_val = event_dict["exception"]["values"][0]
        assert exc_val["type"] == "TypeError"
        assert exc_val["value"] == "frontend.runtime_failed (ERR_NULL_PTR)"
        assert exc_val["module"] == "M-LOG-CAPTURE-ERROR"

        # Stacktrace frames
        frames = exc_val["stacktrace"]["frames"]
        assert len(frames) == 1
        assert frames[0]["filename"] == "app/main.tsx"
        assert frames[0]["function"] == "renderApp"
        assert frames[0]["lineno"] == 42
        assert frames[0]["colno"] == 10
        assert frames[0]["in_app"] is True

        # Tags & Extra
        assert event_dict["tags"]["event"] == "frontend.runtime_failed"
        assert event_dict["tags"]["error.source"] == "window.error"
        assert event_dict["tags"]["route"] == "/profile"
        assert event_dict["tags"]["slice"] == "W-1.7"
        assert event_dict["tags"]["code"] == "ERR_NULL_PTR"

        assert event_dict["extra"]["correlation_id"] == "h1_abc123"
        assert event_dict["extra"]["http"]["status"] == 500


def test_capture_frontend_envelope_fire_and_forget_swallows_exceptions() -> None:
    envelope = {
        "level": "error",
        "event": "frontend.runtime_failed",
        "error": {"kind": "Error"},
    }

    with unittest.mock.patch("sentry_sdk.capture_event", side_effect=RuntimeError("Sentry network crash")):
        # Should not raise exception
        capture_frontend_envelope(envelope)


@pytest.mark.asyncio
async def test_log_intake_integration_forwards_frontend_errors(db_session: AsyncSession) -> None:
    service = LogIntakeService(db_session)
    user_id = uuid.uuid4()

    valid_error_envelope = {
        "ts": "2026-07-24T12:00:00.000Z",
        "level": "error",
        "env": "production",
        "service": "frontend",
        "service_version": "1.0.0",
        "slice": "W-1.7",
        "module": "M-LOG-CAPTURE-ERROR",
        "block": "CAPTURE_API",
        "event": "frontend.runtime_failed",
        "correlation_id": "h1_abc123",
        "error": {"kind": "TypeError"},
    }

    valid_info_envelope = {
        **valid_error_envelope,
        "level": "info",
        "event": "ui.fetch_succeeded",
    }

    with unittest.mock.patch("app.services.error_tracking.capture_frontend_envelope") as mock_forward:
        res = await service.process_batch(user_id, [valid_error_envelope, valid_info_envelope])
        assert res == {"accepted": 2, "rejected": 0}
        assert mock_forward.called
        assert mock_forward.call_count == 1
        assert mock_forward.call_args[0][0]["event"] == "frontend.runtime_failed"
