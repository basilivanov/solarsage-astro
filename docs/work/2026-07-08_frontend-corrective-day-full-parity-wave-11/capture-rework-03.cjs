// Wave 11 Rework 03 Oracle Pixel Parity Capture Script.
// Run from repo root: node docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/capture-rework-03.cjs

const { chromium, request } = require('/opt/solarsage-astro/node_modules/.pnpm/@playwright+test@1.60.0/node_modules/@playwright/test/index.js');
const { execFileSync } = require('child_process');
const { mkdirSync, writeFileSync } = require('fs');
const { resolve } = require('path');

const PROJ = '/opt/solarsage-astro';
const ARTIFACTS = resolve(PROJ, 'docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/pixel-rework-03');
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

async function capturePort(port, label) {
  const url = `http://127.0.0.1:${port}/day/2026-07-05`;
  const initData = genInitData();

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: VIEWPORT });
  const page = await context.newPage();

  // Auth (only needed for candidate, but safe for both)
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

  // Scroll helper using text anchors
  const scrollToText = async (textPatterns) => {
    await page.evaluate((patterns) => {
      const scrollRoot = document.querySelector('.flex-1.overflow-y-auto.overscroll-contain, body');
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
      if (targetElement) {
        if (scrollRoot.tagName === 'BODY') {
          targetElement.scrollIntoView();
        } else {
          const rect = targetElement.getBoundingClientRect();
          const rootRect = scrollRoot.getBoundingClientRect();
          scrollRoot.scrollTop = rect.top - rootRect.top + scrollRoot.scrollTop - 20;
          scrollRoot.dispatchEvent(new Event('scroll', { bubbles: true }));
        }
      }
    }, textPatterns);
    await page.waitForTimeout(600);
  };

  // Wait for concrete advice section to render
  const isOracle = label === 'oracle';
  if (isOracle) {
    await page.locator('text=/конкретно сегодня/i').first().waitFor({ state: 'visible', timeout: 10000 });
  } else {
    await page.getByTestId("concrete-day-advice").waitFor({ state: 'visible', timeout: 10000 });
  }

  // 1. Concrete Collapsed: [label]-concrete-collapsed.png
  await scrollToText(['КОНКРЕТНО СЕГОДНЯ', 'Конкретно сегодня']);
  await page.screenshot({ path: resolve(ARTIFACTS, `${label}-concrete-collapsed.png`), fullPage: false });

  const collapsedRowCount = await page.evaluate((oracle) => {
    const selector = oracle
      ? 'section div.divide-y > div'
      : '[data-testid="concrete-day-advice-row"]';
    // Only find the section that belongs to Concrete Advice
    const section = oracle
      ? Array.from(document.querySelectorAll('section')).find(s => /конкретно сегодня/i.test(s.textContent || ""))
      : document.querySelector('[data-testid="concrete-day-advice"]');
    if (!section) return 0;
    const rows = section.querySelectorAll(selector);
    return Array.from(rows).filter(r => r.getBoundingClientRect().height > 0).length;
  }, isOracle);

  const toggleTextBefore = await page.evaluate((oracle) => {
    const section = oracle
      ? Array.from(document.querySelectorAll('section')).find(s => /конкретно сегодня/i.test(s.textContent || ""))
      : document.querySelector('[data-testid="concrete-day-advice"]');
    if (!section) return "";
    const btn = section.querySelector('button');
    return btn ? btn.textContent.trim() : "";
  }, isOracle);

  // 2. Concrete Expanded: [label]-concrete-expanded.png
  // Click expand using Playwright locator
  const expandBtn = isOracle
    ? page.locator('section').filter({ hasText: /конкретно сегодня/i }).locator('button').first()
    : page.getByTestId('concrete-day-advice').locator('button[aria-controls="concrete-day-advice-rows"]').first();
  await expandBtn.click();
  await page.waitForTimeout(600);
  await page.screenshot({ path: resolve(ARTIFACTS, `${label}-concrete-expanded.png`), fullPage: false });

  const expandedRowCount = await page.evaluate((oracle) => {
    const selector = oracle
      ? 'section div.divide-y > div'
      : '[data-testid="concrete-day-advice-row"]';
    const section = oracle
      ? Array.from(document.querySelectorAll('section')).find(s => /конкретно сегодня/i.test(s.textContent || ""))
      : document.querySelector('[data-testid="concrete-day-advice"]');
    if (!section) return 0;
    const rows = section.querySelectorAll(selector);
    return Array.from(rows).filter(r => r.getBoundingClientRect().height > 0).length;
  }, isOracle);

  const toggleTextAfter = await page.evaluate((oracle) => {
    const section = oracle
      ? Array.from(document.querySelectorAll('section')).find(s => /конкретно сегодня/i.test(s.textContent || ""))
      : document.querySelector('[data-testid="concrete-day-advice"]');
    if (!section) return "";
    const btn = section.querySelector('button');
    return btn ? btn.textContent.trim() : "";
  }, isOracle);

  // Extract exactly 12 row objects in expanded state
  const rows = await page.evaluate((oracle) => {
    const list = [];
    const selector = oracle
      ? 'section div.divide-y > div'
      : '[data-testid="concrete-day-advice-row"]';
    const section = oracle
      ? Array.from(document.querySelectorAll('section')).find(s => /конкретно сегодня/i.test(s.textContent || ""))
      : document.querySelector('[data-testid="concrete-day-advice"]');
    if (!section) return [];
    const elements = section.querySelectorAll(selector);
    elements.forEach(row => {
      const spans = row.querySelectorAll('span');
      if (spans.length >= 3) {
        list.push({
          icon: spans[0].textContent.trim(),
          label: spans[1].textContent.trim(),
          text: spans[2].textContent.trim(),
          status: row.getAttribute('data-status') || ""
        });
      }
    });
    return list;
  }, isOracle);

  // Concrete advice counts from header
  const headerCounts = await page.evaluate((oracle) => {
    const section = oracle
      ? Array.from(document.querySelectorAll('section')).find(s => /конкретно сегодня/i.test(s.textContent || ""))
      : document.querySelector('[data-testid="concrete-day-advice"]');
    if (!section) return "section not found";
    const header = section.querySelector('div.flex.items-center.justify-between.border-b');
    return header ? header.innerText.trim().replace(/\n/g, ' ') : "header not found";
  }, isOracle);

  // 3. Chart Before (scroll to chart and wait)
  await scrollToText(['КАРТА ДНЯ', 'карта дня']);

  // Aspect legend labels
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

  // 4. Chart After Click: [label]-chart-after-click.png
  // Click first planet marker
  const planet = page.locator('[data-testid="day-chart-planet"], svg g.cursor-pointer').first();
  if (await planet.isVisible().catch(() => false)) {
    await planet.click();
    await page.waitForTimeout(800);
  }
  await page.screenshot({ path: resolve(ARTIFACTS, `${label}-chart-after-click.png`), fullPage: false });

  // Focus outline check
  const hasFocusOutline = await page.evaluate(() => {
    const planet = document.querySelector('[data-testid="day-chart-planet"], svg g.cursor-pointer');
    if (planet) {
      const outline = window.getComputedStyle(planet).outlineStyle;
      return outline !== 'none' && outline !== '';
    }
    return false;
  });

  // Webkit tap highlight color check
  const webkitTapHighlightColor = await page.evaluate(() => {
    const planet = document.querySelector('[data-testid="day-chart-planet"], svg g.cursor-pointer');
    if (planet) {
      return window.getComputedStyle(planet).webkitTapHighlightColor || "";
    }
    return "";
  });

  await browser.close();

  return {
    rows,
    collapsedRowCount,
    expandedRowCount,
    headerCounts,
    toggleTextBefore,
    toggleTextAfter,
    legendLabels,
    hasFocusOutline,
    webkitTapHighlightColor
  };
}

