import { chromium } from '@playwright/test';
import { execSync } from 'child_process';

async function main() {
  // Generate initData via Python
  const initData = execSync(
    `python3 scripts/generate-telegram-test-initdata.py 2>/dev/null | grep "^query_id=" | head -1`,
    { encoding: 'utf-8' }
  ).trim();

  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 375, height: 812 } });
  const page = await context.newPage();

  // Inject Telegram WebApp with real initData
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
          text: '', color: '', textColor: '', isVisible: false, isActive: true, isProgressVisible: false,
          setText: () => {}, onClick: () => {}, offClick: () => {}, show: () => {}, hide: () => {},
          enable: () => {}, disable: () => {}, showProgress: () => {}, hideProgress: () => {},
        },
        BackButton: {
          isVisible: false,
          onClick: () => {}, offClick: () => {}, show: () => {}, hide: () => {},
        },
        HapticFeedback: {
          impactOccurred: () => {}, notificationOccurred: () => {}, selectionChanged: () => {},
        },
        onEvent: () => {}, offEvent: () => {}, sendData: () => {},
        switchInlineQuery: () => {}, openLink: () => {}, openTelegramLink: () => {},
        openInvoice: () => {}, showPopup: () => {}, showAlert: () => {}, showConfirm: () => {},
      },
    };
  }, initData);

  // Mark as onboarded to see day page
  await page.addInitScript(() => {
    localStorage.setItem('lumen:onboarded', '1');
  });

  const pages = ['/', '/day/today', '/calendar', '/profile', '/chat', '/onboarding'];
  
  for (const path of pages) {
    console.log(`Navigating to ${path}...`);
    await page.goto(`https://dev.astro.vasiliy-ivanov.ru${path}`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);
    
    const name = path === '/' ? 'home' : path.replace(/\//g, '-').replace(/^-/, '');
    await page.screenshot({ path: `/tmp/prod-${name}.png`, fullPage: false });
    console.log(`  Saved /tmp/prod-${name}.png`);
  }

  await browser.close();
  console.log('Done');
}

main().catch(console.error);
