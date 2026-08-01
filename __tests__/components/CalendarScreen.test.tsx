// ############################################################################
// AI_HEADER: TEST_CALENDAR_SCREEN — restored day/moon calendar contract.
// ROLE: Verifies the active legacy calendar layout against generated calendar/v2 data.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-CALENDAR-SCREEN
// purpose: Test the active CalendarScreen loading, toggle, dayState marker, access, and selected-day contracts.
// owns:
//   - __tests__/components/CalendarScreen.test.tsx
// inputs: generated CalendarPayload fixture and mocked monthly fetch.
// outputs: stable public DOM assertions for the restored calendar surface.
// dependencies: CalendarScreen; generated contract types; Testing Library; Vitest.
// side_effects: none; the calendar API facade is mocked at the module boundary.
// emitted_logs: none.
// invariants: hero/not-computed markers are distinct; ordinary has no marker; locked days retain a lock; moon mode exposes lunar data.
// failure_policy: fail on state, selector, marker, toggle, or access-contract drift.
// END_MODULE_CONTRACT: M-TEST-CALENDAR-SCREEN

// START_MODULE_MAP: M-TEST-CALENDAR-SCREEN
// public_entrypoints:
//   - restored calendar screen assertions
// semantic_blocks:
//   - DAY_STATE_MARKERS
//   - VIEW_TOGGLE
//   - ACCESS_AND_NAVIGATION
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-CALENDAR-SCREEN

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import type { CalendarPayload } from "@/packages/contracts"
import { CalendarScreen } from "@/components/calendar/calendar-screen"

const calendarApi = vi.hoisted(() => ({
  getMonthCalendar: vi.fn(),
}))

vi.mock("@/lib/api/calendar", () => ({
  getMonthCalendar: calendarApi.getMonthCalendar,
}))

vi.mock("@/lib/today", () => ({
  TODAY: new Date(2026, 7, 1, 12),
  sameDay: (left: Date, right: Date) => (
    left.getFullYear() === right.getFullYear()
    && left.getMonth() === right.getMonth()
    && left.getDate() === right.getDate()
  ),
}))

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

const calendarPayload: CalendarPayload = {
  allowedRange: { from: "2026-01-01", to: "2026-12-31" },
  days: [
    {
      access: { state: "full", reason: "active_subscription", subscriptionActive: true },
      date: "2026-08-01",
      dayNumber: 1,
      dayState: "hero",
      disabled: false,
      isCurrentMonth: true,
      isToday: true,
      lunar: {
        phase: "full_moon",
        phaseIndex: 4,
        phaseLabel: "полнолуние",
        illumination: 98,
        lunarDay: 17,
        moonSign: "Capricorn",
        moonSignLabel: "Козерог",
        voidOfCourse: false,
      },
    },
    {
      access: { state: "full", reason: "active_subscription", subscriptionActive: true },
      date: "2026-08-02",
      dayNumber: 2,
      dayState: "ordinary",
      disabled: false,
      isCurrentMonth: true,
      isToday: false,
      lunar: { phaseIndex: 5, lunarDay: 18, voidOfCourse: false },
    },
    {
      access: { state: "full", reason: "active_subscription", subscriptionActive: true },
      date: "2026-08-03",
      dayNumber: 3,
      dayState: "not-computed",
      disabled: false,
      isCurrentMonth: true,
      isToday: false,
      lunar: { phaseIndex: 5, lunarDay: 19, voidOfCourse: false },
    },
    {
      access: { state: "locked", reason: "outside_access_window", subscriptionActive: false },
      date: "2026-08-04",
      dayNumber: 4,
      dayState: "ordinary",
      disabled: false,
      isCurrentMonth: true,
      isToday: false,
      lunar: { phaseIndex: 6, lunarDay: 20, voidOfCourse: true },
    },
  ],
  meta: {
    contractVersion: 2,
    generatedAt: "2026-07-31T00:00:00Z",
    schemaVersion: "calendar/v2",
  },
  month: "2026-08",
  title: "Август 2026",
}

