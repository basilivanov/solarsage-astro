
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_TELEGRAM_PROVIDER
// ROLE: Client-only React context provider that loads Telegram SDK after hydration
// DEPENDENCIES: react, M-TELEGRAM-INIT-DATA
// GRACE_ANCHORS: []
// ############################################################################

// START_MODULE_CONTRACT: M-TELEGRAM-PROVIDER
// purpose: Provide Telegram WebApp context to client components, resolving initData
//   from the SDK instance or the #tgWebAppData URL hash fallback so inTelegram does
//   not depend on a single SDK load moment.
// owns:
//   - components/telegram-provider.tsx
// inputs: children (ReactNode)
// outputs: TelegramProvider React context provider
// dependencies:
//   - react
//   - M-TELEGRAM-INIT-DATA (resolveTelegramInitData)
// side_effects:
//   - window.Telegram access
//   - injects /telegram-web-app.js script into document.head
//   - schedules initData re-check timers (250/500/1000/2000 ms) and a 10 s safety timeout
// emitted_logs: none
// failure_policy: fallback context value (loaded=true, inTelegram=false)
// invariants:
//   - SSR and first client render expose webApp=null, loaded=false, inTelegram=false
//   - a preset window.Telegram.WebApp is detected without loading the script
//   - inTelegram is recomputed on every resolution, never latched
//   - raw initData is never logged
// END_MODULE_CONTRACT: M-TELEGRAM-PROVIDER

// START_MODULE_MAP: M-TELEGRAM-PROVIDER
// public_entrypoints:
//   - TelegramProvider
//   - useTelegram
// semantic_blocks:
//   - TELEGRAM_PROVIDER: Telegram SDK context provider
//   - INIT_DATA_RESOLUTION: SDK load + late-initData re-checks via M-TELEGRAM-INIT-DATA
// owned_tests:
//   - __tests__/components/telegram-provider.test.tsx
//   - __tests__/hooks/useTelegramAuth.test.ts
// END_MODULE_MAP: M-TELEGRAM-PROVIDER

'use client';

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';

import { resolveTelegramInitData } from '@/lib/telegram/init-data';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Local alias resolved from the window global (recognised by ESLint). */
type TelegramWebAppType = NonNullable<typeof window.Telegram>['WebApp'];

const TELEGRAM_SCRIPT_ID = 'telegram-web-app-sdk';

/**
 * Self-hosted SDK path. Vendored 2026-10-22 from
 * https://telegram.org/js/telegram-web-app.js into public/telegram-web-app.js —
 * re-vendor consciously instead of depending on a third-party origin at runtime.
 */
const TELEGRAM_SCRIPT_SRC = '/telegram-web-app.js';

/** Late-initData re-check offsets (ms) after the SDK resolves without initData. */
const INIT_DATA_RECHECK_DELAYS_MS = [250, 500, 1000, 2000] as const;

