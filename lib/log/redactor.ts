// START_MODULE_CONTRACT
// purpose: Library module — lib/log/redactor.ts
// owns:
//   - lib/log/redactor.ts
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

// ############################################################################
// AI_HEADER: MODULE_OBSERVABILITY_REDACTOR_FRONTEND
// ROLE: PII redaction for frontend logging — parity with backend canon §8.4.
// WAVE: W-1.6
// ############################################################################

// ── PII keys (case-insensitive match at any depth) ────────────────────────

const PII_KEYS = new Set([
  "note", "email", "phone", "full_name", "first_name", "last_name", "display_name",
  "fullname", "firstname", "lastname", "displayname",
  "tg_user_id", "telegram_id", "tg_username", "username", "init_data",
  "tg_init_data", "hash", "auth_date",
  "tguserid", "telegramid", "tgusername", "initdata", "tginitdata", "authdate",
  "birth_date", "birth_time", "birth_place", "place", "lat", "latitude",
  "birthdate", "birthtime", "birthplace", "lng", "longitude", "tz", "timezone",
  "password", "password_hash", "token", "access_token", "refresh_token",
  "passwordhash", "accesstoken", "refreshtoken",
  "session_token", "bot_token", "api_key", "secret", "authorization",
  "sessiontoken", "bottoken", "apikey", "cookie", "set-cookie", "setcookie",
  "payment_id", "provider_payment_id", "receipt", "card", "card_number",
  "paymentid", "providerpaymentid", "cardnumber",
  "cvv", "pan", "iban",
  "ip", "remote_addr", "x-forwarded-for", "user_agent",
  "remoteaddr", "xforwardedfor", "useragent",
]);

// ── Allow keys (never redacted) ──────────────────────────────────────────

const ALLOW_KEYS = new Set([
  "correlation_id", "session_id", "packet_id", "user_id_hash",
  "route", "method", "status", "duration_ms",
]);

// ── Value-based patterns (applied to all string values after key redaction) ─

const REDACT_PATTERNS: [RegExp, string][] = [
  [/\b[\w.+-]+@[\w-]+\.[\w.-]+\b/gu, "[redacted-email]"],
  [/\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/g, "[redacted-jwt]"],
  [new RegExp("\\bbearer\\s+[A-Za-z0-9._\\-]+\\b", "gi"), "[redacted-bearer]"],
  [/\btg_user_id[=:\s]+\d{5,}\b/g, "[redacted-tg-id]"],
  [/\b(?:\d{1,3}\.){3}\d{1,3}\b/g, "[redacted-ip]"],
];

/**
 * Redact PII from a value (string, object, array, or primitive).
 * Runs before any console output or ship to backend.
 */
export function redactLogData(data: unknown): unknown {
  if (typeof data === "string") {
    return _redactString(data);
  }
  if (Array.isArray(data)) {
    return data.map(redactLogData);
  }
  if (data !== null && typeof data === "object") {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
      const keyLower = String(key).toLowerCase();
      if (keyLower === "msg" && typeof value === "string") {
        result[key] = _redactString(value);
      } else if (ALLOW_KEYS.has(keyLower)) {
        result[key] = value;
      } else if (PII_KEYS.has(keyLower)) {
        result[key] = "[redacted]";
      } else {
        result[key] = redactLogData(value);
      }
    }
    return result;
  }
  return data;
}

function _redactString(value: string): string {
  let result = value;
  for (const [pattern, replacement] of REDACT_PATTERNS) {
    result = result.replace(pattern, replacement);
  }
  return result;
}

/**
 * Check if we should log to console (dev only, not prod by default).
 */
export function shouldConsoleLog(): boolean {
  if (typeof process === "undefined") return true;
  const env = process.env.NODE_ENV;
  const force = process.env.NEXT_PUBLIC_GRACE_LOG_CONSOLE;
  if (env === "production" && force !== "true") return false;
  return true;
}

/**
 * Redact PII patterns from a string value.
 */
export function redactString(value: string): string {
  return _redactString(value);
}
