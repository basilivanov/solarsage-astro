// ############################################################################
// AI_HEADER: MODULE_HOOK_TODAY_CONVERGENCE — lifecycle hook for the Today envelope.
// ROLE: Coordinates auth-gated fetches, pending polling, impression lineage, and retry cooldowns.
// ############################################################################

// START_MODULE_CONTRACT: M-HOOK-TODAY-CONVERGENCE
// purpose: Expose the transport screen state and generated Today payload to /day/[date].
// owns:
//   - lib/grace/hooks/useTodayConvergence.ts
// inputs: dateParam, shared Telegram auth state (readiness, terminal error, retry), and route retry actions.
// outputs: screenState, optional TodayConvergencePayload, retry cooldown state, and refetch callback.
// dependencies: lib/api/today-convergence.ts, M-HOOK-TELEGRAM-AUTH (shared auth state), next/navigation.
// side_effects: GET/POST day requests, one best-effort day impression, timers, and onboarding redirect.
// emitted_logs: delegated API events plus day.impression_recorded/day.impression_rejected and beacon milestones day.load_start/day.load_ok/day.load_timeout.
// invariants:
//   - pending polling is bounded; impression is once per snapshot and never for preview/locked/unavailable.
//   - the day API is never called while shared auth is loading or ended with an error.
//   - a 401 triggers at most one shared re-auth per mount; a 401 after that becomes screenState=error.
//   - initial and retry follow-up day GETs have a 15 s deadline, one silent retry, then error.
// failure_policy: request failures become error state; retry/poll aborts are ignored after cancellation or unmount.
// END_MODULE_CONTRACT: M-HOOK-TODAY-CONVERGENCE

// START_MODULE_MAP: M-HOOK-TODAY-CONVERGENCE
// public_entrypoints:
//   - DAY_LOAD_TIMEOUT_MS
//   - TodayConvergenceScreenState
//   - UseTodayConvergenceResult
//   - useTodayConvergence
// semantic_blocks:
//   - INITIAL_LOAD: shared-auth-gated date fetch (waits while auth loads, stops on terminal auth error) and onboarding routing.
//   - DAY_DEADLINE: 15 s abort deadline with one silent retry for initial and retry follow-up GETs.
//   - IMPRESSION: post-paint, full-access snapshot guard.
//   - PENDING_POLLING: four-second bounded GET polling.
//   - RETRY: POST retry, Retry-After countdown, bounded 401 -> shared re-auth, and follow-up GET.
//   - LIFECYCLE: abort and unmount safety.
// owned_tests:
//   - __tests__/hooks/useTodayConvergence.test.ts
// END_MODULE_MAP: M-HOOK-TODAY-CONVERGENCE

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTelegramAuth } from "@/hooks/use-telegram-auth";
import {
  fetchTodayConvergence,
  recordDayImpression,
  retryTodayConvergence,
  TodayConvergenceApiError,
} from "@/lib/api/today-convergence";
import { logEvent } from "@/lib/log";
import { sendBeaconEvent } from "@/lib/log/beacon";

export const PENDING_POLL_INTERVAL_MS = 4_000;
export const PENDING_POLL_MAX_MS = 120_000;
export const DEFAULT_RETRY_AFTER_SECONDS = 4;
export const DAY_LOAD_TIMEOUT_MS = 15_000;
const DAY_LOAD_RETRY_DELAY_MS = 2_000;

export type TodayConvergenceScreenState = "loading" | "ready" | "error";

export type UseTodayConvergenceResult = {
  screenState: TodayConvergenceScreenState;
  payload?: Awaited<ReturnType<typeof fetchTodayConvergence>>;
  retryAfterSeconds: number;
  retrying: boolean;
  refetch: () => Promise<void>;
};

type TodayPayload = Awaited<ReturnType<typeof fetchTodayConvergence>>;
type DayLoadResult =
  | { kind: "ok"; payload: TodayPayload }
  | { kind: "error"; error: unknown; afterTimeout: boolean }
  | { kind: "timeout"; attempts: number }
  | { kind: "cancelled" };
