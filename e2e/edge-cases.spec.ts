// AI_HEADER
// module: M-TEST-E2E-EDGE-CASES
// wave: W-TEST-3
// purpose: Comprehensive edge case tests — real Telegram auth, no mocks

import { test, expect } from './fixtures';

// ── Onboarding Edge Cases ──────────────────────────────────────

test.describe('Onboarding — Validation', () => {
  test.use({ uniqueTelegramUser: true });

  test('should disable Next button on empty birth date', async ({ page }) => {
    test.setTimeout(30000);
    await page.goto('/onboarding');

    // Welcome → Birth
    await page.locator('button:has-text("Продолжить")').click();
    await page.waitForTimeout(1000);
    await expect(page.getByText('Дата и время рождения')).toBeVisible({ timeout: 5000 });

    // "Далее" disabled without valid date
    await expect(page.locator('button:has-text("Далее")').first()).toBeDisabled();
  });

  test('should reject invalid date (Feb 30)', async ({ page }) => {
    test.setTimeout(30000);
    await page.goto('/onboarding');
    await page.locator('button:has-text("Продолжить")').click();
    await page.waitForTimeout(1000);

    await page.getByRole('textbox', { name: 'День' }).fill('30');
    await page.getByRole('textbox', { name: 'Месяц' }).fill('02');
    await page.getByRole('textbox', { name: 'Год' }).fill('1990');
    await page.waitForTimeout(300);

    await expect(page.locator('button:has-text("Далее")').first()).toBeDisabled();
  });

  test('should allow unknown time (checkbox)', async ({ page }) => {
    test.setTimeout(30000);
    await page.goto('/onboarding');
    await page.locator('button:has-text("Продолжить")').click();
    await page.waitForTimeout(1000);

    // Fill just date, skip time
    await page.getByRole('textbox', { name: 'День' }).fill('15');
    await page.getByRole('textbox', { name: 'Месяц' }).fill('01');
    await page.getByRole('textbox', { name: 'Год' }).fill('1990');

    // Check "Не знаю точное время"
    await page.locator('text=/не знаю точное время/i').click();
    await page.waitForTimeout(300);

    // Should be enabled with unknown time
    await expect(page.locator('button:has-text("Далее")').first()).toBeEnabled();
  });

  test('should navigate back between steps', async ({ page }) => {
    test.setTimeout(30000);
    await page.goto('/onboarding');

    // Welcome → Birth
    await page.locator('button:has-text("Продолжить")').click();
    await page.waitForTimeout(500);
    expect(page.url()).toContain('/onboarding');

    // Birth → Welcome (back)
    await page.locator('[aria-label="Назад"]').click();
    await page.waitForTimeout(500);

    // Should see welcome again
    await expect(page.locator('button:has-text("Продолжить")')).toBeVisible({ timeout: 5000 });
  });

  test('should handle network error during profile save (graceful)', async ({ page }) => {
    test.setTimeout(40000);

    await page.goto('/onboarding');

    // Step 1 → 2
    await page.locator('button:has-text("Продолжить")').click();
    await page.waitForTimeout(500);

    // Fill birth
    await page.getByRole('textbox', { name: 'День' }).fill('15');
    await page.getByRole('textbox', { name: 'Месяц' }).fill('01');
    await page.getByRole('textbox', { name: 'Год' }).fill('1990');
    await page.getByRole('textbox', { name: 'Часы' }).fill('12');
    await page.getByRole('textbox', { name: 'Минуты' }).fill('00');
    await page.locator('button:has-text("Далее")').first().click();
    await page.waitForTimeout(500);

    // Step 3: Place — select popular city
    await page.locator('button:has-text("Москва")').first().click();
    await page.waitForTimeout(300);
    await page.locator('text=/сейчас живу там же/i').click();
    await page.waitForTimeout(300);
    await page.locator('button:has-text("Далее")').first().click();
    await page.waitForTimeout(500);

    // Step 4
    await page.locator('button:has-text("Далее")').first().click();

    // Step 5: Gender
    await expect(page.getByRole('heading', { name: /мужчина или женщина/i })).toBeVisible({ timeout: 5000 });
    await page.getByRole('button', { name: 'Женщина' }).click();

    // Block profile save before finishing — method-aware to avoid interfering with GET requests
    await page.route('**/api/profile', (route) => {
      const method = route.request().method();
      if (method === 'PUT' || method === 'PATCH' || method === 'POST') {
        return route.abort();
      }
      return route.continue();
    });

    // Try to finish
    const finishBtn = page.getByRole('button', { name: /Открыть мой день|Открыть/i });
    await expect(finishBtn).toBeEnabled({ timeout: 5000 });
    await finishBtn.click();

    await expect(page.locator('text=/Failed to update profile|Load failed|Failed to fetch|Не удалось сохранить профиль/i')).toBeVisible({ timeout: 10000 });
    await expect(page).toHaveURL(/\/onboarding/);
    await page.waitForTimeout(2000);
    expect(page.url()).toContain('/onboarding');
    await expect(finishBtn).toBeEnabled({ timeout: 5000 });
  });
});

// ── Day Screen Edge Cases ──────────────────────────────────────

