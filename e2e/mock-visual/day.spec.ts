// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_DAY_SPEC
// ROLE: Mock visual e2e spec for /day/[date] route. Uses Playwright route
//       interception with contract-valid fixtures. No MSW, no runtime mocks.
//       All API calls must have fixture coverage — the missing-request tracker
//       asserts no unmocked requests after a quiet period.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-DAY-SPEC
// purpose: Verify the /day/[date] screen matches the visual/structural contract
//          on stable API payloads. Exercise ready, locked, and overflow states.
//          Asserts no missing fixtures via expectNoMissingApiFixtures after a quiet
//          wait so late React effects have time to fire.
// owns:
//   - e2e/mock-visual/day.spec.ts
// inputs: Playwright test runner, E2E_BASE_URL env
// outputs: Test pass/fail with assertions on DOM contract and visual structure
// dependencies:
//   - @playwright/test
//   - ./route-interception (installMockApiRoutes, expectNoMissingApiFixtures, MissingRequestsTracker)
//   - ./fixtures/day-2026-07-05 (dayPayload, dayPayloadLocked)
//   - ./fixtures/calendar-2026-07 (calendarPayload)
// side_effects: None (all API calls intercepted)
// invariants:
//   - No product path imports mocks or demo data
//   - Fixtures represent valid TodayPayload shapes
//   - All API calls have fixture coverage (fails on missing)
//   - Missing-fixture assertion runs after a quiet wait for late effects
// failure_policy: Tests fail on missing fixture or assertion failure
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-DAY-SPEC

import { expect, test } from "@playwright/test";
import { expectNoMissingApiFixtures, installMockApiRoutes, type MockApiRouteFixtures } from "./route-interception";
import { dayPayload, dayPayloadLocked, referralPayload } from "./fixtures/day-2026-07-05";
import { calendarPayload } from "./fixtures/calendar-2026-07";

/**
 * Week strip days that could be requested around 2026-07-05.
 * The `startOfWeek` calculation depends on local timezone, so we cover
 * a ±1 day buffer: June 28 (earliest possible Mon) through July 5.
 * July 5 is excluded from minimal fixtures — it has the full payload.
 *
 * Actual week strip days produced in the review run:
 *   2026-06-28 (Sun) through 2026-07-04 (Sat)  or
 *   2026-06-29 (Mon) through 2026-07-05 (Sun)
 */
const WEEK_STRIP_MIN_DATES = [
  "2026-06-28",
  "2026-06-29",
  "2026-06-30",
  "2026-07-01",
  "2026-07-02",
  "2026-07-03",
  "2026-07-04",
];

// ############################################################################
// Helpers
// ############################################################################

/**
 * Build the common fixture map for all tests.
 * The full `/api/day/2026-07-05` payload is set first and must NOT be
 * overwritten by minimal week-strip fixtures.
 */
function buildFixtureBase(): MockApiRouteFixtures {
  return {
    // Main day payload — full TodayPayload (NEVER overwritten)
    "/api/day/2026-07-05": { body: dayPayload },
    // Dev auth
    "/api/auth/dev": {
      status: 200,
      body: { status: "ok", userId: "mock-user-id" },
    },
    // Calendar month (for lunar data)
    "/api/calendar": {
      body: calendarPayload,
    },
    // Referral (used by useShareInvite / Paywall)
    "/api/referral": {
      body: referralPayload,
    },
  };
}

/**
 * Add minimal day-status fixtures for all potential week-strip dates.
 * Crucially skips 2026-07-05 so the full payload fixture survives.
 */
function addWeekStripFixtures(fixtures: MockApiRouteFixtures): void {
  for (const dateStr of WEEK_STRIP_MIN_DATES) {
    if (fixtures[`/api/day/${dateStr}`]) continue; // don't overwrite
    const day = dayPayload.weekStrip.find((w) => w.date === dateStr);
    fixtures[`/api/day/${dateStr}`] = {
      body: { dayStatus: day?.dayStatus ?? "steady" },
    };
  }
}

