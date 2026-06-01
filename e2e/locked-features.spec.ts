// AI_HEADER
// module: M-TEST-LOCKED-FEATURES
// purpose: Smoke tests — chat/natal/horary locked placeholders render without crash

import { test, expect } from './fixtures';

test.describe('Locked Features', () => {
  test('/chat renders locked placeholder without crash', async ({ page }) => {
    test.setTimeout(20000);
    await page.addInitScript(() => localStorage.setItem('lumen:onboarded', '1'));
    await page.goto('/chat');
    await page.waitForTimeout(3000);

    // Should show "Спросить" title or "Скоро" badge
    const lockedTitle = page.locator('text=/Спросить|скоро/i').first();
    await expect(lockedTitle).toBeVisible({ timeout: 5000 });

    // Should NOT show chat composer (no API calls)
    const composer = page.locator('textarea, input[type="text"]').first();
    const hasComposer = await composer.isVisible({ timeout: 2000 }).catch(() => false);
    expect(hasComposer).toBe(false);
  });

  test('/readings/natal renders without crash', async ({ page }) => {
    test.setTimeout(20000);
    await page.addInitScript(() => localStorage.setItem('lumen:onboarded', '1'));
    await page.goto('/readings/natal');
    await page.waitForTimeout(3000);

    // Should show "Натальная карта" or "Скоро"
    const natalText = page.locator('text=/натальная карта|скоро/i').first();
    await expect(natalText).toBeVisible({ timeout: 5000 });

    // Should NOT crash — page should be visible
    const url = page.url();
    expect(url).toContain('/readings/natal');
  });

  test('/readings page shows Спросить in TabBar', async ({ page }) => {
    test.setTimeout(20000);
    await page.addInitScript(() => localStorage.setItem('lumen:onboarded', '1'));
    await page.goto('/');
    await page.waitForTimeout(5000);

    // Navigate to readings to verify TabBar
    await page.goto('/readings');
    await page.waitForTimeout(3000);

    // TabBar should have 5 nav links including "Спросить"
    const tabLinks = page.locator('nav[aria-label="Основная навигация"] a');
    const count = await tabLinks.count();
    expect(count).toBeGreaterThanOrEqual(4);

    // "Спросить" tab should exist
    const askTab = page.locator('nav a[href="/chat"]');
    await expect(askTab).toBeVisible({ timeout: 5000 });
  });
});
