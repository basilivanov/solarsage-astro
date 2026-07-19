// AI_HEADER
// module: M-TEST-E2E-FIXTURES
// wave: W-TEST-3
// purpose: Playwright fixtures with real Telegram auth (no mocks, real HMAC)

import { test as base, expect, request, type Page } from '@playwright/test';
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

function deriveTelegramUserId(projectName: string, testId: string, repeatEachIndex: number): number {
  // Run-scoped salt keeps ids unique across runs so reruns never collide and
  // the acceptance cleanup adapter can find exactly this run's users.
  const runSalt = process.env.E2E_RUN_SALT || process.env.GITHUB_RUN_ID || 'local';
  const digest = createHash('sha256')
    .update(`${runSalt}\0${projectName}\0${testId}\0${repeatEachIndex}`)
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
      ? deriveTelegramUserId(testInfo.project.name, testInfo.testId, testInfo.repeatEachIndex)
      : undefined;
    const initData = generateInitData(userId);

    await seedSessionCookie(page, initData, baseURL);

    // Inject Telegram WebApp globals BEFORE page loads any scripts.
    // The Telegram SDK (telegram-web-app.js) normally sets this up,
    // but in E2E we populate it directly with real initData.
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

    await use(page);
  },
});

export { expect };

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
  const cityInput = page.getByTestId('city-picker-input');
  await cityInput.fill('Москва');
  const cityResult = page.getByTestId('city-picker-suggestion').first();
  await expect(cityResult).toBeVisible({ timeout: 5000 });
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

  // Landed on the day page for real
  await page.waitForURL('**/day/**', { timeout: 15000 });
  expect(page.url()).toMatch(/\/day\/(today|\d{4}-\d{2}-\d{2})/);
  await expect(page.getByTestId('today-screen')).toBeVisible({ timeout: 15000 });
  const onboarded = await page.evaluate(() => localStorage.getItem('lumen:onboarded'));
  expect(['true', '1']).toContain(onboarded);
}
