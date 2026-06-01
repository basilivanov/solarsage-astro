// AI_HEADER
// module: M-TEST-E2E-FIXTURES
// wave: W-TEST-3
// purpose: Playwright fixtures with real Telegram auth (no mocks, real HMAC)

import { test as base, expect, type Page } from '@playwright/test';
import { execSync } from 'child_process';

const SCRIPT_PATH = 'scripts/generate-telegram-test-initdata.py';

/**
 * Generate fresh, HMAC-valid Telegram initData.
 * Calls the Python script that uses the real TELEGRAM_BOT_TOKEN.
 */
function generateInitData(): string {
  const stdout = execSync(`python3 ${SCRIPT_PATH}`, {
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
export const test = base.extend({
  page: async ({ page }, use) => {
    const initData = generateInitData();

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
