// AI_HEADER
// module: M-WEB-HOOKS-USE-DAY
// wave: W-2.7
// purpose: React hook for fetching TodayPayload with loading and error states

'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { fetchDay, ApiError } from '../api/client';
import { useTelegramAuth } from '@/hooks/use-telegram-auth';
import { logger } from '@/lib/log';
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

  console.log('[useDay] authLoading:', authLoading, 'isAuthenticated:', isAuthenticated, 'date:', date);

  useEffect(() => {
    logger.debug('[useDay] useEffect', { extra: { date, authLoading } });

    if (authLoading) {
      logger.debug('[useDay] Waiting for auth...');
      return;
    }

    logger.info('[useDay] Auth complete, loading day...');

    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        setError(null);
        logger.debug('[useDay] Fetching day...');

        await new Promise(resolve => setTimeout(resolve, 100));

        const payload = await fetchDay(date);
        logger.info('[useDay] Day loaded', { extra: { date: payload.date, title: payload.title } });

        if (!cancelled) {
          setData(payload);
          setLoading(false);
        }
      } catch (err) {
        logger.error('[useDay] Fetch failed', { extra: { error: String(err) } });
        if (!cancelled) {
          const apiError = err instanceof ApiError ? err : new ApiError('Unknown error', 500);

          if (apiError.status === 422 && apiError.code === 'NOT_ONBOARDED') {
            logger.info('[useDay] NOT_ONBOARDED — redirecting to /onboarding');
            router.replace('/onboarding');
            return;
          }

          if (apiError.status === 401) {
            logger.warn('[useDay] 401 — unauthorized');
            apiError.message = 'Требуется авторизация. Откройте приложение через Telegram бот.';
          }

          setError(apiError);
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      logger.debug('[useDay] Cleanup (cancelled)');
      cancelled = true;
    };
  }, [date, router, authLoading]);

  return { data, loading, error };
}
