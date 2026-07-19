// ############################################################################
// AI_HEADER: MODULE_E2E_TODAY
// ROLE: E2E tests for Today screen — real Telegram auth, no mocks, no skips
// DEPENDENCIES: @playwright/test, real backend with TELEGRAM_BOT_TOKEN
// GRACE_ANCHORS: [E2E_TODAY_TESTS]
// ############################################################################

import { test, expect, completeOnboarding } from './fixtures';

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
  test('today screen loads after Telegram auth', async ({ page }) => {
    test.setTimeout(60000);
    await ensureOnboarded(page);

    const todayScreen = page.getByTestId('today-screen');
    await expect(todayScreen).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('error-boundary')).toBeHidden();
    await expect(page.getByTestId('day-summary-card')).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId('concrete-day-advice')).toBeVisible({ timeout: 5000 });
    const chart = page.getByTestId('day-chart');
    const chartUnavailable = page.getByTestId('day-chart-unavailable');
    await expect(chart.or(chartUnavailable)).toBeVisible({ timeout: 5000 });
    const paywall = page.locator('text=/открыть доступ|подписки/i');
    await expect(paywall).not.toBeVisible({ timeout: 3000 });
    const whySection = page.locator('text=/почему так у меня/i');
    await expect(whySection).toBeVisible({ timeout: 5000 });
    const tabBar = page.locator('nav[aria-label="Основная навигация"]');
    await expect(tabBar).toBeVisible({ timeout: 5000 });
  });

  test('no placeholder when API returns real data', async ({ page }) => {
    test.setTimeout(60000);
    await ensureOnboarded(page);

    await expect(page.getByTestId('today-screen')).toBeVisible({ timeout: 15000 });

    // Placeholder should NOT be visible — real LLM data should render instead
    const placeholder = page.locator('text=/Данные временно недоступны/i');
    const hasPlaceholder = await placeholder.isVisible({ timeout: 3000 }).catch(() => false);
    expect(hasPlaceholder).toBe(false);
  });

  test('calendar navigation with real auth', async ({ page }) => {
    test.setTimeout(60000);
    await ensureOnboarded(page);

    await page.goto('/calendar');
    await expect(page.getByTestId('calendar-grid')).toBeVisible({ timeout: 15000 });

    const firstOpenableDay = page.locator('[data-testid^="calendar-day-"]:not([disabled])').first();
    await expect(firstOpenableDay).toBeVisible({ timeout: 5000 });
    await firstOpenableDay.click();
    await expect(page).toHaveURL(/\/day\/\d{4}-\d{2}-\d{2}/);
  });

  test('week strip navigation with real auth', async ({ page }) => {
    test.setTimeout(60000);
    await ensureOnboarded(page);

    await page.goto('/day/today');
    await expect(page.getByTestId('today-screen')).toBeVisible({ timeout: 15000 });
    const weekStrip = page.getByTestId('week-strip');
    await expect(weekStrip).toBeVisible({ timeout: 5000 });
    const firstWeekDay = weekStrip.locator('button').first();
    await expect(firstWeekDay).toBeVisible({ timeout: 5000 });
    await firstWeekDay.click();
    await expect(page).toHaveURL(/\/day\/\d{4}-\d{2}-\d{2}/);
  });
});
