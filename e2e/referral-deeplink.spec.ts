// AI_HEADER
// module: M-TEST-E2E-REFERRAL-DEEPLINK
// wave: W-TEST-3
// purpose: Real-API E2E (no route interception): referral deep-link
//   auto-claim — invitee opens the app with tgWebAppStartParam and the real
//   frontend auth flow claims the bonus exactly once (P1-6 slice).

// START_MODULE_CONTRACT: M-TEST-E2E-REFERRAL-DEEPLINK
// purpose: Prove the referral deep-link user path end-to-end: the referrer's
//   invite code from the real API, the invitee's real auto-claim during
//   auth, and idempotency across a reload — all without manual API mutation.
// owns:
//   - e2e/referral-deeplink.spec.ts
// inputs: real Telegram HMAC auth via e2e/fixtures.ts (uniqueTelegramUser
//   referrer + createAuthedUserPage invitee), real API endpoints.
// outputs: Playwright pass/fail; both created users are tracked for the
//   acceptance cleanup adapter via E2E_CREATED_USERS_FILE.
// dependencies: e2e/fixtures.ts (test, expect, completeOnboarding,
//   createAuthedUserPage).
// side_effects: Creates two real users and one real referral claim
//   (14-day access bonus on both sides).
// emitted_logs: none.
// invariants:
//   - No page.route/mock/interception; no early returns, skip/fixme or
//     expect(true) passes; claims happen only through the real frontend
//     auto-claim, never a manual POST from the test.
// failure_policy: any failed expectation fails the test.
// END_MODULE_CONTRACT: M-TEST-E2E-REFERRAL-DEEPLINK

// START_MODULE_MAP: M-TEST-E2E-REFERRAL-DEEPLINK
// public_entrypoints:
//   - Playwright test runner
// semantic_blocks:
//   - REFERRER: onboarding + real invite code proof
//   - INVITEE_CLAIM: deep-link auto-claim + access proof + idempotent reload
// END_MODULE_MAP: M-TEST-E2E-REFERRAL-DEEPLINK

import { test, expect, completeOnboarding, createAuthedUserPage } from './fixtures';

test.describe('Referral deep-link auto-claim — Real API (P1-6)', () => {
  test.use({ uniqueTelegramUser: true });

  test('invitee auto-claims via tgWebAppStartParam and the claim is idempotent', async ({ page, browser, baseURL }, testInfo) => {
    test.setTimeout(240000);

    // --- REFERRER: real onboarding, then the real invite code ---
    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    await page.goto('/onboarding');
    await completeOnboarding(page);

    const readReferralInfo = async () => {
      return page.evaluate(async () => {
        const res = await fetch('/api/referral', {
          credentials: 'include',
          headers: { Accept: 'application/json' },
        });
        if (!res.ok) throw new Error(`GET /api/referral failed: ${res.status}`);
        return res.json();
      });
    };

    const before = await readReferralInfo();
    expect(before.totalInvited).toBe(0);
    const inviteCode = String(before.inviteCode);
    expect(inviteCode).toMatch(/^\d+$/);
    expect(before.inviteUrl).toContain(`startapp=${inviteCode}`);

    // --- INVITEE_CLAIM: isolated second user opened via the deep link ---
    const invitee = await createAuthedUserPage(browser, baseURL, testInfo, 'invitee');
    try {
      expect(String(invitee.tgUserId)).not.toBe(inviteCode);
      const inviteePage = invitee.page;
      await inviteePage.addInitScript(() => {
        localStorage.clear();
        sessionStorage.clear();
      });
      // The deep-link query is present at first auth, so the real
      // use-telegram-auth auto-claim fires the actual POST /api/referral/claim.
      await inviteePage.goto(`/?tgWebAppStartParam=${encodeURIComponent(inviteCode)}`);
      await completeOnboarding(inviteePage);

      // Invitee-side typed proof: the referral bonus is granted (14 days).
      const access = await inviteePage.evaluate(async () => {
        const res = await fetch('/api/access', {
          credentials: 'include',
          headers: { Accept: 'application/json' },
        });
        if (!res.ok) throw new Error(`GET /api/access failed: ${res.status}`);
        return res.json();
      });
      expect(access.user).toBe('trial');
      expect(access.referralDaysLeft).toBeGreaterThanOrEqual(13);

      // Referrer-side proof: exactly one invite recorded.
      const after = await readReferralInfo();
      expect(after.totalInvited).toBe(1);

      // Idempotency: opening the same deep link again must not double-claim
      // (backend ALREADY_CLAIMED; no manual API mutation from the test).
      await inviteePage.goto(`/?tgWebAppStartParam=${encodeURIComponent(inviteCode)}`);
      await expect(inviteePage.getByTestId('today-screen')).toBeVisible({ timeout: 15000 });
      const afterReload = await readReferralInfo();
      expect(afterReload.totalInvited).toBe(1);
    } finally {
      await invitee.context.close();
    }
  });
});
