// ############################################################################
// AI_HEADER: MODULE_TELEGRAM_INIT_DATA
// ROLE: Resolve Telegram WebApp initData from the SDK instance or the #tgWebAppData URL hash fallback.
// DEPENDENCIES: none
// GRACE_ANCHORS: [TELEGRAM_INIT_DATA]
// WAVE: W-AUTH-TIMEOUT-RACE-FIX
// ############################################################################

// START_MODULE_CONTRACT: M-TELEGRAM-INIT-DATA
// purpose: Resolve Telegram initData independently of SDK load timing, using the #tgWebAppData URL hash as a fallback when webApp.initData is empty.
// owns:
//   - lib/telegram/init-data.ts
// inputs:
//   - webApp: object with optional initData (Telegram WebApp instance or null)
//   - window.location.hash (browser only)
// outputs:
//   - parseTgWebAppDataFromHash(): string (decoded initData or '')
//   - resolveTelegramInitData(webApp): string (decoded initData or '')
// dependencies: none
// side_effects: reads window.location.hash
// invariants:
//   - SSR-safe: no window or empty hash returns ''
//   - webApp.initData takes precedence over the hash fallback
//   - never throws on malformed hash
// failure_policy: unparsable hash fails closed to ''
// non_goals:
//   - initData validation, HMAC verification, logging
// END_MODULE_CONTRACT: M-TELEGRAM-INIT-DATA

// START_MODULE_MAP: M-TELEGRAM-INIT-DATA
// public_entrypoints:
//   - parseTgWebAppDataFromHash
//   - resolveTelegramInitData
//   - TelegramInitDataSource
// semantic_blocks:
//   - HASH_PARSER: extract tgWebAppData from window.location.hash
//   - RESOLVER: merge webApp.initData with the hash fallback
// owned_tests:
//   - __tests__/components/telegram-provider.test.tsx
// END_MODULE_MAP: M-TELEGRAM-INIT-DATA

/** Minimal structural view of a Telegram WebApp needed for initData resolution. */
export interface TelegramInitDataSource {
  initData?: string | null;
}

// START_BLOCK: HASH_PARSER
// START_FUNCTION_CONTRACT: F-M-TELEGRAM-INIT-DATA.parseTgWebAppDataFromHash
// purpose: Read the tgWebAppData parameter from the current URL hash.
// inputs: none (reads window.location.hash)
// returns: decoded initData string, or '' when absent, empty or unparsable
// side_effects: reads window.location.hash
// emitted_logs: none
// error_behavior: SSR (no window) or malformed hash returns ''
// END_FUNCTION_CONTRACT: F-M-TELEGRAM-INIT-DATA.parseTgWebAppDataFromHash
export function parseTgWebAppDataFromHash(): string {
  if (typeof window === 'undefined') return '';

  const hash = window.location?.hash ?? '';
  if (!hash) return '';

  const rawHash = hash.startsWith('#') ? hash.slice(1) : hash;
  if (!rawHash) return '';

  try {
    return new URLSearchParams(rawHash).get('tgWebAppData') ?? '';
  } catch {
    return '';
  }
}
// END_BLOCK: HASH_PARSER

// START_BLOCK: RESOLVER
// START_FUNCTION_CONTRACT: F-M-TELEGRAM-INIT-DATA.resolveTelegramInitData
// purpose: Resolve initData from the WebApp instance, falling back to the URL hash.
// inputs: webApp — TelegramInitDataSource | null | undefined
// returns: non-empty initData string, or '' when neither source provides one
// side_effects: reads window.location.hash via the fallback
// emitted_logs: none
// error_behavior: never throws; missing sources return ''
// END_FUNCTION_CONTRACT: F-M-TELEGRAM-INIT-DATA.resolveTelegramInitData
export function resolveTelegramInitData(
  webApp: TelegramInitDataSource | null | undefined,
): string {
  return webApp?.initData || parseTgWebAppDataFromHash();
}
// END_BLOCK: RESOLVER
