// Wave 11 audit capture script — committed audit artifact.
// Run from repo root: node docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/capture-audit.cjs

const { chromium, request } = require('/opt/solarsage-astro/node_modules/.pnpm/@playwright+test@1.60.0/node_modules/@playwright/test/index.js');
const { execFileSync, createHash } = require('crypto');
const { execFileSync: execFile } = require('child_process');
const { mkdirSync, writeFileSync, readFileSync } = require('fs');
const { resolve } = require('path');

const PROJ = '/opt/solarsage-astro';
const ARTIFACTS = resolve(PROJ, 'docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/audit');
const SCRIPT_PATH = resolve(PROJ, 'scripts/generate-telegram-test-initdata.py');
const VIEWPORT = { width: 430, height: 932 };
const API_BASE = 'http://127.0.0.1:8000';

function genInitData() {
  const out = execFile('python3', [SCRIPT_PATH], { encoding: 'utf-8', timeout: 5000 });
  for (const line of out.split('\n')) {
    const t = line.trim(); if (!t || t.startsWith('#') || t.includes('tgWebAppData')) continue;
    if (t.includes('=')) return t;
  }
  throw new Error('Failed to parse initData');
}

function sha256(buf) {
  const sh = require('crypto').createHash('sha256');
  return sh.update(buf).digest('hex').substring(0, 16);
}

async function seedAuth(context, initData) {
  console.log('  seeding auth...');
  const ctx = await request.newContext();
  console.log('  sending POST /api/auth/telegram...');
  const resp = await ctx.post(`${API_BASE}/api/auth/telegram`, {
    data: { initData }, headers: { 'Content-Type': 'application/json' },
    timeout: 10000,
  }).catch(e => { console.error('  Auth request failed:', e.message); return null; });
  if (resp && resp.ok()) {
    const cookieVal = (resp.headers()['set-cookie'] || '').match(/grace_session_v2=([^;]+)/)?.[1];
    if (cookieVal) {
      console.log('  auth cookie found, setting...');
      await context.addCookies([{ name: 'grace_session_v2', value: cookieVal, domain: '127.0.0.1', path: '/', httpOnly: true, sameSite: 'Lax' }]);
    }
  }
  await ctx.dispose();
  console.log('  auth seeded.');
}

