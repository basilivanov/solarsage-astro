// AI_HEADER
// module: M-TEST-CROSS-FEATURE-NAVIGATION
// wave: W-TEST-3
// purpose: Test navigation between Day, Calendar, Chat, Profile — real Telegram auth, no skips

import { test, expect, completeOnboarding, waitForTodayState } from './fixtures';

test.describe('Cross-Feature Navigation', () => {
  test('should navigate Day → Calendar → Chat → Profile → Day', async ({ page }) => {
    test.setTimeout(120000);

    await page.goto('/');
    await page.waitForTimeout(5000);
    if (page.url().includes('/onboarding')) {
      await completeOnboarding(page);
    }

    // Day is the starting point — required, never conditional. Fresh user:
    // wait for the exact terminal locked state, not the loader.
    await waitForTodayState(page, 'locked');

    // Calendar: required link and required destination.
    const calendarLink = page.locator('a[href="/calendar"]');
    await expect(calendarLink).toBeVisible({ timeout: 5000 });
    await calendarLink.click();
    await expect(page).toHaveURL(/\/calendar/);
    await expect(page.getByTestId('calendar-grid')).toBeVisible({ timeout: 10000 });

    // Chat: required link and required destination.
    const chatLink = page.locator('a[href="/chat"]');
    await expect(chatLink).toBeVisible({ timeout: 5000 });
    await chatLink.click();
    await expect(page).toHaveURL(/\/chat/);
    await expect(page.locator('main')).toBeVisible({ timeout: 5000 });

    // Profile: required link and required destination.
    const profileLink = page.locator('a[href="/profile"]');
    await expect(profileLink).toBeVisible({ timeout: 5000 });
    await profileLink.click();
    await expect(page).toHaveURL(/\/profile/);
    await expect(page.getByTestId('profile-screen')).toBeVisible({ timeout: 10000 });

    // Back to day: required link and required canonical destination.
    const dayLink = page.locator('a[href^="/day/"]');
    await expect(dayLink.first()).toBeVisible({ timeout: 5000 });
    await dayLink.first().click();
    await expect(page).toHaveURL(/\/day\/\d{4}-\d{2}-\d{2}/);
    // The final day landing must be terminal (fresh user: locked) before the test ends.
    await waitForTodayState(page, 'locked');
  });
});
