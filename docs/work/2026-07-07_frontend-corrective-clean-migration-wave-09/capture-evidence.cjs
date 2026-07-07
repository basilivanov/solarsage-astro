const { chromium, request } = require('/opt/solarsage-astro/node_modules/.pnpm/@playwright+test@1.60.0/node_modules/@playwright/test/index.js');
const { execFileSync } = require('child_process');
const { createHash } = require('crypto');
const { mkdirSync, writeFileSync, readFileSync, statSync } = require('fs');
const { resolve } = require('path');

const PROJ = '/opt/solarsage-astro';
const ARTIFACTS = resolve(PROJ, 'docs/work/2026-07-07_frontend-corrective-clean-migration-wave-09/artifacts/rework-05');
const SCRIPT_PATH = resolve(PROJ, 'scripts/generate-telegram-test-initdata.py');
const VIEWPORT = { width: 430, height: 932 };
const API_BASE = 'http://127.0.0.1:8000';

function genInitData() {
  const out = execFileSync('python3', [SCRIPT_PATH], { encoding: 'utf-8', timeout: 5000 });
  for (const line of out.split('\n')) {
    const t = line.trim(); if (!t || t.startsWith('#') || t.includes('tgWebAppData')) continue;
    if (t.includes('=')) return t;
  }
  throw new Error('Failed to parse initData');
}

function sha256(buf) { return createHash('sha256').update(buf).digest('hex').substring(0, 16); }

function pngSize(buf) {
  // PNG header has width/height at offset 16 (IHDR chunk)
  if (buf.length < 24) return null;
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  return `${w}x${h}`;
}

async function seedAuth(context, initData) {
  const ctx = await request.newContext();
  const resp = await ctx.post(`${API_BASE}/api/auth/telegram`, {
    data: { initData }, headers: { 'Content-Type': 'application/json' },
  });
  if (resp.ok()) {
    const cookieVal = (resp.headers()['set-cookie'] || '').match(/grace_session_v2=([^;]+)/)?.[1];
    if (cookieVal) await context.addCookies([{ name: 'grace_session_v2', value: cookieVal, domain: '127.0.0.1', path: '/', httpOnly: true, sameSite: 'Lax' }]);
  }
  await ctx.dispose();
}

async function detectScrollContainer(page) {
  return page.evaluate(() => {
    const all = document.querySelectorAll('*');
    let best = null, bestDiff = 0;
    for (const el of all) {
      const sh = el.scrollHeight, ch = el.clientHeight;
      const diff = sh - ch;
      if (diff > bestDiff && ch > 100) { bestDiff = diff; best = el; }
    }
    if (!best) best = document.scrollingElement || document.documentElement;
    // Mark the element
    best.setAttribute('data-evidence-scroll-root', 'true');
    const tag = best.tagName.toLowerCase();
    const id = best.id ? `#${best.id}` : '';
    const cls = best.className && typeof best.className === 'string' ? `.${best.className.split(' ').filter(Boolean).join('.')}` : '';
    return {
      selector: id || cls || tag,
      scrollHeight: best.scrollHeight,
      clientHeight: best.clientHeight,
      maxScrollTop: best.scrollHeight - best.clientHeight,
      documentScrollHeight: Math.max(document.documentElement.scrollHeight, document.body?.scrollHeight || 0),
      documentClientHeight: document.documentElement.clientHeight,
    };
  });
}

