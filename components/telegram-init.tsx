
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_TELEGRAM_INIT
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for telegram-init.tsx behavior
// owns:
//   - components/telegram-init.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// public_entrypoints:
//   - TelegramInit
// semantic_blocks:
//   - TELEGRAM_INIT: Telegram WebApp viewport & theme initialization component
// owned_tests:
//   - __tests__/hooks/useTelegramAuth.test.ts
// END_MODULE_MAP

"use client"

import { useEffect } from "react"
import { useTelegram } from "@/components/telegram-provider"

/** Local alias resolved from the window global (recognised by ESLint). */
type TelegramWebAppType = NonNullable<typeof window.Telegram>['WebApp'];

function setAppHeight() {
  try {
    const h = window.visualViewport?.height ?? window.innerHeight
    document.documentElement.style.setProperty('--app-height', `${h}px`)
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
      setAppHeight()
      window.addEventListener('resize', setAppHeight)
      window.visualViewport?.addEventListener('resize', setAppHeight)
      window.visualViewport?.addEventListener('scroll', setAppHeight)
      return () => {
        window.removeEventListener('resize', setAppHeight)
        window.visualViewport?.removeEventListener('resize', setAppHeight)
        window.visualViewport?.removeEventListener('scroll', setAppHeight)
      }
    }

    // Init Telegram
    try { webApp.ready() } catch { /* noop */ }
    try { (webApp as any).setHeaderColor?.("bg_color") } catch { /* noop */ }
    try { (webApp as any).setBackgroundColor?.("bg_color") } catch { /* noop */ }
    if (webApp.colorScheme === "dark") {
      document.documentElement.classList.add("dark")
    }

    // Expand — retry several times (Telegram may ignore first call during open animation)
    const expand = () => {
      try { webApp.expand() } catch { /* noop */ }
      if (isMethodSupported(webApp, 'requestFullscreen')) {
        try { (webApp as any).requestFullscreen() } catch { /* noop */ }
      }
      if (isMethodSupported(webApp, 'disableVerticalSwipes')) {
        try { (webApp as any).disableVerticalSwipes() } catch { /* noop */ }
      }
    }
    expand()
    const delays = [60, 200, 500, 1000]
    for (const ms of delays) {
      setTimeout(expand, ms)
    }

    // Re-expand on viewport change
    const onViewport = () => {
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
      window.removeEventListener('resize', setAppHeight)
      window.visualViewport?.removeEventListener('resize', setAppHeight)
      window.visualViewport?.removeEventListener('scroll', setAppHeight)
      try { webApp.offEvent?.('viewportChanged', onViewport) } catch { /* noop */ }
    }
  }, [webApp])

  return null
}
// END_BLOCK: TELEGRAM_INIT

