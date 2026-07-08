// Wave 11 audit rework capture script.
// Run from repo root: node docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/capture-audit-rework.cjs

const { chromium, request } = require('/opt/solarsage-astro/node_modules/.pnpm/@playwright+test@1.60.0/node_modules/@playwright/test/index.js');
const { execFileSync } = require('child_process');
const { mkdirSync, writeFileSync, readFileSync } = require('fs');
const { resolve } = require('path');

const PROJ = '/opt/solarsage-astro';
const ARTIFACTS = resolve(PROJ, 'docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/audit-rework-01');
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

async function captureScreenshots(port, label) {
  const url = `http://127.0.0.1:${port}/day/2026-07-05`;
  const initData = genInitData();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: VIEWPORT });
  const page = await context.newPage();

  // Handle logs
  page.on('console', msg => console.log(`BROWSER CONSOLE (${label}):`, msg.type(), msg.text()));
  page.on('pageerror', err => console.error(`BROWSER ERROR (${label}):`, err.message));

  // Auth (only needed for candidate/7777, but safe for both)
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

  // 1. Top viewport: [label]-01-top.png
  const topPath = resolve(ARTIFACTS, `${label}-01-top.png`);
  await page.screenshot({ path: topPath, fullPage: false });

  // Scroll function using text anchors
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
            // Traverse up to find a visible parent element
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

  // 2. Concrete Today: [label]-02-concrete-today.png
  await scrollToText(['КОНКРЕТНО СЕГОДНЯ', 'Конкретно сегодня']);
  const concretePath = resolve(ARTIFACTS, `${label}-02-concrete-today.png`);
  await page.screenshot({ path: concretePath, fullPage: false });

  // 3. Chart Before: [label]-03-chart-before.png
  await scrollToText(['КАРТА ДНЯ', 'карта дня']);
  const chartBeforePath = resolve(ARTIFACTS, `${label}-03-chart-before.png`);
  await page.screenshot({ path: chartBeforePath, fullPage: false });

  // 4. Chart After Click: [label]-04-chart-after-click.png
  // Click first planet marker
  const planetCount = await page.evaluate(() => {
    return document.querySelectorAll('svg g.cursor-pointer, [data-testid="day-chart-planet"]').length;
  });

  let afterClickVisibleText = "";
  if (planetCount > 0) {
    await page.evaluate(() => {
      const planet = document.querySelector('svg g.cursor-pointer, [data-testid="day-chart-planet"]');
      if (planet) {
        planet.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      }
    });
    await page.waitForTimeout(800);
    // Extract popover text
    afterClickVisibleText = await page.evaluate(() => {
      // Look for standard popover wrappers
      const popover = document.querySelector('[data-testid="day-chart-planet-popover"], .backdrop-blur');
      return popover ? popover.innerText.trim() : "no popover element found";
    });
  }
  const chartAfterPath = resolve(ARTIFACTS, `${label}-04-chart-after-click.png`);
  await page.screenshot({ path: chartAfterPath, fullPage: false });

  // Reset selected planet state by clicking outside/center or reload
  // (We will just reload the page to get a clean scroll state for the remaining steps)
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(3000);

  // 5. Reading/Why/Week/History: [label]-05-reading-why-week-history.png
  await scrollToText(['РАЗБОР ДНЯ', 'Почему так у меня', 'БЛИЖАЙШИЕ ДНИ', 'В этот день']);
  const bottomPath = resolve(ARTIFACTS, `${label}-05-reading-why-week-history.png`);
  await page.screenshot({ path: bottomPath, fullPage: false });

  // 6. Full scroll stitched: [label]-00-full-scroll.png
  // Reset style overflows to let it expand naturally
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
  const fullScrollPath = resolve(ARTIFACTS, `${label}-00-full-scroll.png`);
  await page.screenshot({ path: fullScrollPath, fullPage: true });

  // Extract info for summary
  const textContent = await page.evaluate(() => document.body?.innerText || '');
  const legendTexts = await page.evaluate(() => {
    const texts = [];
    const elements = document.querySelectorAll('span, text, div');
    const wanted = new Set(['соединение', 'оппозиция', 'тригон', 'квадратура', 'секстиль', 'conjunction', 'opposition', 'trine', 'square', 'sextile']);
    elements.forEach(el => {
      const txt = el.textContent.trim().toLowerCase();
      if (wanted.has(txt)) {
        texts.push(el.textContent.trim());
      }
    });
    return Array.from(new Set(texts));
  });

  // Find all sections by headers
  const sections = await page.evaluate(() => {
    const found = [];
    const keywords = [
      { key: 'summary', text: 'ровный день' },
      { key: 'summary', text: 'поддерживающий день' },
      { key: 'summary', text: 'благоприятный день' },
      { key: 'advice', text: 'конкретно сегодня' },
      { key: 'chart', text: 'карта дня' },
      { key: 'reading', text: 'разбор дня' },
      { key: 'why', text: 'почему так у меня' },
      { key: 'week', text: 'неделя' },
      { key: 'history', text: 'ближайшие дни' },
      { key: 'history', text: 'в этот день' }
    ];
    // Traverse text
    const txt = document.body.innerText.toLowerCase();
    keywords.forEach(kw => {
      if (txt.includes(kw.text)) {
        found.push(kw.key + ':' + kw.text);
      }
    });
    return Array.from(new Set(found));
  });

  // Check raw debug leaks
  const rawDebugStrings = [];
  const piiChecks = [
    'Crisis Transformation Control',
    'Inner Background Unconscious',
    'Money Security Resources',
    'Thinking Speech Learning',
    'Meaning Expansion Vector'
  ];
  piiChecks.forEach(check => {
    if (textContent.includes(check)) rawDebugStrings.push(check);
  });
  // Check for score patterns (e.g. key: 5.54 or similar sphere row leaks)
  const scoreRegex = /\b\d\.\d{2}\b/g;
  const matches = textContent.match(scoreRegex);
  if (matches) {
    rawDebugStrings.push(...matches);
  }

  await browser.close();

  return {
    sections,
    visibleTextSamples: textContent.split('\n').map(t => t.trim()).filter(t => t.length > 5).slice(0, 30),
    chart: {
      found: planetCount > 0,
      legendTexts,
      clickTargetCount: planetCount,
      afterClickVisibleText
    },
    rawDebugStrings
  };
}

