// ############################################################################
// AI_HEADER: TEST_DAY_PAGE_WIRING — route-level Today Convergence acceptance.
// ROLE: Verifies date routing, hook state projection, onboarding sync, and retry wiring.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-DAY-PAGE-WIRING
// purpose: Verify /day/[date] connects the generated hook to the new TodayScreen.
// owns:
//   - __tests__/app/day-page.test.tsx
// inputs: mocked hook state, route params, and generated Today fixtures.
// outputs: public route DOM and router callback assertions.
// dependencies: app/(grace)/day/[date]/page, useTodayConvergence, TodayScreen.
// side_effects: local router/onboarding spies only.
// emitted_logs: none.
// invariants: tests do not import or render the legacy day screen path; the
//   Today-label test pins its clock locally and always restores real timers.
// failure_policy: fail on route/state wiring mismatch.
// END_MODULE_CONTRACT: M-TEST-DAY-PAGE-WIRING

// START_MODULE_MAP: M-TEST-DAY-PAGE-WIRING
// public_entrypoints:
//   - DayPage route state tests
// semantic_blocks:
//   - ROUTE_DATE: today/ISO/invalid parameter handling.
//   - SCREEN_WIRING: loading, ready, error, and retry projection.
//   - ONBOARDING: ready payload synchronization.
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-DAY-PAGE-WIRING

