// ############################################################################
// AI_HEADER: MODULE_PLAYWRIGHT_CONFIG
// ROLE: Playwright E2E test configuration (W-TEST-3).
// DEPENDENCIES: @playwright/test
// GRACE_ANCHORS: [E2E_CONFIG]
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-E2E-CONFIG
// purpose: Configure Playwright for E2E tests of Today and Calendar screens
// owns:
//   - playwright.config.ts
// inputs:
//   - playwright CLI invocation
// outputs:
//   - E2E test runner configuration
// dependencies:
//   - @playwright/test
//   - Next.js dev server (http://localhost:3002)
// side_effects:
//   - starts dev server if not running
// invariants:
//   - baseURL MUST be http://localhost:3002
//   - webServer MUST start before tests run
// failure_policy:
//   - invalid config -> playwright exits with error
// non_goals:
//   - unit tests, backend tests
// END_MODULE_CONTRACT: M-TEST-E2E-CONFIG

// START_MODULE_MAP: M-TEST-E2E-CONFIG
// public_entrypoints:
//   - default export (playwright config)
// semantic_blocks:
//   - E2E_CONFIG
// owned_tests:
//   - e2e/**/*.spec.ts
// END_MODULE_MAP: M-TEST-E2E-CONFIG

import { defineConfig, devices } from '@playwright/test';

// START_BLOCK: E2E_CONFIG
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['list'],
  ],
  use: {
    baseURL: 'http://localhost:3002',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'mobile',
      use: { ...devices['iPhone 13'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3002',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});
// END_BLOCK: E2E_CONFIG
