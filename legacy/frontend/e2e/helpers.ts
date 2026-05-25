import { expect, type Page } from "@playwright/test"

import {
  installTelegramMock,
  PERSONA_FRESH,
  type TgPersona,
} from "./telegram"

/**
 * E2E-хелперы. Главное правило:
 *
 *   Тесты идут тем же путём, что и пользователь.
 *
 * Никаких записей в `localStorage`, никаких подменённых стейтов,
 * никаких dev-only флагов через query / cookies / window.* — всё
 * только через реальный UI. Если что-то нельзя выразить через UI,
 * значит, у пользователя такого пути нет, и тест не должен это
 * пытаться эмулировать.
 *
 * Состав:
 *   - completeOnboarding(page) — проходит онбординг полностью.
 *   - setAccessStateViaUI(page, state) — переключает доступ через
 *     DevModeSwitcher на /profile (тот самый UI, который видит
 *     dev-пользователь).
 *   - bootstrap(page, opts) — частый префикс: install + goto + onboarding
 *     (+ опциональное переключение доступа).
 */

// ---------------------------------------------------------------------------
// completeOnboarding
// ---------------------------------------------------------------------------

/**
 * Проходит онбординг ровно теми же шагами, что и реальный пользователь:
 *
 *   welcome   →  «Продолжить»
 *   birth     →  ДД·ММ·ГГГГ + ЧЧ:ММ → «Далее»
 *   place     →  город рождения + «Сейчас живу там же» → «Далее»
 *   birthday  →  «встречу там же» (вкл. по умолчанию) → «Далее»
 *   done      →  ждём окончания «расчёта» (~1.5s), жмём «Открыть мой день»
 *
 * После выполнения страница находится на `/day/<today>`.
 *
 * Контракт вызывающего: Telegram-мок уже установлен и `page.goto("/")`
 * уже выполнен. Это намеренно: и установка мока, и первая навигация —
 * это часть теста, а не хелпера.
 */
export async function completeOnboarding(page: Page) {
  // ── 1. Welcome ────────────────────────────────────────────────────────
  await page.getByRole("button", { name: "Продолжить" }).click()

  // ── 2. Birth: 14.07.1995, 08:42 ───────────────────────────────────────
  // На шаге `birth` плейсхолдеры идут в DOM-порядке:
  //   ДД  ·  ММ (месяц)  ·  ГГГГ  |  ЧЧ  :  ММ (минуты)
  // Поэтому "ММ" встречается дважды — берём по индексу.
  await page.getByPlaceholder("ДД").fill("14")
  await page.getByPlaceholder("ММ").first().fill("07") // месяц
  await page.getByPlaceholder("ГГГГ").fill("1995")
  await page.getByPlaceholder("ЧЧ").fill("08")
  await page.getByPlaceholder("ММ").nth(1).fill("42") // минуты
  await page.getByRole("button", { name: "Далее" }).click()

  // ── 3. Place: город рождения + «живу там же» ─────────────────────────
  // CityPicker считает значение валидным, как только в инпуте ≥ 2 символов;
  // кликать саджест не требуется. Плейсхолдер инпута — «Например, Санкт-Петербург».
  await page.getByPlaceholder(/Санкт-Петербург/i).fill("Москва")
  await page.getByText("Сейчас живу там же").click()
  await page.getByRole("button", { name: "Далее" }).click()

  // ── 4. Birthday: «встречу там же» уже включено по умолчанию ──────────
  // (см. initialOnboardingState.birthdaySameAsCurrent === true)
  await page.getByRole("button", { name: "Далее" }).click()

  // ── 5. Done: ждём окончания «расчёта» и открываем день ──────────────
  // Кнопка переключает label с «Ещё секунду…» на «Открыть мой день»
  // примерно через 1.5s — поэтому ждём именно по новому имени.
  const open = page.getByRole("button", { name: "Открыть мой день" })
  await expect(open).toBeVisible({ timeout: 5_000 })
  await expect(open).toBeEnabled()
  await open.click()

  // Финальный инвариант: онбординг ведёт на сегодняшний день.
  await expect(page).toHaveURL(/\/day\/\d{4}-\d{2}-\d{2}$/)
}

// ---------------------------------------------------------------------------
// setAccessStateViaUI
// ---------------------------------------------------------------------------

/**
 * Состояние доступа в проде придёт с биллингового бэкенда; пока его нет,
 * у нас в `/profile` есть `DevModeSwitcher`. Тесты используют ровно его —
 * это единственный путь, который видит и пользователь (на dev-сборке).
 *
 * После переключения хелпер возвращает страницу обратно на тот URL,
 * с которого был вызван, чтобы тест не «терял» контекст.
 */
type AccessTarget = "trial" | "subscription" | "expired" | "none"

const ACCESS_LABELS: Record<AccessTarget, string> = {
  trial: "Триал · 14 дней",
  subscription: "Подписка активна",
  expired: "Доступ истёк",
  none: "Доступа нет",
}

export async function setAccessStateViaUI(
  page: Page,
  target: AccessTarget,
) {
  const returnUrl = page.url()

  await page.goto("/profile")

  // Раскрываем dev-секцию, если она ещё свёрнута.
  const toggle = page.getByRole("button", { name: /Для разработчика/i })
  await expect(toggle).toBeVisible()
  if ((await toggle.getAttribute("aria-expanded")) !== "true") {
    await toggle.click()
  }

  const option = page.getByRole("button", { name: ACCESS_LABELS[target] })
  await expect(option).toBeVisible()
  await option.click()

  // Возвращаемся туда, где были — кроме случая, когда тест и так был на /profile.
  if (!returnUrl.endsWith("/profile")) {
    await page.goto(returnUrl)
  }
}

// ---------------------------------------------------------------------------
// bootstrap
// ---------------------------------------------------------------------------

type BootstrapOptions = {
  persona?: TgPersona
  /**
   * Состояние доступа после онбординга. По умолчанию — `trial` (новое
   * состояние свежего пользователя). Любое другое значение применится
   * через UI dev-switcher после онбординга.
   */
  access?: AccessTarget
}

/**
 * Самый частый префикс теста: установить мок, открыть `/`, пройти
 * онбординг, (опционально) переключить состояние доступа.
 *
 * После выполнения страница — на `/day/<today>` с нужным состоянием доступа.
 */
export async function bootstrap(page: Page, options: BootstrapOptions = {}) {
  const { persona = PERSONA_FRESH, access } = options

  await installTelegramMock(page, persona)
  await page.goto("/")
  await completeOnboarding(page)

  if (access && access !== "trial") {
    await setAccessStateViaUI(page, access)
  }
}
