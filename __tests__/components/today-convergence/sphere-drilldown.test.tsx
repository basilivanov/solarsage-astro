// ############################################################################
// AI_HEADER: TEST_SPHERE_DRILLDOWN — public contract tests for snapshot evidence.
// ROLE: Verifies deterministic event chain, honest transport/access states, and disclosure semantics.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-SPHERE-DRILLDOWN
// purpose: Exercise the public DOM contract of the snapshot sphere drilldown.
// owns:
//   - __tests__/components/today-convergence/sphere-drilldown.test.tsx
// inputs: generated TodaySphereDrilldownPayload fixture and transport props.
// outputs: DOM contract assertions for ready/loading/error/access states.
// dependencies: SphereDrilldown, generated contracts, Testing Library.
// side_effects: local retry callback and disclosure state only.
// emitted_logs: none.
// invariants: evidence assertions use stable selectors/attributes and visible polarity text.
// failure_policy: fail on payload projection or accessibility contract drift.
// END_MODULE_CONTRACT: M-TEST-SPHERE-DRILLDOWN

// START_MODULE_MAP: M-TEST-SPHERE-DRILLDOWN
// public_entrypoints:
//   - ready evidence chain
//   - loading and error states
// semantic_blocks:
//   - READY_EVIDENCE
//   - TRANSPORT_AND_ACCESS
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-SPHERE-DRILLDOWN

import { fireEvent, render, screen, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SphereDrilldown, type SphereDrilldownPayload } from "@/components/today-convergence/sphere-drilldown";

vi.mock("@/components/paywall", () => ({
  Paywall: ({ title }: { title?: string }) => <section data-testid="paywall">{title}</section>,
}));

afterEach(() => cleanup());

const payload: SphereDrilldownPayload = {
  birthTimeMode: "exact",
  convergence: {
    eventIds: ["evt-drill-1", "evt-drill-2"],
    evidenceLevel: "high",
    id: "cvg-drill-1",
    polarity: "supportive",
    primarySphere: "work",
    secondarySphere: "communication",
  },
  dayTone: "supportive",
  events: [
    {
      evidenceLevel: "high",
      id: "evt-drill-1",
      kind: "aspect",
      polarity: "supportive",
      sphere: "work",
      title: "Луна в гармонии с твоим Сатурном",
      time: {
        mode: "exact",
        peak: "15:40",
        start: "13:00",
        end: "18:00",
        peakAt: "2026-08-01T15:40:00Z",
        startAt: "2026-08-01T13:00:00Z",
        endAt: "2026-08-01T18:00:00Z",
        partOfDay: null,
      },
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
  snapshotId: "snap-drill-1",
  sphere: "work",
  state: "convergence_today",
  timezone: "Europe/Moscow",
};

// START_BLOCK: READY_EVIDENCE
describe("SphereDrilldown ready evidence", () => {
  it("renders driver titles, numbered events, textual polarity and convergence reason", () => {
    render(<SphereDrilldown payload={payload} sphereKey="work" />);

    const root = screen.getByTestId("sphere-drilldown");
    expect(root.getAttribute("data-sphere")).toBe("work");
    expect(root.getAttribute("data-screen-state")).toBe("ready");
    expect(root.getAttribute("data-state")).toBe("convergence_today");
    expect(screen.getByRole("heading", { name: "Работа — сегодня" })).toBeTruthy();

    expect(screen.getByTestId("drilldown-event-evt-drill-1").getAttribute("data-polarity")).toBe("supportive");
    expect(screen.getByTestId("drilldown-event-evt-drill-1").textContent).toContain("поддержка");
    expect(screen.getByTestId("drilldown-event-title-evt-drill-1").textContent).toBe(
      "Луна в гармонии с твоим Сатурном",
    );
    expect(screen.getByTestId("drilldown-event-time-evt-drill-1").textContent).toContain(
      "пик 1 августа, 18:40, окно: с 1 августа, 16:00 до 1 августа, 21:00",
    );
    expect(screen.getByTestId("drilldown-event-polarity-evt-drill-1").className).toContain(
      "bg-(--tone-supportive-bg)",
    );
    expect(screen.getByTestId("drilldown-event-evt-drill-2").getAttribute("data-polarity")).toBe("tense");
    expect(screen.getByTestId("drilldown-event-evt-drill-2").textContent).toContain("напряжение");
    expect(screen.queryByTestId("drilldown-event-title-evt-drill-2")).toBeNull();
    expect(screen.getByTestId("drilldown-convergence")).toBeTruthy();
    expect(screen.queryByTestId("drilldown-context")).toBeNull();
    expect(screen.getByTestId("drilldown-evidence").textContent).not.toContain("Событие ·");
    expect(screen.getByTestId("drilldown-evidence").textContent).not.toContain("Это событие несёт смысл");
  });

  it("keeps calculation disclosure accessible", () => {
    render(<SphereDrilldown payload={payload} />);
    const disclosure = screen.getByRole("button", { name: "Как это рассчитано" });
    expect(disclosure.getAttribute("aria-expanded")).toBe("false");
    expect(disclosure.getAttribute("aria-controls")).toBe("today-calculation-details");
    fireEvent.click(disclosure);
    expect(disclosure.getAttribute("aria-expanded")).toBe("true");
    const copy = screen.getByText("День считается относительно твоей натальной карты и текущего положения планет.")
      .parentElement?.textContent ?? "";
    expect(copy).toContain("Пик — точный момент");
    expect(copy).toContain("Возможное проявление — ориентир");
    expect(copy).not.toMatch(/Swiss Ephemeris|snapshot|LLM/iu);
  });
});
// END_BLOCK: READY_EVIDENCE

// START_BLOCK: TRANSPORT_AND_ACCESS
describe("SphereDrilldown transport and access", () => {
  it("renders an accessible loading state", () => {
    render(<SphereDrilldown sphereKey="work" screenState="loading" />);
    const root = screen.getByTestId("sphere-drilldown");
    expect(root.getAttribute("data-screen-state")).toBe("loading");
    expect(root.getAttribute("aria-busy")).toBe("true");
    expect(screen.getByRole("status")).toBeTruthy();
  });

  it("renders a paywall for 403 and an honest unavailable state for 404", () => {
    const { rerender } = render(
      <SphereDrilldown sphereKey="work" screenState="error" errorStatus={403} />,
    );
    expect(screen.getByTestId("sphere-drilldown-access")).toBeTruthy();
    expect(screen.getByTestId("paywall")).toBeTruthy();
    expect(screen.getByText("Нужен полный доступ")).toBeTruthy();

    const onRetry = vi.fn();
    rerender(
      <SphereDrilldown sphereKey="work" screenState="error" errorStatus={404} onRetry={onRetry} />,
    );
    expect(screen.getByTestId("sphere-drilldown-unavailable")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Повторить" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
// END_BLOCK: TRANSPORT_AND_ACCESS