const ROUTES = [
  { port: 3001, route: '/day/2026-07-05', name: 'day-2026-07-05', check: async (p) => (await p.getByTestId('today-screen').isVisible().catch(()=>false)) || (await p.getByText(/14 дней бесплатного доступа/).isVisible().catch(()=>false)) },
  { port: 3001, route: '/calendar', name: 'calendar', check: async (p) => { const b = await p.evaluate(() => document.body?.innerText || ''); return b.includes('КАЛЕНДАРЬ') && b.includes('Июль 2026'); } },
  { port: 3001, route: '/profile', name: 'profile', check: async (p) => { const b = await p.evaluate(() => document.body?.innerText || ''); return b.includes('ПРОФИЛЬ') && (b.includes('ДОСТУП') || b.includes('Доступ активен')); } },
  { port: 3001, route: '/readings', name: 'readings', check: async (p) => (await p.getByText(/ДОСТУПНО СЕЙЧАС|Доступно сейчас/).isVisible().catch(()=>false)) },
  { port: 3001, route: '/readings/horary', name: 'horary', check: async (p) => p.getByText('Хорарный оракул').isVisible().catch(()=>false) },
  { port: 3001, route: '/readings/natal', name: 'natal', check: async (p) => p.getByText('Твоя натальная карта').isVisible().catch(()=>false) },
  { port: 3002, route: '/day/2026-07-05', name: 'day-2026-07-05', check: async (p) => { const s = await p.getByTestId('today-screen').isVisible().catch(()=>false); const a = await p.getByText('14 дней бесплатного доступа').isVisible().catch(()=>false); return s && a; } },
  { port: 3002, route: '/calendar', name: 'calendar', check: async (p) => { const s = await p.getByTestId('calendar-screen').isVisible().catch(()=>false); const l = await p.getByTestId('calendar-loading').isVisible().catch(()=>false); const g = await p.getByTestId('calendar-grid').isVisible().catch(()=>false); const u = await p.getByTestId('calendar-unavailable').isVisible().catch(()=>false); return s && !l && (g || u); } },
  { port: 3002, route: '/profile', name: 'profile', check: async (p) => { const s = await p.getByTestId('profile-screen').isVisible().catch(()=>false); const a = await p.getByTestId('profile-access-card').isVisible().catch(()=>false); return s && a; } },
  { port: 3002, route: '/readings', name: 'readings', check: async (p) => { const s = await p.getByTestId('readings-screen').isVisible().catch(()=>false); const a = await p.getByTestId('readings-available-section').isVisible().catch(()=>false); return s && a; } },
  { port: 3002, route: '/readings/horary', name: 'horary', check: async (p) => { const s = await p.locator('[data-testid="horary-screen"][data-state="ready"]').isVisible().catch(()=>false); const f = await p.getByTestId('horary-form').isVisible().catch(()=>false); const q = await p.getByTestId('horary-quota-section').isVisible().catch(()=>false); return s && (f || q); } },
  { port: 3002, route: '/readings/natal', name: 'natal', check: async (p) => { const s = await p.locator('[data-testid="natal-preview-screen"][data-state="ready"]').isVisible().catch(()=>false); const c = await p.getByTestId('natal-preview-content').isVisible().catch(()=>false); return s && c; } },
];

