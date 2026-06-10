// ############################################################################
// AI_HEADER: MODULE_OBSERVABILITY_EVENTS_FRONTEND
// ROLE: Canonical event registry — TypeScript string-literal union.
// GENERATED FROM: grace/canon/observability.xml §8.5
// WAVE: W-1.6
// WARNING: This file MUST match the canon. Edit the XML, not this file.
// ############################################################################

export type LogEventName =
  // system / technical
  | "system.startup"
  | "system.shutdown"
  | "system.request"
  | "system.error"
  | "system.config_loaded"
  // auth / profile
  | "auth.tg_login_started"
  | "auth.tg_login_succeeded"
  | "auth.tg_login_failed"
  | "auth.session_expired"
  | "auth.logout"
  | "auth.dev_login_blocked"
  | "auth.dev_login_succeeded"
  | "profile.viewed"
  | "profile.update_started"
  | "profile.updated"
  | "profile.update_failed"
  | "profile.cache_invalidation_requested"
  | "profile.cache_invalidated"
  | "profile.lazy_created"
  // day / calendar
  | "day.viewed"
  | "day.payload_built"
  | "calendar.viewed"
  // access / referral / payments
  | "access.checked"
  | "access.subscription_granted"
  | "referral.invite_created"
  | "referral.signup_credited"
  | "payment.intent_created"
  | "payment.succeeded"
  | "payment.failed"
  | "payment.webhook_received"
  // horary
  | "horary.question_created"
  | "horary.question_create_failed"
  | "horary.credit_spent"
  | "horary.credit_refunded"
  | "horary.generation_enqueued"
  | "horary.generation_started"
  | "horary.generation_succeeded"
  | "horary.generation_failed"
  // natal
  | "natal.preview_requested"
  | "natal.preview_succeeded"
  | "natal.preview_failed"
  | "natal.context_cache_hit"
  | "natal.context_cache_miss"
  | "natal.context_build_started"
  | "natal.context_cached"
  | "natal.context_invalidated"
  | "natal.sidecar_called"
  | "natal.sidecar_failed"
  | "natal.report_generation_requested"
  | "natal.report_generation_started"
  | "natal.report_generation_succeeded"
  | "natal.report_generation_failed"
  // sidecar / scoring / llm
  | "sidecar.called"
  | "scoring.computed"
  | "llm.requested"
  | "llm.response_validated"
  | "llm.response_rejected"
  // chat
  | "chat.quota_increased"
  // frontend ux
  | "ui.error_boundary_tripped"
  | "ui.fixtures_mode_toggled"
  | "ui.fetch_started"
  | "ui.fetch_succeeded"
  | "ui.fetch_failed";
