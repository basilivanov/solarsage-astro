import { expect, test } from "@playwright/test"

import { completeOnboarding } from "./helpers"
import { installTelegramMock, PERSONA_FRESH } from "./telegram"

/**
 * Smoke-сценарий онбординга.
 *
 * Канон: приложение стартует от Telegram initData (а не от localStorage),
 * проходит welcome → birth → place → birthday → done и попадает в
 * `/day/<today>`. Каждый шаг заполняется тем же путём, что и у пользователя
 * — через UI-хелпер `completeOnboarding`.
 *
 * Если этот тест падает, значит сломан реальный пользовательский путь
 * (а не «помощь» вокруг него).
 */
test.describe("Онбординг через initData", () => {
  test("свежий пользователь проходит онбординг до сегодняшнего дня", async ({
    page,
  }) => {
    await installTelegramMock(page, PERSONA_FRESH)
    await page.goto("/")

    // Welcome — заголовок первого экрана виден до начала прохождения.
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible()

    await completeOnboarding(page)

    // После онбординга — мы на сегодняшнем дне и видим нижнюю навигацию.
    await expect(page).toHaveURL(/\/day\/\d{4}-\d{2}-\d{2}$/)
    await expect(
      page.getByRole("navigation", { name: /Основная навигация/i }),
    ).toBeVisible()
  })

  test("повторный visit после онбординга сразу ведёт на сегодняшний день", async ({
    page,
  }) => {
    await installTelegramMock(page, PERSONA_FRESH)
    await page.goto("/")
    await completeOnboarding(page)

    // Reload корня: флаг онбординга уже сохранён, страница `/` редиректит
    // на сегодня и онбординг больше не показывается.
    await page.goto("/")
    await expect(page).toHaveURL(/\/day\/\d{4}-\d{2}-\d{2}$/)
    await expect(
      page.getByRole("button", { name: "Продолжить" }),
    ).toHaveCount(0)
  })
})