function buildReadyFixtures(): MockApiRouteFixtures {
  const fixtures = buildFixtureBase();
  addWeekStripFixtures(fixtures);
  return fixtures;
}

function buildLockedFixtures(): MockApiRouteFixtures {
  const fixtures: MockApiRouteFixtures = {
    "/api/day/2026-07-05": { body: dayPayloadLocked },
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
  };
  addWeekStripFixtures(fixtures);
  return fixtures;
}

async function sectionOrder(page: import("@playwright/test").Page): Promise<string[]> {
  return page.getByTestId("today-screen").evaluate((screen) => {
    const wanted = new Set([
      "day-header",
      "access-card",
      "evening-checkin-reminder",
      "day-summary-card",
      "concrete-day-advice",
      "day-chart",
      "day-chart-unavailable",
      "day-reading",
      "why-expanded",
      "week-strip",
      "astro-history-widget",
      "today-bottom-disclaimer",
    ]);
    return Array.from(screen.querySelectorAll("[data-testid]"))
      .map((node) => node.getAttribute("data-testid"))
      .filter((id): id is string => Boolean(id && wanted.has(id)));
  });
}

async function internalScrollMetrics(page: import("@playwright/test").Page) {
  return page.getByTestId("today-screen").evaluate((screen) => {
    const scroller = screen.parentElement;
    if (!scroller) return { scrollHeight: 0, clientHeight: 0, maxScroll: 0 };
    return {
      scrollHeight: scroller.scrollHeight,
      clientHeight: scroller.clientHeight,
      maxScroll: scroller.scrollHeight - scroller.clientHeight,
    };
  });
}

async function scrollInternalTo(page: import("@playwright/test").Page, top: number): Promise<void> {
  await page.getByTestId("today-screen").evaluate((screen, nextTop) => {
    const scroller = screen.parentElement;
    if (scroller) scroller.scrollTop = nextTop;
  }, top);
  await page.waitForTimeout(250);
}

// ############################################################################
// Tests
// ############################################################################

