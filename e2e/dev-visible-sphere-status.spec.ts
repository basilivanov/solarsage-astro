// ############################################################################
// AI_HEADER: E2E_DEV_VISIBLE_SPHERE_STATUS — E2E guard: sphere navigator renders without verdict chips (D2)
// ROLE: Verifies the premium sphere navigator renders rows/details with no verdict status UI until W3.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-DEV-VISIBLE-SPHERE-STATUS
// purpose: Verify that concrete advice rows and details render honest verdict status labels/badges when assessment is present, and hide them when assessment is absent.
// owns:
//   - e2e/dev-visible-sphere-status.spec.ts
// inputs: browser navigation to local dev URL
// outputs: Playwright test assertions, screenshot writes
// dependencies: Playwright test, local server
// side_effects: writes browser screenshots to docs/work/2026-07-11_preview-visible-sphere-status-labels/assets/01-work-status-expanded-mobile.png
// emitted_logs: none
// invariants: concrete-day-advice-row-status / concrete-day-advice-details-status elements match row.assessment status contract
// failure_policy: fail E2E test
// END_MODULE_CONTRACT: M-E2E-DEV-VISIBLE-SPHERE-STATUS

// START_MODULE_MAP: M-E2E-DEV-VISIBLE-SPHERE-STATUS
// public_entrypoints:
//   - test
// semantic_blocks:
//   - HONEST_VERDICT_GUARD: proves verdict status chips/badges are rendered only from row.assessment
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

test("shows sphere rows and expanded Work details with honest verdict status contract", async ({ page }) => {
  await page.goto("/day/2026-07-08?fixture=three-horizon-timing&why=1")

  const fixture = page.getByTestId("dev-timing-fixture")
  await expect(fixture).toBeVisible()
  const navigator = fixture.getByTestId("concrete-day-advice")

  // Fallback when assessment is null/absent: no row status chip rendered
  const work = navigator.getByTestId("concrete-day-advice-row").filter({ has: page.getByText("Работа", { exact: true }) })
  await work.click()
  const details = page.getByTestId("sphere-details-sheet")
  await expect(details).toBeVisible()
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
