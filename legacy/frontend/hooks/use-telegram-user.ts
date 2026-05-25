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
      // @ts-expect-error — window.Telegram типы определены в telegram-init
      const u = window.Telegram?.WebApp?.initDataUnsafe?.user
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
