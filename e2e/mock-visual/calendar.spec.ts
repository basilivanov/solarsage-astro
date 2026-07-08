// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_CALENDAR_SPEC
// ROLE: Mock visual e2e spec for /calendar route. Uses Playwright route
//       interception with contract-valid fixtures. No MSW, no runtime mocks.
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-CALENDAR-SPEC
// purpose: Verify the /calendar screen matches the visual/structural contract
//          on stable API payloads. Exercise ready state, day/moon modes, and
//          overflow. Asserts no missing fixtures via MissingRequestsTracker.
//          Mock-visual runtime fixes Date to 2026-07-08 via addInitScript
//          while keeping browser timers real.
// owns:
//   - e2e/mock-visual/calendar.spec.ts
// inputs: Playwright test runner, E2E_BASE_URL env
// outputs: Test pass/fail with assertions on DOM contract and visual structure
// dependencies:
//   - @playwright/test
//   - ./route-interception (installMockApiRoutes, MissingRequestsTracker, expectNoMissingApiFixtures)
//   - ./fixtures/calendar-2026-07 (calendarPayload, accessPayload)
// side_effects: None (all API calls intercepted)
// invariants:
//   - No product path imports mocks or demo data
//   - Fixtures represent valid API response shapes
//   - All API calls have fixture coverage (fails on missing)
//   - Date.now()/new Date() resolve to 2026-07-08 without fake timers
// failure_policy: Tests fail on missing fixture or assertion failure
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-CALENDAR-SPEC

import { expect, test, type Page } from "@playwright/test";
import {
  expectNoMissingApiFixtures,
  installMockApiRoutes,
  type MissingRequestsTracker,
  type MockApiRouteFixtures,
} from "./route-interception";
import { calendarPayload, accessPayload, dayPayload } from "./fixtures/calendar-2026-07";

function buildCalendarFixtures(): MockApiRouteFixtures {
  const fixtures: MockApiRouteFixtures = {
    "/api/calendar": { body: calendarPayload },
    "/api/access": { body: accessPayload },
    "/api/auth/dev": {
      status: 200,
      body: { status: "ok", userId: "mock-user-id" },
    },
  };

  for (let day = 1; day <= 31; day += 1) {
    const date = `2026-07-${String(day).padStart(2, "0")}`;
    fixtures[`/api/day/${date}`] = {
      body: {
        ...dayPayload,
        date,
      },
    };
  }

  return fixtures;
}

async function installMockVisualRuntime(page: Page): Promise<void> {
  await page.addInitScript(() => {
    localStorage.setItem("lumen:onboarded", "1");

    const fixedNow = new Date("2026-07-08T12:00:00Z").valueOf();
    const RealDate = Date;

    const FixedNowDate = function (this: Date, ...args: unknown[]) {
      if (!(this instanceof RealDate)) {
        return new RealDate(fixedNow).toString();
      }
      return args.length === 0
        ? new RealDate(fixedNow)
        : new (RealDate as any)(...args);
    } as unknown as DateConstructor;

    FixedNowDate.UTC = RealDate.UTC;
    FixedNowDate.parse = RealDate.parse;
    FixedNowDate.now = () => fixedNow;
    Object.setPrototypeOf(FixedNowDate, RealDate);
    Object.defineProperty(FixedNowDate, "prototype", {
      value: RealDate.prototype,
    });
    window.Date = FixedNowDate;

    (window as any).Telegram = {
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
        headerColor: "#ffffff",
        backgroundColor: "#ffffff",
        MainButton: {
          text: "",
          color: "",
          textColor: "",
          isVisible: false,
          isActive: true,
          isProgressVisible: false,
          setText: () => {},
          onClick: () => {},
          offClick: () => {},
          show: () => {},
          hide: () => {},
          enable: () => {},
          disable: () => {},
          showProgress: () => {},
          hideProgress: () => {},
        },
        BackButton: {
          isVisible: false,
          onClick: () => {},
          offClick: () => {},
          show: () => {},
          hide: () => {},
        },
        HapticFeedback: {
          impactOccurred: () => {},
          notificationOccurred: () => {},
          selectionChanged: () => {},
        },
        onEvent: () => {},
        offEvent: () => {},
        sendData: () => {},
        switchInlineQuery: () => {},
        openLink: () => {},
        openTelegramLink: () => {},
        openInvoice: () => {},
        showPopup: () => {},
        showAlert: () => {},
        showConfirm: () => {},
      },
    };
  });
}

async function openCalendarReady(page: Page): Promise<void> {
  await page.goto("/calendar", { waitUntil: "domcontentloaded" });

  const screen = page.getByTestId("calendar-screen");
  await expect(screen).toBeVisible({ timeout: 15000 });
  await expect(screen).toHaveAttribute("data-load-state", "ready", { timeout: 15000 });
}

async function setupCalendarPage(
  page: Page,
  fixtures: MockApiRouteFixtures = buildCalendarFixtures(),
): Promise<MissingRequestsTracker> {
  const tracker = await installMockApiRoutes(page, fixtures);
  await installMockVisualRuntime(page);
  await openCalendarReady(page);
  return tracker;
}

