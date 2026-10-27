// ############################################################################
// AI_HEADER: TEST_RESUME_GUARD — client resume detection and reload-loop coverage.
// ROLE: Verifies snapshot/stale recovery, ready soft-refetch, cache-busted hard reload, and sessionStorage budget.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-RESUME-GUARD
// purpose: Test the public resume-guard behavior against browser events and a mocked location.
// owns:
//   - __tests__/lib/resume-guard.test.ts
// inputs: jsdom window/document/sessionStorage and mocked logEvent.
// outputs: event, navigation, callback, and reload-history assertions.
// dependencies: lib/grace/resume-guard, Vitest fake timers.
// side_effects: local timers, event listeners, sessionStorage, and a mocked location only.
// emitted_logs: none.
// invariants: tests use public resume-guard exports and never inspect internal state.
// failure_policy: fail on resume, reload-budget, or hard-reload contract drift.
// END_MODULE_CONTRACT: M-TEST-RESUME-GUARD

// START_MODULE_MAP: M-TEST-RESUME-GUARD
// public_entrypoints:
//   - resume-guard behavior tests
// semantic_blocks:
//   - PAGESHOW_AND_VISIBILITY
//   - RELOAD_LOOP_GUARD
//   - HEARTBEAT_AND_CLEANUP
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-RESUME-GUARD

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { mockLogEvent, mockSendBeaconEvent } = vi.hoisted(() => ({
  mockLogEvent: vi.fn(),
  mockSendBeaconEvent: vi.fn(),
}));

vi.mock("@/lib/log", () => ({
  logEvent: mockLogEvent,
}));

vi.mock("@/lib/log/beacon", () => ({
  sendBeaconEvent: mockSendBeaconEvent,
}));

import {
  RESUME_HEARTBEAT_MS,
  RESUME_RELOAD_STORAGE_KEY,
  hardReloadWithCacheBuster,
  installResumeGuard,
} from "@/lib/grace/resume-guard";

const originalLocation = window.location;
let replaceMock: ReturnType<typeof vi.fn>;
let cleanupFns: Array<() => void> = [];
let visibility: "visible" | "hidden" = "visible";

function install(options: Parameters<typeof installResumeGuard>[0]) {
  const cleanup = installResumeGuard(options);
  cleanupFns.push(cleanup);
  return cleanup;
}

function dispatchPageShow(persisted: boolean) {
  const event = new Event("pageshow");
  Object.defineProperty(event, "persisted", { value: persisted });
  window.dispatchEvent(event);
}

function dispatchVisibility() {
  document.dispatchEvent(new Event("visibilitychange"));
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-08-01T12:00:00Z"));
  vi.clearAllMocks();
  window.sessionStorage.clear();
  replaceMock = vi.fn();
  Object.defineProperty(window, "location", {
    writable: true,
    value: {
      href: "https://example.test/day/2026-08-01?foo=bar#section",
      replace: replaceMock,
    },
  });
  visibility = "visible";
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    get: () => visibility,
  });
});

afterEach(() => {
  cleanupFns.forEach((cleanup) => cleanup());
  cleanupFns = [];
  vi.useRealTimers();
  Object.defineProperty(window, "location", {
    writable: true,
    value: originalLocation,
  });
  Reflect.deleteProperty(document, "visibilityState");
  window.sessionStorage.clear();
});

