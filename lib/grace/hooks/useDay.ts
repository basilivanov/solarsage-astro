// AI_HEADER
// module: M-WEB-HOOKS-USE-DAY
// wave: W-2.1
// purpose: React hook for fetching TodayPayload with loading and error states

'use client';

import { useState, useEffect } from 'react';
import type { components } from '@/packages/contracts/_generated';
import { fetchDay, ApiError } from '../api/client';

type TodayPayload = components['schemas']['TodayPayload'];

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

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        setError(null);
        const payload = await fetchDay(date);
        if (!cancelled) {
          setData(payload);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          const apiError = err instanceof ApiError ? err : new ApiError('Unknown error', 500);

          // W-2.2: Special handling for auth errors
          if (apiError.status === 401) {
            apiError.message = 'Требуется авторизация. Откройте приложение через Telegram бот.';
          }

          setError(apiError);
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [date]);

  return { data, loading, error };
}
