// AI_HEADER
// module: M-TEST-E2E-FIXTURES
// wave: W-2.2
// purpose: Playwright fixtures with Telegram Web App mock

import { test as base } from '@playwright/test';

/**
 * Extended Playwright test with Telegram Web App mock
 * Automatically injects window.Telegram mock before each test
 */
export const test = base.extend({
  page: async ({ page }, use) => {
    // Mock Telegram Web App API for all tests
    await page.addInitScript(() => {
      (window as any).Telegram = {
        WebApp: {
          initData: '',
          initDataUnsafe: {},
          ready: () => {},
          expand: () => {},
          close: () => {},
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
        },
      };
    });

    await use(page);
  },
});

export { expect } from '@playwright/test';
