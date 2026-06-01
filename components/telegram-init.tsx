"use client"

import { useEffect, useRef } from "react"

let appHeightSet = false

function setAppHeight() {
  try {
    const h = window.visualViewport?.height ?? window.innerHeight
    document.documentElement.style.setProperty('--app-height', `${h}px`)
    appHeightSet = true
  } catch {}
}

export function TelegramInit() {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

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
    try { tg.setHeaderColor("bg_color") } catch {}
    try { tg.setBackgroundColor("bg_color") } catch {}
    if (tg.colorScheme === "dark") {
      document.documentElement.classList.add("dark")
    }

    // Expand — retry several times (Telegram may ignore first call during open animation)
    const expand = () => {
      try { tg.expand() } catch {}
      try { (tg as any).requestFullscreen?.() } catch {}
      try { (tg as any).disableVerticalSwipes?.() } catch {}
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
