// ############################################################################
// AI_HEADER: MODULE_LOG_FRONTEND
// ROLE: Frontend structured logger — canonical envelope per §8.2.
// DEPENDENCIES: lib/log/shipper, lib/log/events.gen, lib/log/redactor
// GRACE_ANCHORS: [LOGGER_CLASS, LOG_METHODS, LOG_EVENT_API]
// WAVE: W-1.6, W-1.7, W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-LOG-FRONTEND
// purpose: Provide structured logging for frontend with canonical envelope
//   (ts, level, env, service, slice, module, block, event, correlation_id, payload, error, http, operation_id, phase, duration_ms).
//   Ships to backend via POST /api/_log when GRACE_LOG_SHIPPING is enabled.
// owns:
//   - lib/log/index.ts
// inputs:
//   - event: LogEventName (typed string-literal union)
//   - payload?: event-specific payload (passes through redactor)
//   - meta?: { slice?, module?, block?, level?, msg?, duration_ms?, error?, http?, operation_id?, phase?, sample_rate? }
// outputs:
//   - console logs (dev)
//   - POST /api/_log (when GRACE_LOG_SHIPPING enabled)
// dependencies:
//   - M-LOG-SHIPPER (getLogShipper)
//   - M-OBSERVABILITY-EVENTS (LogEventName)
// side_effects:
//   - console.log in development
//   - network requests when shipping enabled
// invariants:
//   - envelope format matches canon §8.2
//   - every event has slice/module/block/event/correlation_id
//   - sample_rate applies only to debug/info/warn; error and fatal bypass sampling
//   - sample_rate 0 drops always, 1 emits always, NaN/Infinity fail-open (emit)
//   - redacts PII before ship
// failure_policy:
//   - shipper errors are handled internally (no throw)
// END_MODULE_CONTRACT: M-LOG-FRONTEND

// START_MODULE_MAP: M-LOG-FRONTEND
// public_entrypoints:
//   - logEvent
//   - logStart
//   - logSuccess
//   - logFailure
//   - setCorrelationId
//   - getCorrelationId
//   - setLogContext
//   - logger
// semantic_blocks:
//   - CORRELATION_CONTEXT: correlation ID and log context management.
//   - LOG_EVENT_API: core logEvent function with sampling and envelope assembly.
//   - CONVENIENCE_WRAPPERS: logStart, logSuccess, logFailure helpers.
//   - LEGACY_LOGGER: deprecated Logger class export.
// owned_tests:
//   - __tests__/lib/logger.test.ts
//   - __tests__/lib/capture-error.test.ts
// END_MODULE_MAP: M-LOG-FRONTEND

import { getLogShipper, type CanonEnvelope } from "./shipper";
import type { LogEventName } from "./events.gen";
import { redactLogData, redactString as _redactString, shouldConsoleLog } from "./redactor";

// Re-export for convenience
export type { LogEventName } from "./events.gen";

// ── Log level type ────────────────────────────────────────────────────────

export type LogLevel = "debug" | "info" | "warn" | "error" | "fatal";

export type LogEventMeta = {
  level?: LogLevel;
  msg?: string;
  slice?: string;
  module?: string;
  block?: string;
  duration_ms?: number;
  error?: Record<string, unknown>;
  http?: Record<string, unknown>;
  operation_id?: string;
  phase?: string;
  sample_rate?: number;
};

// ── Context ───────────────────────────────────────────────────────────────

const levelPriority: Record<string, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
  fatal: 4,
};

const LOG_LEVEL = (process.env.NEXT_PUBLIC_LOG_LEVEL || "info").toLowerCase();
const SERVICE_VERSION: string =
  (typeof process !== "undefined" &&
    (process.env?.NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA ||
      process.env?.NEXT_PUBLIC_GRACE_SERVICE_VERSION)) ||
  "dev";

const SERVICE_VERSION_SHORT = SERVICE_VERSION.length > 7
  ? SERVICE_VERSION.slice(0, 7)
  : SERVICE_VERSION;

let _correlationId: string | null = null;
let _sessionId: string | null = null;
let _slice: string = "";
let _module: string = "";
let _block: string = "";

// START_BLOCK: CORRELATION_CONTEXT
// START_FUNCTION_CONTRACT: F-M-LOG-FRONTEND.setCorrelationId
// purpose: Store global correlation ID for frontend log events.
// inputs: id - correlation ID string
// returns: void
// side_effects: updates module-scoped _correlationId
// emitted_logs: none
// END_FUNCTION_CONTRACT: F-M-LOG-FRONTEND.setCorrelationId
export function setCorrelationId(id: string) {
  _correlationId = id;
}

