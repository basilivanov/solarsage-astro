// ############################################################################
// AI_HEADER: E2E_DEV_VISIBLE_SPHERE_STATUS — E2E test verifying semantic sphere status labels
// ROLE: Verifies that semantic status badge and expanded sphere details render correctly.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-DEV-VISIBLE-SPHERE-STATUS
// purpose: Verify verdict label values (Поддержка/Ровно/Внимание/Отложить) and Work badge expansion.
// owns:
//   - e2e/dev-visible-sphere-status.spec.ts
// inputs: browser navigation to local dev URL
// outputs: Playwright test assertions, screenshot writes
// dependencies: Playwright test, local server
// side_effects: writes browser screenshots to docs/work/2026-07-11_preview-visible-sphere-status-labels/assets/01-work-status-expanded-mobile.png
// emitted_logs: none
// invariants: четыре verdict enum имеют стабильные visible labels/data-status, раскрытый Work сохраняет aria/data-status contract
// failure_policy: fail E2E test
// END_MODULE_CONTRACT: M-E2E-DEV-VISIBLE-SPHERE-STATUS

// START_MODULE_MAP: M-E2E-DEV-VISIBLE-SPHERE-STATUS
// public_entrypoints:
//   - test
// semantic_blocks:
//   - VERDICT_LABELS_VERIFICATION: verifies all 4 status label representations
//   - EXPANSION_VERIFICATION: checks Work sphere expand click, badge states, and details panel visibility
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

test("shows visible semantic statuses and expanded Work badge in the local fixture", async ({ page }) => {
  await page.goto("/day/2026-07-08?fixture=three-horizon-timing&why=1")

  const fixture = page.getByTestId("dev-timing-fixture")
  await expect(fixture).toBeVisible()
  const navigator = fixture.getByTestId("concrete-day-advice")
  const statusByVerdict = {
    good: "Поддержка",
    neutral: "Ровно",
    caution: "Внимание",
    avoid: "Отложить",
  }
  for (const [verdict, copy] of Object.entries(statusByVerdict)) {
    const status = navigator.getByTestId("concrete-day-advice-row-status").filter({ hasText: copy }).first()
    await expect(status).toHaveAttribute("data-status", verdict)
  }

  const work = navigator.getByTestId("concrete-day-advice-row").filter({ has: page.getByText("Работа", { exact: true }) })
  await work.click()
  await expect(work).toHaveAttribute("data-status", "caution")
  await expect(work).toHaveAttribute("aria-expanded", "true")
  const details = navigator.getByTestId("concrete-day-advice-details")
  await expect(details).toHaveAttribute("data-status", "caution")
  await expect(details.getByTestId("concrete-day-advice-details-status")).toHaveText("Требует внимания")
  await expect(details).toContainText("Что может проявиться")
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
