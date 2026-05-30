// AI_HEADER
// module: M-WEB-HOOKS-USE-CALENDAR
// wave: W-2.1
// purpose: React hook for fetching CalendarPayload with loading and error states

'use client';

import { useState, useEffect } from 'react';
import type { components } from '@/packages/contracts/_generated';
import { fetchCalendar, ApiError } from '../api/client';

type CalendarPayload = components['schemas']['CalendarPayload'];

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