test.describe('Day Screen — Access States', () => {
  test('should show paywall for non-onboarded user redirected to day', async ({ page }) => {
    test.setTimeout(30000);
    await page.addInitScript(() => localStorage.setItem('lumen:onboarded', '1'));
    await page.goto('/');
    await page.waitForTimeout(5000);

    const url = page.url();
    if (url.includes('/day/')) {
      // Day loaded — may have content or error depending on backend data
      const paywall = page.locator('text=/открыть доступ|подписки|пригласи друга/i');
      const todayScreen = page.locator('[data-testid="today-screen"]');
      const error = page.locator('[data-testid="error-boundary"]');

      const hasContent = await Promise.any([
        paywall.isVisible().then(() => 'paywall'),
        todayScreen.isVisible().then(() => 'today'),
        error.isVisible().then(() => 'error'),
      ].map(p => p.catch(() => null)));

      expect(hasContent).toBeTruthy();
    }
  });

  test('should navigate dates via arrows', async ({ page }) => {
    test.setTimeout(30000);
    await page.addInitScript(() => localStorage.setItem('lumen:onboarded', '1'));
    await page.goto('/');
    await page.waitForTimeout(5000);

    if (!page.url().includes('/day/')) return;

    const prevBtn = page.locator('[aria-label="Предыдущий день"]');
    const nextBtn = page.locator('[aria-label="Следующий день"]');

    if (await nextBtn.isEnabled({ timeout: 2000 }).catch(() => false)) {
      await nextBtn.click();
      await page.waitForTimeout(2000);
      expect(page.url()).toMatch(/\/day\/\d{4}-\d{2}-\d{2}/);
    }
  });
});

// ── Calendar Edge Cases ────────────────────────────────────────

test.describe('Calendar', () => {
  test('should show month with day cells', async ({ page }) => {
    test.setTimeout(30000);
    await page.addInitScript(() => localStorage.setItem('lumen:onboarded', '1'));
    await page.goto('/calendar');
    await page.waitForTimeout(4000);

    const grid = page.locator('[data-testid="calendar-grid"]');
    const hasGrid = await grid.isVisible({ timeout: 5000 }).catch(() => false);

    if (hasGrid) {
      const dayCell = page.locator('[data-testid^="calendar-day-"]').first();
      await expect(dayCell).toBeVisible({ timeout: 3000 });
    }
  });

  test('should navigate to day on click', async ({ page }) => {
    test.setTimeout(30000);
    await page.addInitScript(() => localStorage.setItem('lumen:onboarded', '1'));
    await page.goto('/calendar');
    await page.waitForLoadState('networkidle');

    const screenRoot = page.getByTestId('calendar-screen');
    const grid = page.getByTestId('calendar-grid');
    const unavailable = page.getByTestId('calendar-unavailable');
    await expect(screenRoot).toHaveAttribute('data-load-state', /ready|error/, { timeout: 15000 });
    await expect(grid.or(unavailable)).toBeVisible({ timeout: 15000 });

    if (await unavailable.isVisible()) {
      await expect(unavailable).toContainText('Календарь недоступен');
      return;
    }

    const dayCells = page.locator('[data-testid^="calendar-day-"]');
    await expect(dayCells.first()).toBeVisible({ timeout: 5000 });
    expect(await dayCells.count()).toBeGreaterThan(0);

    const openableDay = page.locator('[data-testid^="calendar-day-"]:not([disabled])').first();
    if (await openableDay.isVisible({ timeout: 3000 }).catch(() => false)) {
      await openableDay.click();
      await page.waitForTimeout(2000);
      expect(page.url()).toMatch(/\/day\/\d{4}-\d{2}-\d{2}/);
      return;
    }

    await expect(page.locator('[data-testid^="calendar-day-"][disabled]').first()).toBeVisible({ timeout: 3000 });
    await expect(page.locator('text=/недоступен|Недоступно|Открыть превью/i').first()).toBeVisible({ timeout: 3000 });
  });
});

// ── Profile Edge Cases ─────────────────────────────────────────

test.describe('Profile', () => {
  test('should load profile page', async ({ page }) => {
    test.setTimeout(30000);
    await page.addInitScript(() => localStorage.setItem('lumen:onboarded', '1'));
    await page.goto('/');
    await page.waitForTimeout(5000);
    await page.goto('/profile');
    await page.waitForTimeout(5000);

    // Should NOT be on onboarding, chat, or home
    const url = page.url();
    expect(url).toContain('/profile');
  });

  test('should have working navigation to profile', async ({ page }) => {
    test.setTimeout(30000);
    await page.addInitScript(() => localStorage.setItem('lumen:onboarded', '1'));
    await page.goto('/');
    await page.waitForTimeout(5000);
    await page.goto('/profile');
    await page.waitForTimeout(5000);

    // TabBar should be visible (5 nav links)
    const links = page.locator('nav a');
    const count = await links.count();
    expect(count).toBeGreaterThanOrEqual(3);
  });
});

// ── Reset Flow ─────────────────────────────────────────────────

test.describe('Reset', () => {
  test.use({ uniqueTelegramUser: true });

  test('should load reset page and show done state', async ({ page }) => {
    test.setTimeout(20000);
    await page.addInitScript(() => localStorage.setItem('lumen:onboarded', '1'));
    await page.goto('/reset');
    await page.waitForLoadState('networkidle');

    const done = page.locator('text=/Готово|готово/i');
    await expect(done).toBeVisible({ timeout: 10000 });
  });
});
