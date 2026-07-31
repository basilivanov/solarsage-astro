// ############################################################################
// AI_HEADER: TEST_APP_CHECKIN_PAGE_V2 — check-in route composition contract.
// ROLE: Verifies timezone target resolution, page selector, back navigation, and completion routing.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-APP-CHECKIN-PAGE-V2
// purpose: Test the /checkin page shell around the snapshot-aware CheckinScreen.
// owns:
//   - __tests__/app/checkin-page.test.tsx
// inputs: mocked route/search/profile state and child callbacks.
// outputs: public check-in page DOM and router assertions.
// dependencies: app/(grace)/checkin/page, CheckinScreen, useProfile.
// side_effects: local router spies only.
// invariants: completion uses the resolved target date; the page does not render forecast detail itself.
// failure_policy: fail on route composition or target-date drift.
// END_MODULE_CONTRACT: M-TEST-APP-CHECKIN-PAGE-V2

// START_MODULE_MAP: M-TEST-APP-CHECKIN-PAGE-V2
// public_entrypoints:
//   - page target and navigation tests
// semantic_blocks:
//   - TARGET_DATE
//   - PAGE_NAVIGATION
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-APP-CHECKIN-PAGE-V2

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  push: vi.fn(),
  back: vi.fn(),
  searchParam: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mocks.push, back: mocks.back }),
  useSearchParams: () => ({ get: mocks.searchParam }),
}));

vi.mock("@/hooks/use-profile", () => ({
  useProfile: () => ({
    profile: { currentLocation: null, birthLocation: null },
  }),
}));

vi.mock("@/components/checkin/checkin-screen", () => ({
  CheckinScreen: ({
    targetDate,
    onComplete,
  }: {
    targetDate: string;
    onComplete?: (result: unknown) => void;
  }) => (
    <section data-testid="checkin-screen">
      <span data-testid="checkin-target-date">{targetDate}</span>
      <button type="button" onClick={() => onComplete?.({ targetDate })}>Сохранить оценку</button>
    </section>
  ),
}));

import CheckinPage from "@/app/(grace)/checkin/page";

beforeEach(() => {
  vi.clearAllMocks();
  mocks.searchParam.mockImplementation((key: string) => (
    key === "target" ? "2026-08-01" : null
  ));
});

// START_BLOCK: TARGET_DATE
describe("CheckinPage target date", () => {
  it("passes an explicit ISO target to the check-in screen", () => {
    render(<CheckinPage />);
    expect(screen.getByTestId("checkin-screen")).toBeTruthy();
    expect(screen.getByTestId("checkin-target-date").textContent).toBe("2026-08-01");
  });

  it("resolves yesterday through the page date helper when requested", () => {
    mocks.searchParam.mockImplementation((key: string) => (
      key === "target" ? "yesterday" : null
    ));
    render(<CheckinPage />);
    expect(screen.getByTestId("checkin-target-date").textContent).toMatch(/^\d{4}-\d{2}-\d{2}$/u);
  });
});
// END_BLOCK: TARGET_DATE

// START_BLOCK: PAGE_NAVIGATION
describe("CheckinPage navigation", () => {
  it("routes back and to the resolved day after completion", () => {
    render(<CheckinPage />);
    fireEvent.click(screen.getByRole("button", { name: "Назад" }));
    expect(mocks.back).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Сохранить оценку" }));
    expect(mocks.push).toHaveBeenCalledWith("/day/2026-08-01");
  });
});
// END_BLOCK: PAGE_NAVIGATION
