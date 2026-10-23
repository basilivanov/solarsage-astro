// ############################################################################
// AI_HEADER: MODULE_LOG_BEACON
// ROLE: Immediate single-envelope telemetry via navigator.sendBeacon.
// DEPENDENCIES: lib/log/events.gen, lib/log/redactor, lib/log/shipper (types only)
// GRACE_ANCHORS: [BEACON_SESSION, BEACON_SEND]
// WAVE: W-WHITE-SCREEN-RESILIENCE
// ############################################################################

// START_MODULE_CONTRACT: M-LOG-BEACON
// purpose: Send canonical log envelopes immediately through navigator.sendBeacon,
//   bypassing the batching shipper, with one page-lifetime correlation/session id.
// owns:
//   - lib/log/beacon.ts
// inputs:
//   - event: LogEventName
//   - payload?: event-specific payload (passes through redactor)
//   - meta?: { level?, msg?, slice?, module?, block?, duration_ms?, error?, http?, operation_id?, phase? }
// outputs:
//   - boolean from navigator.sendBeacon (false when unavailable or rejected)
// dependencies:
//   - M-OBSERVABILITY-EVENTS (LogEventName)
//   - M-OBSERVABILITY-REDACTOR-FRONTEND (redactLogData, redactString)
// side_effects:
//   - one navigator.sendBeacon POST to /api/_log per call
// invariants:
//   - envelope is a single canonical object (not a batch)
//   - Blob content type is application/json
//   - correlation_id is one page-lifetime id shared by every beacon
//   - never throws, even when browser APIs are unavailable
// failure_policy:
//   - unavailable sendBeacon or serialization failure returns false without retry
// non_goals:
//   - no batching, retry queue, storage, or changes to the regular log shipper
// END_MODULE_CONTRACT: M-LOG-BEACON

// START_MODULE_MAP: M-LOG-BEACON
// public_entrypoints:
//   - BEACON_ENDPOINT
//   - sendBeaconEvent
//   - getBeaconCorrelationId
//   - resetBeaconForTests
// semantic_blocks:
//   - BEACON_SESSION: page-lifetime correlation/session id.
//   - BEACON_SEND: canonical envelope assembly and sendBeacon transport.
// owned_tests:
//   - __tests__/lib/beacon.test.ts
// END_MODULE_MAP: M-LOG-BEACON

import type { LogEventName } from "./events.gen";
import { redactLogData, redactString } from "./redactor";
import type { CanonEnvelope } from "./shipper";

export const BEACON_ENDPOINT = "/api/_log";

type BeaconLevel = "debug" | "info" | "warn" | "error" | "fatal";

export type BeaconMeta = {
  level?: BeaconLevel;
  msg?: string;
  slice?: string;
  module?: string;
  block?: string;
  duration_ms?: number;
  error?: Record<string, unknown>;
  http?: Record<string, unknown>;
  operation_id?: string;
  phase?: string;
};

const SERVICE_VERSION: string =
  (typeof process !== "undefined" &&
    (process.env?.NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA ||
      process.env?.NEXT_PUBLIC_GRACE_SERVICE_VERSION)) ||
  "dev";

const SERVICE_VERSION_SHORT = SERVICE_VERSION.length > 7
  ? SERVICE_VERSION.slice(0, 7)
  : SERVICE_VERSION;

let beaconCorrelationId: string | null = null;

function createUuid(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (char) => {
    const random = (Math.random() * 16) | 0;
    const value = char === "x" ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });
}

function getEnv(): string {
  if (process.env.NODE_ENV === "production") {
    if (process.env.NEXT_PUBLIC_VERCEL_ENV === "preview") return "staging";
    return "prod";
  }
  return "dev";
}

// START_BLOCK: BEACON_SESSION
// START_FUNCTION_CONTRACT: F-M-LOG-BEACON.getBeaconCorrelationId
// purpose: Return the shared page-lifetime correlation id, minting it on first use.
// inputs: none
// returns: string (crypto.randomUUID-compatible id)
// side_effects: stores the id in module scope for the lifetime of the page
// emitted_logs: none
// error_behavior: falls back to a local UUID v4-shaped generator when crypto is unavailable
// END_FUNCTION_CONTRACT: F-M-LOG-BEACON.getBeaconCorrelationId
export function getBeaconCorrelationId(): string {
  if (beaconCorrelationId === null) beaconCorrelationId = createUuid();
  return beaconCorrelationId;
}
// END_BLOCK: BEACON_SESSION

// START_BLOCK: BEACON_SEND
function buildEnvelope(
  event: LogEventName,
  payload: Record<string, unknown> | undefined,
  meta: BeaconMeta | undefined,
): CanonEnvelope {
  const correlationId = getBeaconCorrelationId();
  const envelope: CanonEnvelope = {
    ts: new Date().toISOString(),
    level: meta?.level || "info",
    env: getEnv(),
    service: "web",
    service_version: SERVICE_VERSION_SHORT,
    slice: meta?.slice || "W-WHITE-SCREEN-RESILIENCE",
    module: meta?.module || "M-LOG-BEACON",
    block: meta?.block || "BEACON_SEND",
    event,
    correlation_id: correlationId,
  };

  if (meta?.msg) envelope.msg = redactString(meta.msg).slice(0, 500);
  if (payload) envelope.payload = redactLogData(payload) as Record<string, unknown>;
  if (meta?.error) envelope.error = redactLogData(meta.error) as Record<string, unknown>;
  if (meta?.http) envelope.http = redactLogData(meta.http) as Record<string, unknown>;
  if (meta?.operation_id) envelope.operation_id = meta.operation_id;
  if (meta?.phase) envelope.phase = meta.phase;
  if (meta?.duration_ms !== undefined) envelope.duration_ms = meta.duration_ms;

  return envelope;
}

// START_FUNCTION_CONTRACT: F-M-LOG-BEACON.sendBeaconEvent
// purpose: Serialize one canonical envelope and hand it to navigator.sendBeacon immediately.
// inputs: event — registry event name; payload — optional event payload; meta — optional envelope context.
// returns: true when the browser accepted the beacon request; otherwise false.
// side_effects: sends one POST /api/_log request, creates the shared page id on first call.
// emitted_logs: the supplied event name.
// error_behavior: unavailable/blocked sendBeacon and serialization errors return false without throwing.
// END_FUNCTION_CONTRACT: F-M-LOG-BEACON.sendBeaconEvent
export function sendBeaconEvent(
  event: LogEventName,
  payload?: Record<string, unknown>,
  meta?: BeaconMeta,
): boolean {
  try {
    if (
      typeof navigator === "undefined" ||
      typeof navigator.sendBeacon !== "function"
    ) {
      return false;
    }

    const envelope = buildEnvelope(event, payload, meta);
    const body = new Blob([JSON.stringify(envelope)], { type: "application/json" });
    return navigator.sendBeacon(BEACON_ENDPOINT, body);
  } catch {
    return false;
  }
}

// START_FUNCTION_CONTRACT: F-M-LOG-BEACON.resetBeaconForTests
// purpose: Drop the page-lifetime beacon id so tests can assert deterministic sessions.
// inputs: none
// returns: void
// side_effects: clears module-scoped beaconCorrelationId
// emitted_logs: none
// error_behavior: never throws
// END_FUNCTION_CONTRACT: F-M-LOG-BEACON.resetBeaconForTests
export function resetBeaconForTests(): void {
  beaconCorrelationId = null;
}
// END_BLOCK: BEACON_SEND
