// AI_HEADER
// module: M-TEST-E2E-AUTH-HELPER
// wave: W-TEST-3
// purpose: Real Telegram auth for E2E tests — no mocks, real HMAC via Python script

import { execSync } from 'child_process';
import { request } from '@playwright/test';

const SCRIPT_PATH = 'scripts/generate-telegram-test-initdata.py';

export interface TelegramAuthContext {
  /** Full initData query string (for URL hash) */
  initDataRaw: string;
  /** URL hash fragment to append to page URL */
  urlHash: string;
  /** Session cookie name */
  cookieName: string;
  /** Session cookie value (set after backend auth) */
  cookieValue: string;
  /** Authenticated user ID */
  userId: string;
}

/**
 * Generate valid Telegram initData using the project's Python script.
 * The script reads TELEGRAM_BOT_TOKEN from .env.production and
 * produces a fresh HMAC-signed initData string.
 */
function generateInitData(): { initDataRaw: string; urlHash: string } {
  const stdout = execSync(`python3 ${SCRIPT_PATH}`, {
    encoding: 'utf-8',
    cwd: process.cwd(),
    timeout: 5000,
  });

  let initDataRaw = '';
  let urlHash = '';

  for (const line of stdout.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    if (trimmed.startsWith('#tgWebAppData=')) {
      urlHash = trimmed;
    } else if (initDataRaw === '' && trimmed.includes('=')) {
      initDataRaw = trimmed;
    }
  }

  if (!initDataRaw) {
    throw new Error(`Failed to parse initData from script output:\n${stdout}`);
  }

  return { initDataRaw, urlHash };
}

/**
 * Set up real Telegram authentication for an E2E test page.
 *
 * This does TWO things:
 * 1. Fetches /api/auth/telegram directly to get a session cookie
 * 2. Returns the URL hash with tgWebAppData so the page can load
 *    with proper Telegram WebView context
 *
 * Usage:
 *   const auth = await setupTelegramAuth(apiBaseUrl);
 *   await page.goto('/day/today' + auth.urlHash);
 */
export async function setupTelegramAuth(
  apiBaseUrl: string = 'http://127.0.0.1:8000'
): Promise<TelegramAuthContext> {
  const { initDataRaw, urlHash } = generateInitData();

  // Step 1: Call the real /api/auth/telegram endpoint to get a session
  const apiContext = await request.newContext();
  const authResp = await apiContext.post(`${apiBaseUrl}/api/auth/telegram`, {
    data: { initData: initDataRaw },
    headers: { 'Content-Type': 'application/json' },
  });

  if (!authResp.ok()) {
    const body = await authResp.text();
    throw new Error(`Telegram auth failed: ${authResp.status()} ${body}`);
  }

  const { userId } = await authResp.json();

  // Extract session cookie
  const setCookie = authResp.headers()['set-cookie'];
  const cookieMatch = setCookie?.match(/(\w+)=([^;]+)/);
  const cookieName = cookieMatch?.[1] ?? 'grace_session_v2';
  const cookieValue = cookieMatch?.[2] ?? '';

  await apiContext.dispose();

  return { initDataRaw, urlHash, cookieName, cookieValue, userId };
}

/**
 * Set cookies on a Playwright page for an already-authenticated session.
 * Use after setupTelegramAuth to seed the browser with the session cookie.
 */
export async function applyAuthCookies(
  page: import('@playwright/test').Page,
  auth: TelegramAuthContext,
  domain: string = 'localhost'
) {
  await page.context().addCookies([
    {
      name: auth.cookieName,
      value: auth.cookieValue,
      domain,
      path: '/',
      httpOnly: true,
      secure: false,
      sameSite: 'Lax',
    },
  ]);
}
