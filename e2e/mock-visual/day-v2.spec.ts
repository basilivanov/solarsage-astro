// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_DAY_V2 — human-first V2 mobile review.
// ROLE: Exercises test-only routed fixtures against the public Today DOM
//       contract and records the four curated navigator review states.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-DAY-V2
// purpose: Verify the human-first V2 personal story, 12-sphere navigator, and progressive Why disclosure.
// owns:
//   - e2e/mock-visual/day-v2.spec.ts
// inputs: Mock fixture payloads and a running test-only preview at E2E_BASE_URL.
// outputs: Public DOM assertions plus four visual-regression baselines/review assets.
// dependencies: Playwright, mock route interception, test-only fixtures.
// side_effects: Writes committed screenshot artifacts and Playwright snapshots.
// emitted_logs: none.
// invariants:
//   - Product code is never mocked or imported from this test.
//   - API interception remains Playwright-only.
// failure_policy: Fails on missing fixture routes, public-contract regressions, or visual mismatch.
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-DAY-V2

import { expect, test, type Locator, type Page } from "@playwright/test"
import { expectNoMissingApiFixtures, installMockApiRoutes, type MockApiRouteFixtures } from "./route-interception"
import { dayPayloadV2, minimalDayPayloadForDate } from "./fixtures/day-v2-2026-07-08"
import { calendarPayload } from "./fixtures/calendar-2026-07"
import { referralPayload, profilePayload } from "./fixtures/profile"
import fs from "node:fs"
import path from "node:path"
import { inflateSync } from "node:zlib"

const WEEK_STRIP_MIN_DATES = [
  "2026-07-05",
  "2026-07-06",
  "2026-07-07",
  "2026-07-08",
  "2026-07-09",
  "2026-07-10",
  "2026-07-11",
]

const ASSETS_DIR = path.join(
  process.cwd(),
  "docs/work/2026-07-11_solarsage-v2-three-horizon-why-preview/assets",
)

const BANNED_HUMAN_COPY = /транзит|профекци|фирдар|орб|натальн|аспект|convergence|source_frame|target_frame/i

function buildReadyFixtures(): MockApiRouteFixtures {
  const fixtures: MockApiRouteFixtures = {
    "/api/day/2026-07-08": { body: dayPayloadV2 },
    "/api/auth/telegram": { status: 200, body: { status: "ok", userId: "mock-user-id" } },
    "/api/auth/dev": { status: 200, body: { status: "ok", userId: "mock-user-id" } },
    "/api/calendar": { body: calendarPayload },
    "/api/referral": { body: referralPayload },
    "/api/profile": { body: profilePayload },
    "/api/_log": { body: { ok: true } },
  }

  for (const dateStr of WEEK_STRIP_MIN_DATES) {
    if (!fixtures[`/api/day/${dateStr}`]) fixtures[`/api/day/${dateStr}`] = { body: minimalDayPayloadForDate(dateStr) }
  }
  return fixtures
}

async function installTelegramFixture(page: Page) {
  await page.addInitScript(() => {
    const initData = "user=%7B%22id%22%3A1%7D&auth_date=1&hash=mock"
    ;(window as any).Telegram = {
      WebApp: {
        initData,
        initDataUnsafe: { user: { id: 1 } },
        ready: () => {},
        expand: () => {},
        close: () => {},
        MainButton: { hide: () => {}, show: () => {}, onClick: () => {}, offClick: () => {}, setText: () => {} },
        BackButton: { hide: () => {}, show: () => {}, onClick: () => {}, offClick: () => {} },
        themeParams: {},
        colorScheme: "light",
        platform: "web",
        version: "7.0",
      },
    }
    localStorage.setItem("lumen:onboarded", "1")
  })
}

async function hideNextOverlay(page: Page) {
  await page.addStyleTag({
    content: "nextjs-portal,[data-nextjs-dialog-overlay],#__next-build-watcher,[data-nextjs-toast],[data-next-mark-loading]{display:none!important}",
  })
}

