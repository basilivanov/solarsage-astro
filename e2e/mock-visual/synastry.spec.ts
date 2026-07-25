import { test, expect } from "@playwright/test"

test.describe("Synastry mock visual contract", () => {
  test("maintains structural testid and state contract for synastry list screen", async ({ page }) => {
    // Intercept API routes
    await page.route("/api/synastry", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          partners: [
            {
              id: "partner-test-1",
              name: "Максим",
              relationType: "romantic",
              birthDate: "1987-09-09",
              precision: "exact",
              score: 89,
              status: "good",
              summary: "Отличная совместимость натальных карт.",
              createdAt: "2026-07-25T12:00:00Z",
            },
          ],
        }),
      })
    })

    await page.goto("/synastry")
    const screenRoot = page.getByTestId("synastry-screen")
    await expect(screenRoot).toBeVisible()
    await expect(screenRoot).toHaveAttribute("data-state", "ready")

    const partnerCard = page.getByTestId("synastry-card")
    await expect(partnerCard).toBeVisible()
    await expect(partnerCard).toHaveAttribute("data-status", "good")
  })
})
