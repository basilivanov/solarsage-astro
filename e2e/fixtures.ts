// AI_HEADER
// module: M-TEST-E2E-FIXTURES
// wave: W-TEST-3
// purpose: Playwright fixtures with real Telegram auth (no mocks, real HMAC);
//   createAuthedUserPage adds isolated extra users for multi-user flows
//   (same run-salted ids, same cleanup ledger, no duplicated crypto)

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
//   'terminal' (either ready or locked); timeout — default 30000 (real
//   /api/day takes 8.3–18.8s in candidate runs).
// returns: void; Playwright expect throws on timeout.
// side_effects: none (read-only DOM polling via expect).
// error_behavior: throws when the terminal state is not reached in time.
// END_FUNCTION_CONTRACT: F-M-TEST-E2E-FIXTURES.waitForTodayState
export async function waitForTodayState(
  page: Page,
  expected: 'ready' | 'locked' | 'terminal' = 'terminal',
  timeout = 30000,
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
