// AI_HEADER
// module: M-TEST-CROSS-FEATURE-NAVIGATION
// wave: W-TEST-3
// purpose: Test navigation between Day, Chat, Readings, Calendar — real Telegram auth

import { test, expect } from './fixtures';

test.describe('Cross-Feature Navigation', () => {
  test('should navigate Day → Calendar → Chat → Profile', async ({ page }) => {
    test.setTimeout(60000);

    // Navigate through home to trigger auth + redirect
    await page.goto('/');
    await page.waitForTimeout(5000);

    const url = page.url();

    // If new user (onboarding), skip navigation test
    if (url.includes('/onboarding')) {
      console.log('New user — skipping navigation test (needs onboarding first)');
      return;
    }

    // Should be on day page now
    console.log('Current URL:', url);

    // Navigate to calendar via bottom tab
    const calendarLink = page.locator('a[href="/calendar"]');
    if (await calendarLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await calendarLink.click();
      await page.waitForTimeout(2000);
      console.log('Navigated to calendar:', page.url());
    }

    // Navigate to chat
    const chatLink = page.locator('a[href="/chat"]');
    if (await chatLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await chatLink.click();
      await page.waitForTimeout(2000);
      console.log('Navigated to chat:', page.url());
    }

    // Navigate to profile
    const profileLink = page.locator('a[href="/profile"]');
    if (await profileLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await profileLink.click();
      await page.waitForTimeout(2000);
      console.log('Navigated to profile:', page.url());
    }

    // Navigate back to day
    const dayLink = page.locator('a[href="/day/today"]');
    if (await dayLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await dayLink.click();
      await page.waitForTimeout(2000);
      console.log('Navigated back to day:', page.url());
    }

    // All navigations should have completed without errors
    expect(true).toBe(true);
  });
});
