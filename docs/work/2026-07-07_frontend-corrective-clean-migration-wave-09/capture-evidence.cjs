const { chromium, request } = require('/opt/solarsage-astro/node_modules/.pnpm/@playwright+test@1.60.0/node_modules/@playwright/test/index.js');
const { execFileSync } = require('child_process');
const { mkdirSync, writeFileSync } = require('fs');
const { resolve } = require('path');

const PROJ = '/opt/solarsage-astro';
const ARTIFACTS = resolve(PROJ, 'docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-03');
const SCRIPT_PATH = resolve(PROJ, 'scripts/generate-telegram-test-initdata.py');
const VIEWPORT = { width: 430, height: 932 };
const API_BASE = 'http://127.0.0.1:8000';

function genInitData() {
  const out = execFileSync('python3', [SCRIPT_PATH], { encoding: 'utf-8', timeout: 5000 });
  for (const line of out.split('\n')) {
    const t = line.trim();
    if (!t || t.startsWith('#') || t.includes('tgWebAppData')) continue;
    if (t.includes('=')) return t;
  }
  throw new Error('Failed to parse initData');
}

async function seedAuth(context, initData) {
  const ctx = await request.newContext();
  const resp = await ctx.post(`${API_BASE}/api/auth/telegram`, {
    data: { initData }, headers: { 'Content-Type': 'application/json' },
  });
  if (resp.ok()) {
    const cookieVal = (resp.headers()['set-cookie'] || '').match(/grace_session_v2=([^;]+)/)?.[1];
    if (cookieVal) {
      await context.addCookies([{ name: 'grace_session_v2', value: cookieVal, domain: '127.0.0.1', path: '/', httpOnly: true, sameSite: 'Lax' }]);
    }
  }
  await ctx.dispose();
}

const ROUTES = [
  { port: 3001, route: '/day/2026-07-05', name: 'day-2026-07-05',
    check: async (p) => (await p.getByText('14 дней бесплатного доступа').isVisible().catch(()=>false)) || (await p.getByText(/5 июля|5 ИЮЛ/).isVisible().catch(()=>false)) },
  { port: 3001, route: '/calendar', name: 'calendar',
    check: async (p) => { const h = await p.getByText(/КАЛЕНДАРЬ|Календарь/).isVisible().catch(()=>false); const g = await p.getByTestId('calendar-grid').isVisible().catch(()=>false) || await p.getByText(/Июль 2026/).isVisible().catch(()=>false); return h && g; } },
  { port: 3001, route: '/profile', name: 'profile',
    check: async (p) => { const h = await p.getByText(/ПРОФИЛЬ|Профиль/).isVisible().catch(()=>false); const a = await p.getByText(/ДОСТУП|Доступ/).isVisible().catch(()=>false); return h && a; } },
  { port: 3001, route: '/readings', name: 'readings',
    check: async (p) => (await p.getByText(/ДОСТУПНО СЕЙЧАС|Доступно сейчас/).isVisible().catch(()=>false)) },
  { port: 3001, route: '/readings/horary', name: 'horary',
    check: async (p) => p.getByText('Хорарный оракул').isVisible().catch(()=>false) },
  { port: 3001, route: '/readings/natal', name: 'natal',
    check: async (p) => p.getByText('Твоя натальная карта').isVisible().catch(()=>false) },
  { port: 3002, route: '/day/2026-07-05', name: 'day-2026-07-05',
    check: async (p) => { const s = await p.getByTestId('today-screen').isVisible().catch(()=>false); const a = await p.getByText('14 дней бесплатного доступа').isVisible().catch(()=>false); return s && a; } },
  { port: 3002, route: '/calendar', name: 'calendar',
    check: async (p) => { const s = await p.getByTestId('calendar-screen').isVisible().catch(()=>false); const l = await p.getByTestId('calendar-loading').isVisible().catch(()=>false); const g = await p.getByTestId('calendar-grid').isVisible().catch(()=>false); const u = await p.getByTestId('calendar-unavailable').isVisible().catch(()=>false); return s && !l && (g || u); } },
  { port: 3002, route: '/profile', name: 'profile',
    check: async (p) => { const s = await p.getByTestId('profile-screen').isVisible().catch(()=>false); const a = await p.getByTestId('profile-access-card').isVisible().catch(()=>false); return s && a; } },
  { port: 3002, route: '/readings', name: 'readings',
    check: async (p) => { const s = await p.getByTestId('readings-screen').isVisible().catch(()=>false); const a = await p.getByTestId('readings-available-section').isVisible().catch(()=>false); return s && a; } },
  { port: 3002, route: '/readings/horary', name: 'horary',
    check: async (p) => { const s = await p.locator('[data-testid="horary-screen"][data-state="ready"]').isVisible().catch(()=>false); const f = await p.getByTestId('horary-form').isVisible().catch(()=>false); const q = await p.getByTestId('horary-quota-section').isVisible().catch(()=>false); return s && (f || q); } },
  { port: 3002, route: '/readings/natal', name: 'natal',
    check: async (p) => { const s = await p.locator('[data-testid="natal-preview-screen"][data-state="ready"]').isVisible().catch(()=>false); const c = await p.getByTestId('natal-preview-content').isVisible().catch(()=>false); return s && c; } },
];

