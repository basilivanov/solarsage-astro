// ############################################################################
// AI_HEADER: MODULE_OBSERVABILITY_REDACTOR_FRONTEND
// ROLE: PII redaction for frontend logging — parity with backend canon §8.4.
// WAVE: W-1.6
// ############################################################################

// ── PII keys (case-insensitive match at any depth) ────────────────────────

const PII_KEYS = new Set([
  "note", "email", "phone", "full_name", "first_name", "last_name", "display_name",
  "tg_user_id", "telegram_id", "tg_username", "username", "init_data",
  "tg_init_data", "hash", "auth_date",
  "birth_date", "birth_time", "birth_place", "place", "lat", "latitude",
  "lon", "lng", "longitude", "tz", "timezone",
  "password", "password_hash", "token", "access_token", "refresh_token",
  "session_token", "bot_token", "api_key", "secret", "authorization",
  "cookie", "set-cookie",
  "payment_id", "provider_payment_id", "receipt", "card", "card_number",
  "cvv", "pan", "iban",
  "ip", "remote_addr", "x-forwarded-for", "user_agent",
]);

// ── Allow keys (never redacted) ──────────────────────────────────────────

const ALLOW_KEYS = new Set([
  "correlation_id", "session_id", "packet_id", "user_id_hash",
  "route", "method", "status", "duration_ms",
]);

// ── Value-based patterns (applied to all string values after key redaction) ─

const REDACT_PATTERNS: [RegExp, string][] = [
  [/^[\w.+-]+@[\w-]+\.[\w.-]+$/u, "[redacted-email]"],
  [/\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/, "[redacted-jwt]"],
  [new RegExp("\\bbearer\\s+[A-Za-z0-9._\\-]+\\b", "i"), "[redacted-bearer]"],
  [/\btg_user_id[=:\s]+\d{5,}\b/, "[redacted-tg-id]"],
  [/\b(?:\d{1,3}\.){3}\d{1,3}\b/, "[redacted-ip]"],
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
