
// ############################################################################
// AI_HEADER: GRACE_USE_DAY — authenticated day hook with logging and onboarding routing.
// ROLE: Hook used by the day route to await Telegram auth, fetch TodayPayload and expose state or redirect incomplete users.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-GRACE-HOOK-USE-DAY
// purpose: Coordinate auth readiness, delayed day loading, structured logging, cancellation-safe state and onboarding redirects.
// owns:
//   - lib/grace/hooks/useDay.ts
// inputs: ISO date string; Telegram-auth loading state; Next router context.
// outputs: exported UseDayResult interface and useDay hook returning data, loading and error.
// dependencies: React useState/useEffect; next/navigation useRouter; lib/grace/api/client fetchDay and ApiError; hooks/use-telegram-auth; lib/log logEvent; packages/contracts TodayPayload.
// side_effects: structured browser logs, 100 ms delay, delegated day request, React state and router.replace('/onboarding').
// emitted_logs: day.viewed, auth.tg_login_started, day.payload_built, system.error, profile.lazy_created, auth.session_expired.
// invariants:
//   - The render-path INIT log remains and emits day.viewed.
//   - While authLoading is true, the effect logs auth.tg_login_started, does not fetch and leaves loading unchanged.
//   - The load effect remains dependent on [date, router, authLoading] and retains the 100 ms delay.
//   - Successful payload state is applied only when the effect is not cancelled.
//   - HTTP 422 with code NOT_ONBOARDED or HTTP 409 with exact message 'Profile is incomplete' logs profile.lazy_created and redirects to /onboarding without exposing an error.
//   - HTTP 401 logs auth.session_expired and replaces the ApiError message with the existing Russian Telegram authorization copy before exposing it.
//   - Unknown failures become ApiError('Unknown error', 500).
//   - Cleanup logs day.viewed and sets the local cancellation flag.
// failure_policy: Log system.error; redirect recognized incomplete-profile failures; otherwise expose preserved or normalized ApiError and finish loading only while active.
// END_MODULE_CONTRACT: M-FRONTEND-GRACE-HOOK-USE-DAY

// START_MODULE_MAP: M-FRONTEND-GRACE-HOOK-USE-DAY
// public_entrypoints:
//   - UseDayResult
//   - useDay
// semantic_blocks:
//   - RESULT_SHAPE: define data, loading and error output.
//   - DAY_STATE: initialize route payload state.
//   - RENDER_LOG: retain the render-path day.viewed event.
//   - AUTH_GATE: defer day loading while Telegram auth is pending.
//   - DAY_LOAD_EFFECT: delay and delegate the day request.
//   - SUCCESS_APPLY: apply payload only while active.
//   - ERROR_ROUTING: log and redirect recognized incomplete profiles.
//   - UNAUTHORIZED_COPY: preserve the current 401 event and Russian message.
//   - CANCEL_CLEANUP: log cleanup and suppress later state writes.
// owned_tests:
//   - __tests__/hooks/useDay.test.ts
//   - __tests__/app/day-page.test.tsx
// END_MODULE_MAP: M-FRONTEND-GRACE-HOOK-USE-DAY

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { fetchDay, ApiError } from '../api/client';
import { useTelegramAuth } from '@/hooks/use-telegram-auth';
import { logEvent } from '@/lib/log';
import type { TodayPayload } from '@/packages/contracts';

export interface UseDayResult {
  data: TodayPayload | null;
  loading: boolean;
  error: ApiError | null;
}

/**
 * Hook to fetch day data for a specific date
 * @param date - ISO date string (YYYY-MM-DD)
 * @returns Object with data, loading, and error states
 */
export function useDay(date: string): UseDayResult {
  const [data, setData] = useState<TodayPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const router = useRouter();
  const { isLoading: authLoading } = useTelegramAuth();

  logEvent("day.viewed", { date }, { msg: `[useDay] Loading for ${date}`, level: "debug", slice: "W-DAY", module: "M-USE-DAY-HOOK", block: "INIT" })

  useEffect(() => {
    logEvent("day.viewed", { date, authLoading }, { msg: "[useDay] useEffect", level: "debug", slice: "W-DAY", module: "M-USE-DAY-HOOK", block: "EFFECT" })

    if (authLoading) {
      logEvent("auth.tg_login_started", {}, { msg: "[useDay] Waiting for auth...", level: "debug", slice: "W-DAY", module: "M-USE-DAY-HOOK", block: "AUTH_WAIT" })
      return;
    }

    logEvent("day.viewed", { date }, { msg: "[useDay] Auth complete, loading day...", slice: "W-DAY", module: "M-USE-DAY-HOOK", block: "LOAD" })

    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        setError(null);
        logEvent("day.viewed", { date }, { msg: "[useDay] Fetching day...", level: "debug", slice: "W-DAY", module: "M-USE-DAY-HOOK", block: "FETCH" })

        await new Promise(resolve => setTimeout(resolve, 100));

        const payload = await fetchDay(date);
        logEvent("day.payload_built", { date: payload.date, title: payload.title }, { msg: "[useDay] Day loaded", slice: "W-DAY", module: "M-USE-DAY-HOOK", block: "LOADED" })

        if (!cancelled) {
          setData(payload);
          setLoading(false);
        }
      } catch (err) {
        logEvent("system.error", { error: String(err) }, { msg: "[useDay] Fetch failed", level: "error", slice: "W-DAY", module: "M-USE-DAY-HOOK", block: "FETCH" })
        if (!cancelled) {
          const apiError = err instanceof ApiError ? err : new ApiError('Unknown error', 500);

          const needsOnboarding =
            (apiError.status === 422 && apiError.code === 'NOT_ONBOARDED') ||
            (apiError.status === 409 && apiError.message === 'Profile is incomplete');

          if (needsOnboarding) {
            logEvent("profile.lazy_created", {}, { msg: "[useDay] Incomplete profile — redirecting to /onboarding", slice: "W-DAY", module: "M-USE-DAY-HOOK", block: "NOT_ONBOARDED" })
            router.replace('/onboarding');
            return;
          }

          if (apiError.status === 401) {
            logEvent("auth.session_expired", {}, { msg: "[useDay] 401 — unauthorized", level: "warn", slice: "W-DAY", module: "M-USE-DAY-HOOK", block: "UNAUTHORIZED" })
            apiError.message = 'Требуется авторизация. Откройте приложение через Telegram бот.';
          }

          setError(apiError);
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      logEvent("day.viewed", {}, { msg: "[useDay] Cleanup (cancelled)", level: "debug", slice: "W-DAY", module: "M-USE-DAY-HOOK", block: "CLEANUP" })
      cancelled = true;
    };
  }, [date, router, authLoading]);

  return { data, loading, error };
}
