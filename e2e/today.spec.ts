// ############################################################################
// AI_HEADER: MODULE_E2E_TODAY
// ROLE: E2E tests for Today screen — real Telegram auth, no mocks, no skips
// DEPENDENCIES: @playwright/test, real backend with TELEGRAM_BOT_TOKEN
// GRACE_ANCHORS: [E2E_TODAY_TESTS]
// ############################################################################

import { test, expect, completeOnboarding, waitForTodayState } from './fixtures';

// Evidence-based budgets: a single terminal-day wait may take up to 90s
// (observed real first pass 8.3–67.5s); the two navigation tests perform
// TWO terminal-day waits (initial + navigated day; the degraded-payload
// cache is intentionally not guaranteed), so they get 2x90 plus headroom.
const SINGLE_DAY_TEST_BUDGET_MS = 150000; // 90s wait + onboarding/assertions
const TWO_DAY_TEST_BUDGET_MS = 240000; // 2x90s waits + onboarding/calendar/navigation

// START_BLOCK: ENSURE_ONBOARDED
// Every test reaches a real profile: if the app redirects to onboarding,
// the REAL onboarding flow is completed instead of returning green early.
async function ensureOnboarded(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    localStorage.setItem('lumen:onboarded', '1');
  });
  await page.goto('/');
  await page.waitForTimeout(3000);
  if (page.url().includes('/onboarding')) {
    await completeOnboarding(page);
  }
}
// END_BLOCK: ENSURE_ONBOARDED

test.describe('Today Screen - Real Auth', () => {
  test('fresh user gets the honest locked preview (no fabricated access)', async ({ page }) => {
    test.setTimeout(SINGLE_DAY_TEST_BUDGET_MS);
    await ensureOnboarded(page);

    // A fresh user intentionally has NO access ledger: Today is locked with
    // the real preview, never an error and never fabricated full content.
    // The unlocked full-day path is proven separately by the referral flow
    // (e2e/referral-deeplink.spec.ts).
    const todayScreen = page.getByTestId('today-screen');
    await expect(todayScreen).toBeVisible({ timeout: 15000 });
    await waitForTodayState(page, 'locked');
    await expect(page.getByTestId('error-boundary')).toBeHidden();
    // Paywall/preview contract: access card present, full-day cards absent.
    await expect(page.getByTestId('access-card')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('day-summary-card')).toHaveCount(0);
    await expect(page.getByTestId('concrete-day-advice')).toHaveCount(0);
    // Preview content still renders from the real payload.
    await expect(page.getByText('Главное на этот день')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('week-strip')).toBeVisible({ timeout: 10000 });
    const tabBar = page.locator('nav[aria-label="Основная навигация"]');
    await expect(tabBar).toBeVisible({ timeout: 5000 });
  });

  test('no placeholder when API returns real data', async ({ page }) => {
    test.setTimeout(SINGLE_DAY_TEST_BUDGET_MS);
    await ensureOnboarded(page);

    // Wait for the terminal locked preview first — otherwise the check is
    // vacuous against the loading branch.
    await waitForTodayState(page, 'locked');

    // Placeholder should NOT be visible — real LLM data should render instead
    const placeholder = page.locator('text=/Данные временно недоступны/i');
    const hasPlaceholder = await placeholder.isVisible({ timeout: 3000 }).catch(() => false);
    expect(hasPlaceholder).toBe(false);
  });

  test('calendar navigation with real auth', async ({ page }) => {
    test.setTimeout(TWO_DAY_TEST_BUDGET_MS);
    await ensureOnboarded(page);

    await page.goto('/calendar');
    await expect(page.getByTestId('calendar-grid')).toBeVisible({ timeout: 15000 });

    // Selecting a day cell opens the preview card; the PUBLIC CTA
    // («Открыть день» for accessible days, «Открыть превью» for locked)
    // performs the canonical navigation to /day/YYYY-MM-DD.
    const firstOpenableDay = page.locator('[data-testid^="calendar-day-"]:not([disabled])').first();
    await expect(firstOpenableDay).toBeVisible({ timeout: 5000 });
    await firstOpenableDay.click();
    const openCta = page.getByRole('button', { name: /Открыть день|Открыть превью/ });
    await expect(openCta).toBeEnabled({ timeout: 10000 });
    await openCta.click();
    await expect(page).toHaveURL(/\/day\/\d{4}-\d{2}-\d{2}/);
    // The opened day must reach its terminal locked preview before the test ends.
    await waitForTodayState(page, 'locked');
  });

  test('week strip navigation with real auth', async ({ page }) => {
    test.setTimeout(TWO_DAY_TEST_BUDGET_MS);
    await ensureOnboarded(page);

    // Canonical day URL is /day/YYYY-MM-DD (the root route redirects there).
    await page.goto('/');
    await expect(page).toHaveURL(/\/day\/\d{4}-\d{2}-\d{2}/, { timeout: 15000 });
    // A fresh user is locked: wait for the terminal locked preview, not the
    // loading branch, before touching the week strip.
    await waitForTodayState(page, 'locked');
    const weekStrip = page.getByTestId('week-strip');
    await expect(weekStrip).toBeVisible({ timeout: 5000 });
    const firstWeekDay = weekStrip.locator('button').first();
    await expect(firstWeekDay).toBeVisible({ timeout: 5000 });
    await firstWeekDay.click();
    await expect(page).toHaveURL(/\/day\/\d{4}-\d{2}-\d{2}/);
    // The navigated day must also reach terminal state before the test ends
    // (no in-flight day request left behind).
    await waitForTodayState(page, 'locked');
  });
});
