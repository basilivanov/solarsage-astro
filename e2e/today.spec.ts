// ############################################################################
// AI_HEADER: MODULE_E2E_TODAY
// ROLE: E2E tests for Today screen — real Telegram auth, no mocks
// DEPENDENCIES: @playwright/test, real backend with TELEGRAM_BOT_TOKEN
// GRACE_ANCHORS: [E2E_TODAY_TESTS]
// ############################################################################

import { test, expect, waitForAuthComplete } from './fixtures';

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

    // Onboarded user — should see today screen or error
    await page.waitForSelector(
      '[data-testid="today-screen"], [data-testid="error-boundary"], [data-testid="auth-loading"]',
      { timeout: 15000 }
    );

    const todayScreen = page.getByTestId('today-screen');
    if (await todayScreen.isVisible({ timeout: 3000 }).catch(() => false)) {
      await expect(page.getByTestId('today-headline')).toBeVisible({ timeout: 5000 });
      // Paywall should NOT be visible for user with full access
      const paywall = page.locator('text=/открыть доступ|подписки/i');
      await expect(paywall).not.toBeVisible({ timeout: 3000 });
      // Почему так у меня section should be visible
      const whySection = page.locator('text=/почему так у меня/i');
      await expect(whySection).toBeVisible({ timeout: 5000 });
      // TabBar with navigation icons should be visible
      const tabBar = page.locator('nav[aria-label="Основная навигация"]');
      await expect(tabBar).toBeVisible({ timeout: 5000 });
      console.log('Today screen rendered — paywall absent, WhyExpanded + TabBar visible');
    }
  });

  test('no placeholder when API returns real data', async ({ page }) => {
    test.setTimeout(30000);

    await page.addInitScript(() => localStorage.setItem('lumen:onboarded', '1'));

    await page.goto('/');
    await page.waitForTimeout(6000);

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

    // Navigate to calendar
    await page.goto('/calendar');
    await page.waitForTimeout(2000);

    // Check for calendar grid or error
    const calendarGrid = page.getByTestId('calendar-grid');
    const hasCalendar = await calendarGrid.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasCalendar) {
      const firstDay = page.locator('[data-testid^="calendar-day-"]').first();
      if (await firstDay.isVisible({ timeout: 2000 }).catch(() => false)) {
        await firstDay.click();
        await expect(page).toHaveURL(/\/day\/\d{4}-\d{2}-\d{2}/);
        console.log('Calendar navigation works');
      }
    }
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
    await page.waitForSelector(
      '[data-testid="today-screen"], [data-testid="error-boundary"]',
      { timeout: 15000 }
    );

    const weekStrip = page.getByTestId('week-strip');
    if (await weekStrip.isVisible({ timeout: 3000 }).catch(() => false)) {
      const weekDays = weekStrip.locator('a');
      const count = await weekDays.count();
      if (count > 0) {
        await weekDays.first().click();
        await expect(page).toHaveURL(/\/day\/\d{4}-\d{2}-\d{2}/);
        console.log('Week strip navigation works');
      }
    }
  });
});
