"use client"

import { useEffect } from "react"

type TGWebApp = {
  ready?: () => void
  expand?: () => void
  disableVerticalSwipes?: () => void
  setHeaderColor?: (c: string) => void
  setBackgroundColor?: (c: string) => void
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TGWebApp }
  }
}

export function TelegramInit() {
  useEffect(() => {
    const tg = window.Telegram?.WebApp
    if (!tg) return
    try {
      tg.ready?.()
      tg.expand?.()
      // отключаем системный "свайп вниз = закрыть", чтобы не мешал скроллу
      tg.disableVerticalSwipes?.()
      tg.setHeaderColor?.("#f6f3ec")
      tg.setBackgroundColor?.("#f6f3ec")
    } catch {
      // ignore — запуск вне Telegram
    }
  }, [])

  return null
}
