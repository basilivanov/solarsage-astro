// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_PROMO_CAMPAIGN_SPEC
// ROLE: Mock e2e spec for the named promo campaign gate + confirmation sheet.
//       Uses Playwright route interception with contract-valid promo payloads.
//       Verifies the semantic sheet contract, activation, dismiss, terminal
//       error and promoNatal onboarding redirect on stable payloads.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-PROMO-CAMPAIGN-SPEC
// purpose: Verify the promo confirmation sheet flow end-to-end on stable
//          intercepted API payloads: sheet semantic contract (role=dialog,
//          aria-modal, data-state, benefit rows), activate -> redeem -> single
//          reload with cleared token, dismiss without redeem, INVALID_CODE
//          terminal clear, and incomplete-profile redirect to promoNatal
//          onboarding with retained token.
// owns:
//   - e2e/mock-visual/promo-campaign.spec.ts
// inputs: Playwright test runner, E2E_BASE_URL env
// outputs: Test pass/fail with assertions on DOM contract and flow behavior
// dependencies:
//   - @playwright/test
//   - ./route-interception (installMockApiRoutes, expectNoMissingApiFixtures)
//   - ./fixtures/day-2026-07-05, ./fixtures/calendar-2026-07, ./fixtures/profile
// side_effects: None (all API calls intercepted)
// invariants:
//   - Promo token fixture matches the canonical promo alphabet/length
//   - Sheet assertions use only the public DOM contract (data-testid/aria)
//   - Raw token never appears in assertions beyond sessionStorage checks
// failure_policy: Tests fail on missing fixture or assertion failure
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-PROMO-CAMPAIGN-SPEC

// START_MODULE_MAP: M-E2E-MOCK-VISUAL-PROMO-CAMPAIGN-SPEC
// public_entrypoints:
//   - promo confirmation sheet shows offer and activates once
//   - dismiss clears token without redeem
//   - INVALID_CODE clears token without sheet
//   - incomplete profile redirects to promoNatal onboarding
// semantic_blocks:
//   - PROMO_FIXTURES: base + promo fixture builders
//   - PROMO_FLOW_TESTS: sheet/activate/dismiss/error/onboarding tests
// owned_tests: none (this file is the test)
// END_MODULE_MAP: M-E2E-MOCK-VISUAL-PROMO-CAMPAIGN-SPEC

import { expect, test } from "@playwright/test";
import { expectNoMissingApiFixtures, installMockApiRoutes, type MockApiRouteFixtures } from "./route-interception";
import { dayPayload, referralPayload } from "./fixtures/day-2026-07-05";
import { calendarPayload } from "./fixtures/calendar-2026-07";
import { profilePayload } from "./fixtures/profile";

// ############################################################################
// Fixtures
// ############################################################################

const PROMO_TOKEN = "m7q4n9x2r5kd";
const PENDING_KEY = "__astro_pending_promo_token";

const promoOffer = {
  displayName: "Приветственный бонус",
  accessDays: 30,
  bonusCredits: 50,
  unlockNatal: true,
};

const WEEK_STRIP_MIN_DATES = [
  "2026-06-28",
  "2026-06-29",
  "2026-06-30",
  "2026-07-01",
  "2026-07-02",
  "2026-07-03",
  "2026-07-04",
];

function buildBaseFixtures(): MockApiRouteFixtures {
  const fixtures: MockApiRouteFixtures = {
    "/api/day/2026-07-05": { body: dayPayload },
    "/api/auth/dev": {
      status: 200,
      body: { status: "ok", userId: "mock-user-id" },
    },
    "/api/calendar": { body: calendarPayload },
    "/api/referral": { body: referralPayload },
    "/api/profile": { body: profilePayload },
  };
  for (const dateStr of WEEK_STRIP_MIN_DATES) {
    const day = dayPayload.weekStrip.find((w) => w.date === dateStr);
    fixtures[`/api/day/${dateStr}`] = {
      body: { dayStatus: day?.dayStatus ?? "steady" },
    };
  }
  return fixtures;
}

// ############################################################################
// Tests
// ############################################################################

// START_BLOCK: PROMO_FLOW_TESTS

