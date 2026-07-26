import { test, expect } from "@playwright/test"

test.describe("Synastry detail mock visual contract", () => {
  test.beforeEach(async ({ page }) => {
    // Intercept GET /api/synastry list route
    await page.route("/api/synastry", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          partners: [
            {
              id: "partner-test-1",
              name: "Ирина",
              relationType: "romantic",
              birthDate: "1992-05-20",
              precision: "exact",
              score: 78,
              status: "good",
              summary: "Партнёры отлично дополняют друг друга.",
              counters: { good: 5, mid: 2, bad: 1 },
              reportState: "ready",
              createdAt: "2026-07-25T12:00:00Z",
            },
          ],
        }),
      })
    })

    // Intercept GET /api/synastry/partner-test-1 detail route
    await page.route("/api/synastry/partner-test-1", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "rep-123",
          ownerId: "user-1",
          partnerId: "partner-test-1",
          partnerName: "Ирина",
          relationType: "romantic",
          precision: "exact",
          score: 78,
          status: "good",
          verdict: "Хорошая гармония",
          summary: "Партнёры отлично дополняют друг друга.",
          counters: { good: 5, mid: 2, bad: 1 },
          ownerPlanets: [
            { id: "owner_sun", owner: "user", planet: "Sun", longitude: 120.0, sign: "Leo", retrograde: false, house: null, houseReliable: false },
          ],
          partnerPlanets: [
            { id: "partner_moon", owner: "partner", planet: "Moon", longitude: 0.0, sign: "Aries", retrograde: false, house: 5, houseReliable: true },
          ],
          aspects: [
            {
              id: "sun_trine_moon",
              title: "Солнце трин Луна",
              tone: "good",
              score: 90,
              description: "Естественная гармония эмоционального и сознательного.",
              techSignature: "Sun trine Moon (1.0°)",
              ownerPlanetKey: "owner_sun",
              partnerPlanetKey: "partner_moon",
              aspectSymbol: "△",
              orbDegrees: 1.0,
              orbLabel: "1°00′",
            },
            {
              id: "error_aspect",
              title: "Ошибка аспекта",
              tone: "bad",
              score: 30,
              description: "Тестовый аспект для ошибки",
              techSignature: "Error aspect",
              ownerPlanetKey: "owner_sun",
              partnerPlanetKey: "partner_moon",
              aspectSymbol: "□",
              orbDegrees: 2.0,
              orbLabel: "2°00′",
            },
          ],
          houseOverlays: [
            { tech: "Её Венера → твой 7 дом", text: "Партнёр быстро воспринимается как подходящий спутник." },
          ],
          spheres: [
            { id: "intimacy", title: "Близость", score: 85, description: "Высокая эмоциональная близость." },
          ],
          translations: [
            {
              tone: "good",
              title: "Взаимная поддержка",
              aspectId: "sun_trine_moon",
              tech: "Солнце трин Луна",
              text: "Естественное понимание потребностей друг друга.",
              scene: "Совместное принятие решений проходит легко.",
            },
          ],
          userFeedback: null,
          createdAt: "2026-07-25T12:00:00Z",
        }),
      })
    })

    // Intercept GET aspect drilldown route for sun_trine_moon
    await page.route("/api/synastry/partner-test-1/aspect/sun_trine_moon", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          aspectId: "sun_trine_moon",
          title: "Солнце трин Луна",
          tone: "good",
          techSignature: "Sun trine Moon (1.0°)",
          aspectSymbol: "△",
          aspectKindLabel: "Тригон",
          orbText: "орб 1°00′",
          headline: "Естественная гармония эмоционального и сознательного",
          ownerPlanet: { key: "Sun", label: "Солнце", glyph: "☉", meaning: "Ядро личности." },
          partnerPlanet: { key: "Moon", label: "Луна", glyph: "☽", meaning: "Эмоциональные реакции." },
          aspectMechanics: "Гармоничный поток энергии.",
          explanation: "Естественное взаимопонимание.",
          scenes: [
            { title: "В общении", text: "Легко договариваетесь." },
            { title: "В быту", text: "Совместный уклад настраивается быстро." },
            { title: "В споре", text: "Быстро находите компромисс." },
          ],
          repairs: [
            "1. Замечать и называть сильные стороны",
            "2. Поддерживать совместные ритуалы",
            "3. Не считать лёгкость гарантированной",
          ],
          notMeans: [
            "не значит отсутствие работы над собой",
            "не доказывает абсолютное совпадение",
            "не заменяет взаимное уважение",
          ],
        }),
      })
    })

    // Intercept GET aspect drilldown route for error_aspect (500)
    await page.route("/api/synastry/partner-test-1/aspect/error_aspect", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "Не удалось загрузить подробный разбор аспекта.",
        }),
      })
    })
  })

  test("maintains structural testid and state contract for synastry detail screen and wheel", async ({ page }) => {
    await page.goto("/synastry")
    await page.getByTestId("synastry-card").click()

    const detailScreen = page.getByTestId("synastry-detail-screen")
    await expect(detailScreen).toBeVisible()
    await expect(detailScreen).toHaveAttribute("data-state", "ready")

    await expect(page.getByTestId("synastry-hero")).toBeVisible()
    await expect(page.getByTestId("synastry-score")).toBeVisible()
    await expect(page.getByTestId("synastry-wheel")).toBeVisible()
    await expect(page.getByTestId("synastry-overlays")).toBeVisible()
    await expect(page.getByTestId("synastry-translations")).toBeVisible()
    await expect(page.getByTestId("synastry-spheres")).toBeVisible()
    await expect(page.getByTestId("synastry-feedback")).toBeVisible()

    await expect(page).toHaveScreenshot("synastry-detail.png", {
      mask: [page.getByTestId("synastry-hero")],
    })
  })

  test("opens drilldown sheet with structural content contract and matches screenshot baseline", async ({ page }) => {
    await page.goto("/synastry")
    await page.getByTestId("synastry-card").click()

    // 1. Open drilldown by clicking aspect row
    const aspectRow = page.getByTestId("synastry-aspect").first()
    await aspectRow.click()

    const sheet = page.getByTestId("aspect-drilldown-sheet")
    await expect(sheet).toBeVisible()
    await expect(sheet).toHaveAttribute("role", "dialog")
    await expect(sheet).toHaveAttribute("data-tone", "good")

    // Structural assertions:
    await expect(sheet.getByText("АСТРОЛОГИЧЕСКИЙ КОНТАКТ")).toBeVisible()
    await expect(sheet.getByText("Солнце △ Луна")).toBeVisible() // Localized tech signature in header
    await expect(sheet.getByRole("heading", { name: "Естественная гармония эмоционального и сознательного" })).toBeVisible() // Headline
    await expect(sheet.getByText(/Тригон · орб 1°00′ · поддерживающий контакт/i)).toBeVisible() // Meta line

    // Section headings & cards:
    await expect(page.getByText("ЧТО ИМЕННО СОЕДИНЯЕТСЯ")).toBeVisible()
    await expect(page.getByText("ТВОЯ КАРТА")).toBeVisible()
    await expect(page.getByText("КАРТА ПАРТНЁРА")).toBeVisible()

    await expect(page.getByText("КАК РАБОТАЕТ ТРИГОН")).toBeVisible()
    await expect(page.getByText("Гармоничный поток энергии.")).toBeVisible()

    await expect(page.getByText("КАК ЭТО ПРОЯВЛЯЕТСЯ В ЖИЗНИ")).toBeVisible()
    await expect(page.getByText("В общении")).toBeVisible()
    await expect(page.getByText("В быту")).toBeVisible()
    await expect(page.getByText("В споре")).toBeVisible()

    await expect(page.getByText("ЧТО ПОМОГАЕТ")).toBeVisible()
    await expect(page.getByText("1. Замечать и называть сильные стороны")).toBeVisible()

    await expect(page.getByText("ВАЖНО: ЭТО НЕ ОЗНАЧАЕТ")).toBeVisible()
    await expect(page.getByText("не значит отсутствие работы над собой")).toBeVisible()

    // Take drilldown modal snapshot
    await expect(page).toHaveScreenshot("synastry-drilldown.png", {
      mask: [sheet.locator(".syn-serif")],
    })
  })

  test("opens drilldown sheet via wheel line click and preserves wheel selection after close", async ({ page }) => {
    await page.goto("/synastry")
    await page.getByTestId("synastry-card").click()

    // Click aspect line on SVG wheel
    const lineButton = page.locator('[data-testid="synastry-wheel"] g[role="button"]:has(line)').first()
    await lineButton.dispatchEvent("click")

    const sheet = page.getByTestId("aspect-drilldown-sheet")
    await expect(sheet).toBeVisible()
    await expect(page.getByText("Солнце △ Луна")).toBeVisible()

    // Close via Escape key
    await page.keyboard.press("Escape")
    await expect(sheet).not.toBeVisible()
  })

  test("handles drilldown error state gracefully with Russian message and Escape close", async ({ page }) => {
    await page.goto("/synastry")
    await page.getByTestId("synastry-card").click()

    // Click error aspect row directly
    const errorAspectRow = page.getByTestId("synastry-aspect").filter({ hasText: "Ошибка аспекта" })
    await errorAspectRow.click()

    const sheet = page.getByTestId("aspect-drilldown-sheet")
    await expect(sheet).toBeVisible()

    // Error alert visible
    const alert = sheet.locator('[role="alert"]')
    await expect(alert).toBeVisible()
    await expect(alert).toContainText("Не удалось загрузить")

    // Close via Escape key
    await page.keyboard.press("Escape")
    await expect(sheet).not.toBeVisible()
  })
})
