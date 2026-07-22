// ############################################################################
// AI_HEADER: MODULE_E2E_CALENDAR
// ROLE: E2E smoke tests for Calendar screen — real Telegram auth, no mocks
// DEPENDENCIES: @playwright/test, real backend with TELEGRAM_BOT_TOKEN
// GRACE_ANCHORS: [E2E_CALENDAR_TESTS]
// ############################################################################

import { test, expect, waitForTodayState } from './fixtures';

test.describe('Calendar Screen - Real Auth', () => {
  test('calendar renders real payload grid, lunar state, and CTA navigation', async ({ page }) => {
    test.setTimeout(150000);

    await page.addInitScript(() => {
      localStorage.setItem('lumen:onboarded', '1');
    });

    const profileResponse = await page.request.put('/api/profile', {
      data: {
        firstName: 'Calendar Test',
        gender: 'male',
        birth: {
          birthday: '1990-01-15',
          birthTime: '14:30:00',
          birthCity: 'Moscow',
          birthLat: 55.7558,
          birthLon: 37.6173,
          birthTz: 'Europe/Moscow',
        },
      },
    });
    expect(profileResponse.ok()).toBeTruthy();

    // Navigate directly to /calendar to avoid home-page redirect racing with calendar navigation
    await page.goto('/calendar');
    const screenRoot = page.getByTestId('calendar-screen');
    const grid = page.getByTestId('calendar-grid');
    const loading = page.getByTestId('calendar-loading');
    await expect(screenRoot).toHaveAttribute('data-load-state', 'ready', { timeout: 30000 });
    await expect(loading).toBeHidden();
    await expect(grid).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('calendar-unavailable')).toBeHidden();

    await expect(page.locator('[data-testid^="calendar-day-"]').first()).toBeVisible({ timeout: 5000 });
    await expect(page.getByTestId('calendar-month-header')).toContainText(/Июль|Август|Сентябрь|Октябрь|Ноябрь|Декабрь|Январь|Февраль|Март|Апрель|Май|Июнь/);
    await expect(page.getByTestId('lunar-calendar-strip')).toBeVisible({ timeout: 5000 });
    await page.getByTestId('calendar-view-moon').click();
    await expect(page.getByTestId('calendar-grid')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('[data-testid^="calendar-moon-day-"]').first()).not.toHaveText('—');

    await page.getByTestId('calendar-view-day').click();
    await page.getByTestId('calendar-day-2026-07-12').click();
    await expect(page).toHaveURL(/\/calendar$/);
    await expect(page.getByTestId('calendar-selected-summary')).toContainText('12 июля 2026');

    await page.getByRole('button', { name: /Открыть (день|превью)/ }).click();
    await expect(page).toHaveURL(/\/day\/2026-07-12/);
    // The opened day must reach its terminal locked preview before the test ends.
    await waitForTodayState(page, 'locked');
  });
});
