// ############################################################################
// AI_HEADER: TEST_TELEGRAM_INIT — Telegram top-inset wiring coverage.
// ROLE: Verifies telegram-init reads both insets, subscribes to every relevant event, and recomputes after fullscreen.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-TELEGRAM-INIT
// purpose: Test the real TelegramInit effect against a synthetic Telegram WebApp.
// owns:
//   - __tests__/lib/telegram-init.test.tsx
// inputs: mocked useTelegram context and a synthetic WebApp event registry.
// outputs: CSS-variable and subscription assertions.
// dependencies: components/telegram-init, @testing-library/react.
// side_effects: document root CSS variables and local event handlers only.
// emitted_logs: none.
// invariants: tests inspect only the public CSS variable and WebApp event contract.
// failure_policy: fail on missing inset source, event subscription, or fullscreen recomputation.
// END_MODULE_CONTRACT: M-TEST-TELEGRAM-INIT

// START_MODULE_MAP: M-TEST-TELEGRAM-INIT
// public_entrypoints:
//   - TelegramInit component tests
// semantic_blocks:
//   - INITIAL_INSET
//   - EVENT_RECOMPUTATION
//   - FULLSCREEN_TRANSITION
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-TELEGRAM-INIT

import { act, cleanup, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => {
  const handlers = new Map<string, () => void>();
  const webApp = {
    version: "8.0",
    colorScheme: "light",
    isExpanded: true,
    isFullscreen: true,
    safeAreaInset: { top: 20, bottom: 0, left: 0, right: 0 },
    contentSafeAreaInset: { top: 0, bottom: 0, left: 0, right: 0 },
    ready: vi.fn(),
    expand: vi.fn(),
    requestFullscreen: vi.fn(),
    disableVerticalSwipes: vi.fn(),
    setHeaderColor: vi.fn(),
    setBackgroundColor: vi.fn(),
    onEvent: vi.fn((name: string, handler: () => void) => {
      handlers.set(name, handler);
    }),
    offEvent: vi.fn((name: string) => {
      handlers.delete(name);
    }),
  };
  return { handlers, webApp };
});

vi.mock("@/components/telegram-provider", () => ({
  useTelegram: () => ({ webApp: mocks.webApp }),
}));

import { TelegramInit } from "@/components/telegram-init";

const TOP_VAR = "--tg-content-safe-area-inset-top";

beforeEach(() => {
  vi.useFakeTimers();
  mocks.handlers.clear();
  mocks.webApp.isFullscreen = true;
  mocks.webApp.contentSafeAreaInset.top = 0;
  mocks.webApp.safeAreaInset.top = 20;
  document.documentElement.style.removeProperty(TOP_VAR);
});

afterEach(() => {
  cleanup();
  vi.runOnlyPendingTimers();
  vi.useRealTimers();
  document.documentElement.style.removeProperty(TOP_VAR);
});

describe("TelegramInit top safe area", () => {
  it("composes safeAreaInset with the fullscreen reserve and subscribes to all inset events", () => {
    render(<TelegramInit />);

    expect(document.documentElement.style.getPropertyValue(TOP_VAR)).toBe("68px");
    expect(mocks.webApp.onEvent).toHaveBeenCalledWith("safeAreaChanged", expect.any(Function));
    expect(mocks.webApp.onEvent).toHaveBeenCalledWith("contentSafeAreaChanged", expect.any(Function));
    expect(mocks.webApp.onEvent).toHaveBeenCalledWith("viewportChanged", expect.any(Function));
    expect(mocks.webApp.onEvent).toHaveBeenCalledWith("fullscreenChanged", expect.any(Function));
    expect(mocks.webApp.requestFullscreen).toHaveBeenCalled();
  });

  it("recomputes when contentSafeAreaChanged supplies a larger content inset", () => {
    render(<TelegramInit />);

    act(() => {
      mocks.webApp.contentSafeAreaInset.top = 44;
      mocks.handlers.get("contentSafeAreaChanged")?.();
    });

    expect(document.documentElement.style.getPropertyValue(TOP_VAR)).toBe("44px");
  });

  it("recomputes when fullscreen ends and content inset is still zero", () => {
    render(<TelegramInit />);

    act(() => {
      mocks.webApp.isFullscreen = false;
      mocks.handlers.get("fullscreenChanged")?.();
    });

    expect(document.documentElement.style.getPropertyValue(TOP_VAR)).toBe("20px");
  });

  it("recomputes when safeAreaChanged raises the safe inset", () => {
    render(<TelegramInit />);

    act(() => {
      mocks.webApp.safeAreaInset.top = 30;
      mocks.handlers.get("safeAreaChanged")?.();
    });

    expect(document.documentElement.style.getPropertyValue(TOP_VAR)).toBe("78px");
  });
});
