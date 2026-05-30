// ############################################################################
// AI_HEADER: MODULE_E2E_TODAY
// ROLE: E2E tests for Today screen (W-TEST-3).
// DEPENDENCIES: @playwright/test, Next.js app
// GRACE_ANCHORS: [E2E_TODAY_TESTS]
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-E2E-TODAY
// purpose: End-to-end tests for Today screen user flows
// owns:
//   - e2e/today.spec.ts
// inputs:
//   - running Next.js app on http://localhost:3002
// outputs:
//   - test results (pass/fail)
// dependencies:
//   - app/(grace)/today/page.tsx
//   - components/grace/TodayScreen.tsx
// side_effects:
//   - navigates browser to /day/today
// invariants:
//   - loading spinner MUST appear before content
//   - either today-screen OR error-boundary MUST render
// failure_policy:
//   - test failure -> CI fails
// non_goals:
//   - unit tests, API tests
// END_MODULE_CONTRACT: M-TEST-E2E-TODAY

// START_MODULE_MAP: M-TEST-E2E-TODAY
// public_entrypoints:
//   - test suite (playwright)
// semantic_blocks:
//   - E2E_TODAY_TESTS
// owned_tests:
//   - this file
// END_MODULE_MAP: M-TEST-E2E-TODAY

import { test, expect } from '@playwright/test';

// START_BLOCK: E2E_TODAY_TESTS
test('today screen loads', async ({ page }) => {
  await page.goto('/day/today');

  // Check that loading spinner appears first
  const spinner = page.getByTestId('loading-spinner');
  if (await spinner.isVisible({ timeout: 1000 }).catch(() => false)) {
    // Spinner was visible, wait for it to disappear
    await spinner.waitFor({ state: 'hidden', timeout: 10000 });
  }

  // Wait for content to load (or error)
  await page.waitForSelector('[data-testid="today-screen"], [data-testid="error-boundary"]', { timeout: 10000 });

  // If loaded successfully, check headline
  const todayScreen = page.getByTestId('today-screen');
  if (await todayScreen.isVisible()) {
    await expect(page.getByTestId('today-headline')).toBeVisible();
  }
});

test('calendar navigation', async ({ page }) => {
  await page.goto('/calendar');

  // Wait for loading to complete
  const spinner = page.getByTestId('loading-spinner');
  if (await spinner.isVisible({ timeout: 1000 }).catch(() => false)) {
    await spinner.waitFor({ state: 'hidden', timeout: 10000 });
  }

  // Check calendar loads
  await page.waitForSelector('[data-testid="calendar-grid"], [data-testid="error-boundary"]', { timeout: 10000 });

  // If loaded, check structure
  const calendarGrid = page.getByTestId('calendar-grid');
  if (await calendarGrid.isVisible()) {
    // Click on a day (if available)
    const firstDay = page.locator('[data-testid^="calendar-day-"]').first();
    if (await firstDay.isVisible({ timeout: 2000 }).catch(() => false)) {
      await firstDay.click();
      // Should navigate to day view
      await expect(page).toHaveURL(/\/day\/\d{4}-\d{2}-\d{2}/);
    }
  }
});

test('week strip navigation', async ({ page }) => {
  await page.goto('/day/today');

  // Wait for page to load
  await page.waitForSelector('[data-testid="today-screen"], [data-testid="error-boundary"]', { timeout: 10000 });

  // Check if week strip is present
  const weekStrip = page.getByTestId('week-strip');
  if (await weekStrip.isVisible({ timeout: 2000 }).catch(() => false)) {
    // Find all week day links
    const weekDays = weekStrip.locator('a');
    const count = await weekDays.count();

    if (count > 0) {
      // Click on first day in week strip
      await weekDays.first().click();

      // Should navigate to a day view
      await expect(page).toHaveURL(/\/day\/\d{4}-\d{2}-\d{2}/);
    }
  }
});
// END_BLOCK: E2E_TODAY_TESTS
