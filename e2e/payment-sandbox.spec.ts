// AI_HEADER
// module: M-TEST-E2E-PAYMENT-SANDBOX
// wave: W-TEST-3
// purpose: YooKassa SANDBOX release proof in the existing release harness:
//   real catalog prices and initial month/year subscription checkout with
//   the official no-3DS success card plus idempotent webhook fulfillment.
//   No second harness, no route interception, no mocked billing.

// START_MODULE_CONTRACT: M-TEST-E2E-PAYMENT-SANDBOX
// purpose: Prove the real billing path end-to-end in test mode: catalog from
//   the real API, provider checkout via the product UI, provider-verified
//   fulfillment via the existing webhook endpoint (which itself does the
//   authenticated provider GET), and exact month/year subscription
//   semantics. The natal_full_report purchase proof lives in
//   e2e/natal-report.spec.ts (exactly one real natal generation per run).
// owns:
//   - e2e/payment-sandbox.spec.ts
// inputs: real Telegram HMAC auth (fixtures), YooKassa sandbox stack
//   (YOOKASSA_ENABLED=true, MODE=test, recurrent=false, loopback webhook
//   allowlist in APP_ENV=test), official public no-3DS test card.
// outputs: Playwright pass/fail.
// dependencies: e2e/fixtures.ts (test, expect, completeOnboarding,
//   createAuthedUserPage).
// side_effects: TWO subscription sandbox payments (month and year on
//   separate users); local webhook events delivered to the ephemeral API
//   (the runner cannot receive the provider's ingress webhook); no
//   confirmation URLs or provider ids in logs.
// emitted_logs: none.
// invariants:
//   - No page.route/mock/interception; the checkout runs on the real
//     provider page; fulfillment is decided only by the API after the
//     authenticated provider GET.
//   - One official success card variant (no card matrix, no failure cards).
//   - Recurrent job stays off (YOOKASSA_RECURRENT_ENABLED=false).
// failure_policy: any failed expectation fails the test.
// END_MODULE_CONTRACT: M-TEST-E2E-PAYMENT-SANDBOX

// START_MODULE_MAP: M-TEST-E2E-PAYMENT-SANDBOX
// public_entrypoints:
//   - Playwright test runner
// semantic_blocks:
//   - CATALOG: real catalog prices from the API
//   - SUBSCRIPTION: month/year checkout + idempotent fulfillment
// END_MODULE_MAP: M-TEST-E2E-PAYMENT-SANDBOX

import {
  test,
  expect,
  completeOnboarding,
  createAuthedUserPage,
  shimTelegramOpenLink,
  paySandboxCheckout,
  deliverWebhookUntilFulfilled,
  deliverWebhookOnce,
  authedJson,
} from './fixtures';

const DAY_MS = 24 * 60 * 60 * 1000;


