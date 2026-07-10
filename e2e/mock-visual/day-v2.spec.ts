import { expect, test } from "@playwright/test"
import { expectNoMissingApiFixtures, installMockApiRoutes, type MockApiRouteFixtures } from "./route-interception"
import { dayPayloadV2, minimalDayPayloadForDate } from "./fixtures/day-v2-2026-07-08"
import { calendarPayload } from "./fixtures/calendar-2026-07"
import { referralPayload, profilePayload } from "./fixtures/profile"
import path from "node:path"
import fs from "node:fs"

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
  "docs/work/2026-07-10_solarsage-v2-personal-day-preview/assets",
)

function buildReadyFixtures(): MockApiRouteFixtures {
  const fixtures: MockApiRouteFixtures = {
    "/api/day/2026-07-08": { body: dayPayloadV2 },
    "/api/auth/dev": {
      status: 200,
      body: { status: "ok", userId: "mock-user-id" },
    },
    "/api/calendar": {
      body: calendarPayload,
    },
    "/api/referral": {
      body: referralPayload,
    },
    "/api/profile": {
      body: profilePayload,
    },
    "/api/_log": {
      body: { ok: true },
    },
  }

  for (const dateStr of WEEK_STRIP_MIN_DATES) {
    if (fixtures[`/api/day/${dateStr}`]) continue
    fixtures[`/api/day/${dateStr}`] = {
      body: minimalDayPayloadForDate(dateStr),
    }
  }

  return fixtures
}

async function hideNextOverlay(page: import("@playwright/test").Page) {
  await page.addStyleTag({
    content: `
      nextjs-portal, [data-nextjs-dialog-overlay], #__next-build-watcher,
      [data-nextjs-toast], [data-next-mark-loading] { display: none !important; }
    `,
  })
}

