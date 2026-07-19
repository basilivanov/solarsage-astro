// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_READINGS_SPEC
// ROLE: Mock visual e2e spec for /readings route. Uses Playwright route
//       interception with contract-valid fixtures. No MSW, no runtime mocks.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-READINGS-SPEC
// purpose: Verify the /readings overview screen matches the visual/structural
//          contract on stable API payloads. Exercise ready state, navigation
//          targets, coming card overlay, overflow, and negative-proof scenarios.
// owns:
//   - e2e/mock-visual/readings.spec.ts
// inputs: Playwright test runner, E2E_BASE_URL env
// outputs: Test pass/fail with assertions on DOM contract and visual structure
// dependencies:
//   - @playwright/test
//   - ./route-interception (installMockApiRoutes, expectNoMissingApiFixtures)
// side_effects: None (all API calls intercepted)
// invariants:
//   - No product path imports mocks or demo data
//   - All API calls have fixture coverage (fails on missing)
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-READINGS-SPEC

// START_MODULE_MAP: M-E2E-MOCK-VISUAL-READINGS-SPEC
// public_entrypoints: (none — test file)
// semantic_blocks:
//   - READY_STATE: ready-state test with all sections and navigation targets
//   - COMING_OVERLAY: coming card opens in-dev-overlay
//   - OVERFLOW: no horizontal overflow
//   - NEGATIVE_PROOF: missing fixture tracking
// END_MODULE_MAP: M-E2E-MOCK-VISUAL-READINGS-SPEC

import { expect, test } from "@playwright/test";
import { expectNoMissingApiFixtures, installMockApiRoutes, type MockApiRouteFixtures } from "./route-interception";
import { prepareForScreenshot } from "./screenshot";

function buildFixtures(): MockApiRouteFixtures {
  return {
    "/api/auth/dev": { status: 200, body: { status: "ok", userId: "mock-user-id" } },
  };
}

test.describe("Mock Visual — /readings", () => {
  test("readings overview renders in ready state with all sections and navigation targets", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildFixtures());

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/readings");
    await page.waitForLoadState("networkidle");

    // Root screen visible with ready state
    const screen = page.getByTestId("readings-screen");
    await expect(screen).toBeVisible({ timeout: 10000 });
    await expect(screen).toHaveAttribute("data-state", "ready");

    // Header, info banner, available section visible
    await expect(page.getByTestId("readings-header")).toBeVisible();
    await expect(page.getByTestId("readings-info-banner")).toBeVisible();
    await expect(page.getByTestId("readings-available-section")).toBeVisible();
    await expect(page.getByTestId("readings-available-list")).toBeVisible();

    // Horary and natal cards visible with route targets
    const horary = page.getByTestId("readings-card-horary");
    await expect(horary).toBeVisible();
    await expect(horary).toHaveAttribute("data-href", "/readings/horary");

    const natal = page.getByTestId("readings-card-natal");
    await expect(natal).toBeVisible();
    await expect(natal).toHaveAttribute("data-href", "/readings/natal");

    // Coming section visible
    await expect(page.getByTestId("readings-coming-section")).toBeVisible();
    await expect(page.getByTestId("readings-coming-list")).toBeVisible();

    // Deterministic visual baseline (fail-closed; UPDATE_SNAPSHOTS=true to refresh)
    await prepareForScreenshot(page);
    await expect(page).toHaveScreenshot("readings-ready.png");

    // Tab bar navigation is present
    const tabBar = page.locator('nav[aria-label="Основная навигация"]');
    await expect(tabBar).toBeVisible();

    // No missing API fixtures after quiet wait
    await expectNoMissingApiFixtures(page, tracker);
  });

  test("coming card opens in-dev-overlay with role=dialog", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildFixtures());

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/readings");
    await page.waitForLoadState("networkidle");

    // Click first coming card by stable product key
    await page.getByTestId("readings-card-month").click();

    // In-dev overlay is visible with dialog role
    const overlay = page.getByTestId("readings-in-dev-overlay");
    await expect(overlay).toBeVisible();
    await expect(overlay).toHaveAttribute("role", "dialog");

    // Dismiss the overlay
    await page.getByRole("button", { name: "Понятно" }).click();
    await expect(overlay).not.toBeVisible();

    // No missing API fixtures after quiet wait
    await expectNoMissingApiFixtures(page, tracker);
  });

  test("readings screen has no horizontal overflow on mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });

    const tracker = await installMockApiRoutes(page, buildFixtures());

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
      const style = document.createElement("style");
      style.textContent = "* { animation: none !important; transition: none !important; }";
      document.documentElement.appendChild(style);
    });

    await page.goto("/readings");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    const overflowWidth = await page.evaluate(() => {
      return document.documentElement.scrollWidth - document.documentElement.clientWidth;
    });
    expect(overflowWidth).toBeLessThanOrEqual(5);

    await expectNoMissingApiFixtures(page, tracker);
  });

  test("missing API fixture is recorded by the tracker (negative proof)", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, {});

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/readings");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    expect(tracker.count).toBeGreaterThan(0);
    const missingPaths = tracker.all;
    expect(missingPaths.some((p) => p.startsWith("/api/auth/dev"))).toBe(true);
  });
});