export interface TelegramContextValue {
  /** Telegram WebApp instance, or null if not loaded or unavailable */
  webApp: TelegramWebAppType | null;
  /** True after the SDK script has loaded (or failed to load) */
  loaded: boolean;
  /** True when initData is available from the SDK or the URL hash fallback */
  inTelegram: boolean;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const TelegramContext = createContext<TelegramContextValue>({
  webApp: null,
  loaded: false,
  inTelegram: false,
});

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useTelegram(): TelegramContextValue {
  return useContext(TelegramContext);
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

/**
 * Client-only Telegram runtime provider.
 *
 * - Loads `/telegram-web-app.js` **after** hydration (inside `useEffect`),
 *   never during SSR or before React hydrates.
 * - If `window.Telegram` is already set (e.g. E2E test injects it via
 *   `addInitScript`), we detect it during the effect — no duplicate load.
 * - initData is resolved through `resolveTelegramInitData`, so the
 *   `#tgWebAppData=<urlencoded>` URL hash works even when the SDK never
 *   populates `webApp.initData`.
 * - When the SDK resolves without initData, re-checks run at 250/500/1000/2000 ms
 *   and flip `inTelegram` as soon as initData appears (late initData is common
 *   inside Telegram WebView).
 * - Provides the Telegram `WebApp` instance, a `loaded` flag, and an
 *   `inTelegram` flag via `useTelegram()`.
 *
 * The goal is to **eliminate hydration mismatches**: on the server
 * `loaded` is always `false` and `webApp` is always `null`.  During the
 * **first client render** (hydration) the same values are returned, so
 * React sees identical markup.  Only **after** hydration does the SDK
 * load and the context update, triggering a client-only re-render.
 *
 * Safety timeout: if the SDK script fails to load or takes >10 s, we
 * mark as `loaded` anyway so consumers don't stay in a perpetual loading
 * state outside Telegram.
 */
// START_BLOCK: TELEGRAM_PROVIDER
export function TelegramProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<TelegramContextValue>({
    webApp: null,
    loaded: false,
    inTelegram: false,
  });

  useEffect(() => {
    let cancelled = false;
    const recheckTimeouts: Array<ReturnType<typeof setTimeout>> = [];

    const clearRechecks = () => {
      while (recheckTimeouts.length > 0) {
        const timeoutId = recheckTimeouts.pop();
        if (timeoutId !== undefined) clearTimeout(timeoutId);
      }
    };

    // Publish the current WebApp + resolved initData. Returns whether the
    // instance now carries initData (SDK value or URL hash fallback).
    const syncFromWindow = (): boolean => {
      if (cancelled) return true;

      const webApp = window.Telegram?.WebApp ?? null;
      const inTelegram = resolveTelegramInitData(webApp) !== '';
      setState({ webApp, loaded: true, inTelegram });
      return inTelegram;
    };

    // Late-initData polling: only meaningful once the SDK instance exists.
    const scheduleRechecks = () => {
      clearRechecks();
      // START_BLOCK: INIT_DATA_RESOLUTION
      for (const delay of INIT_DATA_RECHECK_DELAYS_MS) {
        recheckTimeouts.push(
          setTimeout(() => {
            if (cancelled) return;
            if (!window.Telegram?.WebApp) return;
            if (syncFromWindow()) clearRechecks();
          }, delay),
        );
      }
      // END_BLOCK: INIT_DATA_RESOLUTION
    };

    const resolveSdk = () => {
      if (cancelled) return;
      if (!syncFromWindow()) scheduleRechecks();
    };

    const existingScript = document.getElementById(TELEGRAM_SCRIPT_ID);
    const script = existingScript ?? document.createElement('script');
    let safetyTimeoutId: ReturnType<typeof setTimeout> | undefined;

    if (window.Telegram?.WebApp) {
      // ---- Already available (E2E fixture or Telegram WebView preload) ----
      resolveSdk();
    } else {
      // ---- Dynamically load the self-hosted Telegram SDK ----
      script.addEventListener('load', resolveSdk);
      script.addEventListener('error', resolveSdk);

      if (!existingScript) {
        script.id = TELEGRAM_SCRIPT_ID;
        script.setAttribute('src', TELEGRAM_SCRIPT_SRC);
        script.setAttribute('async', 'true');
        document.head.appendChild(script);
      }

      // ---- Safety timeout: avoid perpetual loading if script hangs ----
      safetyTimeoutId = setTimeout(() => {
        resolveSdk(); // marks loaded=true even if onload/onerror never fired
      }, 10_000);
    }

    return () => {
      cancelled = true;
      clearRechecks();
      if (safetyTimeoutId !== undefined) clearTimeout(safetyTimeoutId);
      script.removeEventListener('load', resolveSdk);
      script.removeEventListener('error', resolveSdk);
    };
  }, []);

  return (
    <TelegramContext.Provider value={state}>
      {children}
    </TelegramContext.Provider>
  );
}
// END_BLOCK: TELEGRAM_PROVIDER
