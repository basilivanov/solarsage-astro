// ############################################################################
// AI_HEADER: TEST_HOOK_TODAY_CONVERGENCE — lifecycle coverage for the new day hook.
// ROLE: Verifies generated payload loading, impression lineage, bounded polling, retry cooldown, and unmount safety.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-HOOK-TODAY-CONVERGENCE
// purpose: Test the public useTodayConvergence result and lifecycle side effects.
// owns:
//   - __tests__/hooks/useTodayConvergence.test.ts
// inputs: generated Today fixtures and mocked API functions.
// outputs: hook state and API call assertions.
// dependencies: useTodayConvergence, today-convergence API client, React Testing Library.
// side_effects: local timers and callback spies only.
// emitted_logs: none.
// invariants: no state is written after unmount; impression policy follows access/state axes.
// failure_policy: fail on lifecycle, polling, or retry contract drift.
// END_MODULE_CONTRACT: M-TEST-HOOK-TODAY-CONVERGENCE

// START_MODULE_MAP: M-TEST-HOOK-TODAY-CONVERGENCE
// public_entrypoints:
//   - initial state and impression tests
//   - pending polling tests
//   - retry and unmount tests
// semantic_blocks:
//   - INITIAL_AND_IMPRESSION
//   - PENDING_POLLING
//   - RETRY_AND_LIFECYCLE
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-HOOK-TODAY-CONVERGENCE

import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  accessLocked,
  accessPreview,
  contentPending,
  heroSupportive,
  quietSteady,
  stateUnavailable,
} from "../fixtures/today_convergence_v2";

const mocks = vi.hoisted(() => ({
  fetchTodayConvergence: vi.fn(),
  retryTodayConvergence: vi.fn(),
  recordDayImpression: vi.fn(),
  replace: vi.fn(),
}));

vi.mock("@/lib/api/today-convergence", () => ({
  fetchTodayConvergence: mocks.fetchTodayConvergence,
  retryTodayConvergence: mocks.retryTodayConvergence,
  recordDayImpression: mocks.recordDayImpression,
  TodayConvergenceApiError: class TodayConvergenceApiError extends Error {
    kind: "network" | "invalid" | "http";
    status: number;
    code?: string;
    constructor(message: string, kind: "network" | "invalid" | "http", status: number, code?: string) {
      super(message);
      this.kind = kind;
      this.status = status;
      this.code = code;
    }
  },
}));

vi.mock("@/hooks/use-telegram-auth", () => ({
  useTelegramAuth: () => ({ isLoading: false, isAuthenticated: true, error: null }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => mocks,
}));

import {
  DEFAULT_RETRY_AFTER_SECONDS,
  PENDING_POLL_INTERVAL_MS,
  useTodayConvergence,
} from "@/lib/grace/hooks/useTodayConvergence";

afterEach(() => {
  vi.useRealTimers();
});

beforeEach(() => {
  vi.clearAllMocks();
});

async function flushPromises() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

// START_BLOCK: INITIAL_AND_IMPRESSION
describe("useTodayConvergence initial state and impression", () => {
  it("loads ready content and records one full-access impression", async () => {
    mocks.fetchTodayConvergence.mockResolvedValue(heroSupportive);
    const { result, rerender } = renderHook(() => useTodayConvergence("2026-08-01"));

    await waitFor(() => expect(result.current.screenState).toBe("ready"));
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(mocks.recordDayImpression).toHaveBeenCalledTimes(1);
    expect(result.current.payload).toBe(heroSupportive);
    expect(mocks.fetchTodayConvergence).toHaveBeenCalledWith("2026-08-01", expect.any(AbortSignal));

    rerender();
    await flushPromises();
    expect(mocks.recordDayImpression).toHaveBeenCalledTimes(1);
  });

  it.each([
    ["preview", accessPreview],
    ["locked", accessLocked],
    ["calculation unavailable", stateUnavailable],
  ])("does not record an impression for %s", async (_name, fixture) => {
    mocks.fetchTodayConvergence.mockResolvedValue(fixture);
    const { result } = renderHook(() => useTodayConvergence("2026-08-01"));

    await waitFor(() => expect(result.current.screenState).toBe("ready"));
    await new Promise((resolve) => setTimeout(resolve, 5));
    expect(mocks.recordDayImpression).not.toHaveBeenCalled();
  });
});
// END_BLOCK: INITIAL_AND_IMPRESSION

// START_BLOCK: PENDING_POLLING
describe("useTodayConvergence pending polling", () => {
  it("polls pending content and stops after the next ready payload", async () => {
    vi.useFakeTimers();
    mocks.fetchTodayConvergence
      .mockResolvedValueOnce(contentPending)
      .mockResolvedValueOnce(quietSteady);
    const { result } = renderHook(() => useTodayConvergence("2026-08-01"));

    await flushPromises();
    expect(result.current.payload).toBe(contentPending);
    expect(mocks.fetchTodayConvergence).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(PENDING_POLL_INTERVAL_MS);
    });
    await flushPromises();
    expect(result.current.payload).toBe(quietSteady);
    expect(mocks.fetchTodayConvergence).toHaveBeenCalledTimes(2);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(PENDING_POLL_INTERVAL_MS * 2);
    });
    expect(mocks.fetchTodayConvergence).toHaveBeenCalledTimes(2);
  });
});
// END_BLOCK: PENDING_POLLING

