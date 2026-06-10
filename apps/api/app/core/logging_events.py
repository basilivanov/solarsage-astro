# ############################################################################
# AI_HEADER: MODULE_OBSERVABILITY_EVENTS
# ROLE: Canonical event registry — Literal types and payload TypedDicts.
# GENERATED FROM: grace/canon/observability.xml §8.5
# WAVE: W-1.6
# WARNING: This file is code-generated. Manual edits will be overwritten.
# ############################################################################

from __future__ import annotations

from typing import Literal, TypedDict


# ── Event name union ──────────────────────────────────────────────────────

LogEventName = Literal[
    # system / technical
    "system.startup",
    "system.shutdown",
    "system.request",
    "system.error",
    "system.config_loaded",
    # auth / profile
    "auth.tg_login_succeeded",
    "auth.tg_login_failed",
    "auth.tg_login_started",
    "auth.session_expired",
    "auth.logout",
    "auth.dev_login_blocked",
    "auth.dev_login_succeeded",
    "profile.viewed",
    "profile.updated",
    "profile.update_started",
    "profile.update_failed",
    "profile.cache_invalidation_requested",
    "profile.cache_invalidated",
    "profile.lazy_created",
    # day / calendar
    "day.viewed",
    "day.payload_built",
    "calendar.viewed",
    # access / referral / payments
    "access.checked",
    "access.subscription_granted",
    "referral.invite_created",
    "referral.signup_credited",
    "payment.intent_created",
    "payment.succeeded",
    "payment.failed",
    "payment.webhook_received",
    # horary
    "horary.question_created",
    "horary.question_create_failed",
    "horary.credit_spent",
    "horary.credit_refunded",
    "horary.generation_started",
    "horary.generation_succeeded",
    "horary.generation_failed",
    "horary.generation_enqueued",
    # natal
    "natal.preview_requested",
    "natal.preview_succeeded",
    "natal.preview_failed",
    "natal.context_cache_hit",
    "natal.context_cache_miss",
    "natal.context_build_started",
    "natal.context_cached",
    "natal.context_invalidated",
    "natal.sidecar_called",
    "natal.sidecar_failed",
    "natal.report_generation_requested",
    "natal.report_generation_started",
    "natal.report_generation_succeeded",
    "natal.report_generation_failed",
    # sidecar / scoring / llm
    "sidecar.called",
    "scoring.computed",
    "llm.requested",
    "llm.response_validated",
    "llm.response_rejected",
    # frontend ux
    "ui.error_boundary_tripped",
    "ui.fetch_started",
    "ui.fetch_succeeded",
    "ui.fetch_failed",
]


# ── Payload TypedDicts ────────────────────────────────────────────────────

class EventPayloadSystemStartup(TypedDict, total=False):
    pid: int
    env: str

class EventPayloadSystemRequest(TypedDict, total=False):
    cache_status: Literal["hit", "miss", "bypass", "n/a"]

class EventPayloadAuthTgLoginSucceeded(TypedDict, total=False):
    is_new_user: bool

class EventPayloadAuthTgLoginFailed(TypedDict, total=False):
    reason: Literal["bad_hmac", "expired", "malformed"]

class EventPayloadProfileUpdated(TypedDict, total=False):
    changed_fields: list[str]

class EventPayloadDayViewed(TypedDict, total=False):
    date: str
    access_state: Literal["full", "preview", "locked"]
    cached: bool

class EventPayloadDayPayloadBuilt(TypedDict, total=False):
    contract_version: str
    duration_ms: float

class EventPayloadCalendarViewed(TypedDict, total=False):
    month: str

class EventPayloadAccessChecked(TypedDict, total=False):
    state: Literal["full", "preview", "locked"]

class EventPayloadPaymentFailed(TypedDict, total=False):
    reason: str

class EventPayloadSidecarCalled(TypedDict, total=False):
    endpoint: str
    duration_ms: float
    cache_status: Literal["hit", "miss"]

class EventPayloadScoringComputed(TypedDict, total=False):
    day_status: str

class EventPayloadLlmRequested(TypedDict, total=False):
    prompt_version: str

class EventPayloadLlmResponseValidated(TypedDict, total=False):
    ok: bool

class EventPayloadLlmResponseRejected(TypedDict, total=False):
    reason: Literal["schema_invalid", "banned_token", "timeout"]

class EventPayloadUiErrorBoundaryTripped(TypedDict, total=False):
    component: str

class EventPayloadSystemError(TypedDict, total=False):
    kind: str

class EventPayloadHoraryQuestionCreated(TypedDict, total=False):
    question_id_hash: str
    category: str

class EventPayloadNatalContextCacheHit(TypedDict, total=False):
    duration_ms: float

class EventPayloadNatalSidecarCalled(TypedDict, total=False):
    endpoint: str
    duration_ms: float
    cache_status: Literal["hit", "miss"]

# ── Event → Payload mapping ───────────────────────────────────────────────

EVENT_PAYLOAD_TYPES: dict[str, type[TypedDict]] = {
    "system.startup": EventPayloadSystemStartup,
    "system.request": EventPayloadSystemRequest,
    "auth.tg_login_succeeded": EventPayloadAuthTgLoginSucceeded,
    "auth.tg_login_failed": EventPayloadAuthTgLoginFailed,
    "profile.updated": EventPayloadProfileUpdated,
    "day.viewed": EventPayloadDayViewed,
    "day.payload_built": EventPayloadDayPayloadBuilt,
    "calendar.viewed": EventPayloadCalendarViewed,
    "access.checked": EventPayloadAccessChecked,
    "payment.failed": EventPayloadPaymentFailed,
    "sidecar.called": EventPayloadSidecarCalled,
    "scoring.computed": EventPayloadScoringComputed,
    "llm.requested": EventPayloadLlmRequested,
    "llm.response_validated": EventPayloadLlmResponseValidated,
    "llm.response_rejected": EventPayloadLlmResponseRejected,
    "ui.error_boundary_tripped": EventPayloadUiErrorBoundaryTripped,
    "system.error": EventPayloadSystemError,
    "horary.question_created": EventPayloadHoraryQuestionCreated,
    "natal.context_cache_hit": EventPayloadNatalContextCacheHit,
    "natal.sidecar_called": EventPayloadNatalSidecarCalled,
}
