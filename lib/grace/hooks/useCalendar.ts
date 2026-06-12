
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USECALENDAR
// ROLE: UI — useCalendar
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-LOGGING-SPINE
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI useCalendar — component
// owns:
//   - lib/grace/hooks/useCalendar.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// AI_HEADER
// module: M-WEB-HOOKS-USE-CALENDAR
// wave: W-2.1
// purpose: React hook for fetching CalendarPayload with loading and error states

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