// START_BLOCK: RETRY_AND_LIFECYCLE
describe("useTodayConvergence retry and lifecycle", () => {
  it("turns a 202 retry into a countdown and follow-up GET", async () => {
    vi.useFakeTimers();
    mocks.fetchTodayConvergence
      .mockResolvedValueOnce(stateUnavailable)
      .mockResolvedValueOnce(heroSupportive);
    mocks.retryTodayConvergence.mockResolvedValue({ retryAfterSeconds: 2 });
    const { result } = renderHook(() => useTodayConvergence("2026-08-01"));

    await flushPromises();
    let retryPromise!: Promise<void>;
    await act(async () => {
      retryPromise = result.current.refetch();
      await Promise.resolve();
    });
    expect(mocks.retryTodayConvergence).toHaveBeenCalledWith("2026-08-01", expect.any(AbortSignal));
    expect(result.current.retryAfterSeconds).toBe(2);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });
    expect(result.current.retryAfterSeconds).toBe(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });
    await retryPromise;
    expect(result.current.retryAfterSeconds).toBe(0);
    expect(result.current.payload).toBe(heroSupportive);
    expect(result.current.screenState).toBe("ready");
  });

  it("uses the documented default cooldown when Retry-After is absent", async () => {
    vi.useFakeTimers();
    mocks.fetchTodayConvergence
      .mockResolvedValueOnce(stateUnavailable)
      .mockResolvedValueOnce(heroSupportive);
    mocks.retryTodayConvergence.mockResolvedValue({});
    const { result } = renderHook(() => useTodayConvergence("2026-08-01"));

    await flushPromises();
    let retryPromise!: Promise<void>;
    await act(async () => {
      retryPromise = result.current.refetch();
      await Promise.resolve();
    });
    expect(result.current.retryAfterSeconds).toBe(DEFAULT_RETRY_AFTER_SECONDS);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(DEFAULT_RETRY_AFTER_SECONDS * 1_000);
    });
    await retryPromise;
    expect(result.current.payload).toBe(heroSupportive);
  });

  it("aborts an in-flight load on unmount without applying its result", async () => {
    let resolveRequest: (value: typeof heroSupportive) => void = () => undefined;
    mocks.fetchTodayConvergence.mockReturnValue(
      new Promise((resolve) => {
        resolveRequest = resolve;
      }),
    );
    const { result, unmount } = renderHook(() => useTodayConvergence("2026-08-01"));
    unmount();
    resolveRequest(heroSupportive);
    await flushPromises();
    expect(result.current.screenState).toBe("loading");
    expect(mocks.fetchTodayConvergence.mock.calls[0]?.[1].aborted).toBe(true);
  });
});
// END_BLOCK: RETRY_AND_LIFECYCLE

// START_BLOCK: ERROR_AND_REDIRECT
describe("useTodayConvergence error and onboarding branches", () => {
  it("exposes the error screen state when the initial fetch fails", async () => {
    mocks.fetchTodayConvergence.mockRejectedValue(new Error("offline"));
    const { result } = renderHook(() => useTodayConvergence("2026-08-01"));

    await waitFor(() => expect(result.current.screenState).toBe("error"));
  });

  it("redirects to onboarding for a 422 NOT_ONBOARDED failure", async () => {
    const { TodayConvergenceApiError } = await import("@/lib/api/today-convergence");
    mocks.fetchTodayConvergence.mockRejectedValue(
      new TodayConvergenceApiError("Profile is incomplete", "http", 422, "NOT_ONBOARDED"),
    );
    renderHook(() => useTodayConvergence("2026-08-01"));

    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/onboarding"));
  });

  it("reschedules polling after a failed poll attempt", async () => {
    vi.useFakeTimers();
    mocks.fetchTodayConvergence
      .mockResolvedValueOnce(contentPending)
      .mockRejectedValueOnce(new Error("poll offline"))
      .mockResolvedValueOnce(quietSteady);
    const { result } = renderHook(() => useTodayConvergence("2026-08-01"));

    await flushPromises();
    expect(result.current.payload).toBe(contentPending);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(PENDING_POLL_INTERVAL_MS);
    });
    await flushPromises();
    expect(mocks.fetchTodayConvergence).toHaveBeenCalledTimes(2);
    expect(result.current.payload).toBe(contentPending);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(PENDING_POLL_INTERVAL_MS);
    });
    await flushPromises();
    expect(result.current.payload).toBe(quietSteady);
  });
});
// END_BLOCK: ERROR_AND_REDIRECT
