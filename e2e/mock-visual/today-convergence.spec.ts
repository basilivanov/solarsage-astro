// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_TODAY_CONVERGENCE_SPEC — Today convergence visual and structural gate.
// ROLE: Exercises the generated Today payload matrix, snapshot drilldown, static sphere page, and check-in recap.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-TODAY-CONVERGENCE-SPEC
// purpose: Verify the public Today convergence DOM contract against all 16 Today and 3 Yesterday fixtures.
// owns:
//   - e2e/mock-visual/today-convergence.spec.ts
// inputs: generated fixture barrel, inline sphere payloads, Playwright route interception, and E2E_BASE_URL.
// outputs: structural assertions, curated Today/drilldown PNG baselines, and WebKit smoke coverage.
// dependencies: @playwright/test; route-interception; screenshot; generated contracts.
// side_effects: none outside Playwright snapshots.
// emitted_logs: none.
// invariants:
//   - Production runtime never imports these test fixtures; all API mocking stays in page.route.
//   - Every Today fixture exposes the public root state axes and twelve sphere tiles.
//   - Narrative text is masked in visual assertions; structural selectors carry the contract.
//   - Missing API routes fail closed.
// failure_policy: fail on schema-shaped fixture wiring, DOM contract drift, missing routes, or visual mismatch.
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-TODAY-CONVERGENCE-SPEC

// START_MODULE_MAP: M-E2E-MOCK-VISUAL-TODAY-CONVERGENCE-SPEC
// public_entrypoints:
//   - 16-fixture Today structural matrix
//   - curated Today visual baselines
//   - snapshot drilldown and static sphere navigation
//   - Yesterday check-in pre/post/no-snapshot flows
//   - WebKit ready/loading/error smoke tests
// semantic_blocks:
//   - FIXTURE_MATRIX: route builders and deterministic browser runtime.
//   - TODAY_CONTRACT: state axes, hero/quiet/access and sphere navigation.
//   - IMPULSE_GEOMETRY: desktop title/time one-row visibility and mobile overflow safety.
//   - VISUAL_BASELINES: key Today states and snapshot drilldown.
//   - CHECKIN_AND_SPHERE: Yesterday recap and static sphere route wiring.
//   - WEBKIT_SMOKE: minimal cross-engine transport/navigation proof.
// owned_tests:
//   - self
// END_MODULE_MAP: M-E2E-MOCK-VISUAL-TODAY-CONVERGENCE-SPEC

import { expect, test, type Locator, type Page } from "@playwright/test"
import type {
  TodaySphereDrilldownPayload,
} from "../../packages/contracts"
import type { TodaySpherePagePayload } from "../../packages/contracts/today-sphere-page"
import type { TodayConvergencePayload } from "../../packages/contracts/today-convergence"
import {
  birthUnknown,
  contentUnavailable,
  heroMixed,
  heroTense,
  quietSteady,
  stateUnavailable,
  todayConvergenceFixtures,
  yesterdayNoSnapshot,
  yesterdayPostSubmit,
  yesterdayPreSubmit,
} from "../../__tests__/fixtures/today_convergence_v2"
import {
  expectNoMissingApiFixtures,
  installMockApiRoutes,
  type MockApiRouteFixtures,
} from "./route-interception"
import { accessPayload, calendarPayload } from "./fixtures/calendar-2026-07"
import { profilePayload, referralPayload } from "./fixtures/profile"
import { prepareForScreenshot } from "./screenshot"

const TODAY_DATE = "2026-08-01"
const DRILLDOWN_SNAPSHOT = heroTense.snapshotId!
const LONG_IMPULSE_EVENT_ID = "evt_v1_long_title_time"
const LONG_IMPULSE_TITLE = "Луна в гармонии с твоим жребием Брака"
const LONG_IMPULSE_TIME_TEXT = "пик 2 августа, 18:48, окно: с 2 августа, 03:58 до 3 августа, 09:28"

const longImpulseTime: TodayConvergencePayload["events"][number]["time"] = {
  mode: "exact",
  peak: "18:48",
  start: "03:58",
  end: "09:28",
  partOfDay: null,
  peakAt: "2026-08-02T18:48:00+03:00",
  startAt: "2026-08-02T03:58:00+03:00",
  endAt: "2026-08-03T09:28:00+03:00",
}