async function main() {
  mkdirSync(ARTIFACTS, { recursive: true });
  const results = []; const lines = [];

  lines.push('=== PREFLIGHT ===');
  for (const url of ['http://127.0.0.1:8000/api/health', 'http://127.0.0.1:3001/', 'http://127.0.0.1:3002/']) {
    try { const r = await fetch(url); lines.push(`${url}: HTTP ${r.status}`); }
    catch (e) { lines.push(`${url}: UNREACHABLE`); }
  }

  const initData = genInitData();

  for (const entry of ROUTES) {
    const url = `http://127.0.0.1:${entry.port}${entry.route}`;
    lines.push(`\n=== ${entry.port}${entry.route} ===`);
    const result = {
      port: entry.port, route: entry.route, valid: false, blocker: null,
      viewportArtifact: null, fullPageArtifact: null, scrollArtifacts: [],
      artifactHashes: {}, artifactImageSizes: {},
      requestedScrollTops: [], actualScrollTops: [], uniqueScrollHashCount: 0,
      readySentinels: {}, bodyTextSample: '',
      documentScrollHeight: 0, documentClientHeight: 0,
      scrollContainerDescription: '', scrollContainerScrollHeight: 0,
      scrollContainerClientHeight: 0, scrollContainerMaxScrollTop: 0,
      notes: '',
    };

    try {
      const browser = await chromium.launch({ headless: true });
      const context = await browser.newContext({ viewport: VIEWPORT });
      const page = await context.newPage();

      await seedAuth(context, initData);
      await page.addInitScript((data) => {
        window.Telegram = { WebApp: { initData: data, initDataUnsafe: {}, ready: () => {}, expand: () => {}, close: () => {}, platform: 'web', version: '9.5', colorScheme: 'light', themeParams: {}, isExpanded: true, viewportHeight: 932, viewportStableHeight: 932, headerColor: '#ffffff', backgroundColor: '#ffffff',
          MainButton: { text: '', color: '', textColor: '', isVisible: false, isActive: true, isProgressVisible: false, setText: () => {}, onClick: () => {}, offClick: () => {}, show: () => {}, hide: () => {}, enable: () => {}, disable: () => {}, showProgress: () => {}, hideProgress: () => {} },
          BackButton: { isVisible: false, onClick: () => {}, offClick: () => {}, show: () => {}, hide: () => {} },
          HapticFeedback: { impactOccurred: () => {}, notificationOccurred: () => {}, selectionOccurred: () => {} },
          onEvent: () => {}, offEvent: () => {}, sendData: () => {}, switchInlineQuery: () => {},
          openLink: () => {}, openTelegramLink: () => {}, openInvoice: () => {},
          showPopup: () => {}, showAlert: () => {}, showConfirm: () => {},
        } };
      }, initData);

      await page.goto(url, { waitUntil: 'networkidle', timeout: 25000 }).catch(() => {});
      await page.waitForTimeout(3000);

      const authLoading = await page.getByTestId('auth-loading').isVisible().catch(() => false);
      const authError = await page.getByTestId('auth-error').isVisible().catch(() => false);
      const authText = await page.getByText('Авторизация').isVisible().catch(() => false);
      const bodyText = await page.evaluate(() => document.body?.innerText?.substring(0, 500) || '');
      result.bodyTextSample = bodyText;

      const sentinelOk = await entry.check(page);
      const isBlocked = authLoading || authError || authText;
      result.readySentinels = { authLoadingSeen: authLoading, authErrorSeen: authError, authTextSeen: authText, routeReady: sentinelOk };

      const scrollInfo = await detectScrollContainer(page);
      result.documentScrollHeight = scrollInfo.documentScrollHeight;
      result.documentClientHeight = scrollInfo.documentClientHeight;
      result.scrollContainerDescription = scrollInfo.selector;
      result.scrollContainerScrollHeight = scrollInfo.scrollHeight;
      result.scrollContainerClientHeight = scrollInfo.clientHeight;
      result.scrollContainerMaxScrollTop = scrollInfo.maxScrollTop;

      lines.push(`  authL=${authLoading} authE=${authError} authT=${authText} sentinel=${sentinelOk}`);
      lines.push(`  scroll: sh=${scrollInfo.scrollHeight} ch=${scrollInfo.clientHeight} max=${scrollInfo.maxScrollTop}`);
      lines.push(`  container: ${scrollInfo.selector}`);

      const vpName = `${entry.port}-${entry.name}-viewport.png`;
      const fpName = `${entry.port}-${entry.name}-fullpage.png`;
      const vpPath = resolve(ARTIFACTS, vpName);
      const fpPath = resolve(ARTIFACTS, fpName);

      if (!isBlocked && sentinelOk) {
        result.valid = true;
        result.viewportArtifact = vpName;
        result.fullPageArtifact = fpName;

        // Viewport screenshot
        await page.screenshot({ path: vpPath, fullPage: false });
        result.artifactHashes[vpName] = sha256(readFileSync(vpPath));
        result.artifactImageSizes[vpName] = pngSize(readFileSync(vpPath));
        lines.push(`  viewport: ${vpName} hash=${result.artifactHashes[vpName]} size=${result.artifactImageSizes[vpName]}`);

        // FullPage screenshot
        try {
          await page.screenshot({ path: fpPath, fullPage: true });
          result.artifactHashes[fpName] = sha256(readFileSync(fpPath));
          result.artifactImageSizes[fpName] = pngSize(readFileSync(fpPath));
          lines.push(`  fullPage: ${fpName} hash=${result.artifactHashes[fpName]} size=${result.artifactImageSizes[fpName]}`);
        } catch (e) {
          result.notes = `fullPage error: ${e.message}`;
          lines.push(`  fullPage error: ${e.message}`);
        }

        // Scroll the detected container, not window
        if (scrollInfo.maxScrollTop > 0) {
          const viewH = scrollInfo.clientHeight;
          const slices = Math.ceil(scrollInfo.maxScrollTop / viewH) + 1;
          const seen = new Set();

          for (let i = 0; i < slices; i++) {
            const targetTop = Math.min(i * viewH, scrollInfo.maxScrollTop);
            const approx = Math.round(targetTop / 50);
            if (seen.has(approx)) continue;
            seen.add(approx);

            result.requestedScrollTops.push(targetTop);

            const actualTop = await page.evaluate((top) => {
              const el = document.querySelector('[data-evidence-scroll-root="true"]');
              if (!el) return -1;
              el.scrollTop = top;
              el.dispatchEvent(new Event('scroll', { bubbles: true }));
              return el.scrollTop;
            }, targetTop);
            result.actualScrollTops.push(actualTop);
            await page.waitForTimeout(200);

            const sn = `${entry.port}-${entry.name}-scroll-${String(i).padStart(2, '0')}.png`;
            const sp = resolve(ARTIFACTS, sn);
            await page.screenshot({ path: sp, fullPage: false });
            result.scrollArtifacts.push(sn);
            result.artifactHashes[sn] = sha256(readFileSync(sp));
            result.artifactImageSizes[sn] = pngSize(readFileSync(sp));
            lines.push(`  scroll-${i}: ${sn} req=${targetTop} actual=${actualTop} hash=${result.artifactHashes[sn]}`);
          }

          // Bottom capture
          {
            const bSn = `${entry.port}-${entry.name}-scroll-bottom.png`;
            const bSp = resolve(ARTIFACTS, bSn);
            result.requestedScrollTops.push(scrollInfo.maxScrollTop);
            const actualTop = await page.evaluate((top) => {
              const el = document.querySelector('[data-evidence-scroll-root="true"]');
              if (!el) return -1;
              el.scrollTop = top;
              el.dispatchEvent(new Event('scroll', { bubbles: true }));
              return el.scrollTop;
            }, scrollInfo.maxScrollTop);
            result.actualScrollTops.push(actualTop);
            await page.waitForTimeout(200);
            await page.screenshot({ path: bSp, fullPage: false });
            result.scrollArtifacts.push(bSn);
            result.artifactHashes[bSn] = sha256(readFileSync(bSp));
            result.artifactImageSizes[bSn] = pngSize(readFileSync(bSp));
            lines.push(`  scroll-bottom: ${bSn} req=${scrollInfo.maxScrollTop} actual=${actualTop} hash=${result.artifactHashes[bSn]}`);
          }

          // Restore top
          await page.evaluate(() => {
            const el = document.querySelector('[data-evidence-scroll-root="true"]');
            if (el) { el.scrollTop = 0; el.dispatchEvent(new Event('scroll', { bubbles: true })); }
          });

          // Compute unique scroll hashes
          const scrollHashes = result.scrollArtifacts.map((a) => result.artifactHashes[a]).filter(Boolean);
          result.uniqueScrollHashCount = new Set(scrollHashes).size;
          lines.push(`  scroll hashes: ${result.uniqueScrollHashCount} unique among ${result.scrollArtifacts.length} files`);

          // Validate
          const bottomHash = result.artifactHashes[result.scrollArtifacts[result.scrollArtifacts.length - 1]];
          const vpH = result.artifactHashes[vpName];
          if (scrollInfo.maxScrollTop > 100 && bottomHash === vpH) {
            result.notes = 'WARNING: bottom scroll hash equals viewport hash — content may not have scrolled';
            lines.push(`  ⚠️  WARNING: bottom hash matches viewport hash`);
          }
        } else {
          lines.push(`  no scroll needed (maxScrollTop=${scrollInfo.maxScrollTop})`);
        }

        lines.push(`  ✅ VALID: ${entry.port}${entry.route}`);
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
      result.valid = false;
      result.blocker = `exception: ${e.message}`;
      lines.push(`  ❌ EXCEPTION: ${e.message}`);
    }

    results.push(result);
  }

  writeFileSync(resolve(ARTIFACTS, 'capture-results.json'), JSON.stringify(results, null, 2));
  writeFileSync(resolve(ARTIFACTS, 'capture-stdout.txt'), lines.join('\n') + '\n');
  console.log(lines.join('\n'));
  console.log(`\nDone. Artifacts in ${ARTIFACTS}`);

  // Exit non-zero if any route is invalid
  const anyInvalid = results.some(r => !r.valid);
  if (anyInvalid) { console.error('Some routes invalid'); process.exit(1); }
}

main().catch(e => { console.error(e); process.exit(1); });
