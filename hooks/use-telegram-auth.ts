// ############################################################################
// AI_HEADER: MODULE_HOOKS_USE_TELEGRAM_AUTH
// ROLE: React hook for Telegram WebApp authentication and intent-based start_param routing.
// DEPENDENCIES: lib/log, components/telegram-provider, lib/telegram/start-param
// GRACE_ANCHORS: [HOOK_TELEGRAM_AUTH]
// WAVE: W-NAMED-PROMO-CAMPAIGN
// ############################################################################

// START_MODULE_CONTRACT: M-HOOK-TELEGRAM-AUTH
// purpose: Authenticate Telegram WebApp session via /api/auth/telegram, route start_param into referral vs promo intents safely, and manage pending promo token in sessionStorage.
// owns:
//   - hooks/use-telegram-auth.ts
// inputs: Component props / hook params
// outputs: TelegramAuthState ({ isLoading, isAuthenticated, error })
// dependencies: lib/log, components/telegram-provider, lib/telegram/start-param
// side_effects:
//   - POST /api/auth/telegram or /api/auth/dev
//   - POST /api/referral/claim (only for numeric referral codes)
//   - writes promo intent to sessionStorage
//   - cleans tgWebAppStartParam from browser location URL
// emitted_logs: frontend.flow_failed
// invariants:
//   - promo tokens never hit referral claim endpoint or localStorage
//   - only numeric referral codes are persisted to localStorage or claimed
//   - no raw initData, start_param, promo tokens or referral codes in log events
//   - promo intent stored before setting isAuthenticated=true
// failure_policy: Storage or referral errors fail closed without breaking authentication
// END_MODULE_CONTRACT: M-HOOK-TELEGRAM-AUTH

// START_MODULE_MAP: M-HOOK-TELEGRAM-AUTH
// public_entrypoints:
//   - useTelegramAuth
// semantic_blocks:
//   - AUTH_STATE: state and refs management
//   - START_PARAM_ROUTING: classify start_param and route to promo vs referral
//   - AUTHENTICATE_FLOW: backend auth fetch and state updates
// owned_tests:
//   - __tests__/hooks/useTelegramAuth.test.ts
// END_MODULE_MAP: M-HOOK-TELEGRAM-AUTH

'use client';

import { useEffect, useRef, useState } from 'react';
import { logger, logEvent } from '@/lib/log';
import { useTelegram } from '@/components/telegram-provider';
import {
  classifyStartParam,
  savePendingPromoToken,
  cleanStartParamFromUrl,
} from '@/lib/telegram/start-param';

interface TelegramAuthState {
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
}