test.describe("Mock Visual — /calendar", () => {
  test.describe.configure({ mode: "serial" });

  test("fixture lunar facts match backend oracle sentinel days", () => {
    const sentinels = {
      "2026-07-05": {
        phase: "waning_gibbous",
        phaseIndex: 5,
        phaseLabel: "убыв. Луна",
        illumination: 70,
        lunarDay: 21,
      },
      "2026-07-08": {
        phase: "waning_crescent",
        phaseIndex: 7,
        phaseLabel: "убыв. серп",
        illumination: 39,
        lunarDay: 24,
      },
      "2026-07-11": {
        phase: "waning_crescent",
        phaseIndex: 7,
        phaseLabel: "убыв. серп",
        illumination: 12,
        lunarDay: 27,
      },
      "2026-07-23": {
        phase: "waxing_gibbous",
        phaseIndex: 3,
        phaseLabel: "раст. Луна",
        illumination: 64,
        lunarDay: 9,
      },
    } as const;

    for (const [date, expected] of Object.entries(sentinels)) {
      const day = calendarPayload.days.find((item) => item.date === date);
      expect(day?.lunar).toMatchObject(expected);
    }
  });

  test("calendar screen renders in ready state with month header, grid, lunar strip, and summary", async ({ page }) => {
    const tracker = await setupCalendarPage(page);

    // Root screen is visible with ready load state
    const screen = page.getByTestId("calendar-screen");
    await expect(screen).toBeVisible({ timeout: 10000 });
    await expect(screen).toHaveAttribute("data-load-state", "ready");

    // Month header is visible and localized by the frontend from payload.month
    await expect(page.getByTestId("calendar-month-header")).toBeVisible();
    await expect(page.getByTestId("calendar-month-header")).toHaveText("Июль 2026");

    // Grid is visible
    await expect(page.getByTestId("calendar-grid")).toBeVisible();

    // Bottom selected summary is visible
    await expect(page.getByTestId("calendar-selected-summary")).toBeVisible();

    // Positive fixture contains lunar data — assert exact strip, not unavailable fallback
    await expect(page.getByTestId("lunar-calendar-strip")).toBeVisible();
    await expect(page.getByTestId("lunar-calendar-unavailable")).toBeHidden();

    // Segmented controls are present
    await expect(page.getByTestId("calendar-view-day")).toBeVisible();
    await expect(page.getByTestId("calendar-view-moon")).toBeVisible();

    // No missing API fixtures after quiet wait
    await expectNoMissingApiFixtures(page, tracker);
  });

  test("day tap selects locally and footer CTA is the only navigation path", async ({ page }) => {
    const tracker = await setupCalendarPage(page);

    await page.getByTestId("calendar-day-2026-07-10").click();
    await expect(page).toHaveURL(/\/calendar$/);
    const summary = page.getByTestId("calendar-selected-summary");
    await expect(summary).toContainText("10 июля 2026");

    const cta = summary.getByRole("button", { name: /Открыть день/i });
    await expect(cta).toBeEnabled();
    await cta.scrollIntoViewIfNeeded();
    await cta.click();
    await expect(page).toHaveURL(/\/day\/2026-07-10/, { timeout: 10000 });

    await expectNoMissingApiFixtures(page, tracker);
  });

  test("moon mode displays backend lunar values deterministically", async ({ page }) => {
    const tracker = await setupCalendarPage(page);

    // Switch to moon mode first (no navigation since we haven't clicked any day button)
    await page.getByTestId("calendar-view-moon").click();
    await page.waitForTimeout(300);

    // Grid is still visible in moon mode
    await expect(page.getByTestId("calendar-grid")).toBeVisible();

    // The selected day (2026-07-08 in frozen time) moon cell shows backend lunar day number
    const moonDay = page.getByTestId("calendar-moon-day-2026-07-08");
    await expect(moonDay).toBeVisible();
    await expect(moonDay).toContainText("24");

    // Selected summary shows deterministic lunar values for 2026-07-08
    const summary = page.getByTestId("calendar-selected-summary");
    await expect(summary).toContainText("Сегодня");
    await expect(summary).toContainText("8 июля 2026");
    await expect(summary).toContainText("убыв. серп");
    await expect(summary).toContainText("39%");
    await expect(summary).toContainText("24 лунный день");
    await expect(page.getByTestId("calendar-moon-glyph-2026-07-08").locator("svg")).toBeVisible();

    // No missing API fixtures after quiet wait
    await expectNoMissingApiFixtures(page, tracker);
  });

  test("calendar screen has no horizontal overflow on mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });

    const tracker = await installMockApiRoutes(page, buildCalendarFixtures());
    await installMockVisualRuntime(page);
    await page.addInitScript(() => {
      const style = document.createElement("style");
      style.textContent = "* { animation: none !important; transition: none !important; }";
      document.documentElement.appendChild(style);
    });
    await openCalendarReady(page);
    await page.waitForTimeout(1000);

    // Check for horizontal overflow
    const overflowWidth = await page.evaluate(() => {
      return document.documentElement.scrollWidth - document.documentElement.clientWidth;
    });
    expect(overflowWidth).toBeLessThanOrEqual(5);

    // No missing API fixtures after quiet wait
    await expectNoMissingApiFixtures(page, tracker);
  });

  // ########################################################################
  // Negative proof: missing calendar API fixtures are recorded by tracker
  // ########################################################################
  test("missing API fixture is recorded by the tracker (negative proof)", async ({ page }) => {
    // Deliberately omit /api/calendar fixture
    const tracker = await installMockApiRoutes(page, {
      "/api/auth/dev": {
        status: 200,
        body: { status: "ok", userId: "mock-user-id" },
      },
      "/api/access": { body: accessPayload },
    });

    await installMockVisualRuntime(page);

    await page.goto("/calendar", { waitUntil: "domcontentloaded" });
    // The tracker should have recorded the missing /api/calendar request
    await expect.poll(() => tracker.count, { timeout: 10000 }).toBeGreaterThan(0);

    const missingPaths = tracker.all;
    expect(missingPaths.some((p) => p.startsWith("/api/calendar"))).toBe(true);
  });
});
