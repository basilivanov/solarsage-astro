// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_DAY_SPEC
// ROLE: Mock visual e2e spec for /day/[date] route. Uses Playwright route
//       interception with contract-valid fixtures. No MSW, no runtime mocks.
//       All API calls must have fixture coverage — the missing-request tracker
//       ensures any unmocked API call fails the test.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-DAY-SPEC
// purpose: Verify the /day/[date] screen matches the visual/structural contract
//          on stable API payloads. Exercise ready and locked states.
//          Asserts no missing fixtures via MissingRequestsTracker.
// owns:
//   - e2e/mock-visual/day.spec.ts
// inputs: Playwright test runner, E2E_BASE_URL env
// outputs: Test pass/fail with assertions on DOM contract and visual structure
// dependencies:
//   - @playwright/test
//   - ./route-interception (installMockApiRoutes, MissingRequestsTracker)
//   - ./fixtures/day-2026-07-05 (dayPayload, dayPayloadLocked)
//   - ./fixtures/calendar-2026-07 (calendarPayload)
// side_effects: None (all API calls intercepted)
// invariants:
//   - No product path imports mocks or demo data
//   - Fixtures represent valid TodayPayload shapes
//   - All API calls have fixture coverage (fails on missing)
// failure_policy: Tests fail on missing fixture or assertion failure
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-DAY-SPEC

import { expect, test } from "@playwright/test";
import { installMockApiRoutes, type MockApiRouteFixtures } from "./route-interception";
import { dayPayload, dayPayloadLocked } from "./fixtures/day-2026-07-05";
import { calendarPayload } from "./fixtures/calendar-2026-07";

// Week strip days around 2026-07-05 (Mon 2026-06-29 to Sun 2026-07-05)
const WEEK_STRIP_DATES = [
  "2026-06-29",
  "2026-06-30",
  "2026-07-01",
  "2026-07-02",
  "2026-07-03",
  "2026-07-04",
  "2026-07-05",
];

/**
 * Build the fixture map for all API calls made by the /day/2026-07-05 page.
 * Includes: main day payload, dev auth, calendar, week strip day statuses.
 */
function buildReadyFixtures(): MockApiRouteFixtures {
  const fixtures: MockApiRouteFixtures = {
    "/api/day/2026-07-05": { body: dayPayload },
    "/api/auth/dev": {
      status: 200,
      body: { status: "ok", userId: "mock-user-id" },
    },
    "/api/calendar": {
      body: calendarPayload,
    },
  };

  // Add week strip day status fixtures (minimal — only dayStatus needed)
  for (const dateStr of WEEK_STRIP_DATES) {
    const day = dayPayload.weekStrip.find((w) => w.date === dateStr);
    const status = day?.dayStatus ?? "steady";
    fixtures[`/api/day/${dateStr}`] = {
      body: { dayStatus: status },
    };
  }

  return fixtures;
}

function buildLockedFixtures(): MockApiRouteFixtures {
  return {
    "/api/day/2026-07-05": { body: dayPayloadLocked },
    "/api/auth/dev": {
      status: 200,
      body: { status: "ok", userId: "mock-user-id" },
    },
    "/api/calendar": {
      body: calendarPayload,
    },
  };
}

test.describe("Mock Visual — /day/[date]", () => {
  test("day screen renders in ready state with all major sections and no missing API fixtures", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildReadyFixtures());

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/day/2026-07-05");
    await page.waitForLoadState("networkidle");

    // Assert no missing API fixtures
    expect(tracker.count).toBe(0);

    // Root screen is visible with correct data-state
    const screen = page.getByTestId("today-screen");
    await expect(screen).toBeVisible({ timeout: 10000 });
    await expect(screen).toHaveAttribute("data-state", "ready");

    // Major sections are present
    await expect(page.getByTestId("day-header")).toBeVisible();
    await expect(page.getByTestId("day-overview-card")).toBeVisible();
    await expect(page.getByTestId("practical-list")).toBeVisible();
    await expect(page.getByTestId("today-reading")).toBeVisible();

    // Week strip is visible
    await expect(page.getByTestId("week-strip")).toBeVisible();

    // Day overview card has correct status and renders real lunar data
    await expect(page.getByTestId("day-overview-card")).toHaveAttribute("data-status", "supportive");
    await expect(page.getByTestId("day-overview-card")).toContainText("Убывающая Луна");
    await expect(page.getByTestId("day-overview-card")).toContainText("63%");

    // Practical list renders sphere labels, not raw keys
    const practicalList = page.getByTestId("practical-list");
    await expect(practicalList).toContainText("Дом и семья");
    await expect(practicalList).toContainText("Творчество и самовыражение");

    // Tab bar navigation is present
    const tabBar = page.locator('nav[aria-label="Основная навигация"]');
    await expect(tabBar).toBeVisible();
  });

  test("day screen renders in locked state for inaccessible dates and no missing API fixtures", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildLockedFixtures());

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/day/2026-07-05");
    await page.waitForLoadState("networkidle");

    // Assert no missing API fixtures
    expect(tracker.count).toBe(0);

    // Root screen has locked state
    const screen = page.getByTestId("today-screen");
    await expect(screen).toBeVisible({ timeout: 10000 });
    await expect(screen).toHaveAttribute("data-state", "locked");

    // Access (paywall) card is visible
    await expect(page.getByTestId("access-card")).toBeVisible();

    // Only preview content in locked state
    await expect(page.getByTestId("today-reading")).toBeVisible();
  });

  test("day screen has no horizontal overflow on mobile viewport and no missing API fixtures", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });

    const tracker = await installMockApiRoutes(page, buildReadyFixtures());

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
      const style = document.createElement("style");
      style.textContent = "* { animation: none !important; transition: none !important; }";
      document.documentElement.appendChild(style);
    });

    await page.goto("/day/2026-07-05");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    // Assert no missing API fixtures
    expect(tracker.count).toBe(0);

    // Check for horizontal overflow
    const overflowWidth = await page.evaluate(() => {
      return document.documentElement.scrollWidth - document.documentElement.clientWidth;
    });
    expect(overflowWidth).toBeLessThanOrEqual(5);
  });
});