async function renderReady(props: React.ComponentProps<typeof CalendarScreen> = {}) {
  calendarApi.getMonthCalendar.mockResolvedValue(calendarPayload)
  render(<CalendarScreen {...props} />)
  await waitFor(() => {
    expect(screen.getByTestId("calendar-screen").getAttribute("data-state")).toBe("ready")
  })
}

// START_BLOCK: DAY_STATE_MARKERS
describe("CalendarScreen dayState markers", () => {
  it("renders the restored grid and neutral hero/not-computed markers", async () => {
    await renderReady()

    expect(screen.getByTestId("calendar-month-header").textContent).toBe("Август 2026")
    expect(screen.getByTestId("calendar-grid")).toBeTruthy()

    const hero = screen.getByTestId("calendar-day-2026-08-01")
    const ordinary = screen.getByTestId("calendar-day-2026-08-02")
    const notComputed = screen.getByTestId("calendar-day-2026-08-03")

    expect(hero.getAttribute("data-day-state")).toBe("hero")
    expect(ordinary.getAttribute("data-day-state")).toBe("ordinary")
    expect(notComputed.getAttribute("data-day-state")).toBe("not-computed")
    expect(hero.querySelector("[data-testid='calendar-day-hero-dot']")).toBeTruthy()
    expect(notComputed.querySelector("[data-testid='calendar-day-not-computed']")).toBeTruthy()
    expect(ordinary.querySelector("[data-testid='calendar-day-hero-dot']")).toBeNull()
    expect(ordinary.querySelector("[data-testid='calendar-day-not-computed']")).toBeNull()
    expect(screen.queryByText(/напряжённый|поддерживающий|ровный/)).toBeNull()
  })
})
// END_BLOCK: DAY_STATE_MARKERS

// START_BLOCK: VIEW_TOGGLE
describe("CalendarScreen view toggle", () => {
  it("switches between day cells and the lunar strip", async () => {
    await renderReady()

    expect(screen.getByTestId("calendar-view-day").getAttribute("aria-pressed")).toBe("true")
    expect(screen.queryByTestId("lunar-calendar-strip")).toBeNull()

    fireEvent.click(screen.getByTestId("calendar-view-moon"))

    expect(screen.getByTestId("calendar-view-moon").getAttribute("aria-pressed")).toBe("true")
    expect(screen.getByTestId("lunar-calendar-strip")).toBeTruthy()
    expect(screen.getByTestId("calendar-moon-glyph-2026-08-01")).toBeTruthy()
    expect(screen.getByTestId("calendar-moon-day-2026-08-01").textContent).toBe("17")

    fireEvent.click(screen.getByTestId("calendar-view-day"))
    expect(screen.getByTestId("calendar-view-day").getAttribute("aria-pressed")).toBe("true")
    expect(screen.queryByTestId("lunar-calendar-strip")).toBeNull()
  })
})
// END_BLOCK: VIEW_TOGGLE

// START_BLOCK: ACCESS_AND_NAVIGATION
describe("CalendarScreen access and selected-day action", () => {
  it("keeps the lock marker on an ordinary locked day", async () => {
    await renderReady()

    const lockedDay = screen.getByTestId("calendar-day-2026-08-04")
    expect(lockedDay.getAttribute("data-day-state")).toBe("ordinary")
    expect(lockedDay.querySelector("[data-testid='calendar-day-lock']")).toBeTruthy()
  })

  it("opens the selected day through the route callback", async () => {
    const onOpenDay = vi.fn()
    await renderReady({ onOpenDay })

    fireEvent.click(screen.getByTestId("calendar-day-2026-08-02"))
    fireEvent.click(screen.getByRole("button", { name: "Открыть день" }))

    expect(onOpenDay).toHaveBeenCalledTimes(1)
    expect(onOpenDay.mock.calls[0]?.[0]).toEqual(new Date(2026, 7, 2))
  })
})
// END_BLOCK: ACCESS_AND_NAVIGATION