const longImpulseQuietPayload: TodayConvergencePayload = {
  ...quietSteady,
  targetDate: "2026-08-02",
  impulses: [
    {
      ...quietSteady.impulses[0],
      eventId: LONG_IMPULSE_EVENT_ID,
      time: longImpulseTime,
    },
  ],
  events: [
    {
      ...quietSteady.events[0],
      id: LONG_IMPULSE_EVENT_ID,
      title: LONG_IMPULSE_TITLE,
      time: longImpulseTime,
    },
  ],
}

const spherePagePayload: TodaySpherePagePayload = {
  birthTimeMode: "exact",
  housesAvailable: true,
  natal: {
    state: "ready",
    paragraphs: [
      {
        sourceFactIds: ["natal-work-1", "natal-work-2"],
        text: "Натальная опора связана с последовательным развитием навыка и ясной ролью в команде.",
      },
      {
        sourceFactIds: ["natal-work-3"],
        text: "Длинные задачи лучше раскрываются через ритм, который можно поддерживать без рывков.",
      },
    ],
  },
  period: [
    {
      id: "period-work-1",
      technique: "annual_profection",
      title: "Годовая тема профессионального роста",
      activeFrom: "2026-01-01",
      activeUntil: "2026-12-31",
    },
  ],
  periodIdentity: "period-work-v1",
  periodUnavailable: false,
  sphere: "work",
}

const drilldownPayload: TodaySphereDrilldownPayload = {
  birthTimeMode: "exact",
  convergence: {
    eventIds: ["evt-drill-1", "evt-drill-2"],
    evidenceLevel: "high",
    id: "cvg-drill-1",
    polarity: "supportive",
    primarySphere: "work",
    secondarySphere: "communication",
  },
  dayTone: "tense",
  events: [
    {
      evidenceLevel: "high",
      id: "evt-drill-1",
      kind: "aspect",
      polarity: "supportive",
      sphere: "work",
      title: "Луна в гармонии с твоим Сатурном",
      time: { mode: "exact", peak: "15:40", start: "13:00", end: "18:00", partOfDay: null },
    },
    {
      evidenceLevel: "medium",
      id: "evt-drill-2",
      kind: "structural",
      polarity: "tense",
      sphere: "communication",
      title: null,
      time: { mode: "partofday", partOfDay: "evening", peak: null, start: null, end: null },
    },
  ],
  snapshotId: DRILLDOWN_SNAPSHOT,
  sphere: "work",
  state: "convergence_today",
}

type YesterdayFixture = typeof yesterdayPreSubmit

// START_BLOCK: FIXTURE_MATRIX
function buildTodayFixtures(
  payload: TodayConvergencePayload,
  options: {
    dayStatus?: number
    delayMs?: number
    yesterday?: YesterdayFixture
    yesterdayAfterSubmit?: YesterdayFixture
    onCheckin?: () => void
  } = {},
): MockApiRouteFixtures {
  const dayPath = `/api/day/${TODAY_DATE}`
  const fixtures: MockApiRouteFixtures = {
    [dayPath]: async () => {
      if (options.delayMs) await new Promise((resolve) => setTimeout(resolve, options.delayMs))
      return { status: options.dayStatus ?? 200, body: options.dayStatus && options.dayStatus >= 400 ? { detail: "day unavailable" } : payload }
    },
    "/api/auth/dev": { status: 200, body: { status: "ok", userId: "mock-today-user" } },
    "/api/profile": { body: profilePayload },
    "/api/access": { body: accessPayload },
    "/api/calendar": { body: calendarPayload },
    "/api/referral": { body: referralPayload },
    "/api/payment/products": { body: { products: [] } },
    "/api/spheres/work": { body: spherePagePayload },
    [`/api/day/snapshots/${DRILLDOWN_SNAPSHOT}/spheres/work`]: { body: drilldownPayload },
  }

  if (payload.snapshotId) {
    fixtures[`/api/day/snapshots/${payload.snapshotId}/impression`] = { body: { ok: true } }
  }

  if (options.yesterday) {
    let checkinSubmitted = false
    fixtures["/api/checkin/yesterday"] = () => ({
      body: checkinSubmitted ? options.yesterdayAfterSubmit ?? options.yesterday : options.yesterday,
    })
    fixtures["/api/checkin"] = () => {
      checkinSubmitted = true
      options.onCheckin?.()
      return { body: yesterdayPostSubmit.checkin }
    }
  }

  return fixtures
}

