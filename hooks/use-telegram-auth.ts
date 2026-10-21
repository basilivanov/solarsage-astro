// ############################################################################
// AI_HEADER: MODULE_HOOKS_USE_TELEGRAM_AUTH
// ROLE: Module-singleton Telegram auth store + hook; one POST, one deadline, one shared state for every consumer.
// DEPENDENCIES: react, lib/log, components/telegram-provider, lib/telegram/init-data, lib/telegram/start-param
// GRACE_ANCHORS: [HOOK_TELEGRAM_AUTH, AUTH_STORE, AUTH_DEADLINE, AUTH_RETRY]
// WAVE: W-AUTH-TIMEOUT-RACE-FIX
// ############################################################################

// START_MODULE_CONTRACT: M-HOOK-TELEGRAM-AUTH
// purpose: Authenticate a Telegram WebApp session exactly once via a module-level
//   singleton store, guard the attempt with a 12 s deadline, route start_param into
//   referral vs promo intents safely, and expose retry() for terminal errors.
// owns:
//   - hooks/use-telegram-auth.ts
// inputs: provider state ({ webApp, loaded }) through useTelegram()
// outputs: TelegramAuthResult ({ isLoading, isAuthenticated, error, retry })
// dependencies:
//   - react (useSyncExternalStore)
//   - lib/log
//   - M-TELEGRAM-PROVIDER (useTelegram)
//   - M-TELEGRAM-INIT-DATA (resolveTelegramInitData)
//   - M-TELEGRAM-START-PARAM (classifyStartParam, savePendingPromoToken, cleanStartParamFromUrl, isPromoTokenConsumed)
// side_effects:
//   - one POST /api/auth/telegram or /api/auth/dev per attempt (shared by all consumers)
//   - the Telegram POST carries a per-attempt auth_attempt_id for backend log correlation
//   - POST /api/referral/claim (only for numeric referral codes)
//   - writes promo intent to localStorage
//   - cleans tgWebAppStartParam from browser location URL
//   - module-level deadline timer
// emitted_logs: frontend.flow_failed
// invariants:
//   - single shared auth state across every useTelegramAuth() consumer (one POST, one timer)
//   - the deadline (AUTH_TIMEOUT_MS) starts on the first ensure call, before any SDK check
//   - the deadline is cleared immediately on the fetch response and exactly once per attempt
//   - a terminal error is only restartable through retry()
//   - every attempt mints a fresh auth_attempt_id ([A-Za-z0-9-]+, max 64) and reuses it
//     in its POST body and its TIMEOUT/success/fail logs
//   - promo tokens never hit referral claim endpoint or localStorage
//   - only numeric referral codes are persisted to localStorage or claimed
//   - no raw initData, start_param, promo tokens or referral codes in log events
//   - promo intent stored before setting isAuthenticated=true
//   - dev auth is used only when NODE_ENV=development
// failure_policy: Storage or referral errors fail closed without breaking authentication
// END_MODULE_CONTRACT: M-HOOK-TELEGRAM-AUTH

// START_MODULE_MAP: M-HOOK-TELEGRAM-AUTH
// public_entrypoints:
//   - useTelegramAuth
//   - AUTH_TIMEOUT_MS
//   - __resetTelegramAuthForTests
// semantic_blocks:
//   - AUTH_STORE: module-level state + listener set behind useSyncExternalStore
//   - AUTH_DEADLINE: single 12 s deadline armed before the SDK check
//   - AUTH_ATTEMPT_ID: per-attempt correlation id shared by the request body and logs
//   - ENSURE_AUTH: idempotent start/restart of the shared auth flow
//   - AUTHENTICATE_FLOW: backend auth fetch, promo/referral routing, state commits
//   - AUTH_RETRY: explicit restart after a terminal error
// owned_tests:
//   - __tests__/hooks/useTelegramAuth.test.ts
// END_MODULE_MAP: M-HOOK-TELEGRAM-AUTH

