
// ############################################################################
// AI_HEADER: GRACE_USE_CALENDAR — client hook for month-scoped CalendarPayload loading state.
// ROLE: Hook used by calendar consumers to fetch one month and expose data, loading and normalized ApiError state.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-GRACE-HOOK-USE-CALENDAR
// purpose: Fetch CalendarPayload whenever the month input changes and guard state writes after effect cleanup.
// owns:
//   - lib/grace/hooks/useCalendar.ts
// inputs: month string in the existing YYYY-MM caller format.
// outputs: exported UseCalendarResult interface and useCalendar hook returning data, loading and error.
// dependencies: React useState/useEffect; lib/grace/api/client fetchCalendar and ApiError; packages/contracts CalendarPayload.
// side_effects: delegated calendar network request plus React state updates.
// emitted_logs: none.
// invariants:
//   - Initial state remains data=null, loading=true and error=null.
//   - Each month effect sets loading=true and clears error before fetching.
//   - Existing data is not proactively cleared when a new month load starts.
//   - Cleanup marks the request cancelled; later handlers do not update state for that effect.
//   - A month change starts a new fetch through the existing [month] dependency.
//   - Existing ApiError instances are preserved; unknown failures become ApiError('Unknown error', 500).
// failure_policy: Expose preserved or normalized ApiError and finish loading only while the effect remains active; do not throw.
// END_MODULE_CONTRACT: M-FRONTEND-GRACE-HOOK-USE-CALENDAR

// START_MODULE_MAP: M-FRONTEND-GRACE-HOOK-USE-CALENDAR
// public_entrypoints:
//   - UseCalendarResult
//   - useCalendar
// semantic_blocks:
//   - RESULT_SHAPE: define data, loading and normalized error output.
//   - CALENDAR_STATE: initialize and retain hook state across loads.
//   - MONTH_LOAD_EFFECT: fetch whenever the month dependency changes.
//   - CANCEL_GUARD: suppress state writes after effect cleanup without aborting the request.
//   - ERROR_NORMALIZATION: preserve ApiError or create the existing unknown failure.
// owned_tests:
//   - __tests__/hooks/useCalendar.test.ts
// END_MODULE_MAP: M-FRONTEND-GRACE-HOOK-USE-CALENDAR

'use client';

import { useState, useEffect } from 'react';
import { fetchCalendar, ApiError } from '../api/client';
import type { CalendarPayload } from '@/packages/contracts';

export interface UseCalendarResult {
  data: CalendarPayload | null;
  loading: boolean;
  error: ApiError | null;
}

/**
 * Hook to fetch calendar data for a specific month
 * @param month - Month string (YYYY-MM)
 * @returns Object with data, loading, and error states
 */
export function useCalendar(month: string): UseCalendarResult {
  const [data, setData] = useState<CalendarPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        setError(null);
        const payload = await fetchCalendar(month);
        if (!cancelled) {
          setData(payload);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err : new ApiError('Unknown error', 500));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [month]);

  return { data, loading, error };
}
