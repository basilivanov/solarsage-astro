# ############################################################################
# AI_HEADER: MODULE_ERROR_TRACKING
# ROLE: Frontend error forwarder and Sentry SDK initializer for Bugsink.
# DEPENDENCIES: sentry_sdk, app.core.logging
# GRACE_ANCHORS: [ERROR_TRACKING_INIT, CAPTURE_FRONTEND_ENVELOPE]
# WAVE: W-PROD-ERROR-LOOP
# ############################################################################

# START_MODULE_CONTRACT: M-ERROR-TRACKING
# purpose: Initialize Sentry SDK for FastAPI and forward filtered frontend error envelopes to Bugsink without crashing intake.
# owns:
#   - apps/api/app/services/error_tracking.py
# inputs:
#   - DSN, release_sha, frontend log envelope dict
# outputs:
#   - forwards error event to Sentry/Bugsink
# dependencies:
#   - sentry_sdk
# side_effects:
#   - sends HTTP event payload to Bugsink
# invariants:
#   - empty DSN results in safe no-op
#   - send_default_pii is strictly False
#   - filters only level in {"error", "fatal"} and event starting with "frontend."
#   - forwarding exception never propagates or affects log intake
# failure_policy: fail-open / fire-and-forget: catch all exceptions silently
# END_MODULE_CONTRACT: M-ERROR-TRACKING

# START_MODULE_MAP: M-ERROR-TRACKING
# public_entrypoints:
#   - init_error_tracking
#   - capture_frontend_envelope
#   - should_forward_envelope
# semantic_blocks:
#   - ERROR_TRACKING_INIT: sentry_sdk initialization
#   - CAPTURE_FRONTEND_ENVELOPE: envelope filtering and Sentry event mapping
# owned_tests:
#   - apps/api/tests/services/test_error_tracking.py
# END_MODULE_MAP: M-ERROR-TRACKING

from __future__ import annotations

from typing import Any
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

_is_initialized = False


# START_BLOCK: ERROR_TRACKING_INIT
def init_error_tracking(dsn: str, release: str = "") -> None:
    # START_FUNCTION_CONTRACT: F-M-ERROR-TRACKING.init_error_tracking
    # purpose: Initialize Sentry SDK for FastAPI with specified DSN and release identity.
    # inputs: dsn (str), release (str)
    # returns: None
    # side_effects: configures sentry_sdk
    # error_behavior: no-op on empty DSN, swallows initialization errors
    # END_FUNCTION_CONTRACT: F-M-ERROR-TRACKING.init_error_tracking
    global _is_initialized
    if not dsn or not dsn.strip():
        _is_initialized = False
        return

    try:
        sentry_sdk.init(
            dsn=dsn.strip(),
            release=release or None,
            integrations=[FastApiIntegration()],
            send_default_pii=False,
        )
        _is_initialized = True
    except Exception:
        _is_initialized = False
# END_BLOCK: ERROR_TRACKING_INIT


# START_BLOCK: CAPTURE_FRONTEND_ENVELOPE
def should_forward_envelope(envelope: dict[str, Any]) -> bool:
    """Filter rule: only level in {error, fatal} and event starting with 'frontend.'."""
    if not isinstance(envelope, dict):
        return False
    level = envelope.get("level")
    if level not in ("error", "fatal"):
        return False
    event = envelope.get("event")
    if not isinstance(event, str) or not event.startswith("frontend."):
        return False
    return True


def capture_frontend_envelope(envelope: dict[str, Any]) -> None:
    # START_FUNCTION_CONTRACT: F-M-ERROR-TRACKING.capture_frontend_envelope
    # purpose: Map low-PII frontend log envelope to Sentry event and forward to Bugsink.
    # inputs: envelope (dict)
    # returns: None
    # side_effects: sends Sentry event if enabled
    # error_behavior: catches all exceptions silently; never raises
    # END_FUNCTION_CONTRACT: F-M-ERROR-TRACKING.capture_frontend_envelope
    try:
        if not should_forward_envelope(envelope):
            return

        event = str(envelope.get("event", "frontend.error"))
        payload = envelope.get("payload") if isinstance(envelope.get("payload"), dict) else {}
        error_data = envelope.get("error") if isinstance(envelope.get("error"), dict) else {}

        kind = str(error_data.get("kind") or "Error")
        code = error_data.get("code")
        source = str(error_data.get("source") or "unknown")
        fingerprint_val = error_data.get("fingerprint")
        stack_frames = error_data.get("stack_frames") if isinstance(error_data.get("stack_frames"), list) else []

        route = payload.get("route")
        slice_val = envelope.get("slice")
        module_val = envelope.get("module")
        correlation_id = envelope.get("correlation_id")
        http = envelope.get("http")
        duration_ms = envelope.get("duration_ms")

        # Construct Sentry stacktrace frames
        sentry_frames = []
        for frame in stack_frames:
            if isinstance(frame, dict):
                sentry_frames.append(
                    {
                        "filename": str(frame.get("file") or "unknown"),
                        "function": str(frame.get("function") or "<anonymous>"),
                        "lineno": int(frame.get("line") or 0),
                        "colno": int(frame.get("column") or 0),
                        "in_app": True,
                    }
                )

        exception_val: dict[str, Any] = {
            "type": kind,
            "value": f"{event} ({code})" if code else event,
            "module": str(module_val) if module_val else "frontend",
        }
        if sentry_frames:
            exception_val["stacktrace"] = {"frames": sentry_frames}

        tags: dict[str, Any] = {
            "event": event,
            "error.source": source,
        }
        if route:
            tags["route"] = str(route)
        if module_val:
            tags["module"] = str(module_val)
        if slice_val:
            tags["slice"] = str(slice_val)
        if code:
            tags["code"] = str(code)

        extra: dict[str, Any] = {}
        if http:
            extra["http"] = http
        if duration_ms is not None:
            extra["duration_ms"] = duration_ms
        if correlation_id:
            extra["correlation_id"] = correlation_id
        if payload:
            extra["payload"] = payload

        sentry_event: dict[str, Any] = {
            "message": f"{event}: {kind}",
            "level": envelope.get("level", "error"),
            "exception": {"values": [exception_val]},
            "tags": tags,
            "extra": extra,
        }

        if fingerprint_val and isinstance(fingerprint_val, str):
            sentry_event["fingerprint"] = [fingerprint_val]
        else:
            sentry_event["fingerprint"] = [f"{event}:{kind}"]

        sentry_sdk.capture_event(sentry_event)
    except Exception:
        # Fire-and-forget: failure to forward to Bugsink must never affect log intake
        pass
# END_BLOCK: CAPTURE_FRONTEND_ENVELOPE
