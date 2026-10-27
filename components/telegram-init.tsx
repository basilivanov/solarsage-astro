
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_TELEGRAM_INIT
// ROLE: Initializes Telegram viewport behavior and publishes content-safe-area CSS state.
// DEPENDENCIES: local Telegram provider
// GRACE_ANCHORS: TELEGRAM_INIT
// SLICE: W-TODAY-MOBILE-READABILITY/01
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Initialize Telegram viewport/theme behavior and expose a combined safe-area top inset to scoped top controls.
// owns:
//   - components/telegram-init.tsx
// inputs: Component props / hook params
// outputs: null render plus --app-height and --tg-content-safe-area-inset-top document variables.
// dependencies: local modules, lib/telegram/safe-area
// side_effects: document root CSS variables, Telegram event subscriptions, and viewport listeners/timers.
// emitted_logs: n/a (tests)
// invariants:
//   - existing expand/fullscreen and --app-height behavior remains active.
//   - top inset = max(contentSafeAreaInset.top, safeAreaInset.top + fullscreen reserve); consumers add env(safe-area-inset-top) and 1rem.
//   - fullscreen with contentSafeAreaInset.top=0 reserves 48 px above safeAreaInset.top.
//   - safeAreaChanged, contentSafeAreaChanged, viewportChanged, and fullscreenChanged all recompute the inset.
// failure_policy: browser/API capability failures are swallowed to preserve rendering.
// END_MODULE_CONTRACT

// START_MODULE_MAP
// public_entrypoints:
//   - TelegramInit
// semantic_blocks:
//   - TELEGRAM_INIT: Telegram WebApp viewport & theme initialization component
// owned_tests:
//   - __tests__/lib/telegram-safe-area.test.ts
//   - __tests__/lib/telegram-init.test.tsx
//   - __tests__/app/day-page.test.tsx
//   - __tests__/components/CalendarScreen.test.tsx
// END_MODULE_MAP

"use client"

import { useEffect } from "react"
import { useTelegram } from "@/components/telegram-provider"
import {
  computeTelegramTopSafeAreaInset,
  type TelegramSafeAreaSource,
} from "@/lib/telegram/safe-area"

/** Local alias resolved from the window global (recognised by ESLint). */
type TelegramWebAppType = NonNullable<typeof window.Telegram>['WebApp'];

const TOP_SAFE_AREA_VAR = '--tg-content-safe-area-inset-top';

function setAppHeight() {
  try {
    const h = window.visualViewport?.height ?? window.innerHeight
    document.documentElement.style.setProperty('--app-height', `${h}px`)
  } catch { /* noop */ }
}

function setTopSafeArea(webApp: TelegramSafeAreaSource | null) {
  try {
    const top = computeTelegramTopSafeAreaInset(webApp);
    document.documentElement.style.setProperty(TOP_SAFE_AREA_VAR, `${top}px`);
  } catch { /* noop */ }
}

function clearTopSafeArea() {
  try {
    document.documentElement.style.removeProperty(TOP_SAFE_AREA_VAR);
  } catch { /* noop */ }
}

/**
 * Check if a Telegram WebApp method is supported in the current version.
 * Compares the running WebApp version against the minimum required version.
 */
function isMethodSupported(tg: TelegramWebAppType, method: string): boolean {
  try {
    const version = (tg as any).version
    if (!version) return false
    // requestFullscreen requires 7.7+, disableVerticalSwipes requires 7.7+
    const minVersions: Record<string, string> = {
      requestFullscreen: '7.7',
      disableVerticalSwipes: '7.7',
    }
    const minVersion = minVersions[method]
    if (!minVersion) return true
    return version >= minVersion
  } catch {
    return false
  }
}

// START_BLOCK: TELEGRAM_INIT
export function TelegramInit() {
  const { webApp } = useTelegram()

  useEffect(() => {
    if (!webApp) {
      // Outside Telegram: use visualViewport as --app-height
      setTopSafeArea(null)
      setAppHeight()
      window.addEventListener('resize', setAppHeight)
      window.visualViewport?.addEventListener('resize', setAppHeight)
      window.visualViewport?.addEventListener('scroll', setAppHeight)
      return () => {
        window.removeEventListener('resize', setAppHeight)
        window.visualViewport?.removeEventListener('resize', setAppHeight)
        window.visualViewport?.removeEventListener('scroll', setAppHeight)
        clearTopSafeArea()
      }
    }

    // Init Telegram
    try { webApp.ready() } catch { /* noop */ }
    try { (webApp as any).setHeaderColor?.("bg_color") } catch { /* noop */ }
    try { (webApp as any).setBackgroundColor?.("bg_color") } catch { /* noop */ }
    if (webApp.colorScheme === "dark") {
      document.documentElement.classList.add("dark")
    }

    const onSafeAreaChange = () => setTopSafeArea(webApp as TelegramSafeAreaSource)
    onSafeAreaChange()
    try { webApp.onEvent?.('safeAreaChanged', onSafeAreaChange) } catch { /* noop */ }
    try { webApp.onEvent?.('contentSafeAreaChanged', onSafeAreaChange) } catch { /* noop */ }
    try { webApp.onEvent?.('fullscreenChanged', onSafeAreaChange) } catch { /* noop */ }

    // Expand — retry several times (Telegram may ignore first call during open animation).
    // Recompute the inset after every expand/fullscreen attempt: Telegram updates
    // safeAreaInset/contentSafeAreaInset asynchronously around those transitions.
    const expand = () => {
      try { webApp.expand() } catch { /* noop */ }
      if (isMethodSupported(webApp, 'requestFullscreen')) {
        try { (webApp as any).requestFullscreen() } catch { /* noop */ }
      }
      if (isMethodSupported(webApp, 'disableVerticalSwipes')) {
        try { (webApp as any).disableVerticalSwipes() } catch { /* noop */ }
      }
      onSafeAreaChange()
    }
    expand()
    const expandTimers = [60, 200, 500, 1000].map((ms) => setTimeout(expand, ms))

    // Re-expand and recompute on viewport change
    const onViewport = () => {
      onSafeAreaChange()
      setAppHeight()
      if (!webApp.isExpanded) {
        try { webApp.expand() } catch { /* noop */ }
      }
    }
    try { webApp.onEvent?.('viewportChanged', onViewport) } catch { /* noop */ }

    // Track real viewport height for --app-height
    setAppHeight()
    window.addEventListener('resize', setAppHeight)
    window.visualViewport?.addEventListener('resize', setAppHeight)
    window.visualViewport?.addEventListener('scroll', setAppHeight)

    return () => {
      expandTimers.forEach((timer) => clearTimeout(timer))
      window.removeEventListener('resize', setAppHeight)
      window.visualViewport?.removeEventListener('resize', setAppHeight)
      window.visualViewport?.removeEventListener('scroll', setAppHeight)
      try { webApp.offEvent?.('viewportChanged', onViewport) } catch { /* noop */ }
      try { webApp.offEvent?.('safeAreaChanged', onSafeAreaChange) } catch { /* noop */ }
      try { webApp.offEvent?.('contentSafeAreaChanged', onSafeAreaChange) } catch { /* noop */ }
      try { webApp.offEvent?.('fullscreenChanged', onSafeAreaChange) } catch { /* noop */ }
      clearTopSafeArea()
    }
  }, [webApp])

  return null
}
// END_BLOCK: TELEGRAM_INIT
