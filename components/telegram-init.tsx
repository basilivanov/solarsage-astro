"use client"

import { useEffect } from "react"

let appHeightSet = false

function setAppHeight() {
  try {
    const h = window.visualViewport?.height ?? window.innerHeight
    document.documentElement.style.setProperty('--app-height', `${h}px`)
    appHeightSet = true
  } catch {}
}

/**
 * Check if a Telegram WebApp method is supported in the current version.
 * Compares the running WebApp version against the minimum required version.
 */
function isMethodSupported(tg: NonNullable<typeof window.Telegram>['WebApp'], method: string): boolean {
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

export function TelegramInit() {
  useEffect(() => {
    const tg = window?.Telegram?.WebApp
    if (!tg) {
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
    try { tg.ready() } catch {}
    try { (tg as any).setHeaderColor?.("bg_color") } catch {}
    try { (tg as any).setBackgroundColor?.("bg_color") } catch {}
    if (tg.colorScheme === "dark") {
      document.documentElement.classList.add("dark")
    }

    // Expand — retry several times (Telegram may ignore first call during open animation)
    const expand = () => {
      try { tg.expand() } catch {}
      if (isMethodSupported(tg, 'requestFullscreen')) {
        try { (tg as any).requestFullscreen() } catch {}
      }
      if (isMethodSupported(tg, 'disableVerticalSwipes')) {
        try { (tg as any).disableVerticalSwipes() } catch {}
      }
    }
    expand()
    const delays = [60, 200, 500, 1000]
    for (const ms of delays) {
      setTimeout(expand, ms)
    }

    // Re-expand on viewport change
    const onViewport = () => {
      if (!tg.isExpanded) {
        try { tg.expand() } catch {}
      }
    }
    try { tg.onEvent?.('viewportChanged', onViewport) } catch {}

    // Track real viewport height for --app-height
    setAppHeight()
    window.addEventListener('resize', setAppHeight)
    window.visualViewport?.addEventListener('resize', setAppHeight)
    window.visualViewport?.addEventListener('scroll', setAppHeight)

    return () => {
      window.removeEventListener('resize', setAppHeight)
      window.visualViewport?.removeEventListener('resize', setAppHeight)
      window.visualViewport?.removeEventListener('scroll', setAppHeight)
      try { tg.offEvent?.('viewportChanged', onViewport) } catch {}
    }
  }, [])

  return null
}