describe("resume-guard pageshow and visibility", () => {
  it("hard reloads a restored snapshot when the screen is not ready", () => {
    install({ isReady: () => false, refetch: vi.fn() });

    dispatchPageShow(true);

    expect(replaceMock).toHaveBeenCalledTimes(1);
    const target = replaceMock.mock.calls[0][0] as string;
    expect(target).toContain("/day/2026-08-01");
    expect(target).toContain("foo=bar");
    expect(target).toMatch(/[?&]r=\d+/);
    expect(mockLogEvent).toHaveBeenCalledWith(
      "resume.snapshot_reload",
      expect.objectContaining({ reason: "pageshow_persisted", reload_count: 1 }),
      expect.objectContaining({ block: "PAGESHOW" }),
    );
    expect(mockSendBeaconEvent).toHaveBeenCalledWith(
      "resume.snapshot_reload",
      expect.objectContaining({ reason: "pageshow_persisted", reload_count: 1 }),
      expect.objectContaining({ block: "PAGESHOW" }),
    );
  });

  it("does not reload a restored snapshot when the screen is ready", () => {
    const refetch = vi.fn();
    install({ isReady: () => true, refetch });

    dispatchPageShow(true);

    expect(replaceMock).not.toHaveBeenCalled();
    expect(refetch).not.toHaveBeenCalled();
  });

  it("soft-refetches a stale ready screen after a visibility resume", () => {
    const refetch = vi.fn();
    install({ isReady: () => true, refetch });
    vi.setSystemTime(new Date("2026-08-01T12:00:31Z"));

    dispatchVisibility();

    expect(refetch).toHaveBeenCalledTimes(1);
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("hard reloads a stale not-ready screen after a visibility resume", () => {
    install({ isReady: () => false, refetch: vi.fn() });
    vi.setSystemTime(new Date("2026-08-01T12:00:31Z"));

    dispatchVisibility();

    expect(replaceMock).toHaveBeenCalledTimes(1);
    expect(mockLogEvent).toHaveBeenCalledWith(
      "resume.stale_reload",
      expect.objectContaining({ reason: "visibility_stale", reload_count: 1 }),
      expect.objectContaining({ block: "VISIBILITY" }),
    );
  });

  it("keeps a stale detector fresh through the five-second heartbeat", () => {
    install({ isReady: () => false, refetch: vi.fn() });
    vi.advanceTimersByTime(RESUME_HEARTBEAT_MS);
    vi.setSystemTime(new Date("2026-08-01T12:00:20Z"));

    dispatchVisibility();

    expect(replaceMock).not.toHaveBeenCalled();
  });
});

describe("resume-guard local-date rollover", () => {
  it("navigates once instead of soft-refetching an old ISO route", () => {
    let localDate = "2026-08-01";
    const refetch = vi.fn();
    const onDateRollover = vi.fn();
    install({
      isReady: () => true,
      refetch,
      getLocalDateKey: () => localDate,
      onDateRollover,
    });

    localDate = "2026-08-02";
    dispatchVisibility();

    expect(onDateRollover).toHaveBeenCalledTimes(1);
    expect(refetch).not.toHaveBeenCalled();
    expect(replaceMock).not.toHaveBeenCalled();

    dispatchVisibility();
    expect(onDateRollover).toHaveBeenCalledTimes(1);
  });

  it("handles a date change on pageshow before persisted-snapshot recovery", () => {
    let localDate = "2026-08-01";
    const onDateRollover = vi.fn();
    install({
      isReady: () => false,
      refetch: vi.fn(),
      getLocalDateKey: () => localDate,
      onDateRollover,
    });

    localDate = "2026-08-02";
    dispatchPageShow(true);

    expect(onDateRollover).toHaveBeenCalledTimes(1);
    expect(replaceMock).not.toHaveBeenCalled();
    expect(mockLogEvent).not.toHaveBeenCalledWith(
      "resume.snapshot_reload",
      expect.anything(),
      expect.anything(),
    );
  });

  it("handles a date change on a non-persisted pageshow", () => {
    let localDate = "2026-08-01";
    const onDateRollover = vi.fn();
    install({
      isReady: () => true,
      refetch: vi.fn(),
      getLocalDateKey: () => localDate,
      onDateRollover,
    });

    localDate = "2026-08-02";
    dispatchPageShow(false);

    expect(onDateRollover).toHaveBeenCalledTimes(1);
  });

  it("keeps normal resume behavior when the local date is unchanged", () => {
    const refetch = vi.fn();
    const onDateRollover = vi.fn();
    install({
      isReady: () => true,
      refetch,
      getLocalDateKey: () => "2026-08-01",
      onDateRollover,
    });
    vi.setSystemTime(new Date("2026-08-01T12:00:31Z"));

    dispatchVisibility();

    expect(onDateRollover).not.toHaveBeenCalled();
    expect(refetch).toHaveBeenCalledTimes(1);
  });
});

describe("resume-guard reload-loop budget", () => {
  it("allows two auto reloads and suppresses the third", () => {
    const onReloadSuppressed = vi.fn();
    install({ isReady: () => false, refetch: vi.fn(), onReloadSuppressed });

    dispatchPageShow(true);
    dispatchPageShow(true);
    dispatchPageShow(true);

    expect(replaceMock).toHaveBeenCalledTimes(2);
    expect(onReloadSuppressed).toHaveBeenCalledTimes(1);
    expect(mockLogEvent).toHaveBeenCalledWith(
      "resume.reload_loop_suppressed",
      expect.objectContaining({ reason: "pageshow_persisted", reload_count: 2 }),
      expect.objectContaining({ block: "RELOAD_LOOP_GUARD" }),
    );
    expect(JSON.parse(window.sessionStorage.getItem(RESUME_RELOAD_STORAGE_KEY) ?? "[]")).toHaveLength(2);
  });

  it("prunes reload timestamps outside the ten-minute window", () => {
    const onReloadSuppressed = vi.fn();
    install({ isReady: () => false, refetch: vi.fn(), onReloadSuppressed });

    dispatchPageShow(true);
    dispatchPageShow(true);
    dispatchPageShow(true);
    expect(replaceMock).toHaveBeenCalledTimes(2);

    vi.setSystemTime(new Date("2026-08-01T12:10:01Z"));
    dispatchPageShow(true);

    expect(replaceMock).toHaveBeenCalledTimes(3);
    expect(onReloadSuppressed).toHaveBeenCalledTimes(1);
  });
});

describe("resume-guard hard reload helper and cleanup", () => {
  it("adds the cache-buster while preserving the current path, query, and hash", () => {
    expect(hardReloadWithCacheBuster(123456789)).toBe(true);
    expect(replaceMock).toHaveBeenCalledWith("/day/2026-08-01?foo=bar&r=123456789#section");
  });

  it("beacons the last known screen state on pagehide", () => {
    install({
      isReady: () => true,
      refetch: vi.fn(),
      getScreenState: () => "ready",
    });

    window.dispatchEvent(new Event("pagehide"));

    expect(mockSendBeaconEvent).toHaveBeenCalledWith(
      "app.pagehide_state",
      { screen_state: "ready", visibility_state: "visible" },
      expect.objectContaining({ block: "PAGEHIDE" }),
    );
  });

  it("removes listeners and the heartbeat on cleanup", () => {
    const cleanup = install({ isReady: () => false, refetch: vi.fn() });
    cleanup();

    dispatchPageShow(true);

    expect(replaceMock).not.toHaveBeenCalled();
  });
});