async function main() {
  mkdirSync(ARTIFACTS, { recursive: true });
  const results = [];
  const lines = [];

  // Preflight
  lines.push('=== PREFLIGHT ===');
  for (const port of [8000, 3001, 3002]) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/`);
      lines.push(`Port ${port}: HTTP ${r.status}`);
    } catch (e) {
      lines.push(`Port ${port}: UNREACHABLE`);
    }
  }

  const initData = genInitData();

  for (const entry of ROUTES) {
    const url = `http://127.0.0.1:${entry.port}${entry.route}`;
    lines.push(`\n=== ${entry.port}${entry.route} ===`);

    const result = {
      port: entry.port, route: entry.route, valid: false,
      blocker: null, viewportArtifact: null, fullPageArtifact: null,
      scrollArtifacts: [], readySentinels: {}, missingSentinels: {},
      bodyTextSample: '', notes: '',
    };

    try {
      const browser = await chromium.launch({ headless: true });
      const context = await browser.newContext({ viewport: VIEWPORT });
      const page = await context.newPage();

      await seedAuth(context, initData);
      await page.addInitScript((data) => {
        window.Telegram = {
          WebApp: {
            initData: data, initDataUnsafe: {}, ready: () => {}, expand: () => {},
            close: () => {}, platform: 'web', version: '9.5',
            colorScheme: 'light', themeParams: {}, isExpanded: true,
            viewportHeight: 932, viewportStableHeight: 932,
            headerColor: '#ffffff', backgroundColor: '#ffffff',
            MainButton: { text: '', color: '', textColor: '', isVisible: false, isActive: true, isProgressVisible: false, setText: () => {}, onClick: () => {}, offClick: () => {}, show: () => {}, hide: () => {}, enable: () => {}, disable: () => {}, showProgress: () => {}, hideProgress: () => {} },
            BackButton: { isVisible: false, onClick: () => {}, offClick: () => {}, show: () => {}, hide: () => {} },
            HapticFeedback: { impactOccurred: () => {}, notificationOccurred: () => {}, selectionOccurred: () => {} },
            onEvent: () => {}, offEvent: () => {}, sendData: () => {}, switchInlineQuery: () => {},
            openLink: () => {}, openTelegramLink: () => {}, openInvoice: () => {},
            showPopup: () => {}, showAlert: () => {}, showConfirm: () => {},
          },
        };
      }, initData);

      await page.goto(url, { waitUntil: 'networkidle', timeout: 25000 }).catch(() => {});
      await page.waitForTimeout(3000);

      const authLoading = await page.getByTestId('auth-loading').isVisible().catch(() => false);
      const authError = await page.getByTestId('auth-error').isVisible().catch(() => false);
      const authText = await page.getByText('Авторизация').isVisible().catch(() => false);
      const bodyText = await page.evaluate(() => document.body?.innerText?.substring(0, 300) || '');
      result.bodyTextSample = bodyText;

      const sentinelOk = await entry.check(page);
      const isBlocked = authLoading || authError || authText;

      result.readySentinels = { authLoadingSeen: authLoading, authErrorSeen: authError, authTextSeen: authText, routeReady: sentinelOk };

      const vpName = `${entry.port}-${entry.name}-viewport.png`;
      const fpName = `${entry.port}-${entry.name}-fullpage.png`;
      const vpPath = resolve(ARTIFACTS, vpName);
      const fpPath = resolve(ARTIFACTS, fpName);

      lines.push(`  authL=${authLoading} authE=${authError} authT=${authText} sentinel=${sentinelOk}`);
      lines.push(`  body: ${bodyText.substring(0, 120)}`);

      if (!isBlocked && sentinelOk) {
        result.valid = true;
        result.viewportArtifact = vpName;
        result.fullPageArtifact = fpName;

        await page.screenshot({ path: vpPath, fullPage: false });
        lines.push(`  viewport: ${vpName}`);

        try {
          await page.screenshot({ path: fpPath, fullPage: true });
          lines.push(`  fullPage: ${fpName}`);
        } catch (e) {
          result.notes = `fullPage error: ${e.message}`;
          for (let i = 0; i < 5; i++) {
            const sn = `${entry.port}-${entry.name}-scroll-${String(i).padStart(2, '0')}.png`;
            await page.screenshot({ path: resolve(ARTIFACTS, sn), fullPage: false });
            result.scrollArtifacts.push(sn);
            const r = await page.evaluate(() => document.documentElement.scrollHeight - window.innerHeight - window.scrollY);
            if (r <= 0) break;
            await page.evaluate(() => window.scrollBy(0, window.innerHeight));
            await page.waitForTimeout(200);
          }
          lines.push(`  scroll captures: ${result.scrollArtifacts.length}`);
        }
        lines.push(`  ✅ VALID`);
      } else {
        result.blocker = [];
        if (isBlocked) result.blocker.push('auth_blocked');
        if (!sentinelOk) result.blocker.push('no_sentinel');
        result.blocker = result.blocker.join(',');
        await page.screenshot({ path: vpPath, fullPage: false });
        lines.push(`  ❌ BLOCKED: ${result.blocker}`);
      }

      await browser.close();
    } catch (e) {
      result.blocker = `exception: ${e.message}`;
      lines.push(`  ❌ EXCEPTION: ${e.message}`);
    }
    results.push(result);
  }

  writeFileSync(resolve(ARTIFACTS, 'capture-results.json'), JSON.stringify(results, null, 2));
  writeFileSync(resolve(ARTIFACTS, 'capture-stdout.txt'), lines.join('\n') + '\n');
  console.log(lines.join('\n'));
  console.log(`\nDone. Artifacts in ${ARTIFACTS}`);
}

main().catch(e => { console.error(e); process.exit(1); });
