// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_CALENDAR_SPEC
// ROLE: Mock visual e2e spec for /calendar route. Uses Playwright route
//       interception with contract-valid fixtures. No MSW, no runtime mocks.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-CALENDAR-SPEC
// purpose: Verify the /calendar screen matches the visual/structural contract
//          on stable API payloads. Exercise ready state, day/moon modes, and
//          overflow. Asserts no missing fixtures via MissingRequestsTracker.
// owns:
//   - e2e/mock-visual/calendar.spec.ts
// inputs: Playwright test runner, E2E_BASE_URL env
// outputs: Test pass/fail with assertions on DOM contract and visual structure
// dependencies:
//   - @playwright/test
//   - ./route-interception (installMockApiRoutes, MissingRequestsTracker)
//   - ./fixtures/calendar-2026-07 (calendarPayload, accessPayload)
// side_effects: None (all API calls intercepted)
// invariants:
//   - No product path imports mocks or demo data
//   - Fixtures represent valid API response shapes
//   - All API calls have fixture coverage (fails on missing)
// failure_policy: Tests fail on missing fixture or assertion failure
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-CALENDAR-SPEC

import { expect, test } from "@playwright/test";
import { installMockApiRoutes, type MockApiRouteFixtures } from "./route-interception";
import { calendarPayload, accessPayload } from "./fixtures/calendar-2026-07";
import { expectNoMissingApiFixtures } from "./route-interception";

function buildCalendarFixtures(): MockApiRouteFixtures {
  return {
    "/api/calendar": { body: calendarPayload },
    "/api/access": { body: accessPayload },
    "/api/auth/dev": {
      status: 200,
      body: { status: "ok", userId: "mock-user-id" },
    },
  };
}

test.describe("Mock Visual — /calendar", () => {
  test("calendar screen renders in ready state with all major sections", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildCalendarFixtures());

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/calendar");
    await page.waitForLoadState("networkidle");

    // Root screen is visible with ready load state
    const screen = page.getByTestId("calendar-screen");
    await expect(screen).toBeVisible({ timeout: 10000 });
    await expect(screen).toHaveAttribute("data-load-state", "ready");

    // Header and grid are visible
    await expect(page.getByTestId("calendar-grid")).toBeVisible();

    // Bottom selected summary is visible
    await expect(page.getByTestId("calendar-selected-summary")).toBeVisible();

    // Lunar strip or unavailable state is visible
    const lunarStrip = page.locator('[data-testid="lunar-calendar-strip"], [data-testid="lunar-calendar-unavailable"]');
    await expect(lunarStrip).toBeVisible();

    // No missing API fixtures after quiet wait
    await expectNoMissingApiFixtures(page, tracker);
  });

  test("moon mode displays backend lunar values", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildCalendarFixtures());

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/calendar");
    await page.waitForLoadState("networkidle");

    // Switch to moon mode
    await page.getByRole("button", { name: "Луна" }).click();
    await page.waitForTimeout(300);

    // Grid is still visible in moon mode
    await expect(page.getByTestId("calendar-grid")).toBeVisible();

    // A day with known lunar data should show lunar day number
    // 2026-07-05 has lunarDay=20, 63%, Убывающая Луна
    const moonDay = page.getByTestId("calendar-moon-day-2026-07-05");
    await expect(moonDay).toBeVisible();
    await expect(moonDay).toContainText("20");

    // Selected summary shows lunar info in moon mode
    await expect(page.getByTestId("calendar-selected-summary")).toContainText("Убывающая Луна");
    await expect(page.getByTestId("calendar-selected-summary")).toContainText("63%");

    // No missing API fixtures after quiet wait
    await expectNoMissingApiFixtures(page, tracker);
  });

  test("calendar screen has no horizontal overflow on mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });

    const tracker = await installMockApiRoutes(page, buildCalendarFixtures());

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
      const style = document.createElement("style");
      style.textContent = "* { animation: none !important; transition: none !important; }";
      document.documentElement.appendChild(style);
    });

    await page.goto("/calendar");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    // Check for horizontal overflow
    const overflowWidth = await page.evaluate(() => {
      return document.documentElement.scrollWidth - document.documentElement.clientWidth;
    });
    expect(overflowWidth).toBeLessThanOrEqual(5);

    // No missing API fixtures after quiet wait
    await expectNoMissingApiFixtures(page, tracker);
  });

  // ########################################################################
  // Negative proof: missing calendar API fixtures are recorded by tracker
  // ########################################################################
  test("missing API fixture is recorded by the tracker (negative proof)", async ({ page }) => {
    // Deliberately omit /api/calendar fixture
    const tracker = await installMockApiRoutes(page, {
      "/api/auth/dev": {
        status: 200,
        body: { status: "ok", userId: "mock-user-id" },
      },
      "/api/access": { body: accessPayload },
    });

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/calendar");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    // The tracker should have recorded the missing /api/calendar request
    expect(tracker.count).toBeGreaterThan(0);

    const missingPaths = tracker.all;
    expect(missingPaths.some((p) => p.startsWith("/api/calendar"))).toBe(true);
  });
});