// START_FUNCTION_CONTRACT: F-M-LOG-FRONTEND.getCorrelationId
// purpose: Retrieve current global correlation ID.
// inputs: none
// returns: string | null
// side_effects: none
// emitted_logs: none
// END_FUNCTION_CONTRACT: F-M-LOG-FRONTEND.getCorrelationId
export function getCorrelationId(): string | null {
  return _correlationId;
}

// START_FUNCTION_CONTRACT: F-M-LOG-FRONTEND.setLogContext
// purpose: Set default slice, module, and block for subsequent log events.
// inputs: slice, module, block strings
// returns: void
// side_effects: updates module-scoped context variables
// emitted_logs: none
// END_FUNCTION_CONTRACT: F-M-LOG-FRONTEND.setLogContext
export function setLogContext(slice: string, module: string, block: string) {
  _slice = slice;
  _module = module;
  _block = block;
}

function generateId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

function getEnv(): string {
  if (process.env.NODE_ENV === "production") {
    if (process.env.NEXT_PUBLIC_VERCEL_ENV === "preview") return "staging";
    return "prod";
  }
  return "dev";
}
// END_BLOCK: CORRELATION_CONTEXT

function shouldSample(level: LogLevel, sampleRate?: number): boolean {
  if (level === "error" || level === "fatal") return true;
  if (sampleRate === undefined) return true;
  if (typeof sampleRate !== "number" || !Number.isFinite(sampleRate)) return true;

  const clampedRate = Math.max(0, Math.min(1, sampleRate));
  if (clampedRate === 0) return false;
  if (clampedRate === 1) return true;

  return Math.random() < clampedRate;
}

// START_BLOCK: LOG_EVENT_API
// START_FUNCTION_CONTRACT: F-M-LOG-FRONTEND.logEvent
// purpose: Core structured logger function creating canonical envelopes and enqueueing to shipper.
// inputs: event name, payload, meta options
// returns: void
// side_effects: passes envelope to getLogShipper().enqueue
// emitted_logs: event
// END_FUNCTION_CONTRACT: F-M-LOG-FRONTEND.logEvent
export function logEvent(
  event: LogEventName,
  payload?: Record<string, unknown>,
  meta?: LogEventMeta,
): void {
  try {
    const level = meta?.level || "info";
    const minLevel = levelPriority[LOG_LEVEL] ?? 1;
    if ((levelPriority[level] ?? 99) < minLevel) return;

    if (!shouldSample(level, meta?.sample_rate)) return;

    const correlationId = _correlationId || generateId();
    const env = getEnv();

    const envelope: CanonEnvelope = {
      ts: new Date().toISOString(),
      level,
      env,
      service: "web",
      service_version: SERVICE_VERSION_SHORT,
      slice: meta?.slice || _slice || "W-FRONTEND",
      module: meta?.module || _module || "M-LOG-FRONTEND",
      block: meta?.block || _block || "LOG_EVENT",
      event,
      correlation_id: correlationId,
    };

    if (meta?.msg) envelope.msg = meta.msg.slice(0, 500);
    if (payload) envelope.payload = redactLogData(payload) as Record<string, unknown>;
    if (meta?.error) envelope.error = redactLogData(meta.error) as Record<string, unknown>;
    if (meta?.http) {
      const sanitizedHttp: Record<string, unknown> = {};
      if (typeof meta.http.method === "string") sanitizedHttp.method = meta.http.method;
      if (typeof meta.http.route_template === "string") sanitizedHttp.route_template = meta.http.route_template;
      if (typeof meta.http.status === "number") sanitizedHttp.status = meta.http.status;
      envelope.http = redactLogData(sanitizedHttp) as Record<string, unknown>;
    }
    if (meta?.operation_id) envelope.operation_id = meta.operation_id;
    if (meta?.phase) envelope.phase = meta.phase;
    if (meta?.duration_ms !== undefined) envelope.duration_ms = meta.duration_ms;
    if (_sessionId) envelope.session_id = _sessionId;

    // Redact msg before console/ship
    if (envelope.msg) envelope.msg = _redactString(envelope.msg);

    // Console in dev only (or when explicitly enabled)
    if (shouldConsoleLog()) {
      const tag = correlationId ? `[${correlationId.slice(0, 8)}]` : "";
      const levelTag = level.toUpperCase().padEnd(5);
      console.log(
        `${tag}[${levelTag}] ${event}`,
        envelope.msg ?? "",
        payload ? "(redacted)" : "",
      );
    }

    // Ship to backend
    getLogShipper().enqueue(envelope);
  } catch {
    // Logger must never crash the app
  }
}
// END_BLOCK: LOG_EVENT_API