test.describe("V2 Personal Day mock visual", () => {
  test("renders ordered personal V2 day with progressive evidence", async ({ page }) => {
    test.setTimeout(90_000)

    // Inject a minimal Telegram WebApp so auth does not wait on the external SDK.
    // Non-empty initData takes the /api/auth/telegram path (mocked below).
    await page.addInitScript(() => {
      const initData = "user=%7B%22id%22%3A1%7D&auth_date=1&hash=mock"
      ;(window as any).Telegram = {
        WebApp: {
          initData,
          initDataUnsafe: { user: { id: 1 } },
          ready: () => {},
          expand: () => {},
          close: () => {},
          MainButton: {
            hide: () => {},
            show: () => {},
            onClick: () => {},
            offClick: () => {},
            setText: () => {},
          },
          BackButton: { hide: () => {}, show: () => {}, onClick: () => {}, offClick: () => {} },
          themeParams: {},
          colorScheme: "light",
          platform: "web",
          version: "7.0",
        },
      }
      try {
        localStorage.setItem("lumen:onboarded", "1")
      } catch {
        /* ignore */
      }
    })

    const fixtures = buildReadyFixtures()
    fixtures["/api/auth/telegram"] = {
      status: 200,
      body: { status: "ok", userId: "mock-user-id" },
    }
    fixtures["/api/auth/dev"] = {
      status: 200,
      body: { status: "ok", userId: "mock-user-id" },
    }

    const tracker = await installMockApiRoutes(page, fixtures)

    await page.goto("/day/2026-07-08")
    await expect(page.getByTestId("auth-loading")).toBeHidden({ timeout: 30000 })
    await hideNextOverlay(page)

    const screen = page.getByTestId("today-screen")
    await expect(screen).toHaveAttribute("data-state", "ready", { timeout: 30000 })

    const summary = page.getByTestId("day-summary-card")
    const card = page.getByTestId("activation-evidence-card")
    const advice = page.getByTestId("concrete-day-advice")
    await expect(summary).toBeVisible()
    await expect(card).toBeVisible()
    await expect(advice).toBeVisible()

    // DOM order: summary -> V2 card -> concrete advice
    const order = await page.evaluate(() => {
      const a = document.querySelector('[data-testid="day-summary-card"]')
      const b = document.querySelector('[data-testid="activation-evidence-card"]')
      const c = document.querySelector('[data-testid="concrete-day-advice"]')
      if (!a || !b || !c) return null
      return {
        ab: a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING,
        bc: b.compareDocumentPosition(c) & Node.DOCUMENT_POSITION_FOLLOWING,
      }
    })
    expect(order?.ab).toBeTruthy()
    expect(order?.bc).toBeTruthy()

    await expect(card).toContainText(
      "Сегодня особенно заметен внутренний конфликт между контролем и необходимостью что-то изменить",
    )
    await expect(card).toContainText("Именно для вашей карты")

    // Collapsed card screenshot
    fs.mkdirSync(ASSETS_DIR, { recursive: true })
    await card.screenshot({
      path: path.join(ASSETS_DIR, "v2-card-collapsed-mobile.png"),
    })
    await expect(card).toHaveScreenshot("v2-card-collapsed-mobile.png")

    // Expand
    const toggle = page.getByTestId("activation-evidence-toggle")
    await expect(toggle).toHaveAttribute("aria-expanded", "false")
    await toggle.click()
    await expect(toggle).toHaveAttribute("aria-expanded", "true")
    const items = page.getByTestId("activation-evidence-item")
    await expect(items).toHaveCount(3)

    // The expanded card is taller than an iPhone 13 viewport. Use a taller
    // mobile viewport for this card-only review image so the real tab bar
    // does not overlap the capture; width remains the 390px visual contract.
    await page.setViewportSize({ width: 390, height: 1000 })
    await card.screenshot({
      path: path.join(ASSETS_DIR, "v2-card-expanded-mobile.png"),
    })
    await expect(card).toHaveScreenshot("v2-card-expanded-mobile.png")
    await page.setViewportSize({ width: 390, height: 664 })

    // Why block
    const whyToggle = page.getByRole("button", { name: /Почему именно сегодня|Почему так у меня/ })
    await whyToggle.click()
    const whyToday = page.getByTestId("why-today")
    await expect(whyToday).toBeVisible()
    await expect(whyToday).toContainText("Эмоции быстрее доходят до глубинной темы")
    await expect(whyToday).toContainText("У вас есть ресурс удержать структуру")
    await expect(whyToday).toContainText("Это не случайный фон одного дня")

    // Concrete advice evidence humanized
    const row = page.getByTestId("concrete-day-advice-row").first()
    const rowToggle = row.getByRole("button").first()
    await rowToggle.click()
    const evidence = page.getByTestId("concrete-day-advice-evidence")
    await expect(evidence).toBeVisible()
    await expect(evidence).toContainText("Почему именно у вас")
    await expect(evidence).not.toContainText("техника:")
    await expect(evidence).not.toContainText("семейство:")

    // Return to the collapsed top overview for the review asset. This keeps
    // the image useful to a reviewer instead of preserving the prior
    // interaction state from the evidence checks above.
    await rowToggle.click()
    await expect(rowToggle).toHaveAttribute("aria-expanded", "false")
    await whyToggle.click()
    await expect(whyToggle).toHaveAttribute("aria-expanded", "false")
    await toggle.click()
    await expect(toggle).toHaveAttribute("aria-expanded", "false")
    await screen.evaluate((element) => {
      element.parentElement?.scrollTo({ top: 0 })
    })

    // AppShell owns an internal scroller, so page fullPage captures only the
    // viewport. Capture the whole public today-screen locator instead. The
    // temporary height keeps the real tab bar out of the card/advice capture.
    const screenHeight = await screen.evaluate((element) => element.scrollHeight)
    await page.setViewportSize({ width: 390, height: Math.ceil(screenHeight) + 96 })
    await screen.screenshot({
      path: path.join(ASSETS_DIR, "v2-day-full-mobile.png"),
    })
    await expect(screen).toHaveScreenshot("v2-day-full-mobile.png")
    await page.setViewportSize({ width: 390, height: 664 })

    // No horizontal overflow
    const overflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth <= window.innerWidth
    })
    expect(overflow).toBe(true)

    await expectNoMissingApiFixtures(page, tracker)
  })
})