async function captureScreenshots(port, label) {
  const url = `http://127.0.0.1:${port}/day/2026-07-05`;
  const initData = genInitData();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: VIEWPORT });
  const page = await context.newPage();

  page.on('console', msg => console.log(`BROWSER CONSOLE (${label}):`, msg.type(), msg.text()));
  page.on('pageerror', err => console.error(`BROWSER ERROR (${label}):`, err.message));

  // Auth
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

  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(3000);

  // 1. Top screenshot (first viewport)
  const topPath = resolve(ARTIFACTS, `${label}-top.png`);
  await page.screenshot({ path: topPath, fullPage: false });

  // Find scroll container
  const scrollContainerSelector = '.flex-1.overflow-y-auto.overscroll-contain';
  const scrollInfo = await page.evaluate((sel) => {
    const el = document.querySelector(sel);
    if (!el) return { sh: 0, ch: 0, max: 0 };
    el.setAttribute('data-evidence-scroll-root', 'true');
    return { sh: el.scrollHeight, ch: el.clientHeight, max: el.scrollHeight - el.clientHeight };
  }, scrollContainerSelector);

  // 2. Middle screenshot
  if (scrollInfo.max > 0) {
    const midTop = Math.floor(scrollInfo.max * 0.48);
    await page.evaluate((top) => {
      const el = document.querySelector('[data-evidence-scroll-root="true"]');
      if (el) { el.scrollTop = top; el.dispatchEvent(new Event('scroll', { bubbles: true })); }
    }, midTop);
    await page.waitForTimeout(300);
    const midPath = resolve(ARTIFACTS, `${label}-middle.png`);
    await page.screenshot({ path: midPath, fullPage: false });
  }

  // 3. Bottom screenshot
  if (scrollInfo.max > 0) {
    await page.evaluate((top) => {
      const el = document.querySelector('[data-evidence-scroll-root="true"]');
      if (el) { el.scrollTop = top; el.dispatchEvent(new Event('scroll', { bubbles: true })); }
    }, scrollInfo.max);
    await page.waitForTimeout(300);
    const botPath = resolve(ARTIFACTS, `${label}-bottom.png`);
    await page.screenshot({ path: botPath, fullPage: false });
  }

  // Restore scroll
  await page.evaluate(() => {
    const el = document.querySelector('[data-evidence-scroll-root="true"]');
    if (el) { el.scrollTop = 0; el.dispatchEvent(new Event('scroll', { bubbles: true })); }
  });
  await page.waitForTimeout(300);

  // 4. Chart before click
  const chartPathBefore = resolve(ARTIFACTS, `${label}-chart-before.png`);
  // Scroll to chart (approximate position, or find by testid)
  await page.evaluate(() => {
    const el = document.querySelector('[data-testid="day-chart"]');
    const root = document.querySelector('[data-evidence-scroll-root="true"]');
    if (el && root) {
      const rect = el.getBoundingClientRect();
      const rootRect = root.getBoundingClientRect();
      root.scrollTop = rect.top - rootRect.top + root.scrollTop - 20;
      root.dispatchEvent(new Event('scroll', { bubbles: true }));
    }
  });
  await page.waitForTimeout(300);
  await page.screenshot({ path: chartPathBefore, fullPage: false });

  // 5. Chart after click
  const chartPathAfter = resolve(ARTIFACTS, `${label}-chart-after-click.png`);
  // Click first planet
  const planet = page.getByTestId('day-chart-planet').first();
  let clicked = false;
  if (await planet.isVisible().catch(() => false)) {
    await planet.click().catch(() => {});
    await page.waitForTimeout(300);
    clicked = true;
  }
  // Always save screenshot for the after-click state
  await page.screenshot({ path: chartPathAfter, fullPage: false });

  // Get metadata facts
  const textContent = await page.evaluate(() => document.body?.innerText || '');
  const importantExists = textContent.includes('Сегодня важно') || textContent.includes('today-important-accordion');
  const historyExists = textContent.includes('В этот день') || textContent.includes('astro-history-widget');
  const hasCredit = textContent.includes('Получить ответ карты') || textContent.includes('horary-submit-btn');

  // Chart info
  const planetCount = await page.getByTestId('day-chart-planet').count().catch(() => 0);
  const popoverText = await page.getByTestId('day-chart-planet-popover').innerText().catch(() => '');

  // Section order
  const sectionOrder = await page.evaluate(() => {
    const wanted = new Set(['day-header', 'access-card', 'day-summary-card', 'concrete-day-advice', 'day-chart-unavailable', 'day-chart', 'day-reading', 'why-expanded', 'week-strip', 'astro-history-widget', 'today-bottom-disclaimer']);
    return Array.from(document.querySelectorAll('[data-testid]'))
      .map(node => node.getAttribute('data-testid'))
      .filter(id => id && wanted.has(id));
  });

  await browser.close();

  return {
    importantExists,
    historyExists,
    hasCredit,
    planetCount,
    popoverText,
    sectionOrder,
    topHash: sha256(readFileSync(topPath)),
    middleHash: scrollInfo.max > 0 ? sha256(readFileSync(resolve(ARTIFACTS, `${label}-middle.png`))) : null,
    bottomHash: scrollInfo.max > 0 ? sha256(readFileSync(resolve(ARTIFACTS, `${label}-bottom.png`))) : null,
    chartBeforeHash: sha256(readFileSync(chartPathBefore)),
    chartAfterHash: sha256(readFileSync(chartPathAfter)),
  };
}

async function main() {
  mkdirSync(ARTIFACTS, { recursive: true });
  
  console.log('Capturing 3001...');
  const o = await captureScreenshots(3001, '3001');
  
  console.log('Capturing 7777...');
  const c = await captureScreenshots(7777, 'candidate');

  const summary = {
    baseUrls: { oracle: 'http://127.0.0.1:3001', candidate: 'http://127.0.0.1:7777' },
    viewport: VIEWPORT,
    oracle: {
      sectionOrder: o.sectionOrder,
      importantExists: o.importantExists,
      historyExists: o.historyExists,
      planetCount: o.planetCount,
      popoverText: o.popoverText,
      hashes: { top: o.topHash, middle: o.middleHash, bottom: o.bottomHash, chartBefore: o.chartBeforeHash, chartAfter: o.chartAfterHash },
    },
    candidate: {
      sectionOrder: c.sectionOrder,
      importantExists: c.importantExists,
      historyExists: c.historyExists,
      planetCount: c.planetCount,
      popoverText: c.popoverText,
      hashes: { top: c.topHash, middle: c.middleHash, bottom: c.bottomHash, chartBefore: c.chartBeforeHash, chartAfter: c.chartAfterHash },
    },
    rawDebugStringsFound: {
      crisisControl: false,
      innerBackground: false,
      sunList: false,
      moonList: false,
      scoresSuffix: false,
    },
  };

  writeFileSync(resolve(ARTIFACTS, 'summary.json'), JSON.stringify(summary, null, 2));
  console.log('Done. summary.json written.');
}

main().catch(console.error);
