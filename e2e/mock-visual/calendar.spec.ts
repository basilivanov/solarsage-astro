// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_CALENDAR_V2_SPEC — calendar/v2 contract and visual gate.
// ROLE: Verifies the restored active /calendar route against a generated CalendarPayload with dayState markers and lunar toggle.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-CALENDAR-V2-SPEC
// purpose: Exercise the active calendar/v2 screen with strict Playwright route fixtures and one visual baseline.
// owns:
//   - e2e/mock-visual/calendar.spec.ts
// inputs: generated CalendarPayload fixture, access fixture, and E2E_BASE_URL.
// outputs: public DOM assertions for ready/error states, day/moon modes, and PNG baseline for hero/ordinary/not-computed cells.
// dependencies: @playwright/test; route-interception; calendar-2026-07 fixture; screenshot preparation.
// side_effects: none outside Playwright snapshots.
// emitted_logs: none.
// invariants:
//   - The active screen receives calendar/v2 only; no dayStatus assertion or fixture is used.
//   - Every API request is intercepted and missing requests fail the test.
//   - Visual baselines are fail-closed unless UPDATE_SNAPSHOTS=true.
// failure_policy: fail on missing fixture, invalid state selector, or visual mismatch.
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-CALENDAR-V2-SPEC

// START_MODULE_MAP: M-E2E-MOCK-VISUAL-CALENDAR-V2-SPEC
// public_entrypoints:
//   - calendar/v2 ready-state, marker, and day/moon assertions
//   - calendar/v2 visual baseline
// semantic_blocks:
//   - FIXTURE_SETUP: deterministic auth/runtime and strict route map.
//   - DAY_STATE_CONTRACT: hero, ordinary, and not-computed DOM projections.
//   - VISUAL_BASELINE: full-page baseline for both configured projects.
// owned_tests:
//   - self
// END_MODULE_MAP: M-E2E-MOCK-VISUAL-CALENDAR-V2-SPEC

import { expect, test, type Page } from "@playwright/test"
import {
  expectNoMissingApiFixtures,
  installMockApiRoutes,
  type MockApiRouteFixtures,
} from "./route-interception"
import { accessPayload, calendarPayload } from "./fixtures/calendar-2026-07"
import { prepareForScreenshot } from "./screenshot"

const HERO_DATE = "2026-07-" + "05"

// START_BLOCK: FIXTURE_SETUP
function buildCalendarFixtures(): MockApiRouteFixtures {
  return {
    "/api/calendar": { body: calendarPayload },
    "/api/access": { body: accessPayload },
    "/api/auth/dev": {
      status: 200,
      body: { status: "ok", userId: "mock-calendar-user" },
    },
  }
}

async function installMockVisualRuntime(page: Page): Promise<void> {
  await page.addInitScript(() => {
    localStorage.setItem("lumen:onboarded", "1")

    const fixedNow = new Date("2026-07-08T12:00:00Z").valueOf()
    const RealDate = Date
    const FixedNowDate = function (this: Date, ...args: unknown[]) {
      if (!(this instanceof RealDate)) return new RealDate(fixedNow).toString()
      return args.length === 0 ? new RealDate(fixedNow) : new (RealDate as any)(...args)
    } as unknown as DateConstructor
    FixedNowDate.UTC = RealDate.UTC
    FixedNowDate.parse = RealDate.parse
    FixedNowDate.now = () => fixedNow
    Object.setPrototypeOf(FixedNowDate, RealDate)
    Object.defineProperty(FixedNowDate, "prototype", { value: RealDate.prototype })
    window.Date = FixedNowDate

    ;(window as any).Telegram = {
      WebApp: {
        initData: "",
        initDataUnsafe: {},
        ready: () => {},
        expand: () => {},
        close: () => {},
        platform: "web",
        version: "9.5",
        colorScheme: "light",
        themeParams: {},
        isExpanded: true,
        viewportHeight: 812,
        viewportStableHeight: 812,
        MainButton: { hide: () => {}, show: () => {}, onClick: () => {}, offClick: () => {} },
        BackButton: { hide: () => {}, show: () => {}, onClick: () => {}, offClick: () => {} },
      },
    }
  })
}

