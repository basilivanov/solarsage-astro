// ############################################################################
// AI_HEADER: TEST_CALENDAR_SCREEN_V2 — public dayState calendar contract.
// ROLE: Verifies hero, ordinary, not-computed and lock markers on the calendar grid.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-CALENDAR-SCREEN-V2
// purpose: Test the calendar v2 dayState projection exposed by CalendarMonth.
// owns:
//   - __tests__/components/CalendarScreen.test.tsx
// inputs: generated CalendarPayload fixture.
// outputs: stable calendar day DOM assertions.
// dependencies: CalendarMonth, generated contract types, Testing Library.
// side_effects: none.
// emitted_logs: none.
// invariants: ordinary has no marker; hero and not-computed remain visually distinct; lock marker is preserved.
// failure_policy: fail on dayState or public selector drift.
// END_MODULE_CONTRACT: M-TEST-CALENDAR-SCREEN-V2

// START_MODULE_MAP: M-TEST-CALENDAR-SCREEN-V2
// public_entrypoints:
//   - calendar dayState assertions
// semantic_blocks:
//   - DAY_MARKERS
//   - ACCESS_MARKER
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-CALENDAR-SCREEN-V2

import { render, screen, cleanup } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { CalendarPayload } from "@/packages/contracts";
import { CalendarMonth } from "@/components/grace/CalendarMonth";

vi.mock("next/link", () => ({
  default: ({ href, children, ...props }: { href: string; children: ReactNode }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

afterEach(() => cleanup());

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
      isToday: false,
    },
    {
      access: { state: "full", reason: "active_subscription", subscriptionActive: true },
      date: "2026-08-02",
      dayNumber: 2,
      dayState: "ordinary",
      disabled: false,
      isCurrentMonth: true,
      isToday: false,
    },
    {
      access: { state: "full", reason: "active_subscription", subscriptionActive: true },
      date: "2026-08-03",
      dayNumber: 3,
      dayState: "not-computed",
      disabled: false,
      isCurrentMonth: true,
      isToday: false,
    },
    {
      access: { state: "locked", reason: "outside_access_window", subscriptionActive: false },
      date: "2026-08-04",
      dayNumber: 4,
      dayState: "ordinary",
      disabled: false,
      isCurrentMonth: true,
      isToday: false,
    },
  ],
  meta: {
    contractVersion: 2,
    generatedAt: "2026-07-31T00:00:00Z",
    schemaVersion: "calendar/v2",
  },
  month: "2026-08",
  title: "Август 2026",
};

// START_BLOCK: DAY_MARKERS
describe("Calendar v2 dayState markers", () => {
  it("renders hero dot, ordinary without marker, and not-computed outline", () => {
    render(
      <div data-testid="calendar-screen">
        <CalendarMonth month={calendarPayload} />
      </div>,
    );

    expect(screen.getByTestId("calendar-day-2026-08-01").getAttribute("data-day-state")).toBe("hero");
    expect(screen.getByTestId("calendar-day-2026-08-02").getAttribute("data-day-state")).toBe("ordinary");
    expect(screen.getByTestId("calendar-day-2026-08-03").getAttribute("data-day-state")).toBe("not-computed");
    expect(screen.getByTestId("calendar-day-hero-dot")).toBeTruthy();
    expect(screen.getByTestId("calendar-day-not-computed")).toBeTruthy();
    expect(screen.getByTestId("calendar-day-2026-08-02").querySelector("[data-testid='calendar-day-hero-dot']")).toBeNull();
    expect(screen.getByTestId("calendar-day-2026-08-02").querySelector("[data-testid='calendar-day-not-computed']")).toBeNull();
  });
});
// END_BLOCK: DAY_MARKERS

// START_BLOCK: ACCESS_MARKER
describe("Calendar v2 access marker", () => {
  it("keeps the lock marker on an ordinary locked day", () => {
    render(<CalendarMonth month={calendarPayload} />);
    const lockedDay = screen.getByTestId("calendar-day-2026-08-04");
    expect(lockedDay.getAttribute("data-day-state")).toBe("ordinary");
    expect(screen.getByTestId("calendar-day-lock")).toBeTruthy();
  });
});
// END_BLOCK: ACCESS_MARKER
