
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USEDAY
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-LOGGING-SPINE
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/grace/hooks/useDay.ts
// owns:
//   - lib/grace/hooks/useDay.ts
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

// AI_HEADER
// module: M-WEB-HOOKS-USE-DAY
// wave: W-2.7
// purpose: React hook for fetching TodayPayload with loading and error states

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
  const { isAuthenticated, isLoading: authLoading } = useTelegramAuth();

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

          if (apiError.status === 422 && apiError.code === 'NOT_ONBOARDED') {
            logEvent("profile.lazy_created", {}, { msg: "[useDay] NOT_ONBOARDED — redirecting to /onboarding", slice: "W-DAY", module: "M-USE-DAY-HOOK", block: "NOT_ONBOARDED" })
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