import { fireEvent, render, screen, waitFor, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { TodayConvergencePayload } from "@/packages/contracts/today-convergence";
import {
  quietSteady,
} from "../fixtures/today_convergence_v2";

const mocks = vi.hoisted(() => ({
  route: { date: "2026-08-01" },
  replace: vi.fn(),
  push: vi.fn(),
  setOnboarded: vi.fn(),
  useTodayConvergence: vi.fn(),
  todayScreen: vi.fn(
    ({
      payload,
      screenState,
      onRetry,
    }: {
      payload: TodayConvergencePayload;
      screenState: "loading" | "ready" | "error";
      onRetry?: () => void;
    }) => (
      <section
        data-testid="today-screen"
        data-screen-state={screenState}
        data-state={screenState === "ready" ? payload.state ?? undefined : undefined}
        role={screenState === "error" ? "alert" : undefined}
      >
        {screenState === "loading" ? <div role="status">loading</div> : null}
        {screenState === "error" ? (
          <button type="button" onClick={onRetry}>
            Повторить
          </button>
        ) : null}
        {screenState === "ready" ? <span>{payload.targetDate}</span> : null}
      </section>
    ),
  ),
}));

vi.mock("next/navigation", () => ({
  useParams: () => mocks.route,
  useRouter: () => ({ replace: mocks.replace, push: mocks.push }),
}));

vi.mock("@/lib/grace/hooks/useTodayConvergence", () => ({
  useTodayConvergence: mocks.useTodayConvergence,
}));

vi.mock("@/hooks/use-onboarded", () => ({
  useOnboarded: () => ({ setOnboarded: mocks.setOnboarded }),
}));

vi.mock("@/components/today-convergence/today-screen", () => ({
  TodayScreen: mocks.todayScreen,
}));

import DayPage from "@/app/(grace)/day/[date]/page";

afterEach(() => cleanup());

beforeEach(() => {
  vi.clearAllMocks();
  mocks.route.date = "2026-08-01";
  mocks.useTodayConvergence.mockReturnValue({
    screenState: "loading",
    payload: undefined,
    retryAfterSeconds: 0,
    retrying: false,
    refetch: vi.fn(),
  });
});

// START_BLOCK: SCREEN_WIRING
describe("DayPage Today Convergence wiring", () => {
  it("projects hook loading into the new TodayScreen", () => {
    render(<DayPage />);
    expect(screen.getByTestId("today-screen").getAttribute("data-screen-state")).toBe("loading");
    expect(screen.getByRole("status")).toBeTruthy();
    expect(mocks.useTodayConvergence).toHaveBeenCalledWith("2026-08-01");
  });

  it("projects ready payload and preserves onboarding synchronization", async () => {
    mocks.useTodayConvergence.mockReturnValue({
      screenState: "ready",
      payload: quietSteady,
      retryAfterSeconds: 0,
      retrying: false,
      refetch: vi.fn(),
    });

    render(<DayPage />);
    expect(screen.getByTestId("today-screen").getAttribute("data-screen-state")).toBe("ready");
    expect(screen.getByTestId("today-screen").getAttribute("data-state")).toBe("quiet_day");
    await waitFor(() => expect(mocks.setOnboarded).toHaveBeenCalledWith(true));
  });

  it("projects hook error and sends page retry back to refetch", () => {
    const refetch = vi.fn();
    mocks.useTodayConvergence.mockReturnValue({
      screenState: "error",
      payload: undefined,
      retryAfterSeconds: 0,
      retrying: false,
      refetch,
    });

    render(<DayPage />);
    expect(screen.getByTestId("today-screen").getAttribute("data-screen-state")).toBe("error");
    fireEvent.click(screen.getByRole("button", { name: "Повторить" }));
    expect(refetch).toHaveBeenCalledTimes(1);
  });
});
// END_BLOCK: SCREEN_WIRING

// START_BLOCK: ROUTE_DATE
describe("DayPage route date handling", () => {
  it("passes the today sentinel through to the API hook", () => {
    mocks.route.date = "today";
    render(<DayPage />);
    expect(mocks.useTodayConvergence).toHaveBeenCalledWith("today");
    expect(mocks.replace).not.toHaveBeenCalled();
  });

  it("replaces invalid route parameters with today's ISO route", () => {
    mocks.route.date = "not-a-date";
    render(<DayPage />);
    expect(mocks.replace).toHaveBeenCalledWith(expect.stringMatching(/^\/day\/\d{4}-\d{2}-\d{2}$/u));
    expect(mocks.useTodayConvergence).toHaveBeenCalledWith("today");
  });

  it("keeps previous/next date navigation on the page shell", () => {
    render(<DayPage />);
    fireEvent.click(screen.getByRole("button", { name: "Следующий день" }));
    expect(mocks.push).toHaveBeenCalledWith("/day/2026-08-02");
    fireEvent.click(screen.getByRole("button", { name: "Предыдущий день" }));
    expect(mocks.push).toHaveBeenCalledWith("/day/2026-07-31");
  });

  it("renders a human date header with the Today label", async () => {
    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-08-01T12:00:00+03:00"));
      vi.resetModules();
      const { default: DayPageAtPinnedTime } = await import("@/app/(grace)/day/[date]/page");
      render(<DayPageAtPinnedTime />);
      const header = screen.getByTestId("day-date-navigation");

      expect(header.textContent).toContain("Сегодня, 1 августа");
      expect(header.textContent).not.toContain("2026-08-01");
    } finally {
      vi.useRealTimers();
    }
  });

  it("keeps the date controls below Telegram and iOS top safe areas", () => {
    render(<DayPage />);
    const header = screen.getByTestId("day-date-navigation");

    expect(header.getAttribute("style")).toContain("--tg-content-safe-area-inset-top");
    expect(header.getAttribute("style")).toContain("env(safe-area-inset-top)");
  });

  it("navigates next and previous dates from horizontal swipes", () => {
    render(<DayPage />);
    const page = screen.getByTestId("day-date-navigation").parentElement!;

    fireEvent.touchStart(page, { touches: [{ clientX: 220, clientY: 120 }] });
    fireEvent.touchEnd(page, { changedTouches: [{ clientX: 150, clientY: 125 }] });
    expect(mocks.push).toHaveBeenLastCalledWith("/day/2026-08-02");

    fireEvent.touchStart(page, { touches: [{ clientX: 150, clientY: 120 }] });
    fireEvent.touchEnd(page, { changedTouches: [{ clientX: 225, clientY: 125 }] });
    expect(mocks.push).toHaveBeenLastCalledWith("/day/2026-07-31");
  });

  it("ignores vertical and interactive-element gestures", () => {
    render(<DayPage />);
    const page = screen.getByTestId("day-date-navigation").parentElement!;
    const nextButton = screen.getByRole("button", { name: "Следующий день" });

    fireEvent.touchStart(page, { touches: [{ clientX: 220, clientY: 120 }] });
    fireEvent.touchEnd(page, { changedTouches: [{ clientX: 280, clientY: 190 }] });
    expect(mocks.push).not.toHaveBeenCalled();

    fireEvent.touchStart(nextButton, { touches: [{ clientX: 220, clientY: 120 }] });
    fireEvent.touchEnd(nextButton, { changedTouches: [{ clientX: 140, clientY: 125 }] });
    expect(mocks.push).not.toHaveBeenCalled();
  });
});
// END_BLOCK: ROUTE_DATE
