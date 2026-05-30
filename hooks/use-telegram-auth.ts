// AI_HEADER
// module: M-HOOK-TELEGRAM-AUTH
// wave: W-2.2
// purpose: Telegram Web App authentication hook

'use client';

import { useEffect, useState } from 'react';

interface TelegramAuthState {
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
}

/**
 * Hook to authenticate user via Telegram Web App initData
 * Automatically runs on mount and sends initData to backend
 * @returns Object with isLoading, isAuthenticated, and error states
 */
export function useTelegramAuth() {
  const [state, setState] = useState<TelegramAuthState>({
    isLoading: true,
    isAuthenticated: false,
    error: null,
  });

  useEffect(() => {
    const authenticate = async () => {
      console.log('[Telegram Auth] Starting...');

      // Timeout 10 секунд
      const timeoutId = setTimeout(() => {
        console.error('[Telegram Auth] Timeout after 10 seconds!');
        setState({
          isLoading: false,
          isAuthenticated: false,
          error: 'Authentication timeout'
        });
      }, 10000);

      try {
        // Check if we're in browser environment
        if (typeof window === 'undefined') {
          console.log('[Telegram Auth] SSR mode, skipping');
          clearTimeout(timeoutId);
          setState({ isLoading: false, isAuthenticated: false, error: null });
          return;
        }

        const tg = window.Telegram?.WebApp;
        console.log('[Telegram Auth] Telegram.WebApp:', tg ? 'exists' : 'missing');

        // FALLBACK: If not in Telegram Web App - skip auth (dev/test mode)
        if (!tg || !tg.initData) {
          console.log('[Telegram Auth] Not in Telegram Web App, skipping auth (dev mode)');
          clearTimeout(timeoutId);
          setState({ isLoading: false, isAuthenticated: false, error: null });
          return;
        }

        const initData = tg.initData;
        console.log('[Telegram Auth] initData length:', initData.length);
        console.log('[Telegram Auth] Sending to /api/auth/telegram...');

        // Send initData to backend for validation
        const apiBase = process.env.NEXT_PUBLIC_API_URL || '';
        const response = await fetch(`${apiBase}/api/auth/telegram`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ initData }),
          credentials: 'include', // Important: enables session cookie
        });

        console.log('[Telegram Auth] Response status:', response.status);

        if (!response.ok) {
          const error = await response.json();
          console.error('[Telegram Auth] Error response:', error);
          throw new Error(error.detail || 'Authentication failed');
        }

        console.log('[Telegram Auth] Success!');
        clearTimeout(timeoutId);
        setState({ isLoading: false, isAuthenticated: true, error: null });
      } catch (error) {
        console.error('[Telegram Auth] Exception:', error);
        clearTimeout(timeoutId);
        setState({
          isLoading: false,
          isAuthenticated: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        });
      }
    };

    authenticate();
  }, []);

  return state;
}
