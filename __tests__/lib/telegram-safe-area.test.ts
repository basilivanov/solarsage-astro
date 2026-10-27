// ############################################################################
// AI_HEADER: TEST_TELEGRAM_SAFE_AREA — top inset composition coverage.
// ROLE: Verifies content/safe inset precedence and the fullscreen reserve.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-TELEGRAM-SAFE-AREA
// purpose: Test the pure Telegram top safe-area calculation used by telegram-init.
// owns:
//   - __tests__/lib/telegram-safe-area.test.ts
// inputs: synthetic Telegram WebApp safe-area objects.
// outputs: deterministic px assertions.
// dependencies: lib/telegram/safe-area.
// side_effects: none.
// emitted_logs: none.
// invariants: the helper never throws and never returns a negative inset.
// failure_policy: fail on inset precedence or fullscreen-reserve drift.
// END_MODULE_CONTRACT: M-TEST-TELEGRAM-SAFE-AREA

// START_MODULE_MAP: M-TEST-TELEGRAM-SAFE-AREA
// public_entrypoints:
//   - computeTelegramTopSafeAreaInset tests
// semantic_blocks:
//   - INSET_PRECEDENCE
//   - FULLSCREEN_RESERVE
//   - INVALID_VALUES
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-TELEGRAM-SAFE-AREA

import { describe, expect, it } from "vitest";
import {
  TELEGRAM_FULLSCREEN_TOP_RESERVE_PX,
  computeTelegramTopSafeAreaInset,
} from "@/lib/telegram/safe-area";

describe("computeTelegramTopSafeAreaInset", () => {
  it("uses the larger content inset when fullscreen content clearance is present", () => {
    expect(
      computeTelegramTopSafeAreaInset({
        contentSafeAreaInset: { top: 44 },
        safeAreaInset: { top: 20 },
        isFullscreen: true,
      }),
    ).toBe(44);
  });

  it("falls back to safeAreaInset.top outside fullscreen", () => {
    expect(
      computeTelegramTopSafeAreaInset({
        contentSafeAreaInset: { top: 0 },
        safeAreaInset: { top: 20 },
        isFullscreen: false,
      }),
    ).toBe(20);
  });

  it("adds the fullscreen reserve above safeAreaInset.top when content top is zero", () => {
    expect(
      computeTelegramTopSafeAreaInset({
        contentSafeAreaInset: { top: 0 },
        safeAreaInset: { top: 20 },
        isFullscreen: true,
      }),
    ).toBe(20 + TELEGRAM_FULLSCREEN_TOP_RESERVE_PX);
  });

  it("reserves the fullscreen minimum even when both Telegram insets are zero", () => {
    expect(
      computeTelegramTopSafeAreaInset({
        contentSafeAreaInset: { top: 0 },
        safeAreaInset: { top: 0 },
        isFullscreen: true,
      }),
    ).toBe(TELEGRAM_FULLSCREEN_TOP_RESERVE_PX);
    expect(TELEGRAM_FULLSCREEN_TOP_RESERVE_PX).toBeGreaterThanOrEqual(44);
    expect(TELEGRAM_FULLSCREEN_TOP_RESERVE_PX).toBeLessThanOrEqual(56);
  });

  it("does not add the fullscreen reserve when content clearance is already positive", () => {
    expect(
      computeTelegramTopSafeAreaInset({
        contentSafeAreaInset: { top: 12 },
        safeAreaInset: { top: 20 },
        isFullscreen: true,
      }),
    ).toBe(20);
  });

  it("fails closed for missing, negative, and non-finite values", () => {
    expect(computeTelegramTopSafeAreaInset(null)).toBe(0);
    expect(computeTelegramTopSafeAreaInset(undefined)).toBe(0);
    expect(
      computeTelegramTopSafeAreaInset({
        contentSafeAreaInset: { top: Number.NaN },
        safeAreaInset: { top: -4 },
        isFullscreen: true,
      }),
    ).toBe(TELEGRAM_FULLSCREEN_TOP_RESERVE_PX);
    expect(
      computeTelegramTopSafeAreaInset({
        contentSafeAreaInset: { top: Number.POSITIVE_INFINITY },
        safeAreaInset: { top: -1 },
        isFullscreen: false,
      }),
    ).toBe(0);
  });
});