type DayLoadSource = "initial_load" | "refetch";

function logDayLoadTimeout(source: DayLoadSource): void {
  const payload = { source, timeout_ms: DAY_LOAD_TIMEOUT_MS, auto_retry: true };
  const meta = {
    level: "error" as const,
    slice: "W-WHITE-SCREEN-RESILIENCE",
    module: "M-HOOK-TODAY-CONVERGENCE",
    block: source === "initial_load" ? "INITIAL_LOAD" : "RETRY",
  };
  logEvent("day.load_timeout", payload, meta);
  sendBeaconEvent("day.load_timeout", payload, meta);
}

function beaconDayLoadStart(source: DayLoadSource): void {
  sendBeaconEvent(
    "day.load_start",
    { source, timeout_ms: DAY_LOAD_TIMEOUT_MS },
    {
      level: "info",
      slice: "W-WHITE-SCREEN-RESILIENCE",
      module: "M-HOOK-TODAY-CONVERGENCE",
      block: source === "initial_load" ? "INITIAL_LOAD" : "RETRY",
    },
  );
}

function beaconDayLoadOk(source: DayLoadSource, attempt: number, startedAt: number): void {
  sendBeaconEvent(
    "day.load_ok",
    { source, attempt },
    {
      level: "info",
      slice: "W-WHITE-SCREEN-RESILIENCE",
      module: "M-HOOK-TODAY-CONVERGENCE",
      block: source === "initial_load" ? "INITIAL_LOAD" : "RETRY",
      duration_ms: Date.now() - startedAt,
    },
  );
}

function isOnboardingFailure(error: unknown): boolean {
  if (!(error instanceof TodayConvergenceApiError)) return false;
  return (
    (error.status === 422 && error.code === "NOT_ONBOARDED") ||
    (error.status === 409 && error.message === "Profile is incomplete")
  );
}

function isUnauthorizedFailure(error: unknown): boolean {
  return error instanceof TodayConvergenceApiError && error.status === 401;
}

function isCurrent(
  mounted: boolean,
  generation: number,
  currentGeneration: number,
  signal?: AbortSignal,
): boolean {
  return mounted && generation === currentGeneration && !signal?.aborted;
}