test.describe('YooKassa sandbox release proof — real API (no mocks)', () => {
  test('catalog exposes the exact launch prices from the real API', async ({ page }) => {
    await page.goto('/onboarding');
    await completeOnboarding(page);

    const data = await authedJson(page, '/api/payment/products');
    const bySlug = Object.fromEntries(
      (data.products as Array<{ slug: string; priceKopecks: number; currency: string; isActive: boolean }>)
        .map((p) => [p.slug, p]),
    );
    expect(bySlug.subscription_month.priceKopecks).toBe(9900);
    expect(bySlug.subscription_year.priceKopecks).toBe(99900);
    expect(bySlug.natal_full_report.priceKopecks).toBe(39900);
    expect(bySlug.subscription_month.currency).toBe('RUB');
    expect(bySlug.subscription_month.isActive).toBe(true);
    expect(bySlug.subscription_year.isActive).toBe(true);
    expect(bySlug.natal_full_report.isActive).toBe(true);
  });

  test('month subscription: checkout, idempotent webhook, exact 30-day active semantics', async ({ page }) => {
    test.setTimeout(240_000);
    await page.goto('/onboarding');
    await completeOnboarding(page);

    await page.goto('/profile');
    await expect(page.getByTestId('access-card-primary')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('access-card-recurring-consent')).toContainText('99 ₽');

    const startResponsePromise = page.waitForResponse(
      (r) => r.url().includes('/api/payment/subscription/start') && r.status() === 200,
      { timeout: 30000 },
    );
    const popupPromise = page.waitForEvent('popup', { timeout: 60000 });
    // Shim on the TARGET page, immediately before the CTA (it never
    // survives a navigation).
    await shimTelegramOpenLink(page);
    await page.getByTestId('access-card-primary').click();

    const startResponse = await startResponsePromise;
    const startBody = await startResponse.json();
    const providerPaymentId = startBody.providerPaymentId as string;
    expect(providerPaymentId).toBeTruthy();

    // The checkout popup stays OPEN until the webhook proof completes:
    // closing it right after "Оплатить" could cancel the provider request.
    const popup = await popupPromise;
    let status1;
    try {
      await paySandboxCheckout(popup);
      // Fulfillment: local event -> endpoint's own authenticated provider GET.
      await deliverWebhookUntilFulfilled(providerPaymentId);
      status1 = await authedJson(page, '/api/payment/subscription/status');
    } finally {
      await popup.close();
    }
    expect(status1.status).toBe('active');
    expect(status1.productSlug).toBe('subscription_month');
    expect(status1.priceKopecks).toBe(9900);
    expect(status1.renewing).toBe(true);
    expect(status1.cancelable).toBe(true);
    expect(status1.nextChargeAt).toBeTruthy();
    const periodEnd1 = Date.parse(status1.currentPeriodEnd);
    const accessUntil1 = Date.parse(status1.accessUntil);
    expect(periodEnd1 - Date.now()).toBeGreaterThan(28 * DAY_MS);
    expect(periodEnd1 - Date.now()).toBeLessThan(32 * DAY_MS);
    // access ledger end (date) vs current_period_end (datetime): same
    // boundary day, never an exact-timestamp equality.
    expect(Math.abs(accessUntil1 - periodEnd1)).toBeLessThan(1.5 * DAY_MS);

    // Idempotency: the SAME event again -> 200 and NOT a second grant.
    expect(await deliverWebhookOnce(providerPaymentId)).toBe(200);
    const status2 = await authedJson(page, '/api/payment/subscription/status');
    expect(status2.status).toBe('active');
    expect(status2.accessUntil).toBe(status1.accessUntil);
    expect(status2.currentPeriodEnd).toBe(status1.currentPeriodEnd);
  });

  test('year subscription: checkout and exact 365-day semantics for a separate user', async ({ browser, baseURL }, testInfo) => {
    test.setTimeout(240_000);
    // baseURL comes from the fixtures (never undefined): the context needs it
    // for relative navigation AND the correct session-cookie domain.
    const { context, page: yearPage } = await createAuthedUserPage(browser, baseURL, testInfo, 'year');
    try {
      await yearPage.goto('/onboarding');
      await completeOnboarding(yearPage);

      await yearPage.goto('/profile');
      await expect(yearPage.getByTestId('access-card-secondary')).toBeVisible({ timeout: 15000 });
      await expect(yearPage.getByTestId('access-card-recurring-consent')).toContainText('999 ₽');

      const startResponsePromise = yearPage.waitForResponse(
        (r) => r.url().includes('/api/payment/subscription/start') && r.status() === 200,
        { timeout: 30000 },
      );
      const popupPromise = yearPage.waitForEvent('popup', { timeout: 60000 });
      // Shim on the TARGET page, immediately before the CTA.
      await shimTelegramOpenLink(yearPage);
      await yearPage.getByTestId('access-card-secondary').click();

      const startBody = await (await startResponsePromise).json();
      const providerPaymentId = startBody.providerPaymentId as string;
      expect(providerPaymentId).toBeTruthy();

      // Popup stays open until the webhook proof completes.
      const popup = await popupPromise;
      let status;
      try {
        await paySandboxCheckout(popup);
        await deliverWebhookUntilFulfilled(providerPaymentId);
        status = await authedJson(yearPage, '/api/payment/subscription/status');
      } finally {
        await popup.close();
      }
      expect(status.status).toBe('active');
      expect(status.productSlug).toBe('subscription_year');
      expect(status.priceKopecks).toBe(99900);
      expect(status.renewing).toBe(true);
      expect(status.cancelable).toBe(true);
      const periodEnd = Date.parse(status.currentPeriodEnd);
      expect(periodEnd - Date.now()).toBeGreaterThan(360 * DAY_MS);
      expect(periodEnd - Date.now()).toBeLessThan(370 * DAY_MS);
      expect(Math.abs(Date.parse(status.accessUntil) - periodEnd)).toBeLessThan(1.5 * DAY_MS);
    } finally {
      await context.close();
    }
  });
});
