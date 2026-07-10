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

import { expect, test, type Page } from "@playwright/test"
import { expectNoMissingApiFixtures, installMockApiRoutes, type MockApiRouteFixtures } from "./route-interception"
import { dayPayloadV2, minimalDayPayloadForDate } from "./fixtures/day-v2-2026-07-08"
import { calendarPayload } from "./fixtures/calendar-2026-07"
import { referralPayload, profilePayload } from "./fixtures/profile"
import fs from "node:fs"
import path from "node:path"

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
  "docs/work/2026-07-10_solarsage-v2-human-first-navigator-preview/assets",
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

async function capture(page: Page, name: string) {
  fs.mkdirSync(ASSETS_DIR, { recursive: true })
  await page.screenshot({ path: path.join(ASSETS_DIR, name), fullPage: false })
  await expect(page).toHaveScreenshot(name)
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
    const why = page.getByTestId("why-expanded")
    await expect(screen).toHaveAttribute("data-state", "ready", { timeout: 30_000 })
    await expect(summary).toBeVisible()
    await expect(story).toBeVisible()
    await expect(navigator).toBeVisible()
    await expect(why).toBeVisible()

    const order = await page.evaluate(() => {
      const nodes = [
        document.querySelector('[data-testid="day-summary-card"]'),
        document.querySelector('[data-testid="activation-evidence-card"]'),
        document.querySelector('[data-testid="concrete-day-advice"]'),
        document.querySelector('[data-testid="why-expanded"]'),
        document.querySelector('[data-testid="day-chart"], [data-testid="day-chart-unavailable"]'),
        document.querySelector('[data-testid="day-reading"]'),
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
    await expect(navigator).not.toContainText("Показать ещё")
    await expect(navigator).not.toContainText("все 12 сфер")

    // Top state is deliberately captured before scrolling or opening disclosures.
    await page.setViewportSize({ width: 390, height: 1_450 })
    await screen.evaluate((element) => element.parentElement?.scrollTo({ top: 0 }))
    await page.waitForTimeout(150)
    await capture(page, "01-human-first-overview-mobile.png")

    const work = navigator.getByTestId("concrete-day-advice-row").filter({ has: page.getByText("Работа", { exact: true }) })
    await work.click()
    await expect(work).toHaveAttribute("data-selected", "true")
    await expect(work).toHaveAttribute("aria-expanded", "true")
    const workDetails = navigator.getByTestId("concrete-day-advice-details")
    await expect(workDetails).toHaveAttribute("data-sphere-key", "work")
    await expect(workDetails).toContainText("Не форсируйте разговор о статусе — сначала отделите принципиальное от реакции на давление")
    await expect(workDetails).not.toContainText(BANNED_HUMAN_COPY)
    await expect(navigator.getByTestId("concrete-day-advice-details")).toHaveCount(1)

    const workScreenHeight = await screen.evaluate((element) => Math.ceil(element.scrollHeight))
    await page.setViewportSize({ width: 390, height: workScreenHeight + 84 })
    await screen.evaluate((element) => element.parentElement?.scrollTo({ top: 0 }))
    await page.waitForTimeout(150)
    await navigator.screenshot({ path: path.join(ASSETS_DIR, "02-work-sphere-expanded-mobile.png") })
    await expect(navigator).toHaveScreenshot("02-work-sphere-expanded-mobile.png")

    const money = navigator.getByTestId("concrete-day-advice-row").filter({ has: page.getByText("Деньги", { exact: true }) })
    await money.focus()
    await page.keyboard.press("Enter")
    await expect(money).toHaveAttribute("data-selected", "true")
    await expect(work).toHaveAttribute("data-selected", "false")
    await expect(navigator.getByTestId("concrete-day-advice-details")).toHaveCount(1)
    await page.keyboard.press("Space")
    await expect(navigator.getByTestId("concrete-day-advice-details")).toHaveCount(0)

    const heroWork = story.getByTestId("personal-story-sphere-link").filter({ hasText: "Работа и статус" })
    await heroWork.click()
    await expect(work).toHaveAttribute("data-selected", "true")

    const whyToggle = story.getByTestId("personal-story-why-cta")
    await whyToggle.click()
    const whyMainToggle = page.locator("#why-expanded-toggle")
    await expect(whyMainToggle).toHaveAttribute("aria-expanded", "true")
    const humanWhy = why.getByTestId("why-today")
    await expect(humanWhy.getByRole("article")).toHaveCount(3)
    await expect(humanWhy).not.toContainText(BANNED_HUMAN_COPY)

    const astroToggle = why.getByTestId("astrology-calculation-toggle")
    await expect(astroToggle).toHaveAttribute("aria-expanded", "false")
    await astroToggle.click()
    await expect(astroToggle).toHaveAttribute("aria-expanded", "true")
    const technical = why.getByTestId("astrology-calculation")
    await expect(technical.getByTestId("astrology-calculation-item")).toHaveCount(3)
    await expect(technical).toContainText("Луна")
    await expect(technical).toContainText("оппозиция")
    await expect(technical).toContainText(/орб 1[.,]05/)
    await expect(technical).toContainText("Плутон")
    await expect(technical).toContainText("Сатурн")
    await expect(technical).toContainText("Профекция")
    await expect(technical).toContainText("Фирдар")
    await expect(technical).not.toContainText(/Moon opposition|act-|source_frame|target_frame|strength|debug/i)

    const whyScreenHeight = await screen.evaluate((element) => Math.ceil(element.scrollHeight))
    await page.setViewportSize({ width: 390, height: whyScreenHeight + 84 })
    await screen.evaluate((element) => element.parentElement?.scrollTo({ top: 0 }))
    await page.waitForTimeout(150)
    await why.screenshot({ path: path.join(ASSETS_DIR, "03-why-human-and-astro-expanded-mobile.png") })
    await expect(why).toHaveScreenshot("03-why-human-and-astro-expanded-mobile.png")

    const fullScreenHeight = await screen.evaluate((element) => Math.ceil(element.scrollHeight))
    await page.setViewportSize({ width: 390, height: fullScreenHeight + 84 })
    await screen.evaluate((element) => element.parentElement?.scrollTo({ top: 0 }))
    await page.waitForTimeout(150)
    await capture(page, "04-full-day-human-first-mobile.png")

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
    expect(overflow).toBe(true)
    await expectNoMissingApiFixtures(page, tracker)
  })
})
