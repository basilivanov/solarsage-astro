// ############################################################################
// AI_HEADER: MODULE_TELEGRAM_SAFE_AREA — pure Telegram top safe-area composition.
// ROLE: Combines Telegram safeAreaInset/contentSafeAreaInset into one top reserve.
// ############################################################################

// START_MODULE_CONTRACT: M-TELEGRAM-SAFE-AREA
// purpose: Compute the Telegram-owned top inset while preserving fullscreen content clearance.
// owns:
//   - lib/telegram/safe-area.ts
// inputs: Telegram WebApp-like object with safeAreaInset, contentSafeAreaInset, and isFullscreen.
// outputs: non-negative top inset in CSS pixels.
// dependencies: none.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - contentSafeAreaInset.top wins when it is larger than safeAreaInset.top.
//   - fullscreen with contentSafeAreaInset.top=0 adds a 44-56 px reserve above safeAreaInset.top.
//   - malformed, negative, or non-finite values fail closed to zero.
// failure_policy: never throws; invalid values are treated as zero.
// END_MODULE_CONTRACT: M-TELEGRAM-SAFE-AREA

// START_MODULE_MAP: M-TELEGRAM-SAFE-AREA
// public_entrypoints:
//   - TELEGRAM_FULLSCREEN_TOP_RESERVE_PX
//   - TelegramSafeAreaSource
//   - computeTelegramTopSafeAreaInset
// semantic_blocks:
//   - INSET_COMPOSITION: content/safe inset merge with a fullscreen reserve.
// owned_tests:
//   - __tests__/lib/telegram-safe-area.test.ts
// END_MODULE_MAP: M-TELEGRAM-SAFE-AREA

/** Fullscreen reserve used when Telegram reports no content inset. */
export const TELEGRAM_FULLSCREEN_TOP_RESERVE_PX = 48;

export interface TelegramSafeAreaSource {
  safeAreaInset?: { top?: number | null } | null;
  contentSafeAreaInset?: { top?: number | null } | null;
  isFullscreen?: boolean | null;
}

function nonNegativeInset(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : 0;
}

// START_BLOCK: INSET_COMPOSITION
// START_FUNCTION_CONTRACT: F-M-TELEGRAM-SAFE-AREA.computeTelegramTopSafeAreaInset
// purpose: Compose the Telegram top inset for the existing max(var, env, 1rem) consumer formula.
// inputs: webApp — Telegram WebApp-like safe-area source.
// returns: max(contentSafeAreaInset.top, safeAreaInset.top + fullscreen reserve), in px.
// side_effects: none.
// emitted_logs: none.
// error_behavior: never throws; invalid values count as zero.
// END_FUNCTION_CONTRACT: F-M-TELEGRAM-SAFE-AREA.computeTelegramTopSafeAreaInset
export function computeTelegramTopSafeAreaInset(
  webApp: TelegramSafeAreaSource | null | undefined,
): number {
  const contentTop = nonNegativeInset(webApp?.contentSafeAreaInset?.top);
  const safeTop = nonNegativeInset(webApp?.safeAreaInset?.top);
  const fullscreenReserve =
    webApp?.isFullscreen === true && contentTop === 0
      ? TELEGRAM_FULLSCREEN_TOP_RESERVE_PX
      : 0;
  return Math.max(contentTop, safeTop + fullscreenReserve);
}
// END_BLOCK: INSET_COMPOSITION
