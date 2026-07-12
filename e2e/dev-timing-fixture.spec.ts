// ############################################################################
// AI_HEADER: E2E_DEV_TIMING_FIXTURE — E2E test verifying three-horizon timing fixture isolation
// ROLE: Tests the development-only fixture loader and verifies visual rendering of three horizons.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-DEV-TIMING-FIXTURE
// purpose: Verify three-horizon timing fixture UI features are loaded and styled in mobile viewport.
// owns:
//   - e2e/dev-timing-fixture.spec.ts
// inputs: browser navigation to local dev URL
// outputs: Playwright test assertions, screenshot writes
// dependencies: Playwright test, local server
// side_effects: writes browser screenshot to docs/work/2026-07-11_today-v2-real-horizons-main-deploy/b1/01-backend-contract-horizons-mobile.png
// emitted_logs: none
// invariants: fixture делает только guarded fixture API request, обычный route не активирует fixture, три timing blocks соответствуют payload
// failure_policy: fail E2E test
// END_MODULE_CONTRACT: M-E2E-DEV-TIMING-FIXTURE

// START_MODULE_MAP: M-E2E-DEV-TIMING-FIXTURE
// public_entrypoints:
//   - test
// semantic_blocks:
//   - TIMING_VERIFICATION: verifies backend horizon details and stages for three horizons
//   - INTERCEPTION_VERIFICATION: ensures auth and ordinary APIs are not triggered in fixture mode
//   - DATE_ROUTING_VERIFICATION: verifies navigating to other dates strips the fixture query
//   - SCREENSHOT_CAPTURE: writes mobile layout reference to docs/work/2026-07-11_today-v2-real-horizons-main-deploy/b1/01-backend-contract-horizons-mobile.png
// owned_tests:
//   - e2e/dev-timing-fixture.spec.ts
// END_MODULE_MAP: M-E2E-DEV-TIMING-FIXTURE

import { expect, test } from "@playwright/test"
import fs from "node:fs"
import path from "node:path"

const ASSET_PATH = path.join(
  process.cwd(),
  "docs/work/2026-07-11_today-v2-real-horizons-main-deploy/b1/01-backend-contract-horizons-mobile.png",
)

test("isolates the development-only three-horizon timing fixture from normal APIs", async ({ page, browser }) => {
  const apiRequests = new Set<string>()
  page.on("request", (request) => {
    const pathname = new URL(request.url()).pathname
    if (pathname.startsWith("/api/")) apiRequests.add(pathname)
  })

  await page.goto("/day/2026-07-08?fixture=three-horizon-timing&why=1")

  const fixture = page.getByTestId("dev-timing-fixture")
  await expect(fixture).toBeVisible()
  const timing = fixture.getByTestId("why-horizon-timing")
  await expect(timing).toHaveCount(3)
  const horizons = fixture.getByTestId("why-horizons")
  await expect(horizons).toHaveAttribute("data-source", "backend-horizons")
  const long = fixture.locator('[data-testid="why-horizon"][data-horizon="long"]')
  const medium = fixture.locator('[data-testid="why-horizon"][data-horizon="medium"]')
  const fast = fixture.locator('[data-testid="why-horizon"][data-horizon="fast"]')
  await expect(long.getByTestId("why-horizon-tone")).toHaveAttribute("data-status", "mixed")
  await expect(medium.getByTestId("why-horizon-tone")).toHaveAttribute("data-status", "mixed")
  await expect(fast.getByTestId("why-horizon-tone")).toHaveAttribute("data-status", "tense")
  await expect(long).toContainText("Фон уже действует")
  await expect(medium).toContainText("Набирает силу")
  await expect(medium).toContainText("Точный пик — 10 июля, 14:32 по Москве")
  await expect(fast).toContainText("Пик уже пройден")
  await expect(fixture.getByTestId("why-horizon-technical-toggle").first()).toHaveAttribute("aria-expanded", "false")
  await fixture.getByTestId("why-horizon-technical-toggle").first().click()
  await expect(fixture.getByTestId("why-horizon-technical-content")).toContainText("Профекция")
  await fast.getByTestId("why-horizon-technical-toggle").click()
  await expect(fast.getByTestId("why-horizon-technical-content")).toContainText("С 8 по 10 июля по Москве")
  await fixture.getByTestId("why-horizon-sphere").filter({ hasText: "Работа" }).first().click()
  await expect(fixture.getByTestId("concrete-day-advice-details")).toHaveAttribute("data-sphere-key", "work")
  expect([...apiRequests]).toEqual(["/api/dev-fixtures/three-horizon-timing"])
  fs.mkdirSync(path.dirname(ASSET_PATH), { recursive: true })
  const why = fixture.getByTestId("why-expanded")
  const screen = fixture.getByTestId("today-screen")
  const [whyHeight, screenHeight] = await Promise.all([
    why.evaluate((element) => Math.ceil(element.scrollHeight)),
    screen.evaluate((element) => Math.ceil(element.scrollHeight)),
  ])
  await page.setViewportSize({ width: 390, height: Math.max(whyHeight, screenHeight) + 96 })
  await screen.evaluate((element) => element.parentElement?.scrollTo({ top: 0 }))
  await why.scrollIntoViewIfNeeded()
  await why.screenshot({ path: ASSET_PATH })

  const normalContext = await browser.newContext()
  const normalPage = await normalContext.newPage()
  const normalApiRequests = new Set<string>()
  normalPage.on("request", (request) => {
    const pathname = new URL(request.url()).pathname
    if (pathname.startsWith("/api/")) normalApiRequests.add(pathname)
  })
  await normalPage.goto("/day/2026-07-08?why=1")
  await normalPage.waitForTimeout(500)
  await expect(normalPage.getByTestId("dev-timing-fixture")).toHaveCount(0)
  expect([...normalApiRequests]).not.toContain("/api/dev-fixtures/three-horizon-timing")
  expect([...normalApiRequests].some((pathname) => /^\/api\/(auth|profile|day|calendar)/.test(pathname))).toBe(true)
  await normalContext.close()

  const otherDateContext = await browser.newContext()
  const otherDatePage = await otherDateContext.newPage()
  const otherDateApiRequests = new Set<string>()
  otherDatePage.on("request", (request) => {
    const pathname = new URL(request.url()).pathname
    if (pathname.startsWith("/api/")) otherDateApiRequests.add(pathname)
  })
  await otherDatePage.goto("/day/2026-07-09?fixture=three-horizon-timing&why=1")
  await otherDatePage.waitForTimeout(500)
  await expect(otherDatePage.getByTestId("dev-timing-fixture")).toHaveCount(0)
  expect([...otherDateApiRequests]).not.toContain("/api/dev-fixtures/three-horizon-timing")
  await otherDateContext.close()
})