async function installMockVisualRuntime(page: Page): Promise<void> {
  await page.addInitScript(() => {
    localStorage.setItem("lumen:onboarded", "1")
    const fixedNow = new Date("2026-08-01T12:00:00Z").valueOf()
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

async function openToday(
  page: Page,
  payload: TodayConvergencePayload,
  options: Parameters<typeof buildTodayFixtures>[1] = {},
) {
  const tracker = await installMockApiRoutes(page, buildTodayFixtures(payload, options))
  await installMockVisualRuntime(page)
  await page.goto(`/day/${TODAY_DATE}`, { waitUntil: "domcontentloaded" })
  await expect(page.getByTestId("today-screen")).toHaveAttribute("data-screen-state", "ready", { timeout: 15000 })
  return tracker
}
// END_BLOCK: FIXTURE_MATRIX

function expectPayloadRoot(
  root: Locator,
  payload: TodayConvergencePayload,
): void {
  // Structural assertions intentionally avoid dynamic narrative copy.
  expect(root).toHaveAttribute("data-screen-state", "ready")
  expect(root).toHaveAttribute("data-content-state", payload.contentState)
  expect(root).toHaveAttribute("data-access-state", payload.access.state)
  expect(root).toHaveAttribute("data-birth-time-mode", payload.birthTime.mode)
  if (payload.state) expect(root).toHaveAttribute("data-state", payload.state)
  else expect(root).not.toHaveAttribute("data-state")
  if (payload.dayTone) expect(root).toHaveAttribute("data-day-tone", payload.dayTone)
  else expect(root).not.toHaveAttribute("data-day-tone")
}

// START_BLOCK: TODAY_CONTRACT
test.describe("Mock Visual — Today Convergence", () => {
  test("covers all 16 Today fixtures on the desktop public contract", async ({ page }, testInfo) => {
    test.setTimeout(180_000)
    test.skip(testInfo.project.name !== "chromium", "The fixture matrix is the desktop structural gate")
    let activePayload = todayConvergenceFixtures[0]
    const matrixFixtures = buildTodayFixtures(activePayload)
    matrixFixtures[`/api/day/${TODAY_DATE}`] = () => ({ body: activePayload })
    for (const fixture of todayConvergenceFixtures) {
      if (fixture.snapshotId) {
        matrixFixtures[`/api/day/snapshots/${fixture.snapshotId}/impression`] = { body: { ok: true } }
      }
    }
    const tracker = await installMockApiRoutes(page, matrixFixtures)
    await installMockVisualRuntime(page)

    for (const payload of todayConvergenceFixtures) {
      activePayload = payload
      tracker.reset()
      await page.goto(`/day/${payload.targetDate}`, { waitUntil: "domcontentloaded" })
      const root = page.getByTestId("today-screen")
      await expect(root).toHaveAttribute("data-screen-state", "ready", { timeout: 15000 })
      expectPayloadRoot(root, payload)
      await expect(page.locator('a[data-testid^="sphere-tile-"]')).toHaveCount(12)

      if (payload.state === "convergence_today" && payload.access.state === "full") {
        await expect(page.getByTestId("convergence-hero")).toBeVisible()
      }
      if (payload.state === "unavailable") await expect(page.getByTestId("today-unavailable")).toBeVisible()
      if (payload.access.state === "preview") await expect(page.getByTestId("today-preview-teaser")).toBeVisible()
      if (payload.access.state === "locked") await expect(page.getByTestId("paywall")).toBeVisible()
      if (payload.state !== "unavailable" && (payload.contentState === "pending" || payload.contentState === "unavailable")) {
        await expect(page.getByTestId("today-narrative")).toHaveAttribute("data-state", payload.contentState)
      }
      if (payload.birthTime.mode !== "exact") await expect(page.getByTestId("birth-time-banner")).toBeVisible()
      await expectNoMissingApiFixtures(page, tracker)
    }
  })

  test("renders hero tense, hero mixed, quiet steady, birth unknown, unavailable, and content-unavailable baselines", async ({ page }) => {
    const cases = [
      ["hero-tense", heroTense],
      ["hero-mixed", heroMixed],
      ["quiet-steady", quietSteady],
      ["birth-unknown", birthUnknown],
      ["state-unavailable", stateUnavailable],
      ["content-unavailable", contentUnavailable],
    ] as const

    for (const [name, payload] of cases) {
      const tracker = await openToday(page, payload)
      await prepareForScreenshot(page)
      await expect(page).toHaveScreenshot(`${name}.png`, {
        fullPage: true,
        mask: [page.getByTestId("today-narrative")],
      })
      await expectNoMissingApiFixtures(page, tracker)
    }
  })

  test("captures the navigator and opens snapshot drilldown", async ({ page }) => {
    const tracker = await openToday(page, heroTense)
    await prepareForScreenshot(page)
    await expect(page).toHaveScreenshot("today-navigator.png", {
      fullPage: true,
      mask: [page.getByTestId("today-narrative")],
    })

    await page.getByTestId("sphere-tile-work").click()
    await expect(page).toHaveURL(new RegExp(`/day/snapshots/${DRILLDOWN_SNAPSHOT}/spheres/work$`))
    await expect(page.getByTestId("sphere-drilldown")).toHaveAttribute("data-screen-state", "ready", { timeout: 15000 })
    await expect(page.getByTestId("drilldown-evidence")).toBeVisible()
    await prepareForScreenshot(page)
    await expect(page).toHaveScreenshot("sphere-drilldown.png", { fullPage: true })
    await expectNoMissingApiFixtures(page, tracker)
  })

  test("keeps long impulse title and full date-aware time visible without overflow", async ({ page }, testInfo) => {
    const tracker = await openToday(page, longImpulseQuietPayload)
    const meta = page.getByTestId(`impulse-event-meta-${LONG_IMPULSE_EVENT_ID}`)
    const title = page.getByTestId(`impulse-event-title-${LONG_IMPULSE_EVENT_ID}`)
    const time = page.getByTestId(`impulse-event-time-${LONG_IMPULSE_EVENT_ID}`)

    await expect(meta).toBeVisible()
    await expect(title).toHaveText(LONG_IMPULSE_TITLE)
    await expect(title).toBeVisible()
    await expect(time).toHaveText(LONG_IMPULSE_TIME_TEXT)
    await expect(time).toBeVisible()

    const geometry = await page.evaluate((eventId) => {
      const read = (testId: string) => {
        const element = document.querySelector<HTMLElement>(`[data-testid="${testId}"]`)
        if (!element) throw new Error(`missing ${testId}`)
        const rect = element.getBoundingClientRect()
        return {
          y: rect.y,
          height: rect.height,
          clientWidth: element.clientWidth,
          scrollWidth: element.scrollWidth,
          clientHeight: element.clientHeight,
          scrollHeight: element.scrollHeight,
        }
      }
      const metaBox = read(`impulse-event-meta-${eventId}`)
      const titleBox = read(`impulse-event-title-${eventId}`)
      const timeBox = read(`impulse-event-time-${eventId}`)
      return {
        meta: metaBox,
        title: titleBox,
        time: timeBox,
        documentScrollWidth: document.documentElement.scrollWidth,
        viewportWidth: window.innerWidth,
      }
    }, LONG_IMPULSE_EVENT_ID)

    expect(geometry.documentScrollWidth).toBeLessThanOrEqual(geometry.viewportWidth)
    if (testInfo.project.name === "chromium") {
      for (const box of [geometry.meta, geometry.title, geometry.time]) {
        expect(box.height).toBeGreaterThanOrEqual(21)
        expect(box.height).toBeLessThanOrEqual(23)
        expect(box.scrollWidth).toBeLessThanOrEqual(box.clientWidth)
        expect(box.scrollHeight).toBeLessThanOrEqual(box.clientHeight)
      }
      expect(Math.abs(geometry.title.y - geometry.time.y)).toBeLessThanOrEqual(2)
    }
    await expectNoMissingApiFixtures(page, tracker)
  })
})
// END_BLOCK: TODAY_CONTRACT

// START_BLOCK: CHECKIN_AND_SPHERE
test.describe("Mock Visual — Today downstream routes", () => {
  test("shows Yesterday forecast before submit and snapshot recap after submit", async ({ page }) => {
    let submitted = false
    const tracker = await installMockApiRoutes(page, buildTodayFixtures(quietSteady, {
      yesterday: yesterdayPreSubmit,
      yesterdayAfterSubmit: yesterdayPostSubmit,
      onCheckin: () => { submitted = true },
    }))
    await installMockVisualRuntime(page)
    await page.goto(`/checkin?target=${TODAY_DATE}`, { waitUntil: "domcontentloaded" })

    await expect(page.getByTestId("checkin-screen")).toBeVisible()
    await expect(page.getByTestId("yesterday-forecast-available")).toBeVisible({ timeout: 15000 })
    await expect(page.getByTestId("yesterday-forecast-recap")).toHaveCount(0)
    await page.getByTestId("mood-4").click()
    await page.getByTestId("energy-3").click()
    await page.getByTestId("accuracy-3").click()
    await expect.poll(() => submitted).toBe(true)
    await expect(page.getByTestId("checkin-post-submit")).toBeVisible({ timeout: 15000 })
    await expect(page.getByTestId("yesterday-forecast-recap")).toBeVisible()
    await expectNoMissingApiFixtures(page, tracker)
  })

  test("keeps the no-snapshot Yesterday fixture honest", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildTodayFixtures(quietSteady, {
      yesterday: yesterdayNoSnapshot,
    }))
    await installMockVisualRuntime(page)
    await page.goto(`/checkin?target=${TODAY_DATE}`, { waitUntil: "domcontentloaded" })

    await expect(page.getByTestId("checkin-screen")).toBeVisible()
    await expect(page.getByTestId("yesterday-forecast-available")).toHaveCount(0)
    await expect(page.getByTestId("yesterday-forecast-recap")).toHaveCount(0)
    await expect(page.getByText("Оценка уже сохранена")).toBeVisible({ timeout: 15000 })
    await expectNoMissingApiFixtures(page, tracker)
  })

  test("opens the static sphere page from the generated route contract", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildTodayFixtures(quietSteady))
    await installMockVisualRuntime(page)
    await page.goto("/day/spheres/work", { waitUntil: "domcontentloaded" })
    await expect(page.getByTestId("sphere-page")).toHaveAttribute("data-state", "ready", { timeout: 15000 })
    await expect(page.getByTestId("sphere-natal")).toBeVisible()
    await expect(page.getByTestId("sphere-period")).toBeVisible()
    await expectNoMissingApiFixtures(page, tracker)
  })
})
// END_BLOCK: CHECKIN_AND_SPHERE

