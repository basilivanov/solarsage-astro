// ############################################################################
// AI_HEADER: MODULE_E2E_TODAY_CONVERGENCE_REAL_SPEC — real Today/calendar/check-in gate.
// ROLE: Verifies the generated Today and calendar contracts against a real Telegram-authenticated API.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-TODAY-CONVERGENCE-REAL-SPEC
// purpose: Run the minimal real-stack Today convergence, calendar/v2, and check-in acceptance paths without route interception.
// owns:
//   - e2e/today-convergence.spec.ts
// inputs: E2E_BASE_URL, real Telegram HMAC fixtures, and real API data.
// outputs: Today root/state assertions, twelve sphere tiles, calendar dayState, and pre-submit check-in contract.
// dependencies: e2e/fixtures.ts; real API/frontend stack.
// side_effects: real onboarding, referral grant, and disposable E2E users tracked by the shared cleanup ledger.
// emitted_logs: none.
// invariants:
//   - No page.route or mock interception is used.
//   - Tests skip clearly when E2E_BASE_URL is absent.
//   - Dynamic copy is never the sole assertion target.
// failure_policy: real transport, auth, contract, and accessibility failures fail the test.
// END_MODULE_CONTRACT: M-E2E-TODAY-CONVERGENCE-REAL-SPEC

// START_MODULE_MAP: M-E2E-TODAY-CONVERGENCE-REAL-SPEC
// public_entrypoints:
//   - real Today convergence contract
//   - real calendar/check-in contract
// semantic_blocks:
//   - TODAY_READY: onboarding/referral access and Today state axes.
//   - CALENDAR_CHECKIN: calendar/v2 dayState plus hidden pre-submit recap.
// owned_tests:
//   - self
// END_MODULE_MAP: M-E2E-TODAY-CONVERGENCE-REAL-SPEC

import {
  completeOnboarding,
  expect,
  grantReferralAccess,
  test,
} from "./fixtures"

const REAL_E2E_SKIP_REASON = "Skipped: E2E_BASE_URL is not set; this suite requires a real Telegram-authenticated stack."
const DAY_TIMEOUT = 240_000
const PRODUCT_SPHERE_KEYS = [
  "work",
  "finance",
  "documents",
  "relationships",
  "sport",
  "communication",
  "health",
  "home_family",
  "travel",
  "creativity",
  "study",
  "friends_goals",
] as const

test.describe("Today Convergence — Real API", () => {
  test.skip(!process.env.E2E_BASE_URL, REAL_E2E_SKIP_REASON)
  test.use({ uniqueTelegramUser: true })

  // START_BLOCK: TODAY_READY
  test("reaches Today ready state with the generated DOM contract", async ({ page, browser, baseURL }, testInfo) => {
    test.setTimeout(DAY_TIMEOUT)
    await page.addInitScript(() => {
      localStorage.clear()
      sessionStorage.clear()
    })
    await page.goto("/onboarding")
    await completeOnboarding(page)
    await grantReferralAccess(page, browser, baseURL, testInfo)

    await page.goto("/day/today")
    const screen = page.getByTestId("today-screen")
    await expect(screen).toHaveAttribute("data-screen-state", "ready", { timeout: 150_000 })
    await expect(screen).toHaveAttribute("data-state", /^(convergence_today|quiet_day|unavailable)$/)
    await expect(screen).toHaveAttribute("data-content-state", /^(ready|pending|unavailable|not_needed)$/)
    await expect(screen).toHaveAttribute("data-access-state", /^(full|preview|locked)$/)
    await expect(screen).toHaveAttribute("data-birth-time-mode", /^(exact|bucket|unknown)$/)
    const tone = await screen.getAttribute("data-day-tone")
    if (tone !== null) expect(tone).toMatch(/^(steady|supportive|mixed|tense)$/)
    await expect(page.getByTestId("sphere-navigator")).toBeVisible()
    const tiles = page.locator('button[data-testid^="sphere-tile-"]')
    await expect(tiles).toHaveCount(PRODUCT_SPHERE_KEYS.length)
    expect(
      await tiles.evaluateAll((elements) => elements.map((element) => element.getAttribute("data-testid"))),
    ).toEqual(PRODUCT_SPHERE_KEYS.map((key) => `sphere-tile-${key}`))

    const state = await screen.getAttribute("data-state")
    if (state === "convergence_today") {
      await expect(page.getByTestId("convergence-hero")).toBeVisible()
    } else if (state === "quiet_day") {
      await expect(page.getByTestId("sphere-navigator")).toBeVisible()
    } else {
      await expect(page.getByTestId("today-unavailable")).toBeVisible()
    }

    const contentState = await screen.getAttribute("data-content-state")
    if (contentState === "pending") {
      await expect(screen).not.toHaveAttribute("data-content-state", "pending", { timeout: 130_000 })
    }
  })
  // END_BLOCK: TODAY_READY

  // START_BLOCK: CALENDAR_CHECKIN
  test("renders calendar/v2 dayState and keeps check-in recap hidden before submit", async ({ page }) => {
    test.setTimeout(DAY_TIMEOUT)
    await page.addInitScript(() => {
      localStorage.clear()
      sessionStorage.clear()
    })
    await page.goto("/onboarding")
    await completeOnboarding(page)
    await page.goto("/calendar")

    const calendar = page.getByTestId("calendar-screen")
    await expect(calendar).toHaveAttribute("data-state", "ready", { timeout: 30_000 })
    const days = page.locator('[data-testid^="calendar-day-"]')
    await expect(days.first()).toBeVisible({ timeout: 15_000 })
    await expect(days.first()).toHaveAttribute("data-day-state", /^(hero|ordinary|not-computed)$/)

    await page.goto("/checkin?target=yesterday")
    await expect(page.getByTestId("checkin-screen")).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId("checkin-post-submit")).toHaveCount(0)
    await expect(page.getByTestId("yesterday-forecast-recap")).toHaveCount(0)
    await expect(page.getByTestId("mood-4")).toBeVisible({ timeout: 15_000 })
  })
  // END_BLOCK: CALENDAR_CHECKIN
})