// START_BLOCK: CONVENIENCE_WRAPPERS
// START_FUNCTION_CONTRACT: F-M-LOG-FRONTEND.logStart
// purpose: Convenience wrapper for logging operation start events with level info.
// inputs: event, payload, meta
// returns: void
// side_effects: calls logEvent
// emitted_logs: event
// END_FUNCTION_CONTRACT: F-M-LOG-FRONTEND.logStart
export function logStart(
  event: LogEventName,
  payload?: Record<string, unknown>,
  meta?: { slice?: string; module?: string; block?: string },
) {
  logEvent(event, payload, { ...meta, level: "info" });
}

// START_FUNCTION_CONTRACT: F-M-LOG-FRONTEND.logSuccess
// purpose: Convenience wrapper for logging operation success events with level info.
// inputs: event, payload, meta
// returns: void
// side_effects: calls logEvent
// emitted_logs: event
// END_FUNCTION_CONTRACT: F-M-LOG-FRONTEND.logSuccess
export function logSuccess(
  event: LogEventName,
  payload?: Record<string, unknown>,
  meta?: { slice?: string; module?: string; block?: string; duration_ms?: number },
) {
  logEvent(event.replace("_started", "_succeeded") as LogEventName, payload, { ...meta, level: "info" });
}

// START_FUNCTION_CONTRACT: F-M-LOG-FRONTEND.logFailure
// purpose: Convenience wrapper for logging operation failure events with level error.
// inputs: event, error, payload, meta
// returns: void
// side_effects: calls logEvent
// emitted_logs: event
// END_FUNCTION_CONTRACT: F-M-LOG-FRONTEND.logFailure
export function logFailure(
  event: LogEventName,
  error: Error | string,
  payload?: Record<string, unknown>,
  meta?: { slice?: string; module?: string; block?: string; duration_ms?: number },
) {
  const errorPayload = {
    ...payload,
    error: typeof error === "string" ? error : error.message,
  };
  logEvent(event, errorPayload, { ...meta, level: "error" });
}
// END_BLOCK: CONVENIENCE_WRAPPERS

// START_BLOCK: LEGACY_LOGGER
interface LogOptions {
  correlation_id?: string;
  extra?: Record<string, any>;
}

class Logger {
  private shipper = getLogShipper();

  debug(message: string, options?: LogOptions): void {
    this.log("debug", message, options);
  }

  info(message: string, options?: LogOptions): void {
    this.log("info", message, options);
  }

  warn(message: string, options?: LogOptions): void {
    this.log("warn", message, options);
  }

  error(message: string, options?: LogOptions): void {
    this.log("error", message, options);
  }

  private log(level: string, message: string, options?: LogOptions): void {
    const minLevel = levelPriority[LOG_LEVEL] ?? 1;
    if ((levelPriority[level] ?? 99) < minLevel) return;

    const corrId = options?.correlation_id || _correlationId;
    const env = getEnv();

    const envelope: CanonEnvelope = {
      ts: new Date().toISOString(),
      level,
      env,
      service: "web",
      service_version: SERVICE_VERSION_SHORT,
      slice: _slice || "W-CANON-LOG",
      module: _module || "M-LOG-FRONTEND",
      block: _block || "LOG_METHODS",
      event: "system.request",
      correlation_id: corrId || generateId(),
      msg: message.slice(0, 500),
    };

    if (options?.extra) {
      envelope.payload = options.extra;
    }
    if (_sessionId) envelope.session_id = _sessionId;

    // Redact payload before console/ship
    if (envelope.payload) envelope.payload = redactLogData(envelope.payload) as Record<string, unknown>;
    if (envelope.msg) envelope.msg = _redactString(envelope.msg);

    // Console in dev only
    if (shouldConsoleLog()) {
      const tag = corrId ? `[${corrId.slice(0, 8)}]` : '';
      const levelTag = level.toUpperCase().padEnd(5);
      console.log(`${tag}[${levelTag}]`, envelope.msg ?? "", options?.extra ? "(redacted)" : "");
    }

    this.shipper.enqueue(envelope);
  }
}

export const logger = new Logger();
// END_BLOCK: LEGACY_LOGGER
export type { CanonEnvelope } from "./shipper";
