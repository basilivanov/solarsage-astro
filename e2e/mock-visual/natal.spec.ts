// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_NATAL_SPEC
// ROLE: Mock visual e2e spec for /readings/natal route.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-NATAL-SPEC
// purpose: Verify the /readings/natal screen matches the visual/structural
//          contract on stable API payloads.
// owns:
//   - e2e/mock-visual/natal.spec.ts
// dependencies:
//   - @playwright/test
//   - ./route-interception (installMockApiRoutes, expectNoMissingApiFixtures)
//   - ./fixtures/natal-preview (natalPreviewPayload)
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-NATAL-SPEC

import { expect, test } from "@playwright/test";
import { expectNoMissingApiFixtures, installMockApiRoutes, type MockApiRouteFixtures } from "./route-interception";
import { natalPreviewPayload } from "./fixtures/natal-preview";
import { natalReportGeneratingId, natalReportGeneratingPayload } from "./fixtures/natal-report";
import { prepareForScreenshot } from "./screenshot";

function buildFixtures(): MockApiRouteFixtures {
  return {
    "/api/auth/dev": { status: 200, body: { status: "ok", userId: "mock-user-id" } },
    "/api/natal/preview": { body: natalPreviewPayload },
  };
}

test.describe("Mock Visual — /readings/natal", () => {
  test("natal preview renders in ready state with all sections", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildFixtures());

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/readings/natal");
    await page.waitForLoadState("networkidle");

    // Root screen visible
    const screen = page.getByTestId("natal-preview-screen");
    await expect(screen).toBeVisible({ timeout: 10000 });
    await expect(screen).toHaveAttribute("data-state", "ready");
    await expect(screen).toHaveAttribute("data-full-report-available", "false");

    // Header and back link
    await expect(page.getByTestId("natal-preview-header")).toBeVisible();
    await expect(page.getByTestId("natal-preview-back-link")).toBeVisible();

    // Hero with badges
    await expect(page.getByTestId("natal-hero")).toBeVisible();
    await expect(page.getByTestId("natal-hero-badges")).toBeVisible();

    // Personal hook
    await expect(page.getByTestId("natal-personal-hook")).toBeVisible();

    // Highlights
    await expect(page.getByTestId("natal-highlights")).toBeVisible();

    // Calculation depth
    await expect(page.getByTestId("natal-calculation-depth")).toBeVisible();

    // Chart
    await expect(page.getByTestId("natal-chart")).toBeVisible();

    // Spheres
    await expect(page.getByTestId("natal-spheres")).toBeVisible();

    // Planets
    await expect(page.getByTestId("natal-planets")).toBeVisible();

    // Locked chapters
    await expect(page.getByTestId("natal-locked-chapters")).toBeVisible();

    // Sales bullets
    await expect(page.getByTestId("natal-sales-bullets")).toBeVisible();

    // CTA is disabled
    const cta = page.getByTestId("natal-full-report-cta");
    await expect(cta).toBeVisible();
    await expect(cta.locator("button").first()).toBeDisabled();
    await expect(cta.locator("button").first()).toHaveAttribute("aria-disabled", "true");

    // Deterministic visual baseline (fail-closed; UPDATE_SNAPSHOTS=true to refresh)
    await prepareForScreenshot(page);
    await expect(page).toHaveScreenshot("natal-ready.png");

    // No missing API fixtures
    await expectNoMissingApiFixtures(page, tracker);
  });

  test("natal chart unavailable state renders when chart is null", async ({ page }) => {
    const noChartPayload = { ...natalPreviewPayload, chart: null };
    const tracker = await installMockApiRoutes(page, {
      "/api/auth/dev": { status: 200, body: { status: "ok", userId: "mock-user-id" } },
      "/api/natal/preview": { body: noChartPayload },
    });

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/readings/natal");
    await page.waitForLoadState("networkidle");

    await expect(page.getByTestId("natal-chart-unavailable")).toBeVisible();
    await expectNoMissingApiFixtures(page, tracker);
  });

  test("natal preview has no horizontal overflow on mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const tracker = await installMockApiRoutes(page, buildFixtures());

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
      const style = document.createElement("style");
      style.textContent = "* { animation: none !important; transition: none !important; }";
      document.documentElement.appendChild(style);
    });

    await page.goto("/readings/natal");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);

    const overflowWidth = await page.evaluate(() =>
      document.documentElement.scrollWidth - document.documentElement.clientWidth
    );
    expect(overflowWidth).toBeLessThanOrEqual(5);
    await expectNoMissingApiFixtures(page, tracker);
  });

  test("profile-incomplete state renders natal-profile-incomplete with role=alert", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, {
      "/api/auth/dev": { status: 200, body: { status: "ok", userId: "mock-user-id" } },
      "/api/natal/preview": {
        status: 409,
        body: {
          detail: {
            message: "Profile incomplete",
            missingFields: ["birthDate", "birthCity"],
          },
        },
      },
    });

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/readings/natal");
    await page.waitForLoadState("networkidle");

    await expect(page.getByTestId("natal-preview-screen")).toHaveAttribute("data-state", "profile_incomplete");
    await expect(page.getByTestId("natal-profile-incomplete")).toBeVisible();
    await expect(page.getByTestId("natal-profile-incomplete")).toHaveAttribute("role", "alert");

    // Additional state baseline (does NOT replace the data-state=error baseline)
    await prepareForScreenshot(page);
    await expect(page).toHaveScreenshot("natal-profile-incomplete.png");

    await expectNoMissingApiFixtures(page, tracker);
  });

  test("natal report generating state renders on the unified root with screenshot baseline", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, {
      "/api/auth/dev": { status: 200, body: { status: "ok", userId: "mock-user-id" } },
      [`/api/natal/report/${natalReportGeneratingId}`]: { body: natalReportGeneratingPayload },
    });

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto(`/readings/natal/${natalReportGeneratingId}`);
    await page.waitForLoadState("networkidle");

    const screen = page.getByTestId("natal-report-screen");
    await expect(screen).toBeVisible({ timeout: 10000 });
    await expect(screen).toHaveAttribute("data-state", "generating");
    await expect(screen).toHaveAttribute("role", "status");
    await expect(screen).toHaveAttribute("aria-busy", "true");

    // Deterministic generating visual baseline (fail-closed)
    await prepareForScreenshot(page);
    await expect(page).toHaveScreenshot("natal-report-generating.png");

    await expectNoMissingApiFixtures(page, tracker);
  });

  test("natal report error state renders data-state=error with role=alert and screenshot baseline", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, {
      "/api/auth/dev": { status: 200, body: { status: "ok", userId: "mock-user-id" } },
      "/api/natal/report/visual-error": { status: 500, body: { detail: "visual error fixture" } },
    });

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/readings/natal/visual-error");
    await page.waitForLoadState("networkidle");

    const screen = page.getByTestId("natal-report-screen");
    await expect(screen).toBeVisible({ timeout: 10000 });
    await expect(screen).toHaveAttribute("data-state", "error");
    await expect(screen).toHaveAttribute("role", "alert");

    // Deterministic error visual baseline (fail-closed)
    await prepareForScreenshot(page);
    await expect(page).toHaveScreenshot("natal-report-error.png");

    await expectNoMissingApiFixtures(page, tracker);
  });

  test("missing API fixture is recorded by the tracker (negative proof)", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, {
      "/api/auth/dev": { status: 200, body: { status: "ok", userId: "mock-user-id" } },
    });

    await page.addInitScript(() => {
      localStorage.setItem("lumen:onboarded", "1");
    });

    await page.goto("/readings/natal");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    expect(tracker.count).toBeGreaterThan(0);
    expect(tracker.all.some((p) => p.startsWith("/api/natal/preview"))).toBe(true);
  });
});
