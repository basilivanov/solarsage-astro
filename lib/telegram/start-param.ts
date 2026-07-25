// ############################################################################
// AI_HEADER: MODULE_TELEGRAM_START_PARAM — closed Telegram start_param classifier and sessionStorage manager.
// ROLE: Parses and classifies Telegram WebApp start_param into referral, promo, or ignored intent, and safely manages pending promo tokens in sessionStorage.
// DEPENDENCIES: none
// GRACE_ANCHORS: [TELEGRAM_START_PARAM]
// WAVE: W-NAMED-PROMO-CAMPAIGN
// ############################################################################

// START_MODULE_CONTRACT: M-TELEGRAM-START-PARAM
// purpose: Classify raw Telegram WebApp start_param strings into structured intents and manage pending promo tokens in sessionStorage without leaking PII.
// owns:
//   - lib/telegram/start-param.ts
// inputs:
//   - rawParam: string | null | undefined
// outputs:
//   - StartParamIntent ({ kind: "referral", code } | { kind: "promo", token } | { kind: "ignored" })
//   - sessionStorage promo token management functions
//   - localStorage consumed-token marker functions
// dependencies: none
// side_effects:
//   - reads/writes/clears sessionStorage for promo pending token
//   - reads/writes localStorage for promo consumed marker (reload-loop guard)
//   - updates window.history.replaceState to remove tgWebAppStartParam query parameter from visible URL
// invariants:
//   - referral codes are strictly numeric (/^\d+$/)
//   - promo tokens are strictly Base58 lowercase 12..16 chars containing at least one letter
//   - input parameters are evaluated exact without trimming leading/trailing whitespace
//   - pending token uses sessionStorage only; consumed marker uses localStorage only
//   - storage functions never throw
// failure_policy:
//   - invalid start params or storage errors fail-closed to ignored or null without throwing
// END_MODULE_CONTRACT: M-TELEGRAM-START-PARAM

// START_MODULE_MAP: M-TELEGRAM-START-PARAM
// public_entrypoints:
//   - classifyStartParam
//   - savePendingPromoToken
//   - getPendingPromoToken
//   - clearPendingPromoToken
//   - markPromoTokenConsumed
//   - isPromoTokenConsumed
//   - cleanStartParamFromUrl
//   - PROMO_PENDING_SESSION_KEY
//   - PROMO_CONSUMED_STORAGE_KEY
// semantic_blocks:
//   - CLASSIFIER: pure regex classification into referral, promo, or ignored
//   - STORAGE_HELPERS: safe sessionStorage operations for pending promo token
//   - CONSUMED_MARKER: localStorage consumed-token marker (reload-loop guard)
//   - URL_CLEANUP: query parameter removal from visible browser location
// owned_tests:
//   - __tests__/lib/start-param.test.ts
// END_MODULE_MAP: M-TELEGRAM-START-PARAM

export type StartParamIntent =
  | { kind: "referral"; code: string }
  | { kind: "promo"; token: string }
  | { kind: "ignored" }

export const PROMO_PENDING_SESSION_KEY = "__astro_pending_promo_token"
export const PROMO_CONSUMED_STORAGE_KEY = "__astro_consumed_promo_token"

const REFERRAL_REGEX = /^\d+$/
const PROMO_REGEX = /^(?=.{12,16}$)(?=.*[a-hj-km-np-z])[a-hj-km-np-z2-9]+$/

// START_BLOCK: CLASSIFIER
// START_FUNCTION_CONTRACT: F-M-TELEGRAM-START-PARAM.classifyStartParam
// purpose: Pure classification of raw Telegram WebApp start_param into referral, promo, or ignored intent.
// inputs: rawParam — string | null | undefined
// returns: StartParamIntent
// side_effects: none
// emitted_logs: none
// error_behavior: returns { kind: "ignored" } on null, empty, whitespace-padded or invalid input
// END_FUNCTION_CONTRACT: F-M-TELEGRAM-START-PARAM.classifyStartParam
export function classifyStartParam(rawParam?: string | null): StartParamIntent {
  if (!rawParam || typeof rawParam !== "string") {
    return { kind: "ignored" }
  }

  if (REFERRAL_REGEX.test(rawParam)) {
    return { kind: "referral", code: rawParam }
  }

  if (PROMO_REGEX.test(rawParam)) {
    return { kind: "promo", token: rawParam }
  }

  return { kind: "ignored" }
}
// END_BLOCK: CLASSIFIER

// START_BLOCK: STORAGE_HELPERS
// START_FUNCTION_CONTRACT: F-M-TELEGRAM-START-PARAM.savePendingPromoToken
// purpose: Validate and store a pending promo token into sessionStorage.
// inputs: token — promo token string
// returns: boolean — true if successfully stored, false otherwise
// side_effects: writes to sessionStorage
// emitted_logs: none
// error_behavior: catches storage exceptions and returns false without throwing
// END_FUNCTION_CONTRACT: F-M-TELEGRAM-START-PARAM.savePendingPromoToken
export function savePendingPromoToken(token: string): boolean {
  if (!token || typeof token !== "string") return false
  if (!PROMO_REGEX.test(token)) return false

  try {
    if (typeof window !== "undefined" && window.sessionStorage) {
      window.sessionStorage.setItem(PROMO_PENDING_SESSION_KEY, token)
      return true
    }
  } catch {
    // sessionStorage unavailable or blocked
  }
  return false
}

