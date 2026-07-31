// ############################################################################
// AI_HEADER: MODULE_HOOK_TODAY_CONVERGENCE — lifecycle hook for the Today envelope.
// ROLE: Coordinates auth-gated fetches, pending polling, impression lineage, and retry cooldowns.
// ############################################################################

// START_MODULE_CONTRACT: M-HOOK-TODAY-CONVERGENCE
// purpose: Expose the transport screen state and generated Today payload to /day/[date].
// owns:
//   - lib/grace/hooks/useTodayConvergence.ts
// inputs: dateParam, Telegram auth readiness, and route retry actions.
// outputs: screenState, optional TodayConvergencePayload, retry cooldown state, and refetch callback.
// dependencies: lib/api/today-convergence.ts, hooks/use-telegram-auth, next/navigation.
// side_effects: GET/POST day requests, one best-effort day impression, timers, and onboarding redirect.
// emitted_logs: delegated API events plus day.impression_recorded/day.impression_rejected.
// invariants: pending polling is bounded; impression is once per snapshot and never for preview/locked/unavailable.
// failure_policy: request failures become error state; retry/poll aborts are ignored after cancellation or unmount.
// END_MODULE_CONTRACT: M-HOOK-TODAY-CONVERGENCE

// START_MODULE_MAP: M-HOOK-TODAY-CONVERGENCE
// public_entrypoints:
//   - TodayConvergenceScreenState
//   - UseTodayConvergenceResult
//   - useTodayConvergence
// semantic_blocks:
//   - INITIAL_LOAD: auth-gated date fetch and onboarding routing.
//   - IMPRESSION: post-paint, full-access snapshot guard.
//   - PENDING_POLLING: four-second bounded GET polling.
//   - RETRY: POST retry, Retry-After countdown, and follow-up GET.
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

export const PENDING_POLL_INTERVAL_MS = 4_000;
export const PENDING_POLL_MAX_MS = 120_000;
export const DEFAULT_RETRY_AFTER_SECONDS = 4;

export type TodayConvergenceScreenState = "loading" | "ready" | "error";

export type UseTodayConvergenceResult = {
  screenState: TodayConvergenceScreenState;
  payload?: Awaited<ReturnType<typeof fetchTodayConvergence>>;
  retryAfterSeconds: number;
  retrying: boolean;
  refetch: () => Promise<void>;
};

function isOnboardingFailure(error: unknown): boolean {
  if (!(error instanceof TodayConvergenceApiError)) return false;
  return (
    (error.status === 422 && error.code === "NOT_ONBOARDED") ||
    (error.status === 409 && error.message === "Profile is incomplete")
  );
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
  // side_effects: auth-gated API calls, bounded timers, impression POST, and onboarding redirect.
  // emitted_logs: delegated API lifecycle and impression events.
  // error_behavior: active non-onboarding fetch errors expose screenState=error; aborts are ignored.
  // END_FUNCTION_CONTRACT: F-M-HOOK-TODAY-CONVERGENCE.useTodayConvergence
  const router = useRouter();
  const { isLoading: authLoading } = useTelegramAuth();
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
  const pendingStartedAtRef = useRef<number | null>(null);
  const impressionSnapshotsRef = useRef(new Set<string>());
  const retryingRef = useRef(false);
  const retryAfterRef = useRef(0);

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
    };
  }, []);

  // START_BLOCK: INITIAL_LOAD
  useEffect(() => {
    const generation = generationRef.current + 1;
    generationRef.current = generation;
    loadControllerRef.current?.abort();
    pollControllerRef.current?.abort();
    retryControllerRef.current?.abort();
    if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    pendingStartedAtRef.current = null;
    retryAfterRef.current = 0;
    retryingRef.current = false;
    setRetrying(false);
    setRetryAfterSeconds(0);
    setPayload(undefined);
    setScreenState("loading");

    if (authLoading) return undefined;

    const controller = new AbortController();
    loadControllerRef.current = controller;

    const load = async () => {
      try {
        const nextPayload = await fetchTodayConvergence(dateParam, controller.signal);
        if (!isCurrent(mountedRef.current, generation, generationRef.current, controller.signal)) return;
        setPayload(nextPayload);
        setScreenState("ready");
      } catch (error) {
        if (!isCurrent(mountedRef.current, generation, generationRef.current, controller.signal)) return;
        if (isOnboardingFailure(error)) {
          router.replace("/onboarding");
          return;
        }
        setScreenState("error");
      }
    };

    void load();
    return () => {
      controller.abort();
      if (loadControllerRef.current === controller) loadControllerRef.current = null;
    };
  }, [authLoading, dateParam, router]);
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
    // side_effects: POST retry, optional countdown timers, follow-up GET, and state updates.
    // emitted_logs: delegated API lifecycle events.
    // error_behavior: ignores duplicate/cooldown calls; active failures become screenState=error.
    // END_FUNCTION_CONTRACT: F-M-HOOK-TODAY-CONVERGENCE.refetch
    if (
      !mountedRef.current ||
      retryingRef.current ||
      retryAfterRef.current > 0
    ) return;

    const generation = generationRef.current;
    const controller = new AbortController();
    retryControllerRef.current = controller;
    retryingRef.current = true;
    setRetrying(true);

    const active = () => isCurrent(mountedRef.current, generation, generationRef.current, controller.signal);

    try {
      const result = await retryTodayConvergence(dateParam, controller.signal);
      if (!active()) return;

      if (result.payload) {
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

      const nextPayload = await fetchTodayConvergence(dateParam, controller.signal);
      if (!active()) return;
      setPayload(nextPayload);
      setScreenState("ready");
    } catch (error) {
      if (!active()) return;
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
  }, [dateParam, router]);
  // END_BLOCK: RETRY

  return { screenState, payload, retryAfterSeconds, retrying, refetch };
}
// END_BLOCK: LIFECYCLE
