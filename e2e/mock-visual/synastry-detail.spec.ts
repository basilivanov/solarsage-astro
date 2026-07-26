import { test, expect } from "@playwright/test"

test.describe("Synastry detail mock visual contract", () => {
  test("maintains structural testid and state contract for synastry detail screen and wheel", async ({ page }) => {
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
})
