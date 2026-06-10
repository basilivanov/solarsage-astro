# AI_HEADER
# module: M-TEST-LOG-ENVELOPE
# wave: W-1.6
# purpose: Tests for canonical log envelope shape and contextvars.

from __future__ import annotations

import json
import os
import re
from unittest.mock import patch

import pytest
import time

from app.core.logging import (
    build_envelope,
    log_event,
    bind_log_context,
    clear_log_context,
    correlation_id_var,
    slice_var,
    module_var,
    block_var,
    SERVICE_VERSION,
)


def test_envelope_has_required_fields():
    """Every envelope must have ts, level, env, service, service_version,
    slice, module, block, event, correlation_id."""
    clear_log_context()
    bind_log_context(
        correlation_id="test-corr-id",
        slice="W-TEST",
        module="M-TEST",
        block="TEST_BLOCK",
    )

    envelope = build_envelope("system.request", level="info", msg="test")

    required = ["ts", "level", "env", "service", "service_version",
                "slice", "module", "block", "event", "correlation_id"]
    for field in required:
        assert field in envelope, f"Missing required field: {field}"

    assert envelope["event"] == "system.request"
    assert envelope["slice"] == "W-TEST"
    assert envelope["module"] == "M-TEST"
    assert envelope["block"] == "TEST_BLOCK"
    assert envelope["correlation_id"] == "test-corr-id"


def test_envelope_serializes_to_json():
    """Envelope must be JSON-serializable (for stdout)."""
    clear_log_context()
    bind_log_context(
        correlation_id="json-test",
        slice="W-TEST",
        module="M-TEST",
        block="TEST_BLOCK",
    )
    envelope = build_envelope("system.startup", level="info", payload={"pid": 123})
    json_str = json.dumps(envelope, default=str)
    parsed = json.loads(json_str)
    assert parsed["event"] == "system.startup"
    assert parsed["payload"]["pid"] == 123


def test_log_event_writes_to_stdout():
    """log_event must write a valid JSON line to stdout."""
    clear_log_context()
    bind_log_context(correlation_id="stdout-test", slice="W-TEST", module="M-TEST", block="TEST_BLOCK")

    captured = []

    def mock_write(line):
        captured.append(line)

    from app.core.logging import _stdout
    original_write = _stdout.write
    try:
        _stdout.write = mock_write
        log_event("system.request", level="info", msg="stdout test")
    finally:
        _stdout.write = original_write

    assert len(captured) >= 1
    line = captured[0]
    parsed = json.loads(line)
    assert parsed["event"] == "system.request"
    assert parsed["msg"] == "stdout test"


@pytest.mark.parametrize("event", [
    "system.startup", "system.request", "system.error",
    "auth.tg_login_succeeded", "auth.tg_login_failed",
    "profile.viewed", "profile.updated",
    "day.viewed", "calendar.viewed",
    "access.checked",
    "payment.failed",
    "sidecar.called",
    "scoring.computed",
    "llm.requested",
    "llm.response_validated",
    "llm.response_rejected",
    "ui.error_boundary_tripped",
    "horary.question_created",
    "natal.context_cache_hit",
])
def test_known_events_build_valid_envelope(event):
    """All known events must build a valid envelope without errors."""
    clear_log_context()
    bind_log_context(
        correlation_id="event-test",
        slice="W-TEST",
        module="M-TEST-EVENTS",
        block="TEST_KNOWN_EVENTS",
    )
    envelope = build_envelope(event, level="info", msg=f"test {event}")
    assert envelope["event"] == event


def test_contextvars_bind_correctly():
    """Context vars must auto-attach to envelopes."""
    clear_log_context()
    bind_log_context(
        correlation_id="ctx-corr",
        slice="W-TEST-CTX",
        module="M-TEST-CTX",
        block="TEST_CTX",
    )
    envelope = build_envelope("system.startup")
    assert envelope["correlation_id"] == "ctx-corr"
    assert envelope["slice"] == "W-TEST-CTX"
    assert envelope["module"] == "M-TEST-CTX"
    assert envelope["block"] == "TEST_CTX"


def test_service_version_is_set():
    """Service version must be a non-empty string."""
    assert SERVICE_VERSION
    assert isinstance(SERVICE_VERSION, str)


def test_msg_and_http_redaction_in_log_event():
    """log_event() must redact msg and http fields before emitting."""
    clear_log_context()
    bind_log_context(
        correlation_id="redact-test",
        slice="W-TEST",
        module="M-TEST",
        block="TEST_BLOCK",
    )

    captured = []
    def mock_emit(envelope):
        captured.append(envelope)

    with patch("app.core.logging._emit", mock_emit):
        log_event(
            "system.request",
            msg="User email was test@example.com and ip was 127.0.0.1",
            http={
                "method": "POST",
                "route": "/api/auth/telegram",
                "ip": "127.0.0.1",
                "authorization": "Bearer sk-abc123xyz",
            }
        )

    assert len(captured) == 1
    env = captured[0]
    # msg should have email and IP redacted
    assert "test@example.com" not in env["msg"]
    assert "127.0.0.1" not in env["msg"]
    assert "[redacted-email]" in env["msg"]
    assert "[redacted-ip]" in env["msg"]

    # http should have PII keys redacted
    assert env["http"]["ip"] == "[redacted]"
    assert env["http"]["authorization"] == "[redacted]"
    # http route and method are allowed keys, so they should NOT be redacted
    assert env["http"]["method"] == "POST"
    assert env["http"]["route"] == "/api/auth/telegram"