'use client';

import { useEffect, useSyncExternalStore } from 'react';
import { logger, logEvent } from '@/lib/log';
import { useTelegram } from '@/components/telegram-provider';
import {
  resolveTelegramInitData,
  type TelegramInitDataSource,
} from '@/lib/telegram/init-data';
import {
  classifyStartParam,
  savePendingPromoToken,
  cleanStartParamFromUrl,
  isPromoTokenConsumed,
  type StartParamIntent,
} from '@/lib/telegram/start-param';

/** Deadline for the whole auth attempt chain (SDK wait + backend round-trip). */
export const AUTH_TIMEOUT_MS = 12000;

const AUTH_TIMEOUT_ERROR = 'Authentication timeout';

interface TelegramAuthState {
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
}

interface TelegramAuthResult extends TelegramAuthState {
  retry: () => void;
}

/** Structural view of the WebApp fields this module reads. */
type TelegramWebAppLike = TelegramInitDataSource & {
  initDataUnsafe?: {
    start_param?: string;
    user?: { id?: number };
  } | null;
};

// ---------------------------------------------------------------------------
// Module singleton store
// ---------------------------------------------------------------------------

const INITIAL_STATE: TelegramAuthState = {
  isLoading: true,
  isAuthenticated: false,
  error: null,
};

/** Stable snapshot for SSR/hydration — must match INITIAL_STATE values. */
const SERVER_SNAPSHOT: TelegramAuthState = {
  isLoading: true,
  isAuthenticated: false,
  error: null,
};

const store: {
  state: TelegramAuthState;
  listeners: Set<() => void>;
} = {
  state: INITIAL_STATE,
  listeners: new Set(),
};

function setState(next: TelegramAuthState): void {
  store.state = next;
  for (const listener of Array.from(store.listeners)) listener();
}

function subscribe(listener: () => void): () => void {
  store.listeners.add(listener);
  return () => {
    store.listeners.delete(listener);
  };
}

function getSnapshot(): TelegramAuthState {
  return store.state;
}

function getServerSnapshot(): TelegramAuthState {
  return SERVER_SNAPSHOT;
}

// ---------------------------------------------------------------------------
// Module-level attempt bookkeeping
// ---------------------------------------------------------------------------

let deadlineTimer: ReturnType<typeof setTimeout> | null = null;
let deadlineStartedAt: number | null = null;
let deadlineFired = false;
let attempt = 1;
let runId = 0;
let inFlight = false;
let attemptedKey: string | null = null;
let lastInitData = '';
let lastWebApp: TelegramWebAppLike | null = null;
let lastLoaded = false;
/** Attempt id currently in flight (or the last one that ran); read by the deadline warn. */
let activeAuthAttemptId = '';

// START_BLOCK: AUTH_ATTEMPT_ID
/**
 * Mint a correlation id for one auth attempt. Compact UUID (hyphens removed)
 * so the backend PII redactor does not mask it as [redacted-uuid]; the value
 * still matches the backend pattern [A-Za-z0-9-]+ and the 64-char limit.
 */
