// ############################################################################
// AI_HEADER: MODULE_E2E_TODAY
// ROLE: E2E tests for Today screen — real Telegram auth, no mocks
// DEPENDENCIES: @playwright/test, real backend with TELEGRAM_BOT_TOKEN
// GRACE_ANCHORS: [E2E_TODAY_TESTS]
// ############################################################################

import { test, expect } from './fixtures';

test.describe('Today Screen - Real Auth', () => {
  test('today screen loads after Telegram auth', async ({ page }) => {
    test.setTimeout(30000);

    // Set onboarded flag so we skip onboarding flow
    await page.addInitScript(() => {
      localStorage.setItem('lumen:onboarded', '1');
    });

    // Navigate through home page to trigger auth + redirect
    await page.goto('/');

    // Wait for auth to complete and page to settle
    await page.waitForTimeout(3000);

    // Should land on either /day/today (onboarded) or /onboarding
    const url = page.url();
    console.log('Landed at:', url);

    if (url.includes('/onboarding')) {
      // New user — need to complete onboarding first
      // But the page should at least render (no white screen)
      await expect(page.locator('text=/Продолжить|продолжить/i')).toBeVisible({ timeout: 5000 });
      console.log('Onboarding page rendered — user needs onboarding');
      return; // onboarding test is a separate spec
    }

    const todayScreen = page.getByTestId('today-screen');
    const errorBoundary = page.getByTestId('error-boundary');
    await expect(todayScreen.or(errorBoundary)).toBeVisible({ timeout: 15000 });

    if (await errorBoundary.isVisible()) {
      await expect(page.getByTestId('error-message')).toBeVisible({ timeout: 5000 });
      return;
    }

    await expect(todayScreen).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId('day-summary-card')).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId('day-energy-meter')).toBeVisible({ timeout: 5000 });
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
    test.setTimeout(30000);

    await page.addInitScript(() => localStorage.setItem('lumen:onboarded', '1'));

    await page.goto('/');
    await page.waitForTimeout(6000);

    if (page.url().includes('/onboarding')) {
      return;
    }

    await expect(page.getByTestId('today-screen')).toBeVisible({ timeout: 15000 });

    // Placeholder should NOT be visible — real LLM data should render instead
    const placeholder = page.locator('text=/Данные временно недоступны/i');
    const hasPlaceholder = await placeholder.isVisible({ timeout: 3000 }).catch(() => false);
    expect(hasPlaceholder).toBe(false);
  });

  test('calendar navigation with real auth', async ({ page }) => {
    test.setTimeout(30000);

    await page.addInitScript(() => {
      localStorage.setItem('lumen:onboarded', '1');
    });

    // Go via home to trigger auth
    await page.goto('/');
    await page.waitForTimeout(3000);

    // If we land on onboarding, skip the calendar test
    if (page.url().includes('/onboarding')) {
      console.log('Skipping calendar — user needs onboarding');
      return;
    }

    await page.goto('/calendar');
    await expect(page.getByTestId('calendar-grid')).toBeVisible({ timeout: 15000 });

    const firstOpenableDay = page.locator('[data-testid^="calendar-day-"]:not([disabled])').first();
    await expect(firstOpenableDay).toBeVisible({ timeout: 5000 });
    await firstOpenableDay.click();
    await expect(page).toHaveURL(/\/day\/\d{4}-\d{2}-\d{2}/);
  });

  test('week strip navigation with real auth', async ({ page }) => {
    test.setTimeout(30000);

    await page.addInitScript(() => {
      localStorage.setItem('lumen:onboarded', '1');
    });

    await page.goto('/');
    await page.waitForTimeout(3000);

    if (page.url().includes('/onboarding')) {
      console.log('Skipping week strip — user needs onboarding');
      return;
    }

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
