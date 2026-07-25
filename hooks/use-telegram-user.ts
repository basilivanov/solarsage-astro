
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USE_TELEGRAM_USER
// ROLE: React hook
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
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

// START_MODULE_MAP
// public_entrypoints:
//   - useTelegramUser
// semantic_blocks:
//   - USE_TELEGRAM_USER_HOOK: Telegram WebApp user subscriber hook
// owned_tests:
//   - __tests__/hooks/useTelegramAuth.test.ts
// END_MODULE_MAP

"use client"

import { useEffect, useState } from "react"
import { useTelegram } from "@/components/telegram-provider"

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

// START_BLOCK: USE_TELEGRAM_USER_HOOK
export function useTelegramUser(): TelegramUser | null {
  const { webApp, loaded } = useTelegram()
  const [user, setUser] = useState<TelegramUser | null>(null)

  useEffect(() => {
    // Use context webApp, falling back to window.Telegram (tests / E2E)
    const tg = webApp ?? (typeof window !== 'undefined' ? window.Telegram?.WebApp : undefined)
    if (!tg && !loaded) return // SDK not ready yet

    try {
      const u = tg?.initDataUnsafe?.user as any
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
  }, [webApp, loaded])

  return user
}
// END_BLOCK: USE_TELEGRAM_USER_HOOK