// START_BLOCK: LIFECYCLE
export function useTodayConvergence(dateParam: string): UseTodayConvergenceResult {
  // START_FUNCTION_CONTRACT: F-M-HOOK-TODAY-CONVERGENCE.useTodayConvergence
  // purpose: Load one date's generated Today envelope and coordinate its lifecycle.
  // inputs: dateParam — today or ISO date route value.
  // returns: screen state, optional payload, retry metadata, and refetch callback.
  // side_effects: auth-gated API calls, deadline/retry timers, impression POST, and onboarding redirect.
  // emitted_logs: delegated API lifecycle, impression, and beacon day.load_start/day.load_ok/day.load_timeout events.
  // error_behavior: active non-onboarding fetch errors expose screenState=error; aborts are ignored.
  // END_FUNCTION_CONTRACT: F-M-HOOK-TODAY-CONVERGENCE.useTodayConvergence
  const router = useRouter();
  const {
    isLoading: authLoading,
    isAuthenticated,
    error: authError,
    retry: retryAuth,
  } = useTelegramAuth();
  const [screenState, setScreenState] = useState<TodayConvergenceScreenState>("loading");
  const [payload, setPayload] = useState<Awaited<ReturnType<typeof fetchTodayConvergence>> | undefined>();
  const [retryAfterSeconds, setRetryAfterSeconds] = useState(0);
  const [retrying, setRetrying] = useState(false);

  const mountedRef = useRef(true);
  const generationRef = useRef(0);
  const loadControllerRef = useRef<AbortController | null>(null);
  const pollControllerRef = useRef<AbortController | null>(null);
  const retryControllerRef = useRef<AbortController | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const loadTimeoutTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const loadRetryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingStartedAtRef = useRef<number | null>(null);
  const impressionSnapshotsRef = useRef(new Set<string>());
  const retryingRef = useRef(false);
  const retryAfterRef = useRef(0);
  const reauthenticatedRef = useRef(false);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      generationRef.current += 1;
      loadControllerRef.current?.abort();
      pollControllerRef.current?.abort();
      retryControllerRef.current?.abort();
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      if (loadTimeoutTimerRef.current) clearTimeout(loadTimeoutTimerRef.current);
      if (loadRetryTimerRef.current) clearTimeout(loadRetryTimerRef.current);
      loadTimeoutTimerRef.current = null;
      loadRetryTimerRef.current = null;
    };
  }, []);

  // START_BLOCK: DAY_DEADLINE
  const fetchDayWithDayDeadline = useCallback(
    async (generation: number, source: DayLoadSource): Promise<DayLoadResult> => {
      const startedAt = Date.now();
      beaconDayLoadStart(source);
      for (let attempt = 1; attempt <= 2; attempt += 1) {
        const controller = new AbortController();
        loadControllerRef.current = controller;
        let timedOut = false;
        let timeoutId: ReturnType<typeof setTimeout> | null = null;

        const timeoutPromise = new Promise<"timeout">((resolve) => {
          timeoutId = setTimeout(() => {
            timedOut = true;
            controller.abort();
            resolve("timeout");
          }, DAY_LOAD_TIMEOUT_MS);
          loadTimeoutTimerRef.current = timeoutId;
        });

        const outcome = await Promise.race([
          fetchTodayConvergence(dateParam, controller.signal).then(
            (nextPayload) => ({ kind: "ok" as const, payload: nextPayload }),
            (error: unknown) => ({ kind: "error" as const, error }),
          ),
          timeoutPromise.then(() => ({ kind: "timeout" as const })),
        ]);

        if (timeoutId !== null) clearTimeout(timeoutId);
        if (loadTimeoutTimerRef.current === timeoutId) loadTimeoutTimerRef.current = null;
        if (!mountedRef.current || generation !== generationRef.current) {
          return { kind: "cancelled" };
        }

        if (!timedOut && outcome.kind === "ok") {
          if (controller.signal.aborted) return { kind: "cancelled" };
          beaconDayLoadOk(source, attempt, startedAt);
          return { kind: "ok", payload: outcome.payload };
        }
        if (!timedOut && outcome.kind === "error") {
          if (controller.signal.aborted) return { kind: "cancelled" };
          return { kind: "error", error: outcome.error, afterTimeout: attempt > 1 };
        }

        // The deadline fired (or a result raced the abort). One silent retry,
        // then a terminal timeout result for the caller to project as error UI.
        if (attempt === 1) {
          await new Promise<void>((resolve) => {
            loadRetryTimerRef.current = setTimeout(resolve, DAY_LOAD_RETRY_DELAY_MS);
          });
          loadRetryTimerRef.current = null;
          if (!mountedRef.current || generation !== generationRef.current) {
            return { kind: "cancelled" };
          }
          continue;
        }
        return { kind: "timeout", attempts: attempt };
      }
      return { kind: "timeout", attempts: 2 };
    },
    [dateParam],
  );
  // END_BLOCK: DAY_DEADLINE

  // START_BLOCK: INITIAL_LOAD
  useEffect(() => {
    const generation = generationRef.current + 1;
    generationRef.current = generation;
    loadControllerRef.current?.abort();
    pollControllerRef.current?.abort();
    retryControllerRef.current?.abort();
    if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    if (loadTimeoutTimerRef.current) clearTimeout(loadTimeoutTimerRef.current);
    if (loadRetryTimerRef.current) clearTimeout(loadRetryTimerRef.current);
    loadTimeoutTimerRef.current = null;
    loadRetryTimerRef.current = null;
    pendingStartedAtRef.current = null;
    retryAfterRef.current = 0;
    retryingRef.current = false;
    setRetrying(false);
    setRetryAfterSeconds(0);
    setPayload(undefined);
    setScreenState("loading");

    if (authLoading) return undefined;

    // Shared auth finished with a terminal error: the authenticated shell already
    // renders auth-error with its own retry, so the day API must not be called.
    // Dev-skip (error === null, isAuthenticated === false) still loads the day.
    if (!isAuthenticated && authError !== null) return undefined;

    const load = async () => {
      const result = await fetchDayWithDayDeadline(generation, "initial_load");
      if (result.kind === "cancelled") return;
      if (result.kind === "ok") {
        setPayload(result.payload);
        setScreenState("ready");
        return;
      }
      if (result.kind === "timeout") {
        logDayLoadTimeout("initial_load");
        setScreenState("error");
        return;
      }

      // A stale session: re-auth once per mount and keep loading. The effect
      // restarts when shared auth becomes authenticated again.
      if (isUnauthorizedFailure(result.error) && !reauthenticatedRef.current) {
        reauthenticatedRef.current = true;
        retryAuth();
        return;
      }
      if (isOnboardingFailure(result.error)) {
        router.replace("/onboarding");
        return;
      }
      if (result.afterTimeout) logDayLoadTimeout("initial_load");
      setScreenState("error");
    };

    void load();
    return () => {
      loadControllerRef.current?.abort();
      if (loadTimeoutTimerRef.current) clearTimeout(loadTimeoutTimerRef.current);
      if (loadRetryTimerRef.current) clearTimeout(loadRetryTimerRef.current);
      loadTimeoutTimerRef.current = null;
      loadRetryTimerRef.current = null;
    };
  }, [authLoading, isAuthenticated, authError, dateParam, router, retryAuth, fetchDayWithDayDeadline]);
  // END_BLOCK: INITIAL_LOAD

  // START_BLOCK: IMPRESSION
  useEffect(() => {
    if (
      screenState !== "ready" ||
      !payload ||
      payload.access.state !== "full" ||
      payload.state === "unavailable" ||
      !payload.snapshotId ||
      impressionSnapshotsRef.current.has(payload.snapshotId)
    ) {
      return undefined;
    }

    const snapshotId = payload.snapshotId;
    impressionSnapshotsRef.current.add(snapshotId);
    let cancelled = false;
    const timer = setTimeout(() => {
      if (!cancelled && mountedRef.current) void recordDayImpression(snapshotId);
    }, 0);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [payload, screenState]);
  // END_BLOCK: IMPRESSION

  // START_BLOCK: PENDING_POLLING
  useEffect(() => {
    const isPending = screenState === "ready" && payload?.contentState === "pending";
    if (!isPending) {
      pendingStartedAtRef.current = null;
      return undefined;
    }

    if (pendingStartedAtRef.current === null) pendingStartedAtRef.current = Date.now();
    const generation = generationRef.current;
    let cancelled = false;

    const schedulePoll = () => {
      if (cancelled || !mountedRef.current) return;
      const startedAt = pendingStartedAtRef.current ?? Date.now();
      const elapsed = Date.now() - startedAt;
      if (elapsed >= PENDING_POLL_MAX_MS) {
        pendingStartedAtRef.current = null;
        return;
      }

      const delay = Math.min(PENDING_POLL_INTERVAL_MS, PENDING_POLL_MAX_MS - elapsed);
      pollTimerRef.current = setTimeout(async () => {
        if (cancelled || !mountedRef.current) return;
        const controller = new AbortController();
        pollControllerRef.current = controller;
        try {
          const nextPayload = await fetchTodayConvergence(dateParam, controller.signal);
          if (!isCurrent(mountedRef.current, generation, generationRef.current, controller.signal)) return;
          setPayload(nextPayload);
          setScreenState("ready");
          if (nextPayload.contentState === "pending") schedulePoll();
          else pendingStartedAtRef.current = null;
        } catch {
          if (isCurrent(mountedRef.current, generation, generationRef.current, controller.signal)) schedulePoll();
        } finally {
          if (pollControllerRef.current === controller) pollControllerRef.current = null;
        }
      }, delay);
    };

    schedulePoll();
    return () => {
      cancelled = true;
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
      pollControllerRef.current?.abort();
    };
  }, [dateParam, payload?.contentState, screenState]);
  // END_BLOCK: PENDING_POLLING

  // START_BLOCK: RETRY
  const refetch = useCallback(async () => {
    // START_FUNCTION_CONTRACT: F-M-HOOK-TODAY-CONVERGENCE.refetch
    // purpose: Request a server retry, enforce a single-flight cooldown, and refresh the envelope.
    // inputs: none; dateParam and route context come from the hook instance.
    // returns: Promise<void> after the retry request and any Retry-After follow-up.
    // side_effects: POST retry, optional countdown/deadline timers, follow-up GET, and state updates.
    // emitted_logs: delegated API lifecycle plus beacon day.load_start/day.load_ok/day.load_timeout milestones.
    // error_behavior: ignores duplicate/cooldown calls; active failures become screenState=error.
    // END_FUNCTION_CONTRACT: F-M-HOOK-TODAY-CONVERGENCE.refetch
    if (
      !mountedRef.current ||
      retryingRef.current ||
      retryAfterRef.current > 0
    ) return;

    const generation = generationRef.current;
    const retryStartedAt = Date.now();
    const controller = new AbortController();
    retryControllerRef.current = controller;
    retryingRef.current = true;
    setRetrying(true);

    const active = () => isCurrent(mountedRef.current, generation, generationRef.current, controller.signal);

    try {
      const result = await retryTodayConvergence(dateParam, controller.signal);
      if (!active()) return;

      if (result.payload) {
        beaconDayLoadOk("refetch", 1, retryStartedAt);
        setPayload(result.payload);
        setScreenState("ready");
        return;
      }

      const seconds = Math.max(0, Math.ceil(result.retryAfterSeconds ?? DEFAULT_RETRY_AFTER_SECONDS));
      for (let remaining = seconds; remaining > 0; remaining -= 1) {
        retryAfterRef.current = remaining;
        setRetryAfterSeconds(remaining);
        await new Promise<void>((resolve) => {
          retryTimerRef.current = setTimeout(resolve, 1_000);
        });
        if (!active()) return;
      }
      retryAfterRef.current = 0;
      setRetryAfterSeconds(0);

      const loadResult = await fetchDayWithDayDeadline(generation, "refetch");
      if (loadResult.kind === "cancelled" || !active()) return;
      if (loadResult.kind === "ok") {
        setPayload(loadResult.payload);
        setScreenState("ready");
        return;
      }
      if (loadResult.kind === "timeout") {
        logDayLoadTimeout("refetch");
        setScreenState("error");
        return;
      }

      // Stale session on the follow-up GET: re-auth once per mount and stay
      // loading so the auth-error screen does not flash.
      if (isUnauthorizedFailure(loadResult.error) && !reauthenticatedRef.current) {
        reauthenticatedRef.current = true;
        setScreenState("loading");
        retryAuth();
        return;
      }
      if (isOnboardingFailure(loadResult.error)) {
        router.replace("/onboarding");
        return;
      }
      if (loadResult.afterTimeout) logDayLoadTimeout("refetch");
      setScreenState("error");
    } catch (error) {
      if (!active()) return;
      // Stale session on retry: re-auth once per mount and stay in loading so the
      // auth-error screen does not flash. INITIAL_LOAD refetches after re-auth.
      if (isUnauthorizedFailure(error) && !reauthenticatedRef.current) {
        reauthenticatedRef.current = true;
        setScreenState("loading");
        retryAuth();
        return;
      }
      if (isOnboardingFailure(error)) {
        router.replace("/onboarding");
        return;
      }
      setScreenState("error");
    } finally {
      if (mountedRef.current && generation === generationRef.current) {
        retryingRef.current = false;
        retryAfterRef.current = 0;
        setRetrying(false);
        setRetryAfterSeconds(0);
      }
      if (retryControllerRef.current === controller) retryControllerRef.current = null;
    }
  }, [dateParam, router, retryAuth, fetchDayWithDayDeadline]);
  // END_BLOCK: RETRY

  return { screenState, payload, retryAfterSeconds, retrying, refetch };
}
// END_BLOCK: LIFECYCLE