async function main() {
  mkdirSync(ARTIFACTS, { recursive: true });
  
  console.log('Capturing 3001...');
  const o = await captureScreenshots(3001, '3001');
  
  console.log('Capturing 7777...');
  const c = await captureScreenshots(7777, 'candidate');

  const summary = {
    date: "2026-07-05",
    oracle: {
      sections: o.sections,
      visibleTextSamples: o.visibleTextSamples,
      chart: o.chart,
      rawDebugStrings: o.rawDebugStrings
    },
    candidate: {
      sections: c.sections,
      visibleTextSamples: c.visibleTextSamples,
      chart: c.chart,
      rawDebugStrings: c.rawDebugStrings
    },
    gaps: []
  };

  // Populate gaps programmatically based on differences
  if (o.chart.clickTargetCount !== c.chart.clickTargetCount) {
    summary.gaps.push(`Chart planet count mismatch: oracle=${o.chart.clickTargetCount}, candidate=${c.chart.clickTargetCount}`);
  }
  if (o.chart.legendTexts.length !== c.chart.legendTexts.length) {
    summary.gaps.push(`Chart legend mismatch: oracle=[${o.chart.legendTexts.join(', ')}], candidate=[${c.chart.legendTexts.join(', ')}]`);
  }
  if (c.rawDebugStrings.length > 0) {
    summary.gaps.push(`Raw debug strings leaked in candidate: ${c.rawDebugStrings.join(', ')}`);
  }

  writeFileSync(resolve(ARTIFACTS, 'summary-v2.json'), JSON.stringify(summary, null, 2));
  console.log('Done. summary-v2.json written.');
}

main().catch(console.error);
