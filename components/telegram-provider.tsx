
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_TELEGRAM_PROVIDER
// ROLE: Client-only React context provider that loads Telegram SDK after hydration
// DEPENDENCIES: react
// GRACE_ANCHORS: []
// ############################################################################

'use client';

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Local alias resolved from the window global (recognised by ESLint). */
type TelegramWebAppType = NonNullable<typeof window.Telegram>['WebApp'];

const TELEGRAM_SCRIPT_ID = 'telegram-web-app-sdk';

export interface TelegramContextValue {
  /** Telegram WebApp instance, or null if not loaded or unavailable */
  webApp: TelegramWebAppType | null;
  /** True after the SDK script has loaded (or failed to load) */
  loaded: boolean;
  /** True when we have a Telegram WebApp with meaningful initData */
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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** True if the Telegram WebApp carries real initData (i.e. we are inside a
 *  Telegram Mini App, not just loading the SDK in a regular browser). */
function hasTelegramContext(webApp: TelegramWebAppType | null): boolean {
  return !!webApp && !!webApp.initData;
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

/**
 * Client-only Telegram runtime provider.
 *
 * - Loads `https://telegram.org/js/telegram-web-app.js` **after** hydration
 *   (inside `useEffect`), never during SSR or before React hydrates.
 * - If `window.Telegram` is already set (e.g. E2E test injects it via
 *   `addInitScript`), we detect it during the effect — no duplicate load.
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
export function TelegramProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<TelegramContextValue>({
    webApp: null,
    loaded: false,
    inTelegram: false,
  });

  useEffect(() => {
    let cancelled = false;

    // ---- Already available (E2E fixture or Telegram WebView preload) ----
    if (window.Telegram?.WebApp) {
      const webApp = window.Telegram.WebApp;
      setState({
        webApp,
        loaded: true,
        inTelegram: hasTelegramContext(webApp),
      });
      return;
    }

    // ---- Dynamically load the Telegram SDK ----
    const existingScript = document.getElementById(TELEGRAM_SCRIPT_ID);
    const script = existingScript ?? document.createElement('script');

    // Shared handler: resolve with whatever window.Telegram provides
    const resolve = () => {
      if (cancelled) return;

      const webApp = window.Telegram?.WebApp ?? null;
      setState({
        webApp,
        loaded: true,
        inTelegram: hasTelegramContext(webApp),
      });
    };

    script.addEventListener('load', resolve);
    script.addEventListener('error', resolve);

    if (!existingScript) {
      script.id = TELEGRAM_SCRIPT_ID;
      script.setAttribute('src', 'https://telegram.org/js/telegram-web-app.js');
      script.setAttribute('async', 'true');
      document.head.appendChild(script);
    }

    // ---- Safety timeout: avoid perpetual loading if script hangs ----
    const timeoutId = setTimeout(() => {
      resolve(); // marks loaded=true even if onload/onerror never fired
    }, 10_000);

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
      script.removeEventListener('load', resolve);
      script.removeEventListener('error', resolve);
    };
  }, []);

  return (
    <TelegramContext.Provider value={state}>
      {children}
    </TelegramContext.Provider>
  );
}
