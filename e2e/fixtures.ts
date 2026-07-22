// AI_HEADER
// module: M-TEST-E2E-FIXTURES
// wave: W-TEST-3
// purpose: Playwright fixtures with real Telegram auth (no mocks, real HMAC);
//   createAuthedUserPage adds isolated extra users for multi-user flows
//   (same run-salted ids, same cleanup ledger, no duplicated crypto);
//   PAYMENT_SANDBOX_HELPERS adds the shared YooKassa sandbox proof helpers
//   (openLink shim, official no-3DS card fill, local webhook delivery,
//   authenticated JSON reads) for the billing release specs

import { test as base, expect, request, type Browser, type BrowserContext, type Page, type TestInfo } from '@playwright/test';
import { execFileSync } from 'child_process';
import { createHash } from 'crypto';
import { appendFileSync } from 'fs';

const SCRIPT_PATH = 'scripts/generate-telegram-test-initdata.py';
const SESSION_COOKIE_NAME = 'grace_session_v2';
const CREATED_USERS_FILE = process.env.E2E_CREATED_USERS_FILE || '/tmp/solarsage-e2e-created-users.jsonl';

type E2EOptions = {
  uniqueTelegramUser: boolean;
};

/**
 * Generate fresh, HMAC-valid Telegram initData.
 * Calls the Python script that uses the real TELEGRAM_BOT_TOKEN.
 */
function generateInitData(userId?: number): string {
  const args = [SCRIPT_PATH];
  if (userId !== undefined) {
    args.push(`--user-id=${userId}`);
  }

  const stdout = execFileSync('python3', args, {
    encoding: 'utf-8',
    cwd: process.cwd(),
    timeout: 5000,
  });

  for (const line of stdout.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    // Skip the URL hash line, return the raw initData
    if (trimmed.includes('tgWebAppData')) continue;
    if (trimmed.includes('=')) return trimmed;
  }

  throw new Error(`Failed to parse initData from script output:\n${stdout}`);
}

export function deriveTelegramUserId(projectName: string, testId: string, repeatEachIndex: number, retry: number): number {
  // Run-scoped salt keeps ids unique across runs so reruns never collide and
  // the acceptance cleanup adapter can find exactly this run's users. The
  // retry index is part of the deterministic input so a retried test never
  // reuses the already-onboarded user of the failed attempt.
  const runSalt = process.env.E2E_RUN_SALT || process.env.GITHUB_RUN_ID || 'local';
  const digest = createHash('sha256')
    .update(`${runSalt}\0${projectName}\0${testId}\0${repeatEachIndex}\0${retry}`)
    .digest();

  const tgUserId = 1_000_000_000 + (digest.readUInt32BE(0) % 1_000_000_000);
  appendFileSync(
    CREATED_USERS_FILE,
    JSON.stringify({ tg_user_id: tgUserId, test_id: testId, run_salt: runSalt }) + '\n',
  );
  return tgUserId;
}