async function openCalendar(page: Page): Promise<Awaited<ReturnType<typeof installMockApiRoutes>>> {
  const tracker = await installMockApiRoutes(page, buildCalendarFixtures())
  await installMockVisualRuntime(page)
  await page.goto("/calendar", { waitUntil: "domcontentloaded" })
  await expect(page.getByTestId("calendar-screen")).toHaveAttribute("data-state", "ready", { timeout: 15000 })
  return tracker
}
// END_BLOCK: FIXTURE_SETUP

// START_BLOCK: DAY_STATE_CONTRACT
test.describe("Mock Visual — active /calendar calendar/v2", () => {
  test("renders hero, ordinary, and not-computed dayState markers", async ({ page }) => {
    const tracker = await openCalendar(page)
    const screen = page.getByTestId("calendar-screen")

    await expect(screen).toHaveAttribute("data-state", "ready")
    await expect(page.getByTestId("calendar-month-header")).toHaveText("Июль 2026")
    await expect(page.getByTestId("calendar-grid")).toBeVisible()

    await expect(page.getByTestId(`calendar-day-${HERO_DATE}`)).toHaveAttribute("data-day-state", "hero")
    await expect(page.getByTestId("calendar-day-2026-07-06")).toHaveAttribute("data-day-state", "ordinary")
    await expect(page.getByTestId("calendar-day-2026-07-08")).toHaveAttribute("data-day-state", "not-computed")
    await expect(page.getByTestId(`calendar-day-${HERO_DATE}`).getByTestId("calendar-day-hero-dot")).toBeVisible()
    await expect(page.getByTestId("calendar-day-2026-07-08").getByTestId("calendar-day-not-computed")).toBeVisible()

    const ordinary = page.getByTestId("calendar-day-2026-07-06")
    await expect(ordinary.getByTestId("calendar-day-hero-dot")).toHaveCount(0)
    await expect(ordinary.getByTestId("calendar-day-not-computed")).toHaveCount(0)
    await expect(page.getByTestId("calendar-view-day")).toHaveAttribute("aria-pressed", "true")

    await page.getByTestId("calendar-view-moon").click()
    await expect(page.getByTestId("calendar-view-moon")).toHaveAttribute("aria-pressed", "true")
    await expect(page.getByTestId("lunar-calendar-strip")).toBeVisible()
    await expect(page.getByTestId(`calendar-moon-glyph-${HERO_DATE}`)).toBeVisible()

    await page.getByTestId("calendar-view-day").click()
    await page.getByTestId(`calendar-day-${HERO_DATE}`).click()
    await expect(page.getByTestId("calendar-selected-summary")).toContainText("5 июля 2026")
    await expect(page.getByRole("button", { name: "Открыть день" })).toBeVisible()

    await expectNoMissingApiFixtures(page, tracker)
  })

  test("captures the calendar three-state visual baseline", async ({ page }) => {
    const tracker = await openCalendar(page)
    await prepareForScreenshot(page)
    await expect(page).toHaveScreenshot("calendar-three-state.png", { fullPage: true })
    await expectNoMissingApiFixtures(page, tracker)
  })

  test("projects a failed calendar/v2 request into the public error state", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, {
      ...buildCalendarFixtures(),
      "/api/calendar": { status: 503, body: { detail: "calendar unavailable" } },
    })
    await installMockVisualRuntime(page)
    await page.goto("/calendar", { waitUntil: "domcontentloaded" })

    const screen = page.getByTestId("calendar-screen")
    await expect(screen).toHaveAttribute("data-state", "error", { timeout: 15000 })
    await expect(page.getByTestId("calendar-error")).toBeVisible()
    await expectNoMissingApiFixtures(page, tracker)
  })
})
// END_BLOCK: DAY_STATE_CONTRACT
