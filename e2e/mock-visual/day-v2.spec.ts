import { expect, test } from "@playwright/test"
import { expectNoMissingApiFixtures, installMockApiRoutes, type MockApiRouteFixtures } from "./route-interception"
import { dayPayloadV2 } from "./fixtures/day-v2-2026-07-08"
import { calendarPayload } from "./fixtures/calendar-2026-07"
import { referralPayload, profilePayload } from "./fixtures/profile"

const WEEK_STRIP_MIN_DATES = [
  "2026-07-05",
  "2026-07-06",
  "2026-07-07",
  "2026-07-08",
  "2026-07-09",
  "2026-07-10",
  "2026-07-11",
]

function buildReadyFixtures(): MockApiRouteFixtures {
  const fixtures: MockApiRouteFixtures = {
    "/api/day/2026-07-08": { body: dayPayloadV2 },
    "/api/auth/dev": {
      status: 200,
      body: { status: "ok", userId: "mock-user-id" },
    },
    "/api/calendar": {
      body: calendarPayload,
    },
    "/api/referral": {
      body: referralPayload,
    },
    "/api/profile": {
      body: profilePayload,
    },
  }

  for (const dateStr of WEEK_STRIP_MIN_DATES) {
    if (fixtures[`/api/day/${dateStr}`]) continue
    fixtures[`/api/day/${dateStr}`] = {
      body: { dayStatus: "steady" },
    }
  }

  return fixtures
}

test.describe("W6 V2 Day Screen mock visual", () => {
  test("renders V2 blocks: activation card, technique chips, why-today, concrete advice expanded evidence, and audit console", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildReadyFixtures())

    // 1. Visit day page without audit console query param
    await page.goto("/day/2026-07-08")
    await page.waitForLoadState("networkidle")

    // Assert screen state
    const screen = page.getByTestId("today-screen")
    await expect(screen).toHaveAttribute("data-state", "ready")

    // Assert Activation Evidence Card is visible
    const actCard = page.getByTestId("activation-evidence-card")
    await expect(actCard).toBeVisible()
    await expect(actCard).toContainText("Сегодня сходятся 3 независимые техники")

    // Assert Technique Chips render
    const chips = page.getByTestId("technique-chip")
    await expect(chips.first()).toBeVisible()
    await expect(chips.first()).toContainText("Транзит")

    // Assert Why-Today renders
    await page.getByRole("button", { name: "Почему именно сегодня" }).click()
    const whyToday = page.getByTestId("why-today")
    await expect(whyToday).toBeVisible()
    await expect(whyToday).toContainText("Профекция года активирует 3 дом")

    // Assert Concrete Advice Row is present
    const row = page.getByTestId("concrete-day-advice-row").first()
    await expect(row).toBeVisible()
    await expect(row).toContainText("Работа")

    // Click row to expand evidence
    await row.click()
    const evidence = page.getByTestId("concrete-day-advice-evidence")
    await expect(evidence).toBeVisible()
    await expect(evidence).toContainText("Transit Mars trine natal Saturn")

    // Dev Audit Drawer should be hidden by default
    const auditDrawer = page.getByTestId("dev-audit-drawer")
    await expect(auditDrawer).toBeHidden()

    // 2. Visit with audit=1 to see the audit console
    await page.goto("/day/2026-07-08?audit=1")
    await page.waitForLoadState("networkidle")

    const auditDrawerVisible = page.getByTestId("dev-audit-drawer")
    await expect(auditDrawerVisible).toBeVisible()
    await expect(auditDrawerVisible).toContainText("Dev Audit Console")
    await expect(auditDrawerVisible).toContainText("today.v2")

    // Verify no missing API fixtures
    await expectNoMissingApiFixtures(page, tracker)
  })
})
