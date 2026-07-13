
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USE_TELEGRAM_AUTH
// ROLE: React hook
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: API client for use-telegram-auth
// owns:
//   - hooks/use-telegram-auth.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: Network calls to API; Logging via v2 logging spine; React state management
// emitted_logs: v2 logging: logEvent/logStart/logSuccess/logFailure (frontend) or logger.* (backend)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// AI_HEADER
// module: M-HOOK-TELEGRAM-AUTH
// wave: W-2.2
// purpose: Telegram Web App authentication hook

'use client';

import { useEffect, useRef, useState } from 'react';
import { logger } from '@/lib/log';
import { useTelegram } from '@/components/telegram-provider';

interface TelegramAuthState {
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
}

export function useTelegramAuth() {
  const { webApp, loaded } = useTelegram();
  logger.debug('[TGAuth] Hook called');

  // Auth-key guard: prevents duplicate auth runs while still allowing a
  // legitimate transition (e.g. timeout decides "no Telegram", then the
  // SDK loads with real initData later).
  //
  // The key is the initData string itself:
  //   - E2E injection + provider catch-up with the same initData → skip
  //   - Non-Telegram path uses sentinel 'none' → stays 'none'
  //   - Late SDK load with real initData → key changes → allowed
  const authKeyRef = useRef<string | null>(null);

  const [state, setState] = useState<TelegramAuthState>({
    isLoading: true,
    isAuthenticated: false,
    error: null,
  });

  logger.debug('[TGAuth] Initial state', { extra: state });

  useEffect(() => {
    // Wait for Telegram SDK to load (or fail) before making auth decisions.
    // Without this guard the hook would decide "not in Telegram" before the
    // SDK has a chance to load, breaking the real auth flow.
    //
    // Fallback: when no <TelegramProvider> wraps the tree (unit tests, E2E
    // fixtures with addInitScript), we accept window.Telegram directly.
    const fallbackTg = typeof window !== 'undefined' ? window.Telegram?.WebApp : undefined;

    if (!loaded && !fallbackTg) {
      logger.debug('[TGAuth] Waiting for Telegram SDK to load…');
      return;
    }

    // Compute the effective Telegram source and derive the auth key.
    const tg = webApp ?? fallbackTg;
    const authKey = tg?.initData || 'none';

    // Skip if we already attempted auth for exactly this initData key.
    // This prevents a duplicate /api/auth/telegram POST when both the
    // fallback path and the immediate context-update path fire the effect
    // (E2E fixtures), while still allowing a late transition from
    // no-Telegram to real-Telegram (the key changes).
    if (authKeyRef.current === authKey) {
      logger.debug('[TGAuth] Auth already attempted for this key — skipping duplicate', {
        extra: { key: authKey.slice(0, 24) },
      });
      return;
    }
    authKeyRef.current = authKey;

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

        // Use context webApp, falling back to window.Telegram for tests/E2E
        const tg = webApp ?? fallbackTg;
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
          const startParam = (tg.initDataUnsafe as any)?.start_param
            || (() => {
              const sp = new URLSearchParams(window.location.search);
              return sp.get('tgWebAppStartParam') || undefined;
            })()
          const ownId = tg.initDataUnsafe?.user?.id
          const alreadyClaimed = (window as any)[claimKey]

          // Persist referral code to localStorage so it survives
          // the user closing and reopening the Mini App without the deep link.
          if (startParam) {
            try {
              localStorage.setItem(persistKey, startParam)
            } catch {
              // Referral persistence is best-effort; authentication must continue.
            }
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
            try {
              localStorage.removeItem(persistKey)
            } catch {
              // Referral cleanup is best-effort after a completed claim attempt.
            }
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
  }, [loaded, webApp]);

  logger.debug('[TGAuth] Returning state', { extra: state });
  return state;
}
