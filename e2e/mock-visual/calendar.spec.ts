// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_CALENDAR_SPEC
// ROLE: Mock visual e2e spec for /calendar route. Uses Playwright route
//       interception with contract-valid fixtures. No MSW, no runtime mocks.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-CALENDAR-SPEC
// purpose: Verify the /calendar screen matches the visual/structural contract
//          on stable API payloads. Exercise ready state, day/moon modes, and
//          overflow. Asserts no missing fixtures via MissingRequestsTracker.
//          Moon-mode assertions freeze browser time to 2026-07-05 via
//          page.clock.install() so assertions are deterministic regardless of machine date.
// owns:
//   - e2e/mock-visual/calendar.spec.ts
// inputs: Playwright test runner, E2E_BASE_URL env
// outputs: Test pass/fail with assertions on DOM contract and visual structure
// dependencies:
//   - @playwright/test
//   - ./route-interception (installMockApiRoutes, MissingRequestsTracker, expectNoMissingApiFixtures)
//   - ./fixtures/calendar-2026-07 (calendarPayload, accessPayload)
// side_effects: None (all API calls intercepted)
// invariants:
//   - No product path imports mocks or demo data
//   - Fixtures represent valid API response shapes
//   - All API calls have fixture coverage (fails on missing)
//   - Moon-mode assertions freeze browser time to 2026-07-05 via page.clock.install()
// failure_policy: Tests fail on missing fixture or assertion failure
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-CALENDAR-SPEC

import { expect, test } from "@playwright/test";
import { expectNoMissingApiFixtures, installMockApiRoutes, type MockApiRouteFixtures } from "./route-interception";
import { calendarPayload, accessPayload, dayPayload } from "./fixtures/calendar-2026-07";

function buildCalendarFixtures(): MockApiRouteFixtures {
  return {
    "/api/calendar": { body: calendarPayload },
    "/api/access": { body: accessPayload },
    "/api/day/2026-07-10": { body: dayPayload },
    "/api/auth/dev": {
      status: 200,
      body: { status: "ok", userId: "mock-user-id" },
    },
  };
}

test.describe("Mock Visual — /calendar", () => {
  test("calendar screen renders in ready state with month header, grid, lunar strip, and summary", async ({ page }) => {
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

    // Month header is visible and localized by the frontend from payload.month
    await expect(page.getByTestId("calendar-month-header")).toBeVisible();
    await expect(page.getByTestId("calendar-month-header")).toHaveText("Июль 2026");

    // Grid is visible
    await expect(page.getByTestId("calendar-grid")).toBeVisible();

    // Bottom selected summary is visible
    await expect(page.getByTestId("calendar-selected-summary")).toBeVisible();

    // Positive fixture contains lunar data — assert exact strip, not unavailable fallback
    await expect(page.getByTestId("lunar-calendar-strip")).toBeVisible();
    await expect(page.getByTestId("lunar-calendar-unavailable")).toBeHidden();

    // Segmented controls are present
    await expect(page.getByTestId("calendar-view-day")).toBeVisible();
    await expect(page.getByTestId("calendar-view-moon")).toBeVisible();

    // No missing API fixtures after quiet wait
    await expectNoMissingApiFixtures(page, tracker);
  });

  test("day tap selects locally and footer CTA is the only navigation path", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildCalendarFixtures());

    await page.clock.install({ time: new Date("2026-07-05T12:00:00Z") });
    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/calendar");
    await page.waitForLoadState("networkidle");

    await page.getByTestId("calendar-day-2026-07-10").click();
    await expect(page).toHaveURL(/\/calendar$/);
    await expect(page.getByTestId("calendar-selected-summary")).toContainText("10 июля 2026");

    const cta = page.getByRole("button", { name: /Открыть день/i });
    await expect(cta).toBeEnabled();
    await cta.scrollIntoViewIfNeeded();
    await Promise.all([
      page.waitForURL(/\/day\/2026-07-10/, { timeout: 10000 }),
      cta.click(),
    ]);

    await expectNoMissingApiFixtures(page, tracker);
  });

  test("moon mode displays backend lunar values deterministically", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildCalendarFixtures());

    // Freeze time to 2026-07-05 so CalendarScreen selects that day initially
    // and clicking a day does not navigate away (the day won't be TODAY in frozen time)
    await page.clock.install({ time: new Date("2026-07-05T12:00:00Z") });

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/calendar");
    await page.waitForLoadState("networkidle");

    // Switch to moon mode first (no navigation since we haven't clicked any day button)
    await page.getByTestId("calendar-view-moon").click();
    await page.waitForTimeout(300);

    // Grid is still visible in moon mode
    await expect(page.getByTestId("calendar-grid")).toBeVisible();

    // The selected day (2026-07-05 in frozen time) moon cell shows backend lunar day number
    const moonDay = page.getByTestId("calendar-moon-day-2026-07-05");
    await expect(moonDay).toBeVisible();
    await expect(moonDay).toContainText("20");

    // Selected summary shows deterministic lunar values for 2026-07-05
    const summary = page.getByTestId("calendar-selected-summary");
    await expect(summary).toContainText("убыв. Луна");
    await expect(summary).toContainText("63%");
    await expect(summary).toContainText("20 лунный день");
    await expect(page.getByTestId("calendar-moon-glyph-2026-07-05")).toContainText("🌖");

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
    // The tracker should have recorded the missing /api/calendar request
    await expect.poll(() => tracker.count, { timeout: 10000 }).toBeGreaterThan(0);

    const missingPaths = tracker.all;
    expect(missingPaths.some((p) => p.startsWith("/api/calendar"))).toBe(true);
  });
});
