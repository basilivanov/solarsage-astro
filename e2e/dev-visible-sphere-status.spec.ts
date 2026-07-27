// ############################################################################
// AI_HEADER: E2E_DEV_VISIBLE_SPHERE_STATUS — E2E guard: sphere navigator renders without verdict chips (D2)
// ROLE: Verifies the premium sphere navigator renders rows/details with no verdict status UI until W3.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-DEV-VISIBLE-SPHERE-STATUS
// purpose: Verify that concrete advice rows and details render WITHOUT verdict labels/badges
//          (wave W1 decision D2; honest verdict chips return in W3 after the valence backend).
// owns:
//   - e2e/dev-visible-sphere-status.spec.ts
// inputs: browser navigation to local dev URL
// outputs: Playwright test assertions, screenshot writes
// dependencies: Playwright test, local server
// side_effects: writes browser screenshots to docs/work/2026-07-11_preview-visible-sphere-status-labels/assets/01-work-status-expanded-mobile.png
// emitted_logs: none
// invariants: no concrete-day-advice-row-status / concrete-day-advice-details-status elements exist;
//             details panel keeps aria contract and human guidance text
// failure_policy: fail E2E test
// END_MODULE_CONTRACT: M-E2E-DEV-VISIBLE-SPHERE-STATUS

// START_MODULE_MAP: M-E2E-DEV-VISIBLE-SPHERE-STATUS
// public_entrypoints:
//   - test
// semantic_blocks:
//   - NO_VERDICT_GUARD: proves verdict chips/badges are absent from rows and details
//   - EXPANSION_VERIFICATION: checks Work sphere expand click and details panel guidance
//   - SCREENSHOT_CAPTURE: writes mobile layout reference to docs/work/2026-07-11_preview-visible-sphere-status-labels/assets/01-work-status-expanded-mobile.png
// owned_tests:
//   - e2e/dev-visible-sphere-status.spec.ts
// END_MODULE_MAP: M-E2E-DEV-VISIBLE-SPHERE-STATUS

import { expect, test } from "@playwright/test"
import fs from "node:fs"
import path from "node:path"

const ASSET_PATH = path.join(
  process.cwd(),
  "docs/work/2026-07-11_preview-visible-sphere-status-labels/assets/01-work-status-expanded-mobile.png",
)

test("shows sphere rows without verdict chips and expanded Work details in the local fixture", async ({ page }) => {
  await page.goto("/day/2026-07-08?fixture=three-horizon-timing&why=1")

  const fixture = page.getByTestId("dev-timing-fixture")
  await expect(fixture).toBeVisible()
  const navigator = fixture.getByTestId("concrete-day-advice")

  // D2: no verdict chips/badges anywhere in the navigator
  await expect(navigator.getByTestId("concrete-day-advice-row-status")).toHaveCount(0)

  const work = navigator.getByTestId("concrete-day-advice-row").filter({ has: page.getByText("Работа", { exact: true }) })
  await work.click()
  await expect(work).toHaveAttribute("aria-expanded", "true")
  const details = navigator.getByTestId("concrete-day-advice-details")
  await expect(details).toBeVisible()
  await expect(details.getByTestId("concrete-day-advice-details-status")).toHaveCount(0)
  await expect(details).toContainText("Что поможет")

  fs.mkdirSync(path.dirname(ASSET_PATH), { recursive: true })
  const screen = fixture.getByTestId("today-screen")
  const [navigatorHeight, screenHeight] = await Promise.all([
    navigator.evaluate((element) => Math.ceil(element.scrollHeight)),
    screen.evaluate((element) => Math.ceil(element.scrollHeight)),
  ])
  await page.setViewportSize({ width: 390, height: Math.max(navigatorHeight, screenHeight) + 96 })
  await screen.evaluate((element) => element.parentElement?.scrollTo({ top: 0 }))
  await navigator.scrollIntoViewIfNeeded()
  await navigator.screenshot({ path: ASSET_PATH })
})
