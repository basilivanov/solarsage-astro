# ############################################################################
# AI_HEADER: MODULE_OBSERVABILITY_LOGGING
# ROLE: Structured JSON logging with canonical envelope and contextvars.
# DEPENDENCIES: logging, json, contextvars
# GRACE_ANCHORS: [LOG_EVENT, CONTEXT_VARS, LOGGER_SETUP]
# WAVE: W-1.6
# ############################################################################

# START_MODULE_CONTRACT: M-OBSERVABILITY-LOGGING
# purpose: Provide structured JSON logging with canonical envelope per §8.2.
#   Context variables (correlation_id, slice, module, block) are auto-attached.
#   log_event() is the only public API for business events.
# owns:
#   - apps/api/app/core/logging.py
# inputs:
#   - event name from LogEventName registry
#   - optional payload dict
#   - optional meta overrides (level, msg, duration_ms, error, http)
# outputs:
#   - JSON-formatted log lines to stdout
# dependencies:
#   - standard library: logging, json, contextvars
#   - apps/api/app/core/redactor (redact_dict)
#   - apps/api/app/core/logging_events (LogEventName, EVENT_PAYLOAD_TYPES)
# side_effects:
#   - configures global logger instance
#   - writes to stdout
# invariants:
#   - all logs emitted as valid JSON
#   - every envelope has slice/module/block/event/correlation_id
#   - unknown fields are dropped; payload passes through redactor
# failure_policy:
#   - logging errors must not crash the application
# END_MODULE_CONTRACT: M-OBSERVABILITY-LOGGING

from __future__ import annotations

import contextlib
import contextvars
import json
import logging
import os
import re
import traceback
from datetime import UTC, datetime
from typing import Any

from app.core.logging_events import LogEventName
from app.core.redactor import redact_dict


# ── Context variables (auto-attached by middleware) ────────────────────────

correlation_id_var: contextvars.Var[str] = contextvars.ContextVar("correlation_id", default="")
user_id_hash_var: contextvars.Var[str] = contextvars.ContextVar("user_id_hash", default="")
http_route_var: contextvars.Var[str] = contextvars.ContextVar("http_route", default="")
http_method_var: contextvars.Var[str] = contextvars.ContextVar("http_method", default="")
slice_var: contextvars.Var[str] = contextvars.ContextVar("slice", default="")
module_var: contextvars.Var[str] = contextvars.ContextVar("module", default="")
block_var: contextvars.Var[str] = contextvars.ContextVar("block", default="")
operation_id_var: contextvars.Var[str] = contextvars.ContextVar("operation_id", default="")
service_var: contextvars.Var[str] = contextvars.ContextVar("service", default="api")
env_var: contextvars.Var[str] = contextvars.ContextVar("env", default="dev")


def bind_log_context(
    *,
    correlation_id: str = "",
    user_id_hash: str = "",
    http_route: str = "",
    http_method: str = "",
    slice: str = "",
    module: str = "",
    block: str = "",
    operation_id: str = "",
    service: str = "",
    env: str = "",
) -> None:
    """Bind one or more log context variables for the current scope."""
    if correlation_id:
        correlation_id_var.set(correlation_id)
    if user_id_hash:
        user_id_hash_var.set(user_id_hash)
    if http_route:
        http_route_var.set(http_route)
    if http_method:
        http_method_var.set(http_method)
    if slice:
        slice_var.set(slice)
    if module:
        module_var.set(module)
    if block:
        block_var.set(block)
    if operation_id:
        operation_id_var.set(operation_id)
    if service:
        service_var.set(service)
    if env:
        env_var.set(env)


def clear_log_context() -> None:
    """Reset all log context variables."""
    correlation_id_var.set("")
    user_id_hash_var.set("")
    http_route_var.set("")
    http_method_var.set("")
    slice_var.set("")
    module_var.set("")
    block_var.set("")
    operation_id_var.set("")
    service_var.set("api")
    env_var.set(os.getenv("GRACE_ENV", "dev"))


@contextlib.contextmanager
def log_block(*, slice: str = "", module: str = "", block: str = "", operation_id: str = ""):
    """Context manager to temporarily override slice, module, block, or operation_id log context."""
    old_slice = slice_var.get()
    old_module = module_var.get()
    old_block = block_var.get()
    old_op_id = operation_id_var.get()

    if slice:
        slice_var.set(slice)
    if module:
        module_var.set(module)
    if block:
        block_var.set(block)
    if operation_id:
        operation_id_var.set(operation_id)

    try:
        yield
    finally:
        slice_var.set(old_slice)
        module_var.set(old_module)
        block_var.set(old_block)
        operation_id_var.set(old_op_id)


# ── Service version ───────────────────────────────────────────────────────

_SERVICE_VERSION: str = os.getenv("GRACE_SERVICE_VERSION", "dev")
_git_sha_match = re.search(r"[a-f0-9]{7,}", _SERVICE_VERSION)
SERVICE_VERSION: str = _git_sha_match.group(0) if _git_sha_match else _SERVICE_VERSION


# ── Envelope builder ──────────────────────────────────────────────────────