function nearBlackPixelRatio(png: Buffer): number {
  let cursor = 8
  let width = 0
  let height = 0
  let channels = 0
  const idat: Buffer[] = []
  while (cursor < png.length) {
    const length = png.readUInt32BE(cursor)
    const type = png.subarray(cursor + 4, cursor + 8).toString("ascii")
    const data = png.subarray(cursor + 8, cursor + 8 + length)
    if (type === "IHDR") {
      width = data.readUInt32BE(0)
      height = data.readUInt32BE(4)
      if (data[8] !== 8 || ![2, 6].includes(data[9])) throw new Error("Expected an 8-bit RGB or RGBA Playwright PNG")
      channels = data[9] === 6 ? 4 : 3
    }
    if (type === "IDAT") idat.push(data)
    cursor += length + 12
  }
  const bytesPerRow = width * channels
  const decompressed = inflateSync(Buffer.concat(idat))
  let offset = 0
  let nearBlack = 0
  let previous = Buffer.alloc(bytesPerRow)
  for (let row = 0; row < height; row += 1) {
    const filter = decompressed[offset]
    offset += 1
    const raw = decompressed.subarray(offset, offset + bytesPerRow)
    offset += bytesPerRow
    const current = Buffer.alloc(bytesPerRow)
    for (let index = 0; index < bytesPerRow; index += 1) {
      const left = index >= channels ? current[index - channels] : 0
      const above = previous[index]
      const upperLeft = index >= channels ? previous[index - channels] : 0
      const predictor = filter === 0 ? 0
        : filter === 1 ? left
          : filter === 2 ? above
            : filter === 3 ? Math.floor((left + above) / 2)
              : filter === 4 ? paeth(left, above, upperLeft)
                : (() => { throw new Error(`Unsupported PNG filter: ${filter}`) })()
      current[index] = (raw[index] + predictor) & 0xff
    }
    for (let index = 0; index < bytesPerRow; index += channels) {
      if (
        (current[index] < 12 && current[index + 1] < 12 && current[index + 2] < 12)
        || (channels === 4 && current[index + 3] < 250)
      ) nearBlack += 1
    }
    previous = current
  }
  return nearBlack / (width * height)
}

function paeth(left: number, above: number, upperLeft: number): number {
  const estimate = left + above - upperLeft
  const leftDistance = Math.abs(estimate - left)
  const aboveDistance = Math.abs(estimate - above)
  const upperLeftDistance = Math.abs(estimate - upperLeft)
  return leftDistance <= aboveDistance && leftDistance <= upperLeftDistance
    ? left
    : aboveDistance <= upperLeftDistance ? above : upperLeft
}

function expectLightThemePng(png: Buffer) {
  expect(nearBlackPixelRatio(png)).toBeLessThan(0.001)
}

async function capturePage(page: Page, name: string) {
  fs.mkdirSync(ASSETS_DIR, { recursive: true })
  const png = await page.screenshot({ path: path.join(ASSETS_DIR, name), fullPage: false })
  expectLightThemePng(png)
  await expect(page).toHaveScreenshot(name)
}

async function captureLocator(locator: Locator, name: string) {
  fs.mkdirSync(ASSETS_DIR, { recursive: true })
  const png = await locator.screenshot({ path: path.join(ASSETS_DIR, name) })
  expectLightThemePng(png)
  await expect(locator).toHaveScreenshot(name)
}