function createAuthAttemptId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID().replace(/-/g, '');
  }
  return `attempt-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
// END_BLOCK: AUTH_ATTEMPT_ID

function isDevMode(): boolean {
  return process.env.NODE_ENV === 'development';
}

function getWindowWebApp(): TelegramWebAppLike | null {
  if (typeof window === 'undefined') return null;
  return window.Telegram?.WebApp ?? null;
}

// START_BLOCK: AUTH_DEADLINE
function clearDeadline(): void {
  if (deadlineTimer !== null) {
    clearTimeout(deadlineTimer);
    deadlineTimer = null;
  }
}

// START_FUNCTION_CONTRACT: F-M-HOOK-TELEGRAM-AUTH.armDeadline
// purpose: Arm the single shared auth deadline if it is not already running.
// inputs: none (module state)
// returns: void
// side_effects: starts a timer that later logs a safe warn and commits a timeout error
// emitted_logs: none (legacy logger warn on fire)
// error_behavior: never throws
// END_FUNCTION_CONTRACT: F-M-HOOK-TELEGRAM-AUTH.armDeadline
function armDeadline(): void {
  if (deadlineTimer !== null || deadlineFired) return;

  deadlineStartedAt = Date.now();
  deadlineTimer = setTimeout(() => {
    deadlineTimer = null;
    deadlineFired = true;
    const elapsedMs = deadlineStartedAt === null
      ? AUTH_TIMEOUT_MS
      : Date.now() - deadlineStartedAt;

    const extra: Record<string, unknown> = {
      timeout_budget_ms: AUTH_TIMEOUT_MS,
      elapsed_ms: elapsedMs,
      attempt,
    };
    if (activeAuthAttemptId) extra.auth_attempt_id = activeAuthAttemptId;

    logger.warn('[TGAuth] TIMEOUT — auth took too long', { extra });
    setState({
      isLoading: false,
      isAuthenticated: false,
      error: AUTH_TIMEOUT_ERROR,
    });
  }, AUTH_TIMEOUT_MS);
}
// END_BLOCK: AUTH_DEADLINE

// ---------------------------------------------------------------------------
// Start_param / storage helpers
// ---------------------------------------------------------------------------

function readStartParam(initData: string): string | undefined {
  if (typeof window === 'undefined') return undefined;

  const webApp = lastWebApp ?? getWindowWebApp();
  const fromUnsafe = webApp?.initDataUnsafe?.start_param;
  if (fromUnsafe) return fromUnsafe;

  if (initData) {
    const fromInitData = new URLSearchParams(initData).get('start_param');
    if (fromInitData) return fromInitData;
  }

  if (window.location) {
    return new URLSearchParams(window.location.search).get('tgWebAppStartParam') || undefined;
  }
  return undefined;
}

/** Promo intent must be persisted before isAuthenticated=true; consumed tokens are terminal. */
function storePromoIntentIfNeeded(intent: StartParamIntent): void {
  if (intent.kind !== 'promo' || isPromoTokenConsumed(intent.token)) return;

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

async function claimReferralIfNeeded(
  webApp: TelegramWebAppLike | null,
  intent: StartParamIntent,
  rawStartParam: string | undefined,
): Promise<void> {
  const persistKey = '__astro_referral_code';
  const claimKey = '__astro_referral_claimed';

  try {
    const ownId = webApp?.initDataUnsafe?.user?.id;
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
      (window as any)[claimKey] = true;
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
}

// ---------------------------------------------------------------------------
// Auth flow
// ---------------------------------------------------------------------------

function completeAuthRun(
  myRun: number,
  startedAt: number,
  next: TelegramAuthState,
  authAttemptId: string,
): void {
  if (myRun === runId) clearDeadline();
  logger.info('[TGAuth] Auth completed', {
    extra: { duration_ms: Date.now() - startedAt, attempt, auth_attempt_id: authAttemptId },
  });

  if (myRun !== runId) return; // superseded by retry()
  inFlight = false;
  if (deadlineFired) return; // the deadline already committed the timeout error
  setState(next);
}

// START_BLOCK: AUTHENTICATE_FLOW
// START_FUNCTION_CONTRACT: F-M-HOOK-TELEGRAM-AUTH.authenticate
// purpose: Perform the Telegram backend auth for a non-empty initData and commit exactly one terminal state.
// inputs: initData — resolved Telegram initData string
// returns: Promise<void>
// side_effects: POST /api/auth/telegram with a fresh auth_attempt_id, optional POST /api/referral/claim, localStorage writes, URL cleanup
// emitted_logs: frontend.flow_failed (promo intent storage failure)
// error_behavior: network/backend failures commit isLoading=false with an error message
// END_FUNCTION_CONTRACT: F-M-HOOK-TELEGRAM-AUTH.authenticate
async function authenticate(initData: string): Promise<void> {
  const myRun = ++runId;
  const startedAt = Date.now();
  const authAttemptId = createAuthAttemptId();
  activeAuthAttemptId = authAttemptId;
  inFlight = true;
  armDeadline();

  const isCurrent = () => myRun === runId && !deadlineFired;
  const finish = (next: TelegramAuthState) => completeAuthRun(myRun, startedAt, next, authAttemptId);

  logger.info('[TGAuth] authenticate() started', { extra: { auth_attempt_id: authAttemptId } });

  const webApp = lastWebApp ?? getWindowWebApp();
  const rawStartParam = readStartParam(initData);

  // Clean query parameter from location bar immediately
  cleanStartParamFromUrl();

  const intent = classifyStartParam(rawStartParam);
  logger.debug('[TGAuth] Classified start_param intent', { extra: { intentKind: intent.kind } });
  logger.debug('[TGAuth] WebApp', {
    extra: { exists: !!webApp, hasInitData: initData.length > 0 },
  });

  logger.info('[TGAuth] Sending to /api/auth/telegram');

  let response: Response;
  try {
    response = await fetch('/api/auth/telegram', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ initData, authAttemptId }),
      credentials: 'include',
    });
  } catch (error) {
    logger.error('[TGAuth] Exception', { extra: { auth_attempt_id: authAttemptId } });
    finish({
      isLoading: false,
      isAuthenticated: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    });
    return;
  }

  // Deadline is canceled immediately on the response — before sleep(500),
  // before the referral claim and before the state commit.
  if (myRun === runId) clearDeadline();

  logger.debug('[TGAuth] Auth response', { extra: { status: response.status } });

  if (!isCurrent()) {
    finish({
      isLoading: false,
      isAuthenticated: false,
      error: AUTH_TIMEOUT_ERROR,
    });
    return;
  }

  if (!response.ok) {
    const errBody = await response.json().catch(() => ({}));
    logger.error('[TGAuth] Auth failed', { extra: { auth_attempt_id: authAttemptId } });
    finish({
      isLoading: false,
      isAuthenticated: false,
      error: errBody.detail || 'Authentication failed',
    });
    return;
  }

  logger.info('[TGAuth] Auth SUCCESS', { extra: { auth_attempt_id: authAttemptId } });
  await new Promise((resolve) => setTimeout(resolve, 500));

  if (!isCurrent()) {
    finish({
      isLoading: false,
      isAuthenticated: false,
      error: AUTH_TIMEOUT_ERROR,
    });
    return;
  }

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
    storePromoIntentIfNeeded(intent);
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
  await claimReferralIfNeeded(webApp, intent, rawStartParam);

  finish({ isLoading: false, isAuthenticated: true, error: null });
}

// START_FUNCTION_CONTRACT: F-M-HOOK-TELEGRAM-AUTH.settleWithoutInitData
// purpose: Resolve the no-initData branch — dev auth in development, otherwise a terminal skip.
// inputs: none (module state)
// returns: Promise<void>
// side_effects: POST /api/auth/dev in development, promo intent storage, URL cleanup; mints a local auth_attempt_id for logs only
// emitted_logs: frontend.flow_failed (promo intent storage failure)
// error_behavior: dev auth failures commit isLoading=false with an error message
// END_FUNCTION_CONTRACT: F-M-HOOK-TELEGRAM-AUTH.settleWithoutInitData
async function settleWithoutInitData(): Promise<void> {
  const myRun = ++runId;
  const startedAt = Date.now();
  inFlight = true;
  armDeadline();

  logger.info('[TGAuth] Not in Telegram WebApp');
  logger.debug('[TGAuth] Dev mode:', { extra: { isDevMode: isDevMode(), NODE_ENV: process.env.NODE_ENV } });

  const rawStartParam = readStartParam('');
  cleanStartParamFromUrl();

  if (!isDevMode()) {
    logger.info('[TGAuth] Not dev mode, skipping auth');
    clearDeadline();
    inFlight = false;
    setState({ isLoading: false, isAuthenticated: false, error: null });
    return;
  }

  const authAttemptId = createAuthAttemptId();
  activeAuthAttemptId = authAttemptId;
  const finish = (next: TelegramAuthState) => completeAuthRun(myRun, startedAt, next, authAttemptId);

  const intent = classifyStartParam(rawStartParam);
  logger.info('[TGAuth] Using dev auth...');

  try {
    const devResponse = await fetch('/api/auth/dev', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
    });

    // Deadline canceled immediately on the response.
    if (myRun === runId) clearDeadline();

    logger.debug('[TGAuth] Dev auth response', { extra: { status: devResponse.status } });

    if (!devResponse.ok) {
      logger.warn('[TGAuth] Dev auth failed', {
        extra: { status: devResponse.status, auth_attempt_id: authAttemptId },
      });
      throw new Error('Dev auth failed');
    }

    if (myRun !== runId || deadlineFired) {
      finish({
        isLoading: false,
        isAuthenticated: false,
        error: AUTH_TIMEOUT_ERROR,
      });
      return;
    }

    const devData = await devResponse.json();
    logger.info('[TGAuth] Dev auth OK', {
      extra: { userId: devData.userId, auth_attempt_id: authAttemptId },
    });
    await new Promise((resolve) => setTimeout(resolve, 500));

    if (myRun !== runId || deadlineFired) {
      finish({
        isLoading: false,
        isAuthenticated: false,
        error: AUTH_TIMEOUT_ERROR,
      });
      return;
    }

    // Promo intent must also be stored on the dev-auth path — otherwise the gate
    // never sees the pending token outside Telegram. Consumed tokens (terminal
    // completed state) are not re-stored: the webview re-delivers start_param on
    // every load and a re-store would loop preview -> ALREADY_REDEEMED -> reload.
    storePromoIntentIfNeeded(intent);

    finish({ isLoading: false, isAuthenticated: true, error: null });
  } catch (error) {
    logger.error('[TGAuth] Dev auth exception', { extra: { auth_attempt_id: authAttemptId } });
    finish({
      isLoading: false,
      isAuthenticated: false,
      error: error instanceof Error ? error.message : 'Dev auth error',
    });
  }
}
// END_BLOCK: AUTHENTICATE_FLOW

// START_BLOCK: ENSURE_AUTH
// START_FUNCTION_CONTRACT: F-M-HOOK-TELEGRAM-AUTH.ensureAuthStarted
// purpose: Idempotently start (or skip) the shared auth flow for the current provider state.
// inputs: { webApp, loaded } from useTelegram()
// returns: void
// side_effects: arms the deadline, starts authenticate()/dev auth exactly once per key
// emitted_logs: frontend.flow_failed (through authenticate)
// error_behavior: never throws; failures are committed to the shared state
// END_FUNCTION_CONTRACT: F-M-HOOK-TELEGRAM-AUTH.ensureAuthStarted
function ensureAuthStarted({ webApp, loaded }: {
  webApp: TelegramWebAppLike | null;
  loaded: boolean;
}): void {
  lastWebApp = webApp ?? null;
  lastLoaded = loaded;

  const initData = resolveTelegramInitData(webApp ?? getWindowWebApp());
  const key = initData || 'none';

  // The deadline starts on the first ensure call, BEFORE any SDK check, so a
  // missing SDK can never leave consumers in a perpetual loading state.
  if (store.state.isLoading) armDeadline();

  if (inFlight) return;

  // Terminal error is only restartable through retry().
  if (store.state.error !== null) return;

  // Same key already resolved (success or not-in-telegram) — idempotent no-op.
  if (attemptedKey === key) return;

  // No initData and the provider has not resolved the SDK yet: wait for the
  // next provider update; the deadline armed above keeps ticking.
  if (!initData && !loaded) return;

  attemptedKey = key;
  lastInitData = initData;

  if (initData) {
    void authenticate(initData);
  } else {
    void settleWithoutInitData();
  }
}
// END_BLOCK: ENSURE_AUTH

// START_BLOCK: AUTH_RETRY
// START_FUNCTION_CONTRACT: F-M-HOOK-TELEGRAM-AUTH.retry
// purpose: Restart the shared auth flow after a terminal error (timeout, backend 401, etc.).
// inputs: none
// returns: void
// side_effects: clears the deadline, bumps the attempt, resets state to loading and re-runs the flow with the same key
// emitted_logs: none (delegated to authenticate)
// error_behavior: never throws
// END_FUNCTION_CONTRACT: F-M-HOOK-TELEGRAM-AUTH.retry
function retryInternal(): void {
  clearDeadline();
  deadlineFired = false;
  deadlineStartedAt = null;
  attempt += 1;
  runId += 1; // supersede any in-flight run
  inFlight = false;
  attemptedKey = null;
  setState({ isLoading: true, isAuthenticated: false, error: null });

  if (lastInitData) {
    // Full restart with the same key, bypassing the dedup guard.
    attemptedKey = lastInitData;
    void authenticate(lastInitData);
    return;
  }

  // No credentials yet (timeout while waiting for the SDK): re-run the normal
  // decision path with the last known provider state.
  ensureAuthStarted({ webApp: lastWebApp, loaded: lastLoaded });
}
// END_BLOCK: AUTH_RETRY

// START_BLOCK: AUTH_STORE
// START_FUNCTION_CONTRACT: F-M-HOOK-TELEGRAM-AUTH.useTelegramAuth
// purpose: Subscribe a consumer to the shared auth store and ensure the flow has started.
// inputs: none (reads provider state through useTelegram)
// returns: TelegramAuthResult ({ isLoading, isAuthenticated, error, retry })
// side_effects: registers an ensure call per provider state change; unmount does not cancel auth
// emitted_logs: none directly
// error_behavior: server snapshot mirrors the initial loading state (hydration-safe)
// END_FUNCTION_CONTRACT: F-M-HOOK-TELEGRAM-AUTH.useTelegramAuth
export function useTelegramAuth(): TelegramAuthResult {
  const { webApp, loaded } = useTelegram();
  const state = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  useEffect(() => {
    ensureAuthStarted({ webApp, loaded });
  }, [webApp, loaded]);

  return { ...state, retry: retryInternal };
}
// END_BLOCK: AUTH_STORE

// START_BLOCK: AUTH_STORE
// START_FUNCTION_CONTRACT: F-M-HOOK-TELEGRAM-AUTH.__resetTelegramAuthForTests
// purpose: Reset the module singleton store and attempt bookkeeping for test isolation.
// inputs: none
// returns: void
// side_effects: clears timers and listeners, restores the initial state (no notification)
// emitted_logs: none
// error_behavior: never throws
// END_FUNCTION_CONTRACT: F-M-HOOK-TELEGRAM-AUTH.__resetTelegramAuthForTests
export function __resetTelegramAuthForTests(): void {
  if (deadlineTimer !== null) clearTimeout(deadlineTimer);

  deadlineTimer = null;
  deadlineStartedAt = null;
  deadlineFired = false;
  attempt = 1;
  // Invalidate any in-flight run without reusing its id (never reset to 0).
  runId += 1;
  inFlight = false;
  attemptedKey = null;
  lastInitData = '';
  lastWebApp = null;
  lastLoaded = false;
  activeAuthAttemptId = '';

  store.state = { ...INITIAL_STATE };
  store.listeners.clear();
}
// END_BLOCK: AUTH_STORE
