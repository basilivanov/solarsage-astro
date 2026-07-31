// ############################################################################
// AI_HEADER: TEST_TODAY_SCREEN_WIRING — public DOM contract for the new Today screen.
// ROLE: Keeps the page-level TodayScreen acceptance subset on generated fixtures.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-TODAY-SCREEN-WIRING
// purpose: Verify ready, pending, unavailable, access, and transport states of the generated Today screen.
// owns:
//   - __tests__/components/TodayScreen.test.tsx
// inputs: TodayConvergencePayload fixtures and transport props.
// outputs: public DOM contract assertions.
// dependencies: components/today-convergence/today-screen, Today fixtures, Testing Library.
// side_effects: local callback spies only.
// emitted_logs: none.
// invariants: assertions use data-testid, data-*, roles, and aria only; legacy payload shapes are absent.
// failure_policy: fail on a public screen contract mismatch.
// END_MODULE_CONTRACT: M-TEST-TODAY-SCREEN-WIRING

// START_MODULE_MAP: M-TEST-TODAY-SCREEN-WIRING
// public_entrypoints:
//   - TodayScreen state acceptance tests
// semantic_blocks:
//   - READY_STATES: hero and quiet deterministic projections.
//   - ACCESS_STATES: preview and locked projections.
//   - TRANSPORT_STATES: loading/error root semantics.
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-TODAY-SCREEN-WIRING

import { fireEvent, render, screen, cleanup } from "@testing-library/react";
import type { ComponentProps } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { TodayScreen } from "@/components/today-convergence/today-screen";
import {
  accessLocked,
  accessPreview,
  contentPending,
  contentUnavailable,
  heroSupportive,
  quietSteady,
  stateUnavailable,
} from "../fixtures/today_convergence_v2";

vi.mock("@/components/paywall", () => ({
  Paywall: ({ title }: { title?: string }) => <section data-testid="paywall">{title}</section>,
}));

afterEach(() => cleanup());

function renderToday(payload: typeof heroSupportive, overrides?: Partial<ComponentProps<typeof TodayScreen>>) {
  return render(<TodayScreen payload={payload} {...overrides} />);
}

// START_BLOCK: READY_STATES
describe("TodayScreen generated payload states", () => {
  it("renders a convergence hero from the generated payload", () => {
    renderToday(heroSupportive);
    const root = screen.getByTestId("today-screen");

    expect(root.getAttribute("data-screen-state")).toBe("ready");
    expect(root.getAttribute("data-state")).toBe("convergence_today");
    expect(root.getAttribute("data-day-tone")).toBe("supportive");
    expect(screen.getByTestId("convergence-hero")).toBeTruthy();
    expect(screen.getByTestId("convergence-sphere-work").getAttribute("data-polarity")).toBe("supportive");
    expect(screen.getByTestId("today-narrative").getAttribute("data-state")).toBe("ready");
  });

  it("renders quiet deterministic content and pending narrative separately", () => {
    renderToday(quietSteady);
    expect(screen.getByTestId("impulses-list").getAttribute("data-count")).toBe("3");
    expect(screen.getByTestId("today-lookahead").getAttribute("data-target-date")).toBe("2026-08-02");

    cleanup();
    renderToday(contentPending);
    expect(screen.getByTestId("convergence-hero")).toBeTruthy();
    expect(screen.getByTestId("today-narrative").getAttribute("data-state")).toBe("pending");
    expect(screen.getByRole("status")).toBeTruthy();
    expect(screen.queryByTestId("today-loading-skeleton")).toBeNull();
  });

  it("renders a truthful content-unavailable retry in the narrative zone", () => {
    const onRetry = vi.fn();
    renderToday(contentUnavailable, { onRetry });
    expect(screen.getByTestId("today-narrative").getAttribute("data-state")).toBe("unavailable");
    expect(screen.getByTestId("impulses-list")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Повторить" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("renders calculation-unavailable without deterministic facts", () => {
    const onRetry = vi.fn();
    renderToday(stateUnavailable, { onRetry });
    expect(screen.getByTestId("today-unavailable").getAttribute("role")).toBe("alert");
    expect(screen.queryByTestId("convergence-hero")).toBeNull();
    expect(screen.queryByTestId("impulses-list")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Обновить" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
// END_BLOCK: READY_STATES

// START_BLOCK: ACCESS_STATES
describe("TodayScreen access projections", () => {
  it("renders preview teaser and paywall without evidence blocks", () => {
    renderToday(accessPreview);
    expect(screen.getByTestId("today-preview-teaser")).toBeTruthy();
    expect(screen.getByTestId("paywall")).toBeTruthy();
    expect(screen.queryByTestId("convergence-hero")).toBeNull();
    expect(screen.queryByTestId("impulses-list")).toBeNull();
  });

  it("renders locked paywall without nullable calculation axes", () => {
    renderToday(accessLocked);
    const root = screen.getByTestId("today-screen");
    expect(screen.getByTestId("paywall")).toBeTruthy();
    expect(screen.queryByTestId("today-preview-teaser")).toBeNull();
    expect(root.hasAttribute("data-state")).toBe(false);
    expect(root.hasAttribute("data-day-tone")).toBe(false);
  });
});
// END_BLOCK: ACCESS_STATES

// START_BLOCK: TRANSPORT_STATES
describe("TodayScreen transport states", () => {
  it("renders loading as an accessible component skeleton", () => {
    renderToday(heroSupportive, { screenState: "loading" });
    const root = screen.getByTestId("today-screen");
    expect(root.getAttribute("data-screen-state")).toBe("loading");
    expect(root.hasAttribute("data-state")).toBe(false);
    expect(root.getAttribute("aria-busy")).toBe("true");
    expect(screen.getByRole("status")).toBeTruthy();
  });

  it("renders one accessible retry button for transport errors", () => {
    const onRetry = vi.fn();
    renderToday(heroSupportive, { screenState: "error", onRetry });
    const root = screen.getByTestId("today-screen");
    expect(root.getAttribute("data-screen-state")).toBe("error");
    expect(root.getAttribute("role")).toBe("alert");
    expect(screen.getAllByRole("button")).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Повторить" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
// END_BLOCK: TRANSPORT_STATES