// START_BLOCK: AUTH_STATE
export function useTelegramAuth() {
  const { webApp, loaded } = useTelegram();
  logger.debug('[TGAuth] Hook called');

  const authKeyRef = useRef<string | null>(null);

  const [state, setState] = useState<TelegramAuthState>({
    isLoading: true,
    isAuthenticated: false,
    error: null,
  });

  logger.debug('[TGAuth] Initial state', { extra: state });

  useEffect(() => {
    const fallbackTg = typeof window !== 'undefined' ? window.Telegram?.WebApp : undefined;

    if (!loaded && !fallbackTg) {
      logger.debug('[TGAuth] Waiting for Telegram SDK to load…');
      return;
    }

    const tg = webApp ?? fallbackTg;
    const authKey = tg?.initData || 'none';

    if (authKeyRef.current === authKey) {
      logger.debug('[TGAuth] Auth already attempted for this key — skipping duplicate');
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

        // Read raw start_param BEFORE cleaning the URL.
        // Sources in priority order: initDataUnsafe, raw initData string
        // (parsed the same way the backend does — initDataUnsafe may miss
        // start_param in some webviews), then the URL query param.
        const initDataString = tg?.initData || ''
        const rawStartParam =
          (tg?.initDataUnsafe as any)?.start_param
          || (initDataString
            ? new URLSearchParams(initDataString).get('start_param') || undefined
            : undefined)
          || (() => {
            if (typeof window !== 'undefined' && window.location) {
              return new URLSearchParams(window.location.search).get('tgWebAppStartParam') || undefined;
            }
          })();

        // Clean query parameter from location bar immediately
        cleanStartParamFromUrl();

        const intent = classifyStartParam(rawStartParam);
        logger.debug('[TGAuth] Classified start_param intent', { extra: { intentKind: intent.kind } });

        const tgSource = webApp ?? fallbackTg;
        logger.debug('[TGAuth] WebApp', { extra: { exists: !!tgSource, hasInitData: !!tgSource?.initData } });

        if (!tgSource || !tgSource.initData) {
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
                // Promo intent must also be stored on the dev-auth path —
                // otherwise the gate never sees the pending token outside Telegram.
                if (intent.kind === 'promo') {
                  const saved = savePendingPromoToken(intent.token);
                  if (!saved) {
                    logEvent('frontend.flow_failed', { operation: 'promo.intent_store', reason_code: 'session_storage_failed' }, {
                      level: 'error',
                      slice: 'W-FRONTEND',
                      module: 'M-HOOK-TELEGRAM-AUTH',
                      block: 'START_PARAM_ROUTING',
                    });
                  }
                }
                clearTimeout(timeoutId);
                setState({ isLoading: false, isAuthenticated: true, error: null });
                return;
              }

              logger.warn('[TGAuth] Dev auth failed', { extra: { status: devResponse.status } });
              throw new Error('Dev auth failed');
            } catch (error) {
              logger.error('[TGAuth] Dev auth exception');
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

        const initData = tgSource.initData;
        logger.info('[TGAuth] Sending to /api/auth/telegram');

        const response = await fetch('/api/auth/telegram', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ initData }),
          credentials: 'include',
        });

        logger.debug('[TGAuth] Auth response', { extra: { status: response.status } });

        if (!response.ok) {
          const errBody = await response.json().catch(() => ({}));
          logger.error('[TGAuth] Auth failed');
          throw new Error(errBody.detail || 'Authentication failed');
        }

        logger.info('[TGAuth] Auth SUCCESS');
        await new Promise(resolve => setTimeout(resolve, 500));

        // Promo/referral storage and routing executed ONLY AFTER successful Telegram auth
        const persistKey = '__astro_referral_code';

        try {
          if (typeof window !== 'undefined' && window.localStorage) {
            const storedCode = localStorage.getItem(persistKey);
            if (storedCode && !/^\d+$/.test(storedCode)) {
              localStorage.removeItem(persistKey);
            }
          }
        } catch {
          // best-effort
        }

        if (intent.kind === 'promo') {
          const saved = savePendingPromoToken(intent.token);
          if (!saved) {
            logEvent('frontend.flow_failed', { operation: 'promo.intent_store', reason_code: 'session_storage_failed' }, {
              level: 'error',
              slice: 'W-FRONTEND',
              module: 'M-HOOK-TELEGRAM-AUTH',
              block: 'START_PARAM_ROUTING',
            });
          }
        } else if (intent.kind === 'referral') {
          try {
            if (typeof window !== 'undefined' && window.localStorage) {
              localStorage.setItem(persistKey, intent.code);
            }
          } catch {
            // best-effort
          }
        }

        // Auto-claim referral (only numeric referral code, and NEVER if promo or invalid raw start_param present)
        const claimKey = '__astro_referral_claimed';
        try {
          const ownId = tgSource.initDataUnsafe?.user?.id;
          const alreadyClaimed = (window as any)[claimKey];

          let effectiveCode: string | null = null;
          if (intent.kind === 'referral') {
            effectiveCode = intent.code;
          } else if (!rawStartParam && !alreadyClaimed) {
            // Persisted fallback is ONLY allowed when raw start_param is absent
            try {
              const storedCode = localStorage.getItem(persistKey);
              if (storedCode && /^\d+$/.test(storedCode)) {
                effectiveCode = storedCode;
              }
            } catch {
              // ignore
            }
          }

          if (effectiveCode && String(effectiveCode) !== String(ownId) && !alreadyClaimed) {
            logger.info('[TGAuth] Auto-claiming referral');
            const claimRes = await fetch('/api/referral/claim', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify({ referrer_code: effectiveCode }),
            });
            ;(window as any)[claimKey] = true;
            try {
              localStorage.removeItem(persistKey);
            } catch {
              // best-effort
            }
            if (!claimRes.ok) {
              logger.warn('[TGAuth] Referral claim failed');
            } else {
              logger.info('[TGAuth] Referral claimed successfully');
            }
          } else if (effectiveCode && String(effectiveCode) === String(ownId)) {
            logger.info('[TGAuth] Skipping self-referral');
          }
        } catch {
          logger.error('[TGAuth] Referral claim error');
        }

        clearTimeout(timeoutId);
        setState({ isLoading: false, isAuthenticated: true, error: null });
      } catch (error) {
        logger.error('[TGAuth] Exception');
        clearTimeout(timeoutId);
        setState({
          isLoading: false,
          isAuthenticated: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    };

    authenticate().catch(err => {
      logger.error('[TGAuth] authenticate() threw');
      setState({
        isLoading: false,
        isAuthenticated: false,
        error: err.message || 'Authentication failed',
      });
    });
  }, [loaded, webApp]);

  logger.debug('[TGAuth] Returning state', { extra: state });
  return state;
}
// END_BLOCK: AUTH_STATE