test("shows confirmation sheet with offer and activates once with cleared token", async ({ page }) => {
  const fixtures = buildBaseFixtures();
  fixtures["/api/promo/preview"] = { body: { offer: promoOffer, profileComplete: true } };
  let redeemCalls = 0;
  fixtures["/api/promo/redeem"] = () => {
    redeemCalls += 1;
    return {
      body: {
        status: "redeemed",
        offer: promoOffer,
        grants: {
          accessStartsAt: "2026-07-25",
          accessUntil: "2026-08-23",
          bonusCredits: 50,
          bonusCreditsExpiresAt: "2026-08-24T00:00:00Z",
          natalUnlocked: true,
          natalAlreadyOwned: false,
        },
      },
    };
  };

  const tracker = await installMockApiRoutes(page, fixtures);
  await page.goto(`/day/2026-07-05?tgWebAppStartParam=${PROMO_TOKEN}`);

  const sheet = page.getByTestId("promo-confirmation-sheet");
  await expect(sheet).toBeVisible();
  await expect(sheet).toHaveAttribute("role", "dialog");
  await expect(sheet).toHaveAttribute("aria-modal", "true");
  await expect(sheet).toHaveAttribute("data-state", "ready");
  await expect(page.getByTestId("promo-offer-name")).toHaveText("Приветственный бонус");
  await expect(page.getByTestId("promo-benefit-access")).toContainText("30");
  await expect(page.getByTestId("promo-benefit-credits")).toContainText("50");
  await expect(page.getByTestId("promo-benefit-natal")).toBeVisible();

  await page.getByTestId("promo-activate").click();
  await expect.poll(() => redeemCalls).toBe(1);

  // Successful redeem clears the token and triggers one reload; the sheet
  // must not reappear and the pending token must be gone.
  await page.waitForLoadState("load");
  await expect(page.getByTestId("promo-confirmation-sheet")).toHaveCount(0);
  const pending = await page.evaluate((key) => sessionStorage.getItem(key), PENDING_KEY);
  expect(pending).toBeNull();

  await expectNoMissingApiFixtures(page, tracker);
});

test("dismiss clears pending token without redeem", async ({ page }) => {
  const fixtures = buildBaseFixtures();
  fixtures["/api/promo/preview"] = { body: { offer: promoOffer, profileComplete: true } };
  let redeemCalls = 0;
  fixtures["/api/promo/redeem"] = () => {
    redeemCalls += 1;
    return { body: {} };
  };

  const tracker = await installMockApiRoutes(page, fixtures);
  await page.goto(`/day/2026-07-05?tgWebAppStartParam=${PROMO_TOKEN}`);

  const sheet = page.getByTestId("promo-confirmation-sheet");
  await expect(sheet).toBeVisible();

  await page.getByTestId("promo-dismiss").click();
  await expect(page.getByTestId("promo-confirmation-sheet")).toHaveCount(0);
  expect(redeemCalls).toBe(0);
  const pending = await page.evaluate((key) => sessionStorage.getItem(key), PENDING_KEY);
  expect(pending).toBeNull();

  await expectNoMissingApiFixtures(page, tracker);
});

test("INVALID_CODE clears pending token and never shows the sheet", async ({ page }) => {
  const fixtures = buildBaseFixtures();
  fixtures["/api/promo/preview"] = {
    status: 400,
    body: { detail: { code: "INVALID_CODE", message: "Неверный промокод" } },
  };

  const tracker = await installMockApiRoutes(page, fixtures);
  await page.goto(`/day/2026-07-05?tgWebAppStartParam=${PROMO_TOKEN}`);

  await expect(page.getByTestId("today-screen")).toBeVisible();
  await expect(page.getByTestId("promo-confirmation-sheet")).toHaveCount(0);
  await expect
    .poll(async () => page.evaluate((key) => sessionStorage.getItem(key), PENDING_KEY))
    .toBeNull();

  await expectNoMissingApiFixtures(page, tracker);
});

test("incomplete profile redirects to promoNatal onboarding and retains token", async ({ page }) => {
  const fixtures = buildBaseFixtures();
  fixtures["/api/promo/preview"] = { body: { offer: promoOffer, profileComplete: false } };

  const tracker = await installMockApiRoutes(page, fixtures);
  await page.goto(`/day/2026-07-05?tgWebAppStartParam=${PROMO_TOKEN}`);

  await expect(page).toHaveURL(/\/onboarding\?requiredFor=promoNatal/);

  // Sheet is suppressed on the onboarding route; token is retained for the
  // post-onboarding retry.
  await expect(page.getByTestId("promo-confirmation-sheet")).toHaveCount(0);
  const pending = await page.evaluate((key) => sessionStorage.getItem(key), PENDING_KEY);
  expect(pending).toBe(PROMO_TOKEN);

  await expectNoMissingApiFixtures(page, tracker);
});

// END_BLOCK: PROMO_FLOW_TESTS