// START_FUNCTION_CONTRACT: F-M-TELEGRAM-START-PARAM.getPendingPromoToken
// purpose: Retrieve and validate pending promo token from sessionStorage, clearing it if invalid.
// inputs: none
// returns: string | null — validated promo token or null
// side_effects: reads and potentially clears invalid item from sessionStorage
// emitted_logs: none
// error_behavior: catches storage exceptions and returns null without throwing
// END_FUNCTION_CONTRACT: F-M-TELEGRAM-START-PARAM.getPendingPromoToken
export function getPendingPromoToken(): string | null {
  try {
    if (typeof window !== "undefined" && window.sessionStorage) {
      const stored = window.sessionStorage.getItem(PROMO_PENDING_SESSION_KEY)
      if (!stored) return null
      if (PROMO_REGEX.test(stored)) {
        return stored
      }
      // Invalid stored value -> clean up
      clearPendingPromoToken()
    }
  } catch {
    // sessionStorage unavailable
  }
  return null
}

// START_FUNCTION_CONTRACT: F-M-TELEGRAM-START-PARAM.clearPendingPromoToken
// purpose: Remove pending promo token from sessionStorage.
// inputs: none
// returns: void
// side_effects: removes item from sessionStorage
// emitted_logs: none
// error_behavior: catches storage exceptions without throwing
// END_FUNCTION_CONTRACT: F-M-TELEGRAM-START-PARAM.clearPendingPromoToken
export function clearPendingPromoToken(): void {
  try {
    if (typeof window !== "undefined" && window.sessionStorage) {
      window.sessionStorage.removeItem(PROMO_PENDING_SESSION_KEY)
    }
  } catch {
    // sessionStorage unavailable
  }
}
// END_BLOCK: STORAGE_HELPERS

// START_BLOCK: CONSUMED_MARKER
// START_FUNCTION_CONTRACT: F-M-TELEGRAM-START-PARAM.markPromoTokenConsumed
// purpose: Persist a localStorage marker that a promo token reached a terminal
//   completed state (redeem 200 or ALREADY_REDEEMED), so future app loads —
//   where the Telegram webview re-delivers the same start_param — do NOT
//   re-store it and re-preview, which would cause an infinite reload loop.
// inputs: token — promo token string
// returns: void
// side_effects: writes to localStorage
// emitted_logs: none
// error_behavior: catches storage exceptions without throwing
// END_FUNCTION_CONTRACT: F-M-TELEGRAM-START-PARAM.markPromoTokenConsumed
export function markPromoTokenConsumed(token: string): void {
  if (!token || typeof token !== "string") return
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem(PROMO_CONSUMED_STORAGE_KEY, token)
    }
  } catch {
    // localStorage unavailable
  }
}

// START_FUNCTION_CONTRACT: F-M-TELEGRAM-START-PARAM.isPromoTokenConsumed
// purpose: Check whether a promo token was already consumed on this device.
// inputs: token — promo token string
// returns: boolean — true if the stored consumed marker matches the token
// side_effects: reads localStorage
// emitted_logs: none
// error_behavior: returns false on storage exceptions
// END_FUNCTION_CONTRACT: F-M-TELEGRAM-START-PARAM.isPromoTokenConsumed
export function isPromoTokenConsumed(token: string): boolean {
  if (!token || typeof token !== "string") return false
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      return window.localStorage.getItem(PROMO_CONSUMED_STORAGE_KEY) === token
    }
  } catch {
    // localStorage unavailable
  }
  return false
}
// END_BLOCK: CONSUMED_MARKER

// START_BLOCK: URL_CLEANUP
// START_FUNCTION_CONTRACT: F-M-TELEGRAM-START-PARAM.cleanStartParamFromUrl
// purpose: Remove tgWebAppStartParam query parameter from visible URL using history.replaceState while preserving path, hash and other params.
// inputs: none
// returns: void
// side_effects: updates window.history.replaceState
// emitted_logs: none
// error_behavior: catches history API errors without throwing
// END_FUNCTION_CONTRACT: F-M-TELEGRAM-START-PARAM.cleanStartParamFromUrl
export function cleanStartParamFromUrl(): void {
  try {
    if (typeof window === "undefined" || !window.location || !window.history || !window.history.replaceState) {
      return
    }

    const url = new URL(window.location.href)
    if (url.searchParams.has("tgWebAppStartParam")) {
      url.searchParams.delete("tgWebAppStartParam")
      const newRelativeUrl = url.pathname + (url.search ? url.search : "") + url.hash
      window.history.replaceState(window.history.state, "", newRelativeUrl)
    }
  } catch {
    // history API error swallowed safely
  }
}
// END_BLOCK: URL_CLEANUP