async function main() {
  mkdirSync(ARTIFACTS, { recursive: true });

  console.log('Capturing 3001...');
  const o = await capturePort(3001, 'oracle');

  console.log('Capturing 7777...');
  const c = await capturePort(7777, 'candidate');

  // Count placeholder and unavailable rows in candidate
  let placeholderCount = 0;
  let unavailableCount = 0;
  let goodCount = 0;
  let cautionCount = 0;

  c.rows.forEach(r => {
    if (r.text.includes('Нет отдельного сигнала') || r.text.includes('Данные появятся')) {
      placeholderCount++;
    }
    if (r.status === 'unavailable') {
      unavailableCount++;
    }
    if (r.status === 'good') {
      goodCount++;
    }
    if (r.status === 'caution' || r.status === 'avoid') {
      cautionCount++;
    }
  });

  const summary = {
    date: "2026-07-05",
    oracle: {
      rows: o.rows,
      collapsedRowCount: o.collapsedRowCount,
      expandedRowCount: o.expandedRowCount,
      headerCounts: o.headerCounts,
      toggleTextBefore: o.toggleTextBefore,
      toggleTextAfter: o.toggleTextAfter,
      legendLabels: o.legendLabels,
    },
    candidate: {
      rows: c.rows,
      collapsedRowCount: c.collapsedRowCount,
      expandedRowCount: c.expandedRowCount,
      headerCounts: c.headerCounts,
      toggleTextBefore: c.toggleTextBefore,
      toggleTextAfter: c.toggleTextAfter,
      legendLabels: c.legendLabels,
      placeholderTextCount: placeholderCount,
      unavailableStatusCount: unavailableCount,
      goodCount: goodCount,
      cautionCount: cautionCount,
      hasFocusOutline: c.hasFocusOutline,
      webkitTapHighlightColor: c.webkitTapHighlightColor
    }
  };

  writeFileSync(resolve(ARTIFACTS, 'summary.json'), JSON.stringify(summary, null, 2));
  console.log('Done. summary.json written.');
}

main().catch(console.error);