async function seedSessionCookie(page: Page, initData: string, baseURL?: string) {
  const apiBaseURL = (process.env.E2E_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
  const apiContext = await request.newContext();

  try {
    const authResponse = await apiContext.post(`${apiBaseURL}/api/auth/telegram`, {
      data: { initData },
      headers: { 'Content-Type': 'application/json' },
    });

    if (!authResponse.ok()) {
      throw new Error(
        `Telegram auth failed: ${authResponse.status()} ${await authResponse.text()}`
      );
    }

    const setCookie = authResponse.headers()['set-cookie'] || '';
    const cookieValue = setCookie.match(new RegExp(`${SESSION_COOKIE_NAME}=([^;]+)`))?.[1];
    if (!cookieValue) {
      throw new Error(
        `Telegram auth ${authResponse.status()} did not return ${SESSION_COOKIE_NAME} cookie`
      );
    }

    const cookieDomain = new URL(baseURL || 'http://localhost:3000').hostname;
    await page.context().addCookies([
      {
        name: SESSION_COOKIE_NAME,
        value: cookieValue,
        domain: cookieDomain,
        path: '/',
        httpOnly: true,
        secure: false,
        sameSite: 'Lax',
      },
    ]);
  } finally {
    await apiContext.dispose();
  }
}

/**
 * Inject the Telegram WebApp globals with real initData BEFORE any app script
 * runs (the Telegram SDK normally does this). Shared by the fixture page and
 * createAuthedUserPage so the crypto/DOM contract exists exactly once.
 */
async function injectTelegramWebApp(page: Page, initData: string) {
  await page.addInitScript((data: string) => {
    (window as any).Telegram = {
      WebApp: {
        initData: data,
        initDataUnsafe: {},
        ready: () => {},
        expand: () => {},
        close: () => {},
        platform: 'web',
        version: '9.5',
        colorScheme: 'light',
        themeParams: {},
        isExpanded: true,
        viewportHeight: 812,
        viewportStableHeight: 812,
        headerColor: '#ffffff',
        backgroundColor: '#ffffff',
        MainButton: {
          text: '',
          color: '',
          textColor: '',
          isVisible: false,
          isActive: true,
          isProgressVisible: false,
          setText: () => {},
          onClick: () => {},
          offClick: () => {},
          show: () => {},
          hide: () => {},
          enable: () => {},
          disable: () => {},
          showProgress: () => {},
          hideProgress: () => {},
        },
        BackButton: {
          isVisible: false,
          onClick: () => {},
          offClick: () => {},
          show: () => {},
          hide: () => {},
        },
        HapticFeedback: {
          impactOccurred: () => {},
          notificationOccurred: () => {},
          selectionChanged: () => {},
        },
        onEvent: () => {},
        offEvent: () => {},
        sendData: () => {},
        switchInlineQuery: () => {},
        openLink: () => {},
        openTelegramLink: () => {},
        openInvoice: () => {},
        showPopup: () => {},
        showAlert: () => {},
        showConfirm: () => {},
      },
    };
  }, initData);
}

/**
 * Create an additional isolated browser context with its own unique Telegram
 * user (same run-salted id derivation + cleanup ledger + real HMAC auth as the
 * main fixture). Used by multi-user flows (e.g. referral deep-link). The
 * caller owns closing the returned context.
 */
export async function createAuthedUserPage(
  browser: Browser,
  baseURL: string | undefined,
  testInfo: TestInfo,
  idSuffix: string,
): Promise<{ context: BrowserContext; page: Page; tgUserId: number }> {
  const tgUserId = deriveTelegramUserId(
    testInfo.project.name,
    `${testInfo.testId}#${idSuffix}`,
    testInfo.repeatEachIndex,
    testInfo.retry,
  );
  const initData = generateInitData(tgUserId);
  const context = await browser.newContext(baseURL ? { baseURL } : {});
  const page = await context.newPage();
  await seedSessionCookie(page, initData, baseURL);
  await injectTelegramWebApp(page, initData);
  return { context, page, tgUserId };
}

/**
 * Grant the main fixture user real 14-day access through the genuine
 * referral deep-link path: an isolated grantor user is created (same harness
 * primitives), then the page is opened with the tgWebAppStartParam query so
 * the real use-telegram-auth auto-claim fires. Waits for the typed access
 * read-back to prove the bonus. No manual API/DB mutation. Returns the
 * grantor's tg id.
 */
export async function grantReferralAccess(
  page: Page,
  browser: Browser,
  baseURL: string | undefined,
  testInfo: TestInfo,
): Promise<number> {
  const grantor = await createAuthedUserPage(browser, baseURL, testInfo, 'grantor');
  const grantorId = grantor.tgUserId;
  await grantor.context.close();
  await page.goto(`/?tgWebAppStartParam=${encodeURIComponent(String(grantorId))}`);
  await expect(async () => {
    const access = await page.evaluate(async () => {
      const res = await fetch('/api/access', {
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) throw new Error(`GET /api/access failed: ${res.status}`);
      return res.json();
    });
    expect(access.referralDaysLeft ?? 0).toBeGreaterThanOrEqual(13);
  }).toPass({ timeout: 30000 });
  return grantorId;
}

/**
 * Extended Playwright test with real Telegram WebApp auth.
 *
 * Every test gets:
 * - Fresh initData generated with real HMAC
 * - window.Telegram.WebApp populated with that initData
 * - The app's useTelegramAuth hook sends initData → /api/auth/telegram
 * - Backend verifies HMAC, returns real session cookie
 * - All subsequent API calls use the real session
 */
export const test = base.extend<E2EOptions>({
  uniqueTelegramUser: [true, { option: true }],
  page: async ({ page, baseURL, uniqueTelegramUser }, use, testInfo) => {
    const userId = uniqueTelegramUser
      ? deriveTelegramUserId(testInfo.project.name, testInfo.testId, testInfo.repeatEachIndex, testInfo.retry)
      : undefined;
    const initData = generateInitData(userId);

    await seedSessionCookie(page, initData, baseURL);

    // Inject Telegram WebApp globals BEFORE page loads any scripts.
    // The Telegram SDK (telegram-web-app.js) normally sets this up,
    // but in E2E we populate it directly with real initData.
    await injectTelegramWebApp(page, initData);

    await use(page);
  },
});

export { expect };

// START_BLOCK: TODAY_TERMINAL_WAIT
// START_FUNCTION_CONTRACT: F-M-TEST-E2E-FIXTURES.waitForTodayState
// purpose: Block until the day page reaches a TERMINAL public state on the
//   today-screen root. loading/error are never success; a test must not
//   proceed (or finish) while a day request is still in flight.
// inputs: page — Playwright page; expected — 'ready' | 'locked' |
//   'terminal' (either ready or locked); timeout — default 60000 (observed
//   /api/day range in candidate runs: 8.3–51.4s first pass).
// returns: void; Playwright expect throws on timeout.
// side_effects: none (read-only DOM polling via expect).
// error_behavior: throws when the terminal state is not reached in time.
// END_FUNCTION_CONTRACT: F-M-TEST-E2E-FIXTURES.waitForTodayState
export async function waitForTodayState(
  page: Page,
  expected: 'ready' | 'locked' | 'terminal' = 'terminal',
  timeout = 60000,
): Promise<void> {
  const screen = page.getByTestId('today-screen');
  if (expected === 'terminal') {
    await expect(screen).toHaveAttribute('data-state', /^(ready|locked)$/, { timeout });
  } else {
    await expect(screen).toHaveAttribute('data-state', expected, { timeout });
  }
}
// END_BLOCK: TODAY_TERMINAL_WAIT

/**
 * Helper: wait for auth to complete and return to a specific page.
 * After auth, the home page redirects based on onboarding state.
 */
export async function waitForAuthComplete(page: Page, targetPath: string = '/day/today') {
  // Navigate to home - auth runs on mount, then redirect logic fires
  await page.goto('/');
  // Wait for the redirect to complete (either day/today or onboarding)
  await page.waitForURL(`**${targetPath}**`, { timeout: 15000 }).catch(() => {});
  // Wait for the page to settle
  await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
  // Small delay for React hydration
  await page.waitForTimeout(1000);
}

/**
 * Complete the REAL onboarding flow end-to-end (birth data + city + gender).
 * Used by specs that must not skip on the onboarding redirect: no early
 * returns, no conditional passes — the profile is created for real.
 * Mirrors e2e/onboarding-real.spec.ts step-for-step.
 */
export async function completeOnboarding(page: Page) {
  // Welcome: continue
  await page.locator('button:has-text("Продолжить")').first().click();

  // Birth date/time (accessible field names)
  await page.getByRole('textbox', { name: 'День' }).fill('15');
  await page.getByRole('textbox', { name: 'Месяц' }).fill('01');
  await page.getByRole('textbox', { name: 'Год' }).fill('1990');
  await page.getByRole('textbox', { name: 'Часы' }).fill('12');
  await page.getByRole('textbox', { name: 'Минуты' }).fill('00');

  const step2Next = page.getByRole('button', { name: 'Далее' });
  await expect(step2Next).toBeEnabled({ timeout: 5000 });
  await step2Next.click();

  // Birth place: real geo search, first result, then "Сейчас живу там же"
  await expect(page.getByText('Место рождения')).toBeVisible({ timeout: 5000 });
  // Scoped to the birth-city wrapper: StepPlace can render TWO pickers
  // (birth + current) when "same as birth" is unchecked.
  const birthCityField = page.getByTestId('onboarding-birth-city-field');
  const cityInput = birthCityField.getByTestId('city-picker-input');
  await cityInput.fill('Москва');
  const cityResult = birthCityField.getByTestId('city-picker-suggestion').first();
  // Real GeoNames latency is 2.8–5.1s; debounce (300ms) + network needs headroom.
  await expect(cityResult).toBeVisible({ timeout: 15000 });
  await cityResult.click();
  await page.getByText(/сейчас живу там же/i).click();

  const step3Next = page.getByRole('button', { name: 'Далее' });
  await expect(step3Next).toBeEnabled({ timeout: 5000 });
  await step3Next.click();

  // Birthday city step (must not be skipped)
  await expect(page.getByRole('heading', { name: /день рождения/i })).toBeVisible({ timeout: 5000 });
  const step4Next = page.getByRole('button', { name: 'Далее' });
  await expect(step4Next).toBeEnabled({ timeout: 5000 });
  await step4Next.click();

  // Gender step
  await expect(page.getByRole('heading', { name: /мужчина или женщина/i })).toBeVisible({ timeout: 5000 });
  await page.getByRole('button', { name: 'Мужчина' }).click();

  // Done step: finish
  await expect(page.getByText('Готово', { exact: true })).toBeVisible({ timeout: 5000 });
  const finishBtn = page.getByRole('button', { name: /Открыть мой день|Открыть/i });
  await expect(finishBtn).toBeEnabled({ timeout: 5000 });
  await finishBtn.click();

  // Landed on the day page for real — wait for the TERMINAL public state
  // (ready|locked), never just the loading branch, so no test proceeds while
  // the first day request is still in flight.
  await page.waitForURL('**/day/**', { timeout: 15000 });
  expect(page.url()).toMatch(/\/day\/(today|\d{4}-\d{2}-\d{2})/);
  await waitForTodayState(page, 'terminal');
  const onboarded = await page.evaluate(() => localStorage.getItem('lumen:onboarded'));
  expect(['true', '1']).toContain(onboarded);
}


// ############################################################################
// START_BLOCK: PAYMENT_SANDBOX_HELPERS
// Small shared helpers for the YooKassa sandbox release proof (specs only —
// no second harness): official no-3DS card fill, local webhook delivery and
// authenticated JSON reads. Never logs confirmation URLs or provider ids.

const API_BASE = (process.env.E2E_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const WEBHOOK_URL = `${API_BASE}/api/payment/webhook/yookassa`;

// Official public YooKassa sandbox card: SUCCESS WITHOUT 3-D Secure per the
// official YooKassa test-card table (5555 5555 5555 4444; note that
// 5555 5555 5555 4477 explicitly HAS 3-D Secure and is NOT used here).
const SANDBOX_TEST_CARD = {
  number: '5555 5555 5555 4444',
  expiryMonth: '12',
  expiryYear: '30',
  cvc: '123',
};

// START_FUNCTION_CONTRACT: F-M-TEST-E2E-FIXTURES.shimTelegramOpenLink
// purpose: Make the Telegram stub's openLink behave like the real one
//   (opens an external page) for provider-checkout flows; never a mock of
//   app code.
// inputs: page — the TARGET page right before the CTA (the patch never
//   survives a navigation).
// returns: void.
// side_effects: evaluates window.Telegram.WebApp.openLink in the page.
// emitted_logs: none.
// error_behavior: no-op when the Telegram stub is absent.
// END_FUNCTION_CONTRACT: F-M-TEST-E2E-FIXTURES.shimTelegramOpenLink
export async function shimTelegramOpenLink(page: Page) {
  // The fixtures' Telegram stub ships openLink as a no-op (there is no real
  // Telegram shell in CI). The faithful test-only behavior of the real shim
  // is opening an external page — exactly what production openLink does.
  // This is NOT a mock of app code: the product flow runs unchanged. Apply
  // it on the TARGET page right before the CTA (it never survives a
  // navigation).
  await page.evaluate(() => {
    const tg = (window as any).Telegram?.WebApp;
    if (tg) {
      tg.openLink = (url: string) => {
        window.open(url, '_blank');
      };
    }
  });
}

// START_FUNCTION_CONTRACT: F-M-TEST-E2E-FIXTURES.paySandboxCheckout
// purpose: Pay the real YooKassa sandbox checkout with the official public
//   no-3DS success card. Handles BOTH normal states: the card form already
//   open OR the method chooser with the stable provider selector
//   data-qa="bankcard-show-other-cards-payment-option" (chooser is NOT
//   unconditionally required). The real card form has SPLIT expiry inputs
//   (expiry-month/expiry-year/security-code, all data-qa'd in the provider
//   trace) — they are filled separately and every field is verified to
//   actually hold the value (fail-closed) BEFORE the single pay click; a
//   bounded pre-submit fill-and-verify stabilization (up to 3 short
//   attempts) covers provider-controlled inputs dropping the first fill.
//   A chrome-error page is reported as an EXTERNAL provider navigation
//   failure (never masked as a missing option). Never logs URL/order/
//   provider ids.
// inputs: popup — the provider checkout page (kept open by the caller).
// returns: void (throws on missing card form / pay button, an incomplete
//   fill, or an external navigation failure).
// side_effects: real provider interaction (sandbox payment).
// emitted_logs: none.
// error_behavior: throws Error (no partial payment attempts, no retries).
// END_FUNCTION_CONTRACT: F-M-TEST-E2E-FIXTURES.paySandboxCheckout
export async function paySandboxCheckout(popup: Page) {
  const cardNumberSel =
    'input[name="card-number"], input[autocomplete="cc-number"], input[name="cardNumber"], input[name="card"], input[placeholder*="0000"]';
  const expiryMonthSel =
    'input[data-qa="field-expiry-month"], input[autocomplete="cc-exp-month"], input[name="expiry-month"]';
  const expiryYearSel =
    'input[data-qa="field-expiry-year"], input[autocomplete="cc-exp-year"], input[name="expiry-year"]';
  const combinedExpirySel =
    'input[name="expiry"], input[name="expiryDate"], input[placeholder*="ММ"], input[placeholder*="MM"], input[autocomplete="cc-exp"]';
  const cvcSel =
    'input[data-qa-bankcard-field-name="security-code"], input[name="security-code"], input[autocomplete="cc-csc"], input[name="cvc"], input[name="cvv"], input[placeholder*="CVC"], input[placeholder*="CVV"]';

  const cardNumberVisible = async () => {
    for (const frame of popup.frames()) {
      const visible = await frame
        .locator(cardNumberSel)
        .first()
        .isVisible()
        .catch(() => false);
      if (visible) return frame;
    }
    return null;
  };

  // 1) Bounded state loop: the card form is checked on EVERY iteration
  //    (the real trace shows it appearing ~360 ms AFTER the chooser click).
  //    The chooser is clicked AT MOST once, and a successful chooser click
  //    never breaks the loop — the bounded wait for the form continues.
  //    The semantic exact-text fallback is probed independently whenever
  //    the primary data-qa selector is not found. A chrome-error page is an
  //    EXTERNAL provider navigation failure — reported as itself.
  let formFrame: import('@playwright/test').Frame | null = null;
  let chooserClicked = false;
  for (let attempt = 0; attempt < 12 && !formFrame; attempt += 1) {
    if (popup.url().startsWith('chrome-error://')) {
      throw new Error('external provider navigation failure: checkout failed to load');
    }
    formFrame = await cardNumberVisible();
    if (formFrame) break;

    const chooser = popup.locator('[data-qa="bankcard-show-other-cards-payment-option"]').first();
    if (await chooser.isVisible().catch(() => false)) {
      if (!chooserClicked) {
        await chooser.click({ timeout: 3000 }).catch(() => {});
        chooserClicked = true;
        // No break: the form needs time to render — keep waiting below.
      }
    } else if (!chooserClicked) {
      // Primary selector not found: independent semantic exact-text probe.
      for (const frame of popup.frames()) {
        const option = frame.getByText(/^(New card|Новая карта|Банковская карта)$/).first();
        if (await option.isVisible().catch(() => false)) {
          await option.click({ timeout: 2000 }).catch(() => {});
          chooserClicked = true;
          break;
        }
      }
    }
    await popup.waitForTimeout(1000);
  }
  if (!formFrame) {
    throw new Error('sandbox checkout: neither card form nor bank-card chooser appeared');
  }

  // 2) Fill. The real checkout uses SPLIT expiry fields (trace-proven
  //    data-qa field-expiry-month / field-expiry-year / security-code);
  //    a combined field is only a fallback. Split shape is detected
  //    BEFORE any fill: split mode ONLY when BOTH split fields exist;
  //    exactly one is an incomplete split form — fail closed with an
  //    empty form, never fill/fallback blindly.
  const monthField = formFrame.locator(expiryMonthSel).first();
  const yearField = formFrame.locator(expiryYearSel).first();
  const monthCount = await monthField.count();
  const yearCount = await yearField.count();
  const splitMode = monthCount > 0 && yearCount > 0;
  if (monthCount + yearCount === 1) {
    throw new Error('sandbox checkout: incomplete split expiry form (only one of month/year present)');
  }

  const cardNumber = formFrame.locator(cardNumberSel).first();
  const cvcField = formFrame.locator(cvcSel).first();
  const combinedField = formFrame.locator(combinedExpirySel).first();

  // FAIL-CLOSED verification of every expected value (masked,
  // provider-controlled inputs may silently drop a fill — a pre-submit
  // form race observed in CI 29912821828, never a payment failure).
  const verifyAll = async (): Promise<string[]> => {
    const mismatches: string[] = [];
    if (!(await cardNumber.inputValue()).replace(/\D/g, '').endsWith('4444')) {
      mismatches.push('cardNumber');
    }
    if (splitMode) {
      if ((await monthField.inputValue()).trim() !== SANDBOX_TEST_CARD.expiryMonth) {
        mismatches.push('expiryMonth');
      }
      if ((await yearField.inputValue()).trim() !== SANDBOX_TEST_CARD.expiryYear) {
        mismatches.push('expiryYear');
      }
    } else if (
      !(await combinedField.inputValue())
        .replace(/\D/g, '')
        .startsWith(`${SANDBOX_TEST_CARD.expiryMonth}${SANDBOX_TEST_CARD.expiryYear}`)
    ) {
      mismatches.push('expiry');
    }
    if ((await cvcField.inputValue()).replace(/\D/g, '') !== SANDBOX_TEST_CARD.cvc) {
      mismatches.push('cvc');
    }
    return mismatches;
  };

  // Bounded fill-and-verify stabilization (pre-submit only): refill the
  // mismatched fields and re-read, up to 3 short attempts. Pay is clicked
  // exactly once and ONLY after ALL fields hold simultaneously.
  let verified = false;
  let lastMismatches: string[] = [];
  for (let attempt = 0; attempt < 3 && !verified; attempt += 1) {
    lastMismatches = await verifyAll();
    if (lastMismatches.length === 0) {
      verified = true;
      break;
    }
    for (const field of lastMismatches) {
      if (field === 'cardNumber') {
        await cardNumber.fill(SANDBOX_TEST_CARD.number);
      } else if (field === 'expiryMonth') {
        await monthField.fill(SANDBOX_TEST_CARD.expiryMonth);
      } else if (field === 'expiryYear') {
        await yearField.fill(SANDBOX_TEST_CARD.expiryYear);
      } else if (field === 'expiry') {
        await combinedField.fill(`${SANDBOX_TEST_CARD.expiryMonth}/${SANDBOX_TEST_CARD.expiryYear}`);
      } else if (field === 'cvc') {
        await cvcField.fill(SANDBOX_TEST_CARD.cvc);
      }
    }
    await popup.waitForTimeout(400);
  }
  if (!verified) {
    throw new Error(
      `sandbox checkout: form fields did not stabilize before pay (${lastMismatches.join(', ')})`,
    );
  }

  // 4) Single pay click (bounded search across frames).
  for (let attempt = 0; attempt < 5; attempt += 1) {
    for (const frame of popup.frames()) {
      const payButton = frame.getByRole('button', { name: /оплатить|заплатить|pay/i }).first();
      try {
        await payButton.click({ timeout: 3000 });
        return;
      } catch {
        // keep searching
      }
    }
  }
  throw new Error('sandbox checkout pay button not found');
}

// START_FUNCTION_CONTRACT: F-M-TEST-E2E-FIXTURES.deliverWebhookUntilFulfilled
// purpose: Deliver the minimal REAL payment.succeeded event to the local
//   webhook endpoint until the endpoint (via its own authenticated provider
//   GET) fulfills it; bounded redelivery of the SAME event while the
//   provider payment is not final (retryable 500).
// inputs: providerPaymentId, timeoutMs (default 90s).
// returns: void (throws on timeout with the last HTTP status).
// side_effects: POST /api/payment/webhook/yookassa from the runner loopback.
// emitted_logs: none.
// error_behavior: throws Error on timeout.
// END_FUNCTION_CONTRACT: F-M-TEST-E2E-FIXTURES.deliverWebhookUntilFulfilled
export async function deliverWebhookUntilFulfilled(providerPaymentId: string, timeoutMs = 90000): Promise<void> {
  // The runner cannot receive the provider's ingress webhook, so the spec
  // delivers the minimal REAL event to the existing local endpoint — which
  // itself performs the authenticated provider GET before granting anything.
  // While the sandbox payment is not final yet the endpoint answers a
  // retryable 500; the bounded loop redelivers the SAME event (which is also
  // the first half of the idempotency proof).
  const deadline = Date.now() + timeoutMs;
  const ctx = await request.newContext();
  try {
    for (;;) {
      const resp = await ctx.post(WEBHOOK_URL, {
        data: { type: 'notification', event: 'payment.succeeded', object: { id: providerPaymentId } },
      });
      const status = resp.status();
      await resp.dispose();
      if (status === 200) return;
      if (Date.now() > deadline) {
        throw new Error(`webhook was not fulfilled within ${timeoutMs}ms (last status ${status})`);
      }
      await new Promise((resolve) => setTimeout(resolve, 3000));
    }
  } finally {
    await ctx.dispose();
  }
}

// START_FUNCTION_CONTRACT: F-M-TEST-E2E-FIXTURES.deliverWebhookOnce
// purpose: Deliver the minimal REAL payment.succeeded event exactly once
//   and return the endpoint HTTP status (200 expected, incl. idempotent
//   repeats). Request context is always disposed.
// inputs: providerPaymentId.
// returns: HTTP status code.
// side_effects: POST /api/payment/webhook/yookassa from the runner loopback.
// emitted_logs: none.
// error_behavior: request context disposed in finally.
// END_FUNCTION_CONTRACT: F-M-TEST-E2E-FIXTURES.deliverWebhookOnce
export async function deliverWebhookOnce(providerPaymentId: string): Promise<number> {
  const ctx = await request.newContext();
  try {
    const resp = await ctx.post(WEBHOOK_URL, {
      data: { type: 'notification', event: 'payment.succeeded', object: { id: providerPaymentId } },
    });
    const status = resp.status();
    await resp.dispose();
    return status;
  } finally {
    await ctx.dispose();
  }
}

// START_FUNCTION_CONTRACT: F-M-TEST-E2E-FIXTURES.authedJson
// purpose: Authenticated GET against the ephemeral API returning parsed
//   JSON; fails the test on any non-200.
// inputs: page (carries the session cookies), path (API path).
// returns: parsed JSON body.
// side_effects: one API request.
// emitted_logs: none.
// error_behavior: expect-failure on non-200.
// END_FUNCTION_CONTRACT: F-M-TEST-E2E-FIXTURES.authedJson
export async function authedJson(page: Page, path: string) {
  const resp = await page.request.get(`${API_BASE}${path}`);
  expect(resp.status(), `GET ${path} failed with ${resp.status()}`).toBe(200);
  return resp.json();
}
// END_BLOCK: PAYMENT_SANDBOX_HELPERS
