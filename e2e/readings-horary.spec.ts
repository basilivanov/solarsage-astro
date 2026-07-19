// AI_HEADER
// module: M-TEST-E2E-READINGS-HORARY
// wave: W-TEST-3
// purpose: Real-API E2E (no route interception): readings list contract and
//   the horary create → answer → read → history path on the real stack
//   (P1-6 slice).

// START_MODULE_CONTRACT: M-TEST-E2E-READINGS-HORARY
// purpose: Prove the readings screen contract and the real horary question
//   lifecycle (weekly-free credit under active referral access) with
//   structural assertions only.
// owns:
//   - e2e/readings-horary.spec.ts
// inputs: real Telegram HMAC auth via e2e/fixtures.ts (uniqueTelegramUser),
//   real API/LLM endpoints.
// outputs: Playwright pass/fail; created users tracked for the acceptance
//   cleanup adapter via E2E_CREATED_USERS_FILE (fixtures default).
// dependencies: e2e/fixtures.ts (test, expect, completeOnboarding,
//   grantReferralAccess, createAuthedUserPage).
// side_effects: Creates two real users (main + referral grantor), one real
//   referral claim (14-day access), and one real horary question with a real
//   LLM answer. No delete/archive operation exists in the product and none
//   is invented here.
// emitted_logs: none.
// invariants:
//   - No page.route/mock/interception; no conditional early returns or
//     expect(true) passes; no LLM-text-only assertions.
// failure_policy: any failed expectation fails the test.
// END_MODULE_CONTRACT: M-TEST-E2E-READINGS-HORARY

// START_MODULE_MAP: M-TEST-E2E-READINGS-HORARY
// public_entrypoints:
//   - Playwright test runner
// semantic_blocks:
//   - READINGS_LIST: readings screen available cards contract
//   - HORARY_FLOW: submit → answer view → API read-back → history
// END_MODULE_MAP: M-TEST-E2E-READINGS-HORARY

import { test, expect, completeOnboarding, grantReferralAccess } from './fixtures';

test.describe('Readings + horary — Real API (P1-6)', () => {
  test.use({ uniqueTelegramUser: true });

  test('lists reading types and completes a real horary question lifecycle', async ({ page, browser, baseURL }, testInfo) => {
    test.setTimeout(240000);

    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    // Fresh users intentionally have NO horary weekly credit (no access
    // ledger). Grant REAL 14-day access through the genuine referral
    // deep-link flow — never a direct POST/DB seed.
    await grantReferralAccess(page, browser, baseURL, testInfo);
    await completeOnboarding(page);

    // --- READINGS_LIST: the real readings screen contract ---
    await page.goto('/readings');
    await expect(page.getByTestId('readings-screen')).toHaveAttribute('data-state', 'ready', { timeout: 15000 });
    await expect(page.getByTestId('readings-card-horary')).toBeVisible();
    await expect(page.getByTestId('readings-card-natal')).toBeVisible();

    // --- HORARY_FLOW: open horary via the card (real navigation) ---
    await page.getByTestId('readings-card-horary').click();
    const horaryScreen = page.getByTestId('horary-screen');
    await expect(horaryScreen).toHaveAttribute('data-state', 'ready', { timeout: 15000 });
    // Active referral access creates the weekly-free credit → unlocked form
    // (a fresh user WITHOUT an access ledger is locked by design).
    await expect(horaryScreen).toHaveAttribute('data-access-state', 'unlocked');

    // Quota proof (typed API read-back): real access granted a spendable credit.
    const quota = await page.evaluate(async () => {
      const res = await fetch('/api/horary/quota', {
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) throw new Error(`GET /api/horary/quota failed: ${res.status}`);
      return res.json();
    });
    expect(quota.weeklyFreeAvailable || quota.bonusCredits > 0 || quota.paidCredits > 0).toBe(true);

    // Submit a real question (category + text + profile-confirmed moment).
    await page.getByTestId('horary-category-career').click();
    await page.getByTestId('horary-question-input').fill('Стоит ли мне менять работу в этом месяце?');
    const submitButton = page.getByTestId('horary-submit-btn');
    await expect(submitButton).toBeEnabled({ timeout: 5000 });
    await submitButton.click();

    // The real answer arrives asynchronously; the app auto-navigates to it.
    await page.waitForURL(/\/readings\/horary\/[0-9a-f-]{36}$/, { timeout: 180000 });
    await expect(page.getByTestId('horary-answer-view')).toBeVisible({ timeout: 30000 });
    // Structural proof of the answer, never LLM-text-dependent.
    await expect(page.getByTestId('horary-verdict-card')).toBeVisible({ timeout: 30000 });
    const questionId = page.url().match(/\/readings\/horary\/([0-9a-f-]{36})$/)![1];

    // Read path (real API): the stored question is answered.
    const question = await page.evaluate(async (id) => {
      const res = await fetch(`/api/horary/questions/${id}`, {
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) throw new Error(`GET /api/horary/questions/${id} failed: ${res.status}`);
      return res.json();
    }, questionId);
    expect(question.status).toBe('answered');

    // History path: the answered question is listed on the horary screen.
    await page.goto('/readings/horary');
    await expect(page.getByTestId('horary-screen')).toHaveAttribute('data-state', 'ready', { timeout: 15000 });
    const historyCard = page.getByTestId('horary-history-section').getByTestId('horary-question-card').first();
    await expect(historyCard).toBeVisible({ timeout: 10000 });
  });
});