def build_envelope(
    event: LogEventName,
    *,
    level: str = "info",
    msg: str = "",
    payload: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
    duration_ms: float | None = None,
    http: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a canonical log envelope per §8.2, auto-attaching context vars."""
    now = datetime.now(UTC)

    slice_val = slice_var.get()
    module_val = module_var.get()
    block_val = block_var.get()
    corr_id = correlation_id_var.get()
    env_val = env_var.get()
    svc = service_var.get()

    # Required fields must be non-empty
    assert slice_val, "slice is required for log events"
    assert module_val, "module is required for log events"
    assert block_val, "block is required for log events"
    assert corr_id, "correlation_id is required for log events"

    envelope: dict[str, Any] = {
        "ts": now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z",
        "level": level,
        "env": env_val,
        "service": svc,
        "service_version": SERVICE_VERSION,
        "slice": slice_val,
        "module": module_val,
        "block": block_val,
        "event": event,
        "correlation_id": corr_id,
    }

    if msg:
        envelope["msg"] = msg[:500]
    if payload:
        envelope["payload"] = payload
    if error:
        envelope["error"] = error
    if duration_ms is not None:
        envelope["duration_ms"] = duration_ms
    if http:
        envelope["http"] = http

    user_id_hash = user_id_hash_var.get()
    if user_id_hash:
        envelope["user_id_hash"] = user_id_hash

    operation_id = operation_id_var.get()
    if operation_id:
        envelope["operation_id"] = operation_id

    return envelope


# ── Public API ────────────────────────────────────────────────────────────

def log_event(
    event: LogEventName,
    *,
    level: str = "info",
    msg: str = "",
    payload: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
    duration_ms: float | None = None,
    http: dict[str, Any] | None = None,
) -> None:
    """Emit a structured log event with the canonical envelope.

    Args:
        event: Event name from LogEventName registry.
        level: Log level (debug, info, warn, error, fatal).
        msg: Human-readable message (max 500 chars).
        payload: Event-specific structured fields (passes through redactor).
        error: Present iff level in {error, fatal}.
        duration_ms: Wall-clock duration for timed operations.
        http: HTTP context (method, route, status).

    Raises:
        ValueError: If event name is not in the registry.
    """
    from app.core.logging_events import LogEventName
    import typing
    # Always validate at runtime to catch typos and enforce the closed registry
    valid_events = typing.get_args(LogEventName)
    if event not in valid_events:
        raise ValueError(f"Unknown log event: {event}. Must be one of {valid_events}")

    try:
        envelope = build_envelope(
            event,
            level=level,
            msg=msg,
            payload=payload,
            error=error,
            duration_ms=duration_ms,
            http=http,
        )

        # Redact payload, error, msg, and http
        if "payload" in envelope:
            envelope["payload"] = redact_dict(envelope["payload"])
        if "error" in envelope:
            envelope["error"] = redact_dict(envelope["error"])
        if "msg" in envelope:
            envelope["msg"] = redact_dict(envelope["msg"])
        if "http" in envelope:
            envelope["http"] = redact_dict(envelope["http"])

        _emit(envelope)
    except Exception:
        # Logging must never crash the application
        try:
            _emit({
                "ts": datetime.now(UTC).isoformat(),
                "level": "error",
                "event": "system.error",
                "msg": "log_event failed",
                "service": service_var.get(),
                "slice": slice_var.get() or "W-CANON-LOG",
                "module": "M-OBSERVABILITY-LOGGING",
                "block": "LOG_EVENT",
            })
        except Exception:
            pass


def _emit(envelope: dict[str, Any]) -> None:
    """Write envelope to stdout as single-line JSON."""
    line = json.dumps(envelope, default=str, ensure_ascii=False)
    _stdout.write(line + "\n")
    _stdout.flush()


_stdout = open(1, "w", encoding="utf-8", closefd=False)


# ── Internal logging.Logger based helper (for ad-hoc debug only) ──────────

import logging as _logging

_logger: _logging.Logger | None = None


def _get_fallback_logger() -> _logging.Logger:
    """Get a fallback stdlib logger for use during context setup only.
    All production code should use log_event() instead."""
    global _logger
    if _logger is None:
        _logger = _logging.getLogger("astro.fallback")
        _logger.setLevel(_logging.INFO)
        if not _logger.handlers:
            handler = _logging.StreamHandler()
            handler.setFormatter(_logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s"
            ))
            _logger.addHandler(handler)
            _logger.propagate = False
    return _logger


# ── Logger setup (for backward-compat with legacy log calls) ──────────────

_log: _logging.Logger | None = None


def setup_logging() -> _logging.Logger:
    """Setup legacy structured logging (deprecated — use log_event() instead).

    Returns:
        Configured logger instance for backward compatibility.
    """
    global _log
    if _log is None:
        _log = _logging.getLogger("astro")
        _log.setLevel(_logging.INFO)
        if _log.handlers:
            _log.handlers.clear()
        handler = _logging.StreamHandler()
        handler.setFormatter(_logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        ))
        _log.addHandler(handler)
        _log.propagate = False
    return _log


# Global legacy logger instance (deprecated — use log_event)
logger = setup_logging()
