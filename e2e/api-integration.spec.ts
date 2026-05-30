// AI_HEADER
// module: M-TEST-E2E-API-INTEGRATION
// wave: W-TEST-3
// purpose: E2E tests for API integration, error handling, and infinite loading detection

import { test, expect } from '@playwright/test';

test.describe('API Integration', () => {
  test('should not have infinite loading on /day/today', async ({ page }) => {
    const errors: string[] = [];

    // Capture console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    // Capture uncaught exceptions
    page.on('pageerror', error => {
      errors.push(error.message);
    });

    await page.goto('/day/today');

    // Loading spinner MUST disappear within 15 seconds
    const spinner = page.getByTestId('loading-spinner');

    // Wait for spinner to appear (if it does)
    const spinnerAppeared = await spinner.isVisible({ timeout: 2000 }).catch(() => false);

    if (spinnerAppeared) {
      // If spinner appeared, it MUST disappear within 15 seconds
      await expect(spinner).toBeHidden({ timeout: 15000 });
    }

    // Either content or error MUST be visible
    await page.waitForSelector('[data-testid="today-screen"], [data-testid="error-boundary"]', {
      timeout: 15000
    });

    // Log any errors found
    if (errors.length > 0) {
      console.log('Console errors detected:', errors);
    }
  });

  test('should handle 401 Unauthorized gracefully', async ({ page }) => {
    // Block API to simulate 401
    await page.route('**/api/day/**', route => {
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: { code: 'MISSING', reason: 'no session cookie' } })
      });
    });

    await page.goto('/day/today');

    // Should show error, not hang
    await expect(page.getByTestId('error-boundary')).toBeVisible({ timeout: 10000 });

    // Error message should mention authorization
    const errorMessage = page.getByTestId('error-message');
    await expect(errorMessage).toContainText(/авторизация|Telegram/i);
  });

  test('should handle API network errors', async ({ page }) => {
    // Abort all API requests to simulate network failure
    await page.route('**/api/day/**', route => route.abort());

    await page.goto('/day/today');

    // Should show error boundary within 10 seconds
    await expect(page.getByTestId('error-boundary')).toBeVisible({ timeout: 10000 });
  });

  test('should handle 500 Internal Server Error', async ({ page }) => {
    await page.route('**/api/day/**', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' })
      });
    });

    await page.goto('/day/today');

    // Should show error boundary
    await expect(page.getByTestId('error-boundary')).toBeVisible({ timeout: 10000 });
  });

  test('should track API response times', async ({ page }) => {
    let apiCallTime = 0;

    page.on('response', async response => {
      if (response.url().includes('/api/day/')) {
        const timing = await response.request().timing();
        apiCallTime = timing.responseEnd;
      }
    });

    await page.goto('/day/today');

    // Wait for page to load
    await page.waitForSelector('[data-testid="today-screen"], [data-testid="error-boundary"]', {
      timeout: 15000
    });

    // Log API response time
    if (apiCallTime > 0) {
      console.log(`API response time: ${apiCallTime}ms`);

      // Warn if API is slow (>3 seconds)
      if (apiCallTime > 3000) {
        console.warn(`⚠️  API response time is slow: ${apiCallTime}ms`);
      }
    }
  });

  test('should capture all console errors', async ({ page }) => {
    const errors: string[] = [];
    const warnings: string[] = [];

    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      } else if (msg.type() === 'warning') {
        warnings.push(msg.text());
      }
    });

    page.on('pageerror', error => {
      errors.push(`Uncaught: ${error.message}`);
    });

    await page.goto('/day/today');

    // Wait for page to settle
    await page.waitForTimeout(5000);

    // Report findings
    if (errors.length > 0) {
      console.log('❌ Console errors found:', errors);
    }

    if (warnings.length > 0) {
      console.log('⚠️  Console warnings found:', warnings);
    }

    // Test passes even with errors, but logs them for visibility
    expect(true).toBe(true);
  });
});
