// Wave 11 implementation capture script.
// Run from repo root: node docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/capture-implementation.cjs

const { chromium, request } = require('/opt/solarsage-astro/node_modules/.pnpm/@playwright+test@1.60.0/node_modules/@playwright/test/index.js');
const { execFileSync } = require('child_process');
const { mkdirSync, writeFileSync } = require('fs');
const { resolve } = require('path');

const PROJ = '/opt/solarsage-astro';
const ARTIFACTS = resolve(PROJ, 'docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/implementation-01');
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

async function seedAuth(context, initData) {
  const ctx = await request.newContext();
  const resp = await ctx.post(`${API_BASE}/api/auth/telegram`, {
    data: { initData }, headers: { 'Content-Type': 'application/json' },
    timeout: 10000,
  }).catch(e => { console.error('  Auth request failed:', e.message); return null; });
  if (resp && resp.ok()) {
    const cookieVal = (resp.headers()['set-cookie'] || '').match(/grace_session_v2=([^;]+)/)?.[1];
    if (cookieVal) {
      await context.addCookies([{ name: 'grace_session_v2', value: cookieVal, domain: '127.0.0.1', path: '/', httpOnly: true, sameSite: 'Lax' }]);
    }
  }
  await ctx.dispose();
}

async function main() {
  mkdirSync(ARTIFACTS, { recursive: true });
  const url = `http://127.0.0.1:7777/day/2026-07-05`;
  const initData = genInitData();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: VIEWPORT });
  const page = await context.newPage();

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
  await page.waitForTimeout(4000);

  // 1. Top viewport: candidate-01-top.png
  await page.screenshot({ path: resolve(ARTIFACTS, 'candidate-01-top.png'), fullPage: false });

  // Scroll helper
  const scrollToText = async (textPatterns) => {
    await page.evaluate((patterns) => {
      const scrollRoot = document.querySelector('.flex-1.overflow-y-auto.overscroll-contain');
      if (!scrollRoot) return;
      const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let node;
      let targetElement = null;
      while (node = walk.nextNode()) {
        const txt = node.textContent.trim();
        for (const pat of patterns) {
          if (txt.toLowerCase().includes(pat.toLowerCase())) {
            let p = node.parentElement;
            while (p && p.offsetHeight === 0) p = p.parentElement;
            if (p) { targetElement = p; break; }
          }
        }
        if (targetElement) break;
      }
      if (targetElement && scrollRoot) {
        const rect = targetElement.getBoundingClientRect();
        const rootRect = scrollRoot.getBoundingClientRect();
        scrollRoot.scrollTop = rect.top - rootRect.top + scrollRoot.scrollTop - 20;
        scrollRoot.dispatchEvent(new Event('scroll', { bubbles: true }));
      }
    }, textPatterns);
    await page.waitForTimeout(600);
  };

  // Expand concrete advice first to capture it expanded
  await page.evaluate(() => {
    const btn = document.querySelector('button[aria-controls="concrete-day-advice-rows"]');
    if (btn) btn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
  await page.waitForTimeout(500);

  // 2. Concrete Today: candidate-02-concrete-today-expanded.png
  await scrollToText(['КОНКРЕТНО СЕГОДНЯ', 'Конкретно сегодня']);
  await page.screenshot({ path: resolve(ARTIFACTS, 'candidate-02-concrete-today-expanded.png'), fullPage: false });

  // 3. Chart Before: candidate-03-chart-before.png
  await scrollToText(['КАРТА ДНЯ', 'карта дня']);
  await page.screenshot({ path: resolve(ARTIFACTS, 'candidate-03-chart-before.png'), fullPage: false });

  // 4. Chart After Click: candidate-04-chart-after-click.png
  await page.evaluate(() => {
    const planet = document.querySelector('[data-testid="day-chart-planet"]');
    if (planet) planet.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
  await page.waitForTimeout(800);
  
  const chartPopoverText = await page.evaluate(() => {
    const el = document.querySelector('[data-testid="day-chart-planet-popover"]');
    return el ? el.innerText.trim() : "not found";
  });
  await page.screenshot({ path: resolve(ARTIFACTS, 'candidate-04-chart-after-click.png'), fullPage: false });

  // Reload to clear click state
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(3000);

  // 5. Reading/Why/Week/History: candidate-05-reading-why-week-history.png
  await scrollToText(['РАЗБОР ДНЯ', 'Почему так у меня', 'БЛИЖАЙШИЕ ДНИ', 'В этот день']);
  await page.screenshot({ path: resolve(ARTIFACTS, 'candidate-05-reading-why-week-history.png'), fullPage: false });

  // 6. Full scroll stitched: candidate-00-full-scroll.png
  // Expand concrete advice again to capture all 12 spheres in full scroll
  await page.evaluate(() => {
    const btn = document.querySelector('button[aria-controls="concrete-day-advice-rows"]');
    if (btn) btn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
  await page.waitForTimeout(500);

  await page.evaluate(() => {
    const scrollRoot = document.querySelector('.flex-1.overflow-y-auto.overscroll-contain');
    if (scrollRoot) {
      scrollRoot.style.height = 'auto';
      scrollRoot.style.overflow = 'visible';
      scrollRoot.style.maxHeight = 'none';
      scrollRoot.classList.remove('flex-1');
    }
    let parent = scrollRoot ? scrollRoot.parentElement : null;
    while (parent) {
      if (parent.style) {
        parent.style.height = 'auto';
        parent.style.overflow = 'visible';
        parent.style.maxHeight = 'none';
      }
      parent = parent.parentElement;
    }
    document.body.style.height = 'auto';
    document.body.style.overflow = 'visible';
  });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: resolve(ARTIFACTS, 'candidate-00-full-scroll.png'), fullPage: true });

  // Extract info for summary-implementation.json
  const textContent = await page.evaluate(() => document.body?.innerText || '');
  
  // Section order
  const sectionOrder = await page.evaluate(() => {
    const wanted = new Set(['day-header', 'access-card', 'day-summary-card', 'concrete-day-advice', 'day-chart', 'day-reading', 'why-expanded', 'week-strip', 'astro-history-widget', 'today-bottom-disclaimer']);
    return Array.from(document.querySelectorAll('[data-testid]'))
      .map(node => node.getAttribute('data-testid'))
      .filter(id => id && wanted.has(id));
  });

  // Concrete advice labels
  const adviceLabels = await page.evaluate(() => {
    const labels = [];
    document.querySelectorAll('[data-testid="concrete-day-advice-row"] span').forEach(el => {
      const txt = el.textContent.trim();
      if (txt && txt.length > 2 && txt.length < 20 && !txt.includes('\n')) {
        labels.push(txt);
      }
    });
    return Array.from(new Set(labels));
  });

  // Chart legend labels
  const legendLabels = await page.evaluate(() => {
    const labels = [];
    const elements = document.querySelectorAll('span, text, div');
    const wanted = new Set(['соединение', 'оппозиция', 'тригон', 'квадратура', 'секстиль']);
    elements.forEach(el => {
      const txt = el.textContent.trim().toLowerCase();
      if (wanted.has(txt)) labels.push(el.textContent.trim());
    });
    return Array.from(new Set(labels));
  });

  // History text
  const historyText = await page.evaluate(() => {
    const el = document.querySelector('[data-testid="astro-history-widget"]');
    return el ? el.innerText.trim() : "";
  });

  // Check raw debug leaks
  const rawDebugStrings = [];
  const piiChecks = [
    'Crisis Transformation Control',
    'Inner Background Unconscious',
    'Money Security Resources',
    'Thinking Speech Learning',
    'Meaning Expansion Vector',
    'Cancer',
    'Aries',
    'Taurus'
  ];
  piiChecks.forEach(check => {
    if (textContent.includes(check)) rawDebugStrings.push(check);
  });
  // Check for score patterns in rows
  const scoreRegex = /\b\d\.\d{2}\b/g;
  const matches = textContent.match(scoreRegex);
  if (matches) rawDebugStrings.push(...matches);

  const summary = {
    date: "2026-07-05",
    candidate: {
      sectionOrder,
      concreteAdviceLabels: adviceLabels,
      concreteAdviceRowCountAfterExpand: adviceLabels.length,
      rawDebugStringsFound: rawDebugStrings,
      chartLegendLabels: legendLabels,
      chartPopoverTextAfterClick: chartPopoverText,
      historyHeadingAndCardText: historyText
    }
  };

  writeFileSync(resolve(ARTIFACTS, 'summary-implementation.json'), JSON.stringify(summary, null, 2));
  console.log('Done. summary-implementation.json written.');

  await browser.close();
}

main().catch(console.error);
