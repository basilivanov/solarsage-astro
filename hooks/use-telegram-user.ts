
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USE_TELEGRAM_USER
// ROLE: React hook
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: UI use-telegram-user — component
// owns:
//   - hooks/use-telegram-user.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { useEffect, useState } from "react"

/**
 * Подписчик на Telegram WebApp user.
 *
 * Работает только в Telegram mini-app окружении. Если SDK ещё не загрузился
 * или приложение открыто вне Telegram — возвращает `null`.
 *
 * Sample payload SDK мы нормализуем в camelCase, чтобы UI не разбирался
 * с `first_name`/`photo_url` напрямую.
 */
export type TelegramUser = {
  firstName?: string
  lastName?: string
  username?: string
  photoUrl?: string
}

export function useTelegramUser(): TelegramUser | null {
  const [user, setUser] = useState<TelegramUser | null>(null)

  useEffect(() => {
    try {
      const u = window.Telegram?.WebApp?.initDataUnsafe?.user as any
      if (!u) return
      setUser({
        firstName: u.first_name,
        lastName: u.last_name,
        username: u.username,
        photoUrl: u.photo_url,
      })
    } catch {
      /* ignore */
    }
  }, [])

  return user
}
