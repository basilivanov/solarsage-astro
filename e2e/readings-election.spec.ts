// AI_HEADER
// module: M-TEST-E2E-READINGS-ELECTION
// wave: W-TEST-ELECTION
// purpose: Real-API E2E (no route interception): election search lifecycle on the real stack.

// START_MODULE_CONTRACT: M-TEST-E2E-READINGS-ELECTION
// purpose: Prove the election reading card presence and the real election search
//   lifecycle (lunar window -> election engine -> LLM narrative) with structural assertions.
// owns:
//   - e2e/readings-election.spec.ts
// inputs: real Telegram HMAC auth via e2e/fixtures.ts, real API/LLM endpoints.
// outputs: Playwright pass/fail.
// dependencies: e2e/fixtures.ts (test, expect, completeOnboarding, grantReferralAccess).
// side_effects: Creates real users, real referral claim, real election search request with LLM output.
// emitted_logs: none.
// invariants:
//   - No page.route/mock/interception; structural assertions only.
// failure_policy: any failed expectation fails the test.
// END_MODULE_CONTRACT: M-TEST-E2E-READINGS-ELECTION

// START_MODULE_MAP: M-TEST-E2E-READINGS-ELECTION
// public_entrypoints:
//   - Playwright test runner
// semantic_blocks:
//   - ELECTION_FLOW: submit -> processing -> result view -> calendar & hero -> quota check
// END_MODULE_MAP: M-TEST-E2E-READINGS-ELECTION

import { test, expect, completeOnboarding, grantReferralAccess } from './fixtures';

test.describe('Readings + election — Real API', () => {
  test.use({ uniqueTelegramUser: true });

  test('lists election card and completes a real election search lifecycle', async ({ page, browser, baseURL }, testInfo) => {
    test.setTimeout(240000);

    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    // Grant 14-day referral access -> weekly-free credit
    await grantReferralAccess(page, browser, baseURL, testInfo);
    await completeOnboarding(page);

    // --- 1. Readings List: card visible ---
    await page.goto('/readings');
    await expect(page.getByTestId('readings-screen')).toHaveAttribute('data-state', 'ready', { timeout: 15000 });
    await expect(page.getByTestId('readings-card-election')).toBeVisible();

    // --- 2. Election Screen: open election screen ---
    await page.getByTestId('readings-card-election').click();
    const electionScreen = page.getByTestId('election-screen');
    await expect(electionScreen).toHaveAttribute('data-state', 'ready', { timeout: 15000 });
    await expect(electionScreen).toHaveAttribute('data-access-state', 'unlocked');

    // Quota proof: credit available
    const quota = await page.evaluate(async () => {
      const res = await fetch('/api/election/quota', {
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) throw new Error(`GET /api/election/quota failed: ${res.status}`);
      return res.json();
    });
    expect(quota.weeklyFreeAvailable || quota.bonusCredits > 0 || quota.paidCredits > 0).toBe(true);

    // --- 3. Form interaction: category & subcategory ---
    await page.getByTestId('election-category-card-relations').click();
    await expect(page.getByTestId('election-subcategories')).toBeVisible();
    await page.getByTestId('election-sub-chip-date').click();

    const customInput = page.getByTestId('election-custom-input');
    await expect(customInput).toHaveValue('Свидание');

    // Submit form with default 2-week window
    const submitBtn = page.getByTestId('election-submit-btn');
    await expect(submitBtn).toBeEnabled({ timeout: 5000 });
    await submitBtn.click();

    // --- 4. Processing & Auto-navigation to Detail Page ---
    await page.waitForURL(/\/readings\/election\/[0-9a-f-]{36}$/, { timeout: 30000 });
    const detailPage = page.getByTestId('election-detail-page');

    // Wait for done state (real sidecar + engine + LLM narrative, up to 120s)
    await expect(detailPage).toHaveAttribute('data-state', 'done', { timeout: 120000 });
    await expect(page.getByTestId('election-result-view')).toBeVisible();

    // Structural assertions on result view
    await expect(page.getByTestId('election-hero')).toBeVisible();

    // Expand "Почему этот день?" and verify narrative text presence
    const expandBtn = page.getByTestId('election-hero').getByRole('button', { name: /Почему этот день/i });
    await expandBtn.click();
    await expect(page.getByTestId('election-hero')).toContainText('Астрологически:');
    await expect(page.getByTestId('election-hero')).toContainText('Простыми словами:');

    // Calendar assertion: visible and contains best/good marked days
    await expect(page.getByTestId('election-calendar')).toBeVisible();
    const calendarDays = page.getByTestId('election-calendar').locator('[data-testid^="election-calendar-day-"]');
    const dayCount = await calendarDays.count();
    expect(dayCount).toBeGreaterThan(0);

    // --- 5. Quota check after search ---
    const searchId = page.url().match(/\/readings\/election\/([0-9a-f-]{36})$/)![1];
    expect(searchId).toBeTruthy();

    await page.getByTestId('election-reset-btn').click();
    await expect(electionScreen).toHaveAttribute('data-state', 'ready', { timeout: 15000 });

    const quotaAfter = await page.evaluate(async () => {
      const res = await fetch('/api/election/quota', {
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) throw new Error(`GET /api/election/quota failed: ${res.status}`);
      return res.json();
    });
    // Weekly-free credit consumed (or total available decremented)
    expect(quotaAfter.weeklyFreeAvailable).toBe(false);
  });
});
