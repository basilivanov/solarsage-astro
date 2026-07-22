// AI_HEADER
// module: M-TEST-E2E-NATAL-REPORT
// wave: W-TEST-3
// purpose: Real-API E2E (no route interception): natal preview contract,
//   the product's own /readings/natal/generating UI path, and the ready
//   report view (P1-6 slice).

// START_MODULE_CONTRACT: M-TEST-E2E-NATAL-REPORT
// purpose: Prove the natal preview ready contract, the real sandbox purchase
//   of the full report (399 ₽, one official no-3DS success card, idempotent
//   webhook fulfillment via the endpoint's own authenticated provider GET),
//   and the real generation path exactly as the product exposes it: the
//   generating route starts generation, polls and redirects to the ready
//   report. Exactly ONE real natal generation exists (here, not duplicated).
// owns:
//   - e2e/natal-report.spec.ts
// inputs: real Telegram HMAC auth via e2e/fixtures.ts (uniqueTelegramUser),
//   real API/LLM endpoints. Requires NATAL_REPORT_ENABLED=true in the
//   ephemeral E2E stack (production flag stays off).
// outputs: Playwright pass/fail; created users tracked for the acceptance
//   cleanup adapter via E2E_CREATED_USERS_FILE (fixtures default).
// dependencies: e2e/fixtures.ts (test, expect, completeOnboarding,
//   shimTelegramOpenLink, paySandboxCheckout, deliverWebhookUntilFulfilled,
//   deliverWebhookOnce, authedJson); YooKassa sandbox stack
//   (YOOKASSA_ENABLED=true, MODE=test, recurrent=false).
// side_effects: ONE sandbox natal_full_report purchase (399 ₽) + local
//   webhook events to the ephemeral API; then ONE real natal report
//   (synchronous LLM generation) through the product's own generation
//   route; an API read-back is used only as additional proof, never instead
//   of the UI path.
// emitted_logs: none.
// invariants:
//   - No page.route/mock/interception; no direct API mutation bypassing the
//     UI generation route; no conditional early returns or expect(true)
//     passes; no LLM-text-only assertions.
// failure_policy: any failed expectation fails the test.
// END_MODULE_CONTRACT: M-TEST-E2E-NATAL-REPORT

// START_MODULE_MAP: M-TEST-E2E-NATAL-REPORT
// public_entrypoints:
//   - Playwright test runner
// semantic_blocks:
//   - PREVIEW: natal preview ready structural contract
//   - PURCHASE: sandbox 399 ₽ checkout + idempotent webhook entitlement
//   - GENERATE_AND_VIEW: product generating route → ready report screen
// END_MODULE_MAP: M-TEST-E2E-NATAL-REPORT

import {
  test,
  expect,
  completeOnboarding,
  shimTelegramOpenLink,
  paySandboxCheckout,
  deliverWebhookUntilFulfilled,
  deliverWebhookOnce,
  authedJson,
} from './fixtures';

// Shared budget for the synchronous natal generation path: the real LLM
// generates 8 sections inline and latency varies widely across candidates
// (observed 79s–360+s); the URL wait and the outer test budget must cover it
// exactly once — a timed-out first pass is a real signal, not a retry case.
const NATAL_GENERATION_WAIT_MS = 600_000;
const NATAL_TEST_TIMEOUT_MS = 720_000;

test.describe('Natal preview + full report — Real API (P1-6)', () => {
  test.use({ uniqueTelegramUser: true });

  test('renders preview and generates a real full report view', async ({ page }) => {
    test.setTimeout(NATAL_TEST_TIMEOUT_MS);

    await page.addInitScript(() => {
      localStorage.clear();
      sessionStorage.clear();
    });

    await page.goto('/onboarding');
    await completeOnboarding(page);

    // --- PREVIEW: real calculated preview, structural assertions ---
    await page.goto('/readings/natal');
    const preview = page.getByTestId('natal-preview-screen');
    await expect(preview).toHaveAttribute('data-state', 'ready', { timeout: 30000 });
    await expect(page.getByTestId('natal-calculation-depth')).toBeVisible();
    await expect(page.getByTestId('natal-spheres')).toBeVisible();
    await expect(page.getByTestId('natal-planets')).toBeVisible();

    // --- PURCHASE (sandbox): the real 399 ₽ YooKassa checkout BEFORE
    // generation. With YOOKASSA_ENABLED=true the generating route requires
    // the delivered entitlement (402 otherwise), so the proof buys the report
    // through the product CTA first — one official no-3DS success card, then
    // the minimal real event delivered twice to the local webhook endpoint
    // (the endpoint itself does the authenticated provider GET; the second
    // delivery proves idempotency).
    const cta = page.getByTestId('natal-full-report-cta-button');
    await expect(cta).toHaveAttribute('data-state', 'ready');
    await expect(cta).toContainText('399 ₽');

    const startResponsePromise = page.waitForResponse(
      (r) => r.url().includes('/api/payment/purchase/start') && r.status() === 200,
      { timeout: 30000 },
    );
    const popupPromise = page.waitForEvent('popup', { timeout: 60000 });
    // Shim on the TARGET page, immediately before the CTA (it never
    // survives a navigation).
    await shimTelegramOpenLink(page);
    await cta.click();

    const startBody = await (await startResponsePromise).json();
    const providerPaymentId = startBody.providerPaymentId as string;
    const purchaseId = startBody.purchaseId as string;
    expect(providerPaymentId).toBeTruthy();
    expect(purchaseId).toBeTruthy();

    // The checkout popup stays OPEN until the webhook proof completes:
    // closing it right after "Оплатить" could cancel the provider request.
    const popup = await popupPromise;
    try {
      await paySandboxCheckout(popup);
      await deliverWebhookUntilFulfilled(providerPaymentId);
      // Idempotency: the SAME event again -> 200 and NOT a second grant.
      expect(await deliverWebhookOnce(providerPaymentId)).toBe(200);
    } finally {
      await popup.close();
    }

    const purchase = await authedJson(page, `/api/payment/purchase/${purchaseId}`);
    // Delivered entitlement, never a weaker "not pending".
    expect(purchase.status).toBe('delivered');

    // --- GENERATE_AND_VIEW: the product's own generation route ---
    // The app's purchase-status poll navigates to /readings/natal/generating
    // after the confirmed fulfillment; the route then polls and redirects to
    // /readings/natal/<id> on READY.
    await page.waitForURL(/\/readings\/natal\/generating/, { timeout: 120000 });
    await page.waitForURL(/\/readings\/natal\/[0-9a-f-]{36}$/, { timeout: NATAL_GENERATION_WAIT_MS });
    const reportId = page.url().match(/\/readings\/natal\/([0-9a-f-]{36})$/)![1];

    // The ready report renders through the real UI on the unified root.
    const reportScreen = page.getByTestId('natal-report-screen');
    await expect(reportScreen).toHaveAttribute('data-state', 'ready', { timeout: 30000 });
    // Structural proof: the chapter list exists (8 canonical sections).
    const chapterButtons = reportScreen.locator('main button');
    await expect(chapterButtons.first()).toBeVisible({ timeout: 15000 });
    expect(await chapterButtons.count()).toBeGreaterThanOrEqual(8);

    // Additional API read-back proof (never instead of the UI path).
    const report = await page.evaluate(async (id) => {
      const res = await fetch(`/api/natal/report/${id}`, {
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) throw new Error(`GET /api/natal/report/${id} failed: ${res.status}`);
      return res.json();
    }, reportId);
    expect(report.status).toBe('READY');
    expect(report.sections.length).toBeGreaterThanOrEqual(8);
  });
});
