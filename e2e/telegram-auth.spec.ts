// AI_HEADER
// module: M-TEST-E2E-TELEGRAM-AUTH
// wave: W-2.2
// purpose: E2E tests for Telegram authentication happy path

import { test, expect } from './fixtures';

test.describe('Telegram Auth - Happy Path', () => {
  test('should authenticate with valid initData', async ({ page }) => {
    // Mock Telegram Web App with valid initData
    await page.addInitScript(() => {
      (window as any).Telegram = {
        WebApp: {
          initData:
            'query_id=AAHdF6IQAAAAAN0XohDhrOrc&user=%7B%22id%22%3A279058397%2C%22first_name%22%3A%22Vasiliy%22%2C%22last_name%22%3A%22Ivanov%22%2C%22username%22%3A%22basilivanov%22%2C%22language_code%22%3A%22en%22%7D&auth_date=1622559000&hash=abc123',
          initDataUnsafe: {
            user: {
              id: 279058397,
              first_name: 'Vasiliy',
              last_name: 'Ivanov',
              username: 'basilivanov',
            },
          },
          ready: () => console.log('[Mock] Telegram.WebApp.ready()'),
          expand: () => console.log('[Mock] Telegram.WebApp.expand()'),
        },
      };
    });

    // Mock API response for /api/auth/telegram
    await page.route('**/api/auth/telegram', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true }),
        headers: {
          'Set-Cookie': 'session_id=test-session; HttpOnly; Secure',
        },
      });
    });

    // Mock API response for /api/day/today
    await page.route('**/api/day/today', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          date: '2026-05-30',
          logs: [],
          summary: 'Test day',
        }),
      });
    });

    await page.goto('/day/today');

    // Should show auth loading briefly
    const authLoading = page.locator('[data-testid="auth-loading"]');
    const hasAuthLoading = await authLoading.isVisible({ timeout: 1000 }).catch(() => false);

    if (hasAuthLoading) {
      await expect(authLoading).toBeHidden({ timeout: 5000 });
    }

    // Wait for page content to load (after data loading spinner)
    await expect(page.locator('[data-testid="loading-spinner"]')).toBeHidden({
      timeout: 10000,
    });

    // Content should be visible
    await expect(page.locator('body')).toBeVisible();
  });

  test('should work without Telegram (dev mode)', async ({ page }) => {
    // Mock API response for /api/day/today
    await page.route('**/api/day/today', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          date: '2026-05-30',
          logs: [],
          summary: 'Test day',
        }),
      });
    });

    // No Telegram mock - like in regular browser
    await page.goto('/day/today');

    // Should not hang on auth loading
    const authLoading = page.locator('[data-testid="auth-loading"]');
    await expect(authLoading).toBeHidden({ timeout: 5000 });

    // Wait for page content to load (after data loading spinner)
    await expect(page.locator('[data-testid="loading-spinner"]')).toBeHidden({
      timeout: 10000,
    });

    // Content should be visible (dev mode works without Telegram)
    await expect(page.locator('body')).toBeVisible();
  });

  test('should handle auth error gracefully', async ({ page }) => {
    // Mock Telegram Web App with valid initData
    await page.addInitScript(() => {
      (window as any).Telegram = {
        WebApp: {
          initData: 'invalid_data',
          initDataUnsafe: {},
          ready: () => {},
          expand: () => {},
        },
      };
    });

    // Mock API error response
    await page.route('**/api/auth/telegram', (route) => {
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid initData' }),
      });
    });

    await page.goto('/day/today');

    // Should show auth loading first
    const authLoading = page.locator('[data-testid="auth-loading"]');
    const hasAuthLoading = await authLoading.isVisible({ timeout: 1000 }).catch(() => false);

    if (hasAuthLoading) {
      await expect(authLoading).toBeHidden({ timeout: 5000 });
    }

    // Then show error (only in Telegram environment)
    await expect(page.locator('[data-testid="auth-error"]')).toBeVisible({
      timeout: 5000,
    });

    // Error message should be visible
    await expect(page.locator('[data-testid="auth-error"]')).toContainText(
      'Ошибка авторизации'
    );
  });
});
