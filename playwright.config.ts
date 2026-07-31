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
//   - E2E_BASE_URL optional base URL override
//   - E2E_WORKERS optional positive integer worker override for local runs
// outputs:
//   - E2E test runner configuration
// dependencies:
//   - @playwright/test
//   - local or deployed frontend selected by E2E_BASE_URL
// side_effects:
//   - none
// invariants:
//   - default e2e worker count is 1 for deterministic visual/readiness gates
//   - CI worker count is always 1
//   - E2E_WORKERS must be a positive integer when provided outside CI
// failure_policy:
//   - invalid config or invalid E2E_WORKERS -> playwright exits with error
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
function configuredWorkers(): number {
  if (process.env.CI) return 1;

  const raw = process.env.E2E_WORKERS;
  if (raw == null || raw === '') return 1;

  const parsed = Number(raw);
  if (!Number.isInteger(parsed) || parsed < 1) {
    throw new Error('E2E_WORKERS must be a positive integer when set');
  }

  return parsed;
}

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  // E2E visual/readiness specs share one app server and auth/runtime setup.
  // Keep the default deterministic; opt into local parallelism explicitly.
  workers: configuredWorkers(),
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['list'],
  ],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3002',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  // Visual regression testing config
  expect: {
    toHaveScreenshot: {
      maxDiffPixels: 100, // допустимая разница в пикселях
      threshold: 0.2, // 20% допустимой разницы
    },
    timeout: 15000, // Увеличенный таймаут для всех expect утверждений (включая toHaveScreenshot)
  },
  // Update snapshots with --update-snapshots flag; do not create missing snapshots by default (fail-closed policy)
  updateSnapshots: process.env.UPDATE_SNAPSHOTS === 'true' ? 'all' : 'none',
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'mobile',
      use: { ...devices['iPhone 13'] },
    },
    {
      name: 'webkit-smoke',
      grep: /@webkit-smoke/,
      use: { ...devices['Desktop Safari'] },
    },
  ],
  // webServer disabled - tests run against deployed environment
  // webServer: {
  //   command: 'npm run dev',
  //   url: 'http://localhost:3002',
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 120000,
  // },
});
// END_BLOCK: E2E_CONFIG
