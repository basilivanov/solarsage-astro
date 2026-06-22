// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

// ############################################################################
// AI_HEADER: MODULE_LOG_FRONTEND
// ROLE: Frontend structured logger — canonical envelope per §8.2.
// DEPENDENCIES: lib/log/shipper, lib/log/events.gen
// GRACE_ANCHORS: [LOGGER_CLASS, LOG_METHODS, LOG_EVENT_API]
// WAVE: W-1.6, W-1.7
// ############################################################################

// START_MODULE_CONTRACT: M-LOG-FRONTEND
// purpose: Provide structured logging for frontend with canonical envelope
//   (ts, level, env, service, slice, module, block, event, correlation_id, payload).
//   Ships to backend via POST /api/_log when GRACE_LOG_SHIPPING is enabled.
// owns:
//   - lib/log/index.ts
// inputs:
//   - event: LogEventName (typed string-literal union)
//   - payload?: event-specific payload (passes through redactor)
//   - meta?: { slice?, module?, block?, level?, msg?, duration_ms? }
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
//   - redacts PII before ship
// failure_policy:
//   - shipper errors are handled internally (no throw)
// END_MODULE_CONTRACT: M-LOG-FRONTEND

import { getLogShipper, type CanonEnvelope } from "./shipper";
import type { LogEventName } from "./events.gen";
import { redactLogData, redactString as _redactString, shouldConsoleLog } from "./redactor";

// Re-export for convenience
export type { LogEventName } from "./events.gen";

// ── Log level type ────────────────────────────────────────────────────────

export type LogLevel = "debug" | "info" | "warn" | "error" | "fatal";

// ── Context ───────────────────────────────────────────────────────────────

interface LogContext {
  slice: string;
  module: string;
  block: string;
  event: LogEventName;
  correlation_id?: string;
}

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

export function setCorrelationId(id: string) {
  _correlationId = id;
}

export function getCorrelationId(): string | null {
  return _correlationId;
}

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
  // Default to dev, override via build-time env
  if (process.env.NODE_ENV === "production") {
    if (process.env.NEXT_PUBLIC_VERCEL_ENV === "preview") return "staging";
    return "prod";
  }
  return "dev";
}

// ── Public API ────────────────────────────────────────────────────────────

export function logEvent(
  event: LogEventName,
  payload?: Record<string, unknown>,
  meta?: {
    level?: LogLevel;
    msg?: string;
    slice?: string;
    module?: string;
    block?: string;
    duration_ms?: number;
  },
): void {
  try {
    const level = meta?.level || "info";
    const minLevel = levelPriority[LOG_LEVEL] ?? 1;
    if ((levelPriority[level] ?? 99) < minLevel) return;

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

// ── Convenience wrappers ─────────────────────────────────────────────────

export function logStart(
  event: LogEventName,
  payload?: Record<string, unknown>,
  meta?: { slice?: string; module?: string; block?: string },
) {
  logEvent(event, payload, { ...meta, level: "info" });
}

export function logSuccess(
  event: LogEventName,
  payload?: Record<string, unknown>,
  meta?: { slice?: string; module?: string; block?: string; duration_ms?: number },
) {
  logEvent(event.replace("_started", "_succeeded") as LogEventName, payload, { ...meta, level: "info" });
}

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

// ── Legacy Logger class (deprecated — use logEvent directly) ─────────────

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
export type { CanonEnvelope } from "./shipper";
