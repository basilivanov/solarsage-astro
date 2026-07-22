// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_HORARY_SPEC
// ROLE: Mock visual e2e spec for /readings/horary route.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-HORARY-SPEC
// purpose: Verify the /readings/horary screen matches the visual/structural
//          contract on stable API payloads.
// owns:
//   - e2e/mock-visual/horary.spec.ts
// dependencies:
//   - @playwright/test
//   - ./route-interception (installMockApiRoutes, expectNoMissingApiFixtures)
//   - ./fixtures/horary (horaryQuotaPayload, horaryQuestionsPayload, profilePayload)
// side_effects: None (all API calls intercepted)
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-HORARY-SPEC

import { expect, test } from "@playwright/test";
import { expectNoMissingApiFixtures, installMockApiRoutes, type MockApiRouteFixtures } from "./route-interception";
import { horaryQuotaPayload, horaryQuestionsPayload, profilePayload } from "./fixtures/horary";
import { prepareForScreenshot } from "./screenshot";

function buildFixtures(): MockApiRouteFixtures {
  return {
    "/api/auth/dev": { status: 200, body: { status: "ok", userId: "mock-user-id" } },
    "/api/horary/quota": { body: horaryQuotaPayload },
    "/api/horary/questions": { body: horaryQuestionsPayload },
    "/api/profile": { body: profilePayload },
  };
}

test.describe("Mock Visual — /readings/horary", () => {
  // Deterministic timezone for the quota expiry label: the fixture carries
  // weeklyFreeExpiresAt "2026-07-09T00:00:00Z" which renders as 03:00 only
  // in Europe/Moscow; CI runners default to UTC and shift the label by the
  // offset. Pin the browser timezone instead of changing fixture time or
  // masking the text.
  test.use({ timezoneId: "Europe/Moscow" });

  test("horary screen renders in ready state with all sections", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildFixtures());

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/readings/horary");
    await page.waitForLoadState("networkidle");

    // Root screen visible
    const screen = page.getByTestId("horary-screen");
    await expect(screen).toBeVisible({ timeout: 10000 });
    await expect(screen).toHaveAttribute("data-state", "ready");
    await expect(screen).toHaveAttribute("data-has-credit", "true");
    await expect(screen).toHaveAttribute("data-access-state", "unlocked");

    // Header and back link
    await expect(page.getByTestId("horary-header")).toBeVisible();
    await expect(page.getByTestId("horary-back-link")).toBeVisible();

    // Quota section and bar
    await expect(page.getByTestId("horary-quota-section")).toBeVisible();
    await expect(page.getByTestId("horary-quota-bar")).toBeVisible();

    // Form section and form
    await expect(page.getByTestId("horary-form-section")).toBeVisible();
    await expect(page.getByTestId("horary-form")).toBeVisible();

    // Question input
    await expect(page.getByTestId("horary-question-input")).toBeVisible();

    // Category chips
    await expect(page.getByTestId("horary-category-love")).toBeVisible();

    // Submit button
    await expect(page.getByTestId("horary-submit-btn")).toBeVisible();

    // History section with empty state
    await expect(page.getByTestId("horary-history-section")).toBeVisible();
    await expect(page.getByTestId("horary-empty-history")).toBeVisible();

    // Deterministic visual baseline including the empty-history state
    // (fail-closed; UPDATE_SNAPSHOTS=true to refresh)
    await prepareForScreenshot(page);
    await expect(page).toHaveScreenshot("horary-ready.png");

    // No missing API fixtures
    await expectNoMissingApiFixtures(page, tracker);
  });

  test("no-credit state renders horary-no-credit-card with product-safe copy", async ({ page }) => {
    const noCreditQuota = { ...horaryQuotaPayload, weeklyFreeAvailable: false, bonusCredits: 0, paidCredits: 0 };
    const tracker = await installMockApiRoutes(page, {
      "/api/auth/dev": { status: 200, body: { status: "ok", userId: "mock-user-id" } },
      "/api/horary/quota": { body: noCreditQuota },
      "/api/horary/questions": { body: horaryQuestionsPayload },
      "/api/profile": { body: profilePayload },
    });

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/readings/horary");
    await page.waitForLoadState("networkidle");

    await expect(page.getByTestId("horary-screen")).toHaveAttribute("data-has-credit", "false");
    await expect(page.getByTestId("horary-screen")).toHaveAttribute("data-access-state", "locked");
    await expect(page.getByTestId("horary-no-credit-card")).toBeVisible();
    await expect(page.getByTestId("horary-no-credit-card")).not.toContainText("докупите");

    // Deterministic locked/no-credit visual baseline (fail-closed)
    await prepareForScreenshot(page);
    await expect(page).toHaveScreenshot("horary-no-credit.png");

    await expectNoMissingApiFixtures(page, tracker);
  });

  test("horary screen has no horizontal overflow on mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const tracker = await installMockApiRoutes(page, buildFixtures());

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
      const style = document.createElement("style");
      style.textContent = "* { animation: none !important; transition: none !important; }";
      document.documentElement.appendChild(style);
    });

    await page.goto("/readings/horary");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    const overflowWidth = await page.evaluate(() =>
      document.documentElement.scrollWidth - document.documentElement.clientWidth
    );
    expect(overflowWidth).toBeLessThanOrEqual(5);

    await expectNoMissingApiFixtures(page, tracker);
  });

  test("missing API fixture is recorded by the tracker (negative proof)", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, {
      "/api/auth/dev": { status: 200, body: { status: "ok", userId: "mock-user-id" } },
    });

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/readings/horary");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    expect(tracker.count).toBeGreaterThan(0);
    expect(tracker.all.some((p) => p.startsWith("/api/horary/quota") || p.startsWith("/api/profile"))).toBe(true);
  });
});
