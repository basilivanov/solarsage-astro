import { expect, test } from "@playwright/test"

import { bootstrap, setAccessStateViaUI } from "./helpers"
import { installTelegramMock, PERSONA_FRESH } from "./telegram"

/**
 * E2E-инварианты — бизнес-правила, которые переживут смену копирайта,
 * рефакторинг стора, замену моков на бэк.
 *
 * Все тесты идут пользовательским путём:
 *   - стартуют со страницы `/` с Telegram initData,
 *   - проходят онбординг через UI (см. `bootstrap`),
 *   - переключают состояние доступа через DevModeSwitcher на `/profile`.
 *
 * Никаких прямых записей в localStorage. Никаких soft-asserts вида
 * «if (visible) click». Если инвариант сломан — тест падает.
 */

// ---------------------------------------------------------------------------
// Routing guard: без онбординга все защищённые роуты ведут обратно на `/`
// ---------------------------------------------------------------------------

test.describe("Routing guard: онбординг обязателен", () => {
  test("прямой URL защищённого роута без онбординга редиректит на /", async ({
    page,
  }) => {
    await installTelegramMock(page, PERSONA_FRESH)

    // Guard живёт в layout `(app)` — если он работает для одного роута,
    // он работает для всех. Берём один, не зависящий от даты.
    await page.goto("/calendar")
    await expect(page).toHaveURL("/")
  })
})

// ---------------------------------------------------------------------------
// Access invariants: trial / subscription / expired / none
// ---------------------------------------------------------------------------

test.describe("Access-инварианты", () => {
  test("свежий пользователь после онбординга видит trial-баннер", async ({
    page,
  }) => {
    await bootstrap(page) // по умолчанию — trial

    await expect(
      page.getByText(/14 дней бесплатного доступа/i),
    ).toBeVisible()
  })

  test("при подписке trial-баннер не показывается", async ({ page }) => {
    await bootstrap(page, { access: "subscription" })

    await expect(
      page.getByText(/14 дней бесплатного доступа/i),
    ).toHaveCount(0)
  })

  test("при истёкшем доступе сегодня уходит под paywall", async ({ page }) => {
    await bootstrap(page, { access: "expired" })

    // Paywall на экране дня — заголовок и CTA подписки.
    await expect(
      page.getByRole("heading", {
        name: /разбор на сегодня уже готов|день уже рассчитан/i,
      }),
    ).toBeVisible()
    await expect(
      page.getByRole("button", { name: /Оформить подписку/i }),
    ).toBeVisible()
  })

  test("переключение subscription → none делает разборы недоступными", async ({
    page,
  }) => {
    await bootstrap(page, { access: "subscription" })

    // На подписке доступ к сегодняшнему дню есть — paywall'а нет.
    await expect(
      page.getByRole("button", { name: /Оформить подписку/i }),
    ).toHaveCount(0)

    // Переключаем доступ через тот же dev-switcher, что видит
    // dev-пользователь в `/profile`.
    await setAccessStateViaUI(page, "none")

    // На сегодняшнем дне теперь paywall.
    await expect(
      page.getByRole("button", { name: /Оформить подписку/i }),
    ).toBeVisible()
  })
})

// ---------------------------------------------------------------------------
// Chat: пользовательский bubble появляется немедленно и переживает reload
// ---------------------------------------------------------------------------

test.describe("Chat-инварианты", () => {
  test("отправка сообщения сразу рисует пользовательский bubble", async ({
    page,
  }) => {
    await bootstrap(page, { access: "subscription" })

    await page.goto("/chat")

    const input = page.getByRole("textbox", { name: /Сообщение/i })
    await expect(input).toBeVisible()
    await input.fill("Тестовое сообщение")
    await input.press("Enter")

    // Локальный, синхронный эффект reducer'а — должен появиться сразу.
    await expect(
      page.getByText("Тестовое сообщение", { exact: true }),
    ).toBeVisible({ timeout: 1_000 })
  })

  test("история чата сохраняется после reload", async ({ page }) => {
    await bootstrap(page, { access: "subscription" })

    await page.goto("/chat")

    const input = page.getByRole("textbox", { name: /Сообщение/i })
    await input.fill("Сообщение для проверки сохранения")
    await input.press("Enter")

    await expect(
      page.getByText("Сообщение для проверки сохранения", { exact: true }),
    ).toBeVisible({ timeout: 1_000 })

    await page.reload()

    await expect(
      page.getByText("Сообщение для проверки сохранения", { exact: true }),
    ).toBeVisible({ timeout: 2_000 })
  })
})


