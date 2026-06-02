// AI_HEADER
// module: M-HOOK-TELEGRAM-AUTH
// wave: W-2.2
// purpose: Telegram Web App authentication hook

'use client';

import { useEffect, useState } from 'react';
import { logger } from '@/lib/log';

interface TelegramAuthState {
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
}

export function useTelegramAuth() {
  logger.debug('[TGAuth] Hook called');
  const [state, setState] = useState<TelegramAuthState>({
    isLoading: true,
    isAuthenticated: false,
    error: null,
  });

  logger.debug('[TGAuth] Initial state', { extra: state });

  useEffect(() => {
    logger.debug('[TGAuth] useEffect triggered');

    const authenticate = async () => {
      logger.info('[TGAuth] authenticate() started');

      const timeoutId = setTimeout(() => {
        logger.warn('[TGAuth] TIMEOUT — auth took too long');
        setState({
          isLoading: false,
          isAuthenticated: false,
          error: 'Authentication timeout'
        });
      }, 5000);

      try {
        if (typeof window === 'undefined') {
          logger.debug('[TGAuth] SSR — skipping');
          clearTimeout(timeoutId);
          setState({ isLoading: false, isAuthenticated: false, error: null });
          return;
        }

        const tg = window.Telegram?.WebApp;
        logger.debug('[TGAuth] WebApp', { extra: { exists: !!tg, hasInitData: !!tg?.initData } });

        if (!tg || !tg.initData) {
          logger.info('[TGAuth] Not in Telegram WebApp');

          const isDevMode = process.env.NODE_ENV === 'development';
          logger.debug('[TGAuth] Dev mode:', { extra: { isDevMode, NODE_ENV: process.env.NODE_ENV } });

          if (isDevMode) {
            logger.info('[TGAuth] Using dev auth...');
            try {
              const devResponse = await fetch('/api/auth/dev', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
              });

              logger.debug('[TGAuth] Dev auth response', { extra: { status: devResponse.status } });

              if (devResponse.ok) {
                const devData = await devResponse.json();
                logger.info('[TGAuth] Dev auth OK', { extra: { userId: devData.userId } });
                await new Promise(resolve => setTimeout(resolve, 500));
                clearTimeout(timeoutId);
                setState({ isLoading: false, isAuthenticated: true, error: null });
                return;
              }

              logger.warn('[TGAuth] Dev auth failed', { extra: { status: devResponse.status } });
              throw new Error('Dev auth failed');
            } catch (error) {
              logger.error('[TGAuth] Dev auth exception', { extra: { error: String(error) } });
              clearTimeout(timeoutId);
              setState({
                isLoading: false,
                isAuthenticated: false,
                error: error instanceof Error ? error.message : 'Dev auth error'
              });
              return;
            }
          }

          logger.info('[TGAuth] Not dev mode, skipping auth');
          clearTimeout(timeoutId);
          setState({ isLoading: false, isAuthenticated: false, error: null });
          return;
        }

        const initData = tg.initData;
        logger.info('[TGAuth] Sending to /api/auth/telegram', { extra: { len: initData.length } });

        const response = await fetch('/api/auth/telegram', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ initData }),
          credentials: 'include',
        });

        logger.debug('[TGAuth] Auth response', { extra: { status: response.status } });

        if (!response.ok) {
          const errBody = await response.json();
          logger.error('[TGAuth] Auth failed', { extra: { status: response.status, body: errBody } });
          throw new Error(errBody.detail || 'Authentication failed');
        }

        logger.info('[TGAuth] Auth SUCCESS');
        await new Promise(resolve => setTimeout(resolve, 500));

        // Auto-claim referral if opened via startapp link (once per session)
        const claimKey = '__astro_referral_claimed';
        const persistKey = '__astro_referral_code';
        try {
          const startParam = tg.initDataUnsafe?.start_param
            || (() => {
              const sp = new URLSearchParams(window.location.search);
              return sp.get('tgWebAppStartParam') || undefined;
            })()
          const ownId = tg.initDataUnsafe?.user?.id
          const alreadyClaimed = (window as any)[claimKey]

          // Persist referral code to localStorage so it survives
          // the user closing and reopening the Mini App without the deep link.
          if (startParam) {
            try { localStorage.setItem(persistKey, startParam); } catch (_) {}
          }

          // Fallback: use persisted code from a previous visit
          const effectiveCode = startParam || (
            !alreadyClaimed ? (() => { try { return localStorage.getItem(persistKey); } catch (_) { return null; } })() : null
          )

          if (effectiveCode && String(effectiveCode) !== String(ownId) && !alreadyClaimed) {
            logger.info('[TGAuth] Auto-claiming referral', { extra: { code: effectiveCode } })
            const claimRes = await fetch('/api/referral/claim', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify({ referrer_code: effectiveCode }),
            })
            ;(window as any)[claimKey] = true
            try { localStorage.removeItem(persistKey); } catch (_) {}
            if (!claimRes.ok) {
              const err = await claimRes.json().catch(() => ({}))
              logger.warn(`[TGAuth] Referral claim failed: HTTP ${claimRes.status} code=${err.detail?.code || '?'}`)
            } else {
              logger.info('[TGAuth] Referral claimed! +14 days')
            }
          } else if (effectiveCode && String(effectiveCode) === String(ownId)) {
            logger.info('[TGAuth] Skipping self-referral')
          } else if (!startParam) {
            logger.info('[TGAuth] No start_param — not a referral link')
          }
        } catch (e) {
          logger.error('[TGAuth] Referral claim error', { extra: { error: String(e) } })
        }

        clearTimeout(timeoutId);
        setState({ isLoading: false, isAuthenticated: true, error: null });
      } catch (error) {
        logger.error('[TGAuth] Exception', { extra: { error: String(error) } });
        clearTimeout(timeoutId);
        setState({
          isLoading: false,
          isAuthenticated: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        });
      }
    };

    authenticate().catch(err => {
      logger.error('[TGAuth] authenticate() threw', { extra: { error: String(err) } });
      setState({
        isLoading: false,
        isAuthenticated: false,
        error: err.message || 'Authentication failed'
      });
    });
  }, []);

  logger.debug('[TGAuth] Returning state', { extra: state });
  return state;
}