// START_BLOCK: WEBKIT_SMOKE
test.describe("WebKit Today smoke", () => {
  test("@webkit-smoke reaches ready Today navigation", async ({ page }) => {
    const tracker = await openToday(page, heroTense)
    await expect(page.getByTestId("today-screen")).toHaveAttribute("data-screen-state", "ready")
    await expect(page.locator('a[data-testid^="sphere-tile-"]')).toHaveCount(12)
    await expectNoMissingApiFixtures(page, tracker)
  })

  test("@webkit-smoke exposes loading before the day response resolves", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildTodayFixtures(heroTense, { delayMs: 700 }))
    await installMockVisualRuntime(page)
    const navigation = page.goto(`/day/${TODAY_DATE}`, { waitUntil: "domcontentloaded" })
    await expect(page.getByTestId("today-screen")).toHaveAttribute("data-screen-state", "loading", { timeout: 5000 })
    await navigation
    await expect(page.getByTestId("today-screen")).toHaveAttribute("data-screen-state", "ready", { timeout: 15000 })
    await expectNoMissingApiFixtures(page, tracker)
  })

  test("@webkit-smoke exposes an accessible Today transport error", async ({ page }) => {
    const tracker = await installMockApiRoutes(page, buildTodayFixtures(heroTense, { dayStatus: 503 }))
    await installMockVisualRuntime(page)
    await page.goto(`/day/${TODAY_DATE}`, { waitUntil: "domcontentloaded" })
    const root = page.getByTestId("today-screen")
    await expect(root).toHaveAttribute("data-screen-state", "error", { timeout: 15000 })
    await expect(root).toHaveAttribute("role", "alert")
    await expect(page.getByTestId("today-transport-error")).toBeVisible()
    await expectNoMissingApiFixtures(page, tracker)
  })
})
// END_BLOCK: WEBKIT_SMOKE
