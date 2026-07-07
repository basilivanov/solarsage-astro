// Audit-only Playwright script for Wave 09 evidence capture.
// Uses real Telegram auth fixtures. Do not import into product code.

import { chromium } from 'playwright';
import { execFileSync } from 'child_process';
import { mkdirSync, writeFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ARTIFACTS_DIR = resolve(__dirname, 'artifacts', 'rework-01');
const SCRIPT_PATH = resolve(__dirname, '..', '..', '..', 'scripts', 'generate-telegram-test-initdata.py');

const ROUTES = [
  { path: '/day/2026-07-05', name: 'day-2026-07-05', sentinel: 'today-screen' },
  { path: '/calendar', name: 'calendar', sentinel: 'calendar-screen' },
  { path: '/profile', name: 'profile', sentinel: 'profile-screen' },
  { path: '/readings', name: 'readings', sentinel: 'readings-screen' },
  { path: '/readings/horary', name: 'horary', sentinel: 'horary-screen' },
  { path: '/readings/natal', name: 'natal', sentinel: 'natal-preview-screen' },
];

function generateInitData() {
  const stdout = execFileSync('python3', [SCRIPT_PATH], {
    encoding: 'utf-8',
    timeout: 5000,
  });
  for (const line of stdout.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#') || trimmed.includes('tgWebAppData')) continue;
    if (trimmed.includes('=')) return trimmed;
  }
  throw new Error(`Failed to parse initData from script output`);
}

async function main() {
  mkdirSync(ARTIFACTS_DIR, { recursive: true });

  for (const { port, label } of [{ port: 3001, label: '3001' }, { port: 3002, label: '3002' }]) {
    const baseURL = `http://127.0.0.1:${port}`;
    console.log(`\n=== ${label}:${baseURL} ===`);
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 430, height: 932 } });
    const page = await context.newPage();

    // Auth for 3002 (production) — 3001 (mock-preview) does not require Telegram auth
    if (port === 3002) {
      try {
        const initData = generateInitData();
        const apiBaseURL = process.env.E2E_API_BASE_URL || 'http://127.0.0.1:8000';
        const { request } = await import('playwright');
        const apiContext = await request.newContext();
        const authResp = await apiContext.post(`${apiBaseURL}/api/auth/telegram`, {
          data: { initData },
          headers: { 'Content-Type': 'application/json' },
        });
        if (authResp.ok()) {
          const setCookie = authResp.headers()['set-cookie'] || '';
          const cookieValue = setCookie.match(/grace_session_v2=([^;]+)/)?.[1];
          if (cookieValue) {
            await context.addCookies([{
              name: 'grace_session_v2',
              value: cookieValue,
              domain: '127.0.0.1',
              path: '/',
              httpOnly: true,
              sameSite: 'Lax',
            }]);
          }
        }
        await apiContext.dispose();
        await page.addInitScript((data) => {
          (window).Telegram = {
            WebApp: {
              initData: data, initDataUnsafe: {}, ready: () => {}, expand: () => {},
              close: () => {}, platform: 'web', version: '9.5',
              colorScheme: 'light', themeParams: {}, isExpanded: true,
              viewportHeight: 932, viewportStableHeight: 932,
              headerColor: '#ffffff', backgroundColor: '#ffffff',
              MainButton: {
                text: '', color: '', textColor: '', isVisible: false, isActive: true,
                isProgressVisible: false, setText: () => {}, onClick: () => {}, offClick: () => {},
                show: () => {}, hide: () => {}, enable: () => {}, disable: () => {},
                showProgress: () => {}, hideProgress: () => {},
              },
              BackButton: {
                isVisible: false, onClick: () => {}, offClick: () => {}, show: () => {}, hide: () => {},
              },
              HapticFeedback: {
                impactOccurred: () => {}, notificationOccurred: () => {}, selectionOccurred: () => {},
              },
              onEvent: () => {}, offEvent: () => {}, sendData: () => {}, switchInlineQuery: () => {},
              openLink: () => {}, openTelegramLink: () => {}, openInvoice: () => {},
              showPopup: () => {}, showAlert: () => {}, showConfirm: () => {},
            },
          };
        }, initData);
      } catch (e) {
        console.error(`Auth setup failed for ${label}:`, e.message);
      }
    }

    for (const route of ROUTES) {
      const { path, name, sentinel } = route;
      const artifactPath = resolve(ARTIFACTS_DIR, `${label}-${name}.png`);
      const blockerPath = resolve(ARTIFACTS_DIR, `${label}-${name}.txt`);

      try {
        await page.goto(path, { waitUntil: 'networkidle', timeout: 20000 }).catch(() => {});
        await page.waitForTimeout(2000);

        const url = page.url();
        const content = await page.content();
        const hasAuthText = content.includes('Авторизация');
        const hasSentinel = content.includes(sentinel);

        console.log(`  ${label}${path}: url=${url} auth=${hasAuthText} sentinel=${hasSentinel}`);

        if (!hasAuthText && hasSentinel) {
          await page.screenshot({ path: artifactPath, fullPage: false });
          console.log(`  ✓ VALID: ${label}${path}`);
        } else if (hasAuthText) {
          writeFileSync(blockerPath, `BLOCKED_AUTH: page shows "Авторизация..."\nURL: ${url}\n`);
          console.log(`  ✗ BLOCKED_AUTH: ${label}${path}`);
        } else {
          writeFileSync(blockerPath, `NO_SENTINEL: expected "${sentinel}" not found\nURL: ${url}\n`);
          console.log(`  ✗ NO_SENTINEL: ${label}${path}`);
        }
      } catch (err) {
        writeFileSync(blockerPath, `EXCEPTION: ${err.message}\n`);
        console.log(`  ✗ EXCEPTION: ${label}${path}: ${err.message}`);
      }
    }

    await browser.close();
  }
}

main().catch(console.error);
