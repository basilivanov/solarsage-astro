// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_PROFILE_SPEC
// ROLE: Mock visual e2e spec for /profile route. Uses Playwright route
//       interception with contract-valid fixtures. No MSW, no runtime mocks.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-PROFILE-SPEC
// purpose: Verify the /profile screen matches the visual/structural contract
//          on stable API payloads. Exercise ready state, edit-sheet, overflow,
//          and negative-proof scenarios.
// owns:
//   - e2e/mock-visual/profile.spec.ts
// inputs: Playwright test runner, E2E_BASE_URL env
// outputs: Test pass/fail with assertions on DOM contract and visual structure
// dependencies:
//   - @playwright/test
//   - ./route-interception (installMockApiRoutes, expectNoMissingApiFixtures)
//   - ./fixtures/profile (profilePayload, accessPayload, etc.)
// side_effects: None (all API calls intercepted)
// invariants:
//   - No product path imports mocks or demo data
//   - Fixtures represent valid API response shapes
//   - All API calls have fixture coverage (fails on missing)
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-PROFILE-SPEC

// START_MODULE_MAP: M-E2E-MOCK-VISUAL-PROFILE-SPEC
// public_entrypoints: (none — test file)
// semantic_blocks:
//   - READY_STATE: ready-state test with all sections
//   - EDIT_SHEET: edit-sheet visibility
//   - OVERFLOW: no horizontal overflow
//   - NEGATIVE_PROOF: missing fixture tracking
// END_MODULE_MAP: M-E2E-MOCK-VISUAL-PROFILE-SPEC

import { expect, test } from "@playwright/test";
import { expectNoMissingApiFixtures, installMockApiRoutes, type MockApiRouteFixtures } from "./route-interception";
import {
  profilePayload,
  accessPayload,
  horaryQuotaPayload,
  referralPayload,
  checkinMetricsPayload,
} from "./fixtures/profile";
import { prepareForScreenshot } from "./screenshot";

function buildProfileFixtures(): MockApiRouteFixtures {
  return {
    "/api/auth/dev": { status: 200, body: { status: "ok", userId: "mock-user-id" } },
    "/api/profile": { body: profilePayload },
    "/api/access": { body: accessPayload },
    "/api/horary/quota": { body: horaryQuotaPayload },
    "/api/referral": { body: referralPayload },
    "/api/checkin/metrics": { body: checkinMetricsPayload },
  };
}

test.describe("Mock Visual — /profile", () => {
  test("profile screen renders in ready state with all major sections", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildProfileFixtures());

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/profile");
    await page.waitForLoadState("networkidle");

    // Root screen visible with ready state and access state
    const screen = page.getByTestId("profile-screen");
    await expect(screen).toBeVisible({ timeout: 10000 });
    await expect(screen).toHaveAttribute("data-state", "ready");
    await expect(screen).toHaveAttribute("data-access-state", "trial");

    // Header visible
    await expect(page.getByTestId("profile-header")).toBeVisible();

    // Access card visible
    await expect(page.getByTestId("profile-access-card")).toBeVisible();

    // Referral card visible with fixture-backed reward days (14)
    await expect(page.getByTestId("profile-referral-card")).toBeVisible();
    await expect(page.getByTestId("profile-referral-card")).toContainText("14 дней доступа");

    // Horary card visible
    await expect(page.getByTestId("profile-horary-card")).toBeVisible();

    // Checkin statistics visible
    await expect(page.getByTestId("profile-checkin-statistics")).toBeVisible();

    // Data section visible with rows
    await expect(page.getByTestId("profile-data-section")).toBeVisible();
    await expect(page.getByTestId("profile-data-row-birth-date")).toBeVisible();
    await expect(page.getByTestId("profile-data-row-birth-place")).toBeVisible();

    // Service section visible
    await expect(page.getByTestId("profile-service-section")).toBeVisible();

    // Deterministic visual baseline (fail-closed; UPDATE_SNAPSHOTS=true to refresh)
    await prepareForScreenshot(page);
    await expect(page).toHaveScreenshot("profile-ready.png");

    // No missing API fixtures after quiet wait
    await expectNoMissingApiFixtures(page, tracker);
  });

  test("edit sheet opens when clicking a profile data row after hydration", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildProfileFixtures());

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/profile");
    await page.waitForLoadState("networkidle");

    // Click a data row to open edit sheet
    await page.getByTestId("profile-data-row-birth-date").click();

    // Edit sheet dialog is visible
    await expect(page.getByTestId("profile-edit-sheet")).toBeVisible();
    await expect(page.getByTestId("profile-edit-sheet")).toHaveAttribute("role", "dialog");

    // No missing API fixtures after quiet wait
    await expectNoMissingApiFixtures(page, tracker);
  });

  test("profile screen has no horizontal overflow on mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });

    const tracker = await installMockApiRoutes(page, buildProfileFixtures());

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
      const style = document.createElement("style");
      style.textContent = "* { animation: none !important; transition: none !important; }";
      document.documentElement.appendChild(style);
    });

    await page.goto("/profile");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    const overflowWidth = await page.evaluate(() => {
      return document.documentElement.scrollWidth - document.documentElement.clientWidth;
    });
    expect(overflowWidth).toBeLessThanOrEqual(5);

    await expectNoMissingApiFixtures(page, tracker);
  });

  test("missing API fixture is recorded by the tracker (negative proof)", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, {
      "/api/auth/dev": { status: 200, body: { status: "ok", userId: "mock-user-id" } },
      "/api/access": { body: accessPayload },
    });

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/profile");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    expect(tracker.count).toBeGreaterThan(0);
    const missingPaths = tracker.all;
    expect(missingPaths.some((p) => p.startsWith("/api/profile"))).toBe(true);
  });
});
