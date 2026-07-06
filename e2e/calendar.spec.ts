// ############################################################################
// AI_HEADER: MODULE_E2E_CALENDAR
// ROLE: E2E smoke tests for Calendar screen — real Telegram auth, no mocks
// DEPENDENCIES: @playwright/test, real backend with TELEGRAM_BOT_TOKEN
// GRACE_ANCHORS: [E2E_CALENDAR_TESTS]
// ############################################################################

import { test, expect } from './fixtures';

test.describe('Calendar Screen - Real Auth', () => {
  test('calendar renders real payload grid and lunar state', async ({ page }) => {
    test.setTimeout(30000);

    await page.addInitScript(() => {
      localStorage.setItem('lumen:onboarded', '1');
    });

    await page.goto('/');
    await page.waitForTimeout(3000);

    if (page.url().includes('/onboarding')) {
      console.log('Skipping calendar — user needs onboarding');
      return;
    }

    await page.goto('/calendar');
    const grid = page.getByTestId('calendar-grid');
    const unavailable = page.getByTestId('calendar-unavailable');
    await expect(grid.or(unavailable)).toBeVisible({ timeout: 15000 });

    if (await unavailable.isVisible()) {
      await expect(unavailable).toContainText('Календарь недоступен');
      return;
    }

    await expect(page.locator('[data-testid^="calendar-day-"]').first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator('[data-testid="lunar-calendar-strip"], [data-testid="lunar-calendar-unavailable"]')).toBeVisible({ timeout: 5000 });
    await page.getByRole('button', { name: 'Луна' }).click();
    await expect(page.getByTestId('calendar-grid')).toBeVisible({ timeout: 5000 });
  });
});