test.describe("V2 human-first navigator mock visual", () => {
  test("renders, navigates, explains, and captures the four review states", async ({ page }) => {
    test.setTimeout(90_000)
    await page.setViewportSize({ width: 390, height: 844 })
    await installTelegramFixture(page)
    const tracker = await installMockApiRoutes(page, buildReadyFixtures())

    await page.goto("/day/2026-07-08")
    await expect(page.getByTestId("auth-loading")).toBeHidden({ timeout: 30_000 })
    await hideNextOverlay(page)

    const screen = page.getByTestId("today-screen")
    const summary = page.getByTestId("day-summary-card")
    const story = page.getByTestId("activation-evidence-card")
    const navigator = page.getByTestId("concrete-day-advice")
    const focus = page.getByTestId("today-focus")
    const contextDisclosure = page.getByTestId("day-context-disclosure")
    await expect(screen).toHaveAttribute("data-state", "ready", { timeout: 30_000 })
    await expect(summary).toBeVisible()
    await expect(story).toBeVisible()
    await expect(navigator).toBeVisible()
    await expect(focus).toBeVisible()
    await expect(contextDisclosure).toBeVisible()

    const order = await page.evaluate(() => {
      const nodes = [
        document.querySelector('[data-testid="day-summary-card"]'),
        document.querySelector('[data-testid="today-focus"]'),
        document.querySelector('[data-testid="activation-evidence-card"]'),
        document.querySelector('[data-testid="concrete-day-advice"]'),
        document.querySelector('[data-testid="day-context-disclosure"]'),
        document.querySelector('[data-testid="day-reading-disclosure"]'),
        document.querySelector('[data-testid="day-tech-disclosure"]'),
      ]
      for (let index = 1; index < nodes.length; index += 1) {
        const previous = nodes[index - 1]
        const current = nodes[index]
        if (!(previous instanceof Element) || !(current instanceof Element)) return false
        if (!(previous.compareDocumentPosition(current) & Node.DOCUMENT_POSITION_FOLLOWING)) return false
      }
      return nodes[0] instanceof Element
    })
    expect(order).toBe(true)

    await expect(story).toContainText("ИМЕННО ДЛЯ ТЕБЯ")
    await expect(story).toContainText("Главное:")
    await expect(story.getByTestId("personal-story-sphere-link")).toHaveCount(3)
    await expect(story).not.toContainText(BANNED_HUMAN_COPY)
    await expect(navigator.getByTestId("concrete-day-advice-row")).toHaveCount(12)
    await expect(navigator.getByTestId("concrete-day-advice-show-all")).toHaveCount(0)

    const work = navigator.getByTestId("concrete-day-advice-row").filter({ has: page.getByText("Работа", { exact: true }) })
    await work.click()
    await expect(work).toHaveAttribute("data-selected", "true")
    await expect(work).toHaveAttribute("aria-haspopup", "dialog")
    const workDetails = page.getByTestId("sphere-details-sheet")
    await expect(workDetails).toHaveAttribute("data-sphere-key", "work")
    await expect(workDetails).toContainText("Не форсируйте разговор о статусе — сначала отделите принципиальное от реакции на давление")
    await expect(workDetails).not.toContainText(BANNED_HUMAN_COPY)
    await expect(page.getByTestId("sphere-details-sheet")).toHaveCount(1)

    const closeBtn = workDetails.getByRole("button", { name: "Закрыть" })
    await closeBtn.click()
    await expect(page.getByTestId("sphere-details-sheet")).toHaveCount(0)

    const money = navigator.getByTestId("concrete-day-advice-row").filter({ has: page.getByText("Деньги", { exact: true }) })
    await money.click()
    await expect(money).toHaveAttribute("data-selected", "true")
    const moneyDetails = page.getByTestId("sphere-details-sheet")
    await expect(moneyDetails).toHaveAttribute("data-sphere-key", "money")
    await moneyDetails.getByRole("button", { name: "Закрыть" }).click()
    await expect(page.getByTestId("sphere-details-sheet")).toHaveCount(0)

    const heroWork = story.getByTestId("personal-story-sphere-link").filter({ hasText: "Работа и статус" })
    await heroWork.click()
    const heroSheet = page.getByTestId("sphere-details-sheet")
    await expect(heroSheet).toHaveAttribute("data-sphere-key", "work")
    await heroSheet.getByRole("button", { name: "Закрыть" }).click()
    await expect(page.getByTestId("sphere-details-sheet")).toHaveCount(0)

    // TodayFocus block: enriched fixture has single_impulses with one timed event
    await expect(focus).toHaveAttribute("data-state", "single_impulses")
    await expect(focus).toContainText("СОБЫТИЯ ДНЯ")
    await expect(focus.getByTestId("today-focus-event")).toHaveCount(1)
    await expect(focus).toContainText("Луна в напряжении с твоим Плутоном")
    await expect(focus).toContainText("точный пик")

    // Period context disclosure: open and verify the long horizon content
    await contextDisclosure.getByTestId("day-context-disclosure-toggle").click()
    await expect(contextDisclosure.getByTestId("day-context-disclosure-toggle")).toHaveAttribute("aria-expanded", "true")
    await expect(contextDisclosure).toContainText("Долгий цикл")
    await expect(contextDisclosure).toContainText("Фон уже действует")
    await expect(contextDisclosure).toContainText("Как проявляется")
    await expect(contextDisclosure).not.toContainText(BANNED_HUMAN_COPY)

    const [contextHeight, screenHeight] = await Promise.all([
      contextDisclosure.evaluate((element) => Math.ceil(element.scrollHeight)),
      screen.evaluate((element) => Math.ceil(element.scrollHeight)),
    ])
    await page.setViewportSize({ width: 390, height: Math.max(contextHeight, screenHeight) + 96 })
    await screen.evaluate((element) => element.parentElement?.scrollTo({ top: 0 }))
    await contextDisclosure.scrollIntoViewIfNeeded()
    await page.waitForTimeout(150)
    await captureLocator(contextDisclosure, "01-why-three-horizons-mobile.png")

    // Back to phone-sized viewport for the technical disclosure of the focus block
    await page.setViewportSize({ width: 390, height: 844 })
    await page.getByTestId("today-focus-technical-toggle").click()
    await expect(page.getByTestId("today-focus-technical-content")).toBeVisible()
    await page.waitForTimeout(150)
    await captureLocator(page.getByTestId("today-focus-technical-content"), "02-why-three-horizons-calculation-mobile.png")

    const fullScreenHeight = await screen.evaluate((element) => Math.ceil(element.scrollHeight))
    await page.setViewportSize({ width: 390, height: fullScreenHeight + 96 })
    await screen.evaluate((element) => element.parentElement?.scrollTo({ top: 0 }))
    await page.waitForTimeout(150)
    await capturePage(page, "03-full-day-three-horizons-mobile.png")

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
    expect(overflow).toBe(true)
    await expectNoMissingApiFixtures(page, tracker)
  })
})
