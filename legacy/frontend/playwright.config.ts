import { defineConfig, devices } from "@playwright/test"

/**
 * E2E канон Lumen mini-app.
 *
 * Один веб-сервер (next dev на :3000), один проект (мобильный Safari —
 * это близко к реальному окружению Telegram WebApp на iOS).
 * Тесты живут в `e2e/` и стартуют приложение через initData (см. `e2e/telegram.ts`).
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",

  /* Snapshot settings for visual regression */
  snapshotDir: "./e2e/__snapshots__",
  snapshotPathTemplate: "{snapshotDir}/{testFilePath}/{arg}{ext}",

  expect: {
    toHaveScreenshot: {
      /* Allow 0.5% pixel diff to handle antialiasing/rendering variance */
      maxDiffPixelRatio: 0.005,
      /* Animations must be disabled for stable screenshots */
      animations: "disabled",
      /* Wait for fonts to load */
      caret: "hide",
    },
  },

  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
    /* Consistent viewport for screenshots */
    screenshot: "only-on-failure",
  },

  projects: [
    {
      name: "mobile-safari",
      use: { ...devices["iPhone 14"] },
    },
  ],

  webServer: {
    command: "pnpm dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
