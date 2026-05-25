import type { Page } from "@playwright/test"

/**
 * Канон: всё, что приложение знает о пользователе Telegram, оно получает
 * через `window.Telegram.WebApp.initDataUnsafe.user`. Тесты идут тем же
 * путём — никаких обходов через query/localStorage/cookies.
 *
 * Этот файл — единственный источник правды для e2e: формат initData,
 * заглушки методов WebApp, готовые персоны.
 */

export type TgUser = {
  id: number
  first_name: string
  last_name?: string
  username?: string
  photo_url?: string
  language_code?: string
}

export type TgPersona = {
  user: TgUser
  /** Параметр диплинка `?startapp=...`. Пока нигде не читаем, но кладём — пригодится. */
  start_param?: string
}

/** Свежий пользователь, онбординг не пройден. */
export const PERSONA_FRESH: TgPersona = {
  user: {
    id: 1001,
    first_name: "Alice",
    username: "alice_test",
    language_code: "ru",
  },
}

/** Тот же пользователь, но «вернувшийся» (start_param на будущее). */
export const PERSONA_RETURNING: TgPersona = {
  user: {
    id: 1002,
    first_name: "Bob",
    username: "bob_test",
    language_code: "ru",
  },
  start_param: "onboarded",
}

/**
 * Ставит мок Telegram WebApp ДО любой навигации.
 * Должен вызываться до `page.goto(...)`.
 *
 * Заглушки методов — no-op: TelegramInit вызывает ready/expand/...,
 * нам важно только не упасть и оставить корректный initDataUnsafe.
 */
export async function installTelegramMock(page: Page, persona: TgPersona) {
  const initDataUnsafe = {
    user: persona.user,
    auth_date: Math.floor(Date.now() / 1000),
    hash: "test-hash",
    ...(persona.start_param ? { start_param: persona.start_param } : {}),
  }

  await page.addInitScript((data) => {
    const noop = () => {}
    // Минимальный, но достаточный для текущего кода набор API.
    const WebApp = {
      initData: "",
      initDataUnsafe: data,
      ready: noop,
      expand: noop,
      close: noop,
      disableVerticalSwipes: noop,
      enableVerticalSwipes: noop,
      setHeaderColor: noop,
      setBackgroundColor: noop,
      MainButton: { show: noop, hide: noop, setText: noop, onClick: noop },
      BackButton: { show: noop, hide: noop, onClick: noop },
      HapticFeedback: { impactOccurred: noop, notificationOccurred: noop, selectionChanged: noop },
    }
    ;(window as unknown as { Telegram: { WebApp: typeof WebApp } }).Telegram = { WebApp }
  }, initDataUnsafe)
}