test.describe("Mock Visual — /day/[date]", () => {
  test("day screen renders in ready state with all major sections and no missing API fixtures", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildReadyFixtures());

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/day/2026-07-05");
    await page.waitForLoadState("networkidle");

    // Root screen is visible with correct data-state
    const screen = page.getByTestId("today-screen");
    await expect(screen).toBeVisible({ timeout: 10000 });
    await expect(screen).toHaveAttribute("data-state", "ready");

    // Major sections are present
    await expect(page.getByTestId("day-header")).toBeVisible();
    await expect(page.getByTestId("access-card")).toBeVisible();
    await expect(page.getByTestId("evening-checkin-reminder")).toHaveCount(0);
    await expect(page.getByTestId("day-summary-card")).toBeVisible();
    await expect(page.getByTestId("concrete-day-advice")).toBeVisible();
    await expect(page.getByTestId("day-chart-unavailable")).toBeVisible();
    await expect(page.getByTestId("day-reading")).toBeVisible();
    await expect(page.getByTestId("why-expanded")).toBeVisible();

    // Week strip is visible
    await expect(page.getByTestId("week-strip")).toBeVisible();
    await expect(page.getByTestId("astro-history-widget")).toBeVisible();

    expect(await sectionOrder(page)).toEqual([
      "day-header",
      "access-card",
      "day-summary-card",
      "concrete-day-advice",
      "day-chart-unavailable",
      "day-reading",
      "why-expanded",
      "week-strip",
      "astro-history-widget",
      "today-bottom-disclaimer",
    ]);

    // Day summary card renders real lunar data
    await expect(page.getByTestId("day-summary-card")).toContainText("Поддерживающий");
    await expect(page.getByTestId("day-summary-card")).toContainText("Убывающая Луна");

    // Concrete advice renders sphere labels via getSphereLabel, not raw keys
    const concreteAdvice = page.getByTestId("concrete-day-advice");
    await expect(concreteAdvice).toContainText("Мышление, речь, обучение");
    await expect(concreteAdvice).toContainText("Деньги, безопасность, ресурсы");
    await expect(concreteAdvice.getByRole("button", { name: /все 12 сфер/i })).toHaveAttribute("aria-expanded", "false");

    // Tab bar navigation is present
    const tabBar = page.locator('nav[aria-label="Основная навигация"]');
    await expect(tabBar).toBeVisible();

    // Assert no missing API fixtures — after a quiet wait for late effects
    await expectNoMissingApiFixtures(page, tracker);

    const metrics = await internalScrollMetrics(page);
    expect(metrics.maxScroll).toBeGreaterThan(100);

    const firstViewportBottom = metrics.clientHeight;
    const concreteTop = await page.getByTestId("concrete-day-advice").evaluate((node) => node.getBoundingClientRect().top);
    expect(concreteTop).toBeGreaterThan(firstViewportBottom * 0.45);

    await scrollInternalTo(page, Math.floor(metrics.maxScroll * 0.48));
    await expect(page.getByTestId("concrete-day-advice")).toBeVisible();
    await expect(page.getByTestId("day-chart-unavailable")).toBeVisible();

    await scrollInternalTo(page, metrics.maxScroll);
    await expect(page.getByTestId("day-reading")).toBeVisible();
    await expect(page.getByTestId("why-expanded")).toBeVisible();
    await expect(page.getByTestId("week-strip")).toBeVisible();
    await expect(page.getByTestId("astro-history-widget")).toBeVisible();
    await expect(page.getByTestId("today-bottom-disclaimer")).toBeVisible();
  });

  test("day screen renders in locked state for inaccessible dates and no missing API fixtures", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildLockedFixtures());

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/day/2026-07-05");
    await page.waitForLoadState("networkidle");

    // Root screen has locked state
    const screen = page.getByTestId("today-screen");
    await expect(screen).toBeVisible({ timeout: 10000 });
    await expect(screen).toHaveAttribute("data-state", "locked");

    // Access (paywall) card is visible
    await expect(page.getByTestId("access-card")).toBeVisible();

    // Only preview content in locked state
    await expect(page.getByTestId("day-reading")).toBeVisible();

    // Assert no missing API fixtures — after a quiet wait for late effects
    await expectNoMissingApiFixtures(page, tracker);
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

    // Check for horizontal overflow
    const overflowWidth = await page.evaluate(() => {
      return document.documentElement.scrollWidth - document.documentElement.clientWidth;
    });
    expect(overflowWidth).toBeLessThanOrEqual(5);

    // Assert no missing API fixtures — after a quiet wait for late effects
    await expectNoMissingApiFixtures(page, tracker);
  });

  // ########################################################################
  // Negative proof: an unmocked API request is recorded by the tracker
  // ########################################################################
  test("missing API fixture is recorded by the tracker (negative proof)", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, {
      "/api/auth/dev": {
        status: 200,
        body: { status: "ok", userId: "mock-user-id" },
      },
      "/api/day/2026-07-05": { body: dayPayload },
      "/api/referral": { body: referralPayload },
      "/api/calendar": { body: calendarPayload },
    });

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/day/2026-07-05");
    await page.waitForLoadState("networkidle");
    // Wait for late effects (week strip, referral, etc.)
    await page.waitForTimeout(1500);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    // This test deliberately has NO week-strip fixtures.
    // The tracker should have recorded missing paths.
    expect(tracker.count).toBeGreaterThan(0);

    // Verify at least one expected path is in the missing list
    const missingPaths = tracker.all;
    expect(missingPaths.some((p) => p.startsWith("/api/day/2026-06-"))).toBe(true);
  });
});
