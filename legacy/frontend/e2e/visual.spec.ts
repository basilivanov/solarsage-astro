import { expect, test } from "@playwright/test"

import { bootstrap } from "./helpers"

/**
 * Визуальные контракты — только для экранов, чьё отличие нельзя выразить
 * текстовым ассертом без жёсткой привязки к копирайту/вёрстке.
 *
 * Текстовые/state-инварианты живут в `invariants.spec.ts`. Здесь — три
 * крупных layout'а:
 *
 *   - calendar  — сетка месяца, статусы дней, заголовки.
 *   - readings  — карусель/карточки разборов.
 *   - paywall   — состояние «доступ истёк» на экране дня.
 *
 * Снапшоты в репозитории отсутствуют — при первом запуске сгенерировать
 * и закоммитить:
 *
 *   pnpm playwright test e2e/visual.spec.ts --update-snapshots
 *
 * Снапшоты лежат рядом со спекой в `e2e/visual.spec.ts-snapshots/`.
 */

// Бюджет на затухание transition-анимаций — ровно столько, сколько они
// идут в этом UI. Без него сравнение мерцает.
const SETTLE_MS = 300

test("calendar: сетка месяца", async ({ page }) => {
  await bootstrap(page, { access: "subscription" })
  await page.goto("/calendar")
  await expect(page).toHaveURL(/\/calendar$/)
  await page.waitForTimeout(SETTLE_MS)

  await expect(page).toHaveScreenshot("calendar.png", { fullPage: true })
})

test("readings: список разборов на подписке", async ({ page }) => {
  await bootstrap(page, { access: "subscription" })
  await page.goto("/readings")
  await expect(page).toHaveURL(/\/readings$/)
  await page.waitForTimeout(SETTLE_MS)

  await expect(page).toHaveScreenshot("readings.png", { fullPage: true })
})

test("today: paywall после истечения доступа", async ({ page }) => {
  await bootstrap(page, { access: "expired" })

  await expect(
    page.getByRole("button", { name: /Оформить подписку/i }),
  ).toBeVisible()
  await page.waitForTimeout(SETTLE_MS)

  await expect(page).toHaveScreenshot("today-expired-paywall.png", {
    fullPage: true,
  })
})
