// ############################################################################
// AI_HEADER: TEST_TODAY_CONVERGENCE_SCREEN — public DOM acceptance for the 16 Today states.
// ROLE: Renders generated fixtures through the new component suite and checks only DOM contract surfaces.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-SCREEN
// purpose: Verify every Today fixture, transport state, time presentation, disclosure, and accessibility contract.
// owns:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// inputs: 16 generated TodayConvergencePayload fixtures and TodayScreen props.
// outputs: Vitest assertions against data-testid, data-* state attributes, roles, and aria attributes.
// dependencies: @testing-library/react, packages/contracts/today-convergence.ts, Today component suite.
// side_effects: none; callbacks are local spies only.
// emitted_logs: none.
// invariants: tests never inspect CSS classes, React internals, or legacy payload fields.
// failure_policy: fail with the public DOM contract mismatch.
// END_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-SCREEN

// START_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-SCREEN
// public_entrypoints:
//   - Today fixture matrix test
//   - transport state tests
//   - accessibility and formatting tests
// semantic_blocks:
//   - FIXTURE_MATRIX: all sixteen generated payload states.
//   - TRANSPORT: loading/error root states and retry.
//   - ACCESSIBILITY: disclosures, roles, and dismiss actions.
//   - TIME_FORMAT: exact, partofday, and date public text.
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-SCREEN

import { fireEvent, render, screen, cleanup } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { TodayConvergencePayload } from "@/packages/contracts/today-convergence";
import {
  accessLocked,
  accessPreview,
  birthBucket,
  birthUnknown,
  contentPending,
  contentUnavailable,
  heroMixed,
  heroSupportive,
  heroTense,
  heroThreeSpheres,
  quietGeneralBackground,
  quietMainMax,
  quietSteady,
  quietZeroImpulses,
  stateUnavailable,
  todayConvergenceFixtures,
} from "../../fixtures/today_convergence_v2";
import { TodayScreen } from "@/components/today-convergence/today-screen";
import { formatEventTime } from "@/components/today-convergence/today-formatters";

vi.mock("@/components/paywall", () => ({
  Paywall: ({ title }: { title?: string }) => <section data-testid="paywall">{title}</section>,
}));

const FIXTURE_NAMES = [
  "01_hero_supportive",
  "02_hero_tense",
  "03_hero_mixed",
  "04_hero_three_spheres",
  "05_quiet_steady",
  "06_quiet_tense_impulse",
  "07_quiet_zero_impulses",
  "08_quiet_main_max",
  "09_quiet_general_background",
  "10_content_pending",
  "11_content_unavailable",
  "12_state_unavailable",
  "13_birth_bucket",
  "14_birth_unknown",
  "15_access_preview",
  "16_access_locked",
] as const;

const NAMED_FIXTURES: readonly [string, TodayConvergencePayload][] = FIXTURE_NAMES.map((name, index) => [
  name,
  todayConvergenceFixtures[index],
]);

afterEach(() => {
  cleanup();
});

function renderToday(payload: TodayConvergencePayload, overrides?: Partial<React.ComponentProps<typeof TodayScreen>>) {
  return render(<TodayScreen payload={payload} {...overrides} />);
}

// START_BLOCK: FIXTURE_MATRIX
describe("Today Convergence screen fixture matrix", () => {
  it.each(NAMED_FIXTURES)("renders public root axes for %s", (_name, fixture) => {
    renderToday(fixture);
    const root = screen.getByTestId("today-screen");

    expect(root.getAttribute("data-screen-state")).toBe("ready");
    expect(root.getAttribute("data-content-state")).toBe(fixture.contentState);
    expect(root.getAttribute("data-access-state")).toBe(fixture.access.state);
    expect(root.getAttribute("data-birth-time-mode")).toBe(fixture.birthTime.mode);

    if (fixture.state === null) {
      expect(root.hasAttribute("data-state")).toBe(false);
    } else {
      expect(root.getAttribute("data-state")).toBe(fixture.state);
    }
    if (fixture.dayTone === null) {
      expect(root.hasAttribute("data-day-tone")).toBe(false);
    } else {
      expect(root.getAttribute("data-day-tone")).toBe(fixture.dayTone);
    }
  });

  it("renders hero only for convergence states and exposes claim text", () => {
    for (const fixture of [heroSupportive, heroTense, heroMixed, heroThreeSpheres, contentPending]) {
      cleanup();
      renderToday(fixture);
      expect(screen.getByTestId("convergence-hero")).toBeTruthy();
    }

    cleanup();
    renderToday(heroThreeSpheres);
    expect(screen.getAllByTestId("convergence-secondary")).toHaveLength(2);
    expect(screen.getByTestId("convergence-hero").textContent).toContain("Что сошлось сегодня");
    expect(screen.getByTestId("today-screen").textContent).toContain(
      heroThreeSpheres.convergences[0].summary?.text ?? "",
    );
    expect(screen.getByTestId("convergence-hero").getAttribute("data-evidence-level")).toBe("high");
  });

  it("renders quiet main event, impulses, context, and lookahead from deterministic blocks", () => {
    renderToday(quietMainMax);
    expect(screen.getByTestId("main-event").getAttribute("data-polarity")).toBe("mixed");
    expect(screen.getByTestId("impulses-list").getAttribute("data-count")).toBe("3");
    expect(screen.getByTestId("today-lookahead").getAttribute("data-target-date")).toBe("2026-08-02");

    cleanup();
    renderToday(quietZeroImpulses);
    expect(screen.queryByTestId("impulses-list")).toBeNull();
    expect(screen.getByTestId("period-context")).toBeTruthy();
  });

  it("keeps pending skeleton inside narrative and preserves deterministic hero", () => {
    renderToday(contentPending);
    expect(screen.getByTestId("convergence-hero")).toBeTruthy();
    expect(screen.getByTestId("today-narrative").getAttribute("data-state")).toBe("pending");
    expect(screen.getByTestId("today-narrative").getAttribute("role")).toBeNull();
    expect(screen.getByRole("status")).toBeTruthy();
    expect(screen.queryByTestId("today-loading-skeleton")).toBeNull();
  });

  it("shows content-unavailable retry only inside the narrative zone", () => {
    const onRetry = vi.fn();
    renderToday(contentUnavailable, { onRetry });
    expect(screen.getByTestId("impulses-list")).toBeTruthy();
    const narrative = screen.getByTestId("today-narrative");
    expect(narrative.getAttribute("data-state")).toBe("unavailable");
    expect(narrative.textContent).toContain("Персональный разбор пока не готов");
    fireEvent.click(screen.getByRole("button", { name: "Повторить" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("keeps calculation-unavailable free of hero and impulse blocks", () => {
    const onRetry = vi.fn();
    renderToday(stateUnavailable, { onRetry });
    const root = screen.getByTestId("today-screen");
    expect(screen.getByTestId("today-unavailable").getAttribute("role")).toBe("alert");
    expect(screen.queryByTestId("convergence-hero")).toBeNull();
    expect(screen.queryByTestId("impulses-list")).toBeNull();
    expect(screen.queryByTestId("today-narrative")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Обновить" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
    expect(root.getAttribute("data-state")).toBe("unavailable");
  });
});
// END_BLOCK: FIXTURE_MATRIX

// START_BLOCK: ACCESSIBILITY
describe("Today Convergence transport, access, and accessibility contract", () => {
  it("renders loading as a transport skeleton with nullable axes absent", () => {
    renderToday(heroSupportive, { screenState: "loading" });
    const root = screen.getByTestId("today-screen");
    expect(root.getAttribute("data-screen-state")).toBe("loading");
    expect(root.hasAttribute("data-state")).toBe(false);
    expect(root.hasAttribute("data-content-state")).toBe(false);
    expect(root.getAttribute("aria-busy")).toBe("true");
    expect(screen.getByRole("status")).toBeTruthy();
  });

  it("renders one accessible transport retry on error", () => {
    const onRetry = vi.fn();
    renderToday(heroSupportive, { screenState: "error", onRetry });
    const root = screen.getByTestId("today-screen");
    expect(root.getAttribute("role")).toBe("alert");
    expect(root.getAttribute("data-screen-state")).toBe("error");
    expect(root.hasAttribute("data-access-state")).toBe(false);
    expect(screen.getAllByRole("button")).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Повторить" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("uses disclosure aria state while keeping content in the DOM", () => {
    renderToday(quietZeroImpulses);
    const button = screen.getByRole("button", { name: "Контекст периода" });
    const contentId = button.getAttribute("aria-controls");
    expect(button.getAttribute("aria-expanded")).toBe("false");
    expect(contentId).toBeTruthy();
    const content = document.getElementById(contentId ?? "");
    expect(content).toBeTruthy();
    expect(content?.hasAttribute("hidden")).toBe(true);

    fireEvent.click(button);
    expect(button.getAttribute("aria-expanded")).toBe("true");
    expect(content?.hasAttribute("hidden")).toBe(false);
  });

  it("dismisses the birth-time banner through the parent callback", () => {
    const onDismiss = vi.fn();
    const { rerender } = renderToday(birthBucket, {
      birthTimeDismissed: false,
      onBirthTimeDismiss: onDismiss,
    });
    expect(screen.getByTestId("birth-time-banner")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Скрыть подсказку о времени рождения" }));
    expect(onDismiss).toHaveBeenCalledTimes(1);

    rerender(
      <TodayScreen payload={birthBucket} birthTimeDismissed onBirthTimeDismiss={onDismiss} />,
    );
    expect(screen.queryByTestId("birth-time-banner")).toBeNull();
  });
});
// END_BLOCK: ACCESSIBILITY

// START_BLOCK: TIME_FORMAT
describe("Today Convergence public time and access projections", () => {
  it("formats exact event time with peak and window", () => {
    renderToday(quietSteady);
    const event = screen.getByTestId(`impulse-${quietSteady.impulses[0].eventId}`);
    expect(event.textContent).toContain("пик 09:30, окно 08:00–11:00");
    expect(event.getAttribute("data-time-mode")).toBe("exact");
  });

  it("formats overnight windows with an arrow and keeps midnight same-day", () => {
    expect(
      formatEventTime({ mode: "exact", peak: "10:06", start: "22:42", end: "21:21" }),
    ).toBe("пик 10:06, окно 22:42 → 21:21");
    expect(
      formatEventTime({ mode: "exact", peak: "15:40", start: "13:00", end: "18:00" }),
    ).toBe("пик 15:40, окно 13:00–18:00");
    expect(
      formatEventTime({ mode: "exact", peak: "00:00", start: "00:00", end: "00:00" }),
    ).toBe("пик 00:00, окно 00:00–00:00");
  });

  it("formats bucket and unknown event times without exact clocks", () => {
    renderToday(birthBucket);
    const bucketEvent = screen.getByTestId(`impulse-${birthBucket.impulses[0].eventId}`);
    expect(bucketEvent.textContent).toContain("утром");
    expect(bucketEvent.textContent).not.toMatch(/\d{2}:\d{2}/u);

    cleanup();
    renderToday(birthUnknown);
    const dateEvent = screen.getByTestId(`impulse-${birthUnknown.impulses[1].eventId}`);
    const partOfDayEvent = screen.getByTestId(`impulse-${birthUnknown.impulses[0].eventId}`);
    expect(dateEvent.textContent).toContain("в течение даты");
    expect(partOfDayEvent.textContent).toContain("днём");
    expect(dateEvent.textContent).not.toMatch(/\d{2}:\d{2}/u);
    expect(partOfDayEvent.textContent).not.toMatch(/\d{2}:\d{2}/u);
  });

  it("keeps preview teaser visible and locked content empty", () => {
    renderToday(accessPreview);
    expect(screen.getByTestId("today-preview-teaser")).toBeTruthy();
    expect(screen.getByTestId("paywall")).toBeTruthy();
    expect(screen.queryByTestId("convergence-hero")).toBeNull();
    expect(screen.queryByTestId("impulses-list")).toBeNull();

    cleanup();
    renderToday(accessLocked);
    expect(screen.getByTestId("paywall")).toBeTruthy();
    expect(screen.queryByTestId("today-preview-teaser")).toBeNull();
    expect(screen.queryByTestId("convergence-hero")).toBeNull();
    expect(screen.queryByTestId("impulses-list")).toBeNull();
    expect(screen.getByTestId("today-screen").hasAttribute("data-state")).toBe(false);
  });

  it("renders the fixed twelve-tile navigator with neutral markers and real paths", () => {
    renderToday(heroSupportive);
    const navigator = screen.getByTestId("sphere-navigator");
    const tiles = navigator.querySelectorAll("a[data-testid^='sphere-tile-']");
    const icons = navigator.querySelectorAll("svg[data-testid^='sphere-icon-']");
    expect(tiles).toHaveLength(12);
    expect(icons).toHaveLength(12);
    for (const icon of icons) {
      expect(icon.getAttribute("width")).toBe("24");
      expect(icon.getAttribute("height")).toBe("24");
      expect(icon.getAttribute("fill")).toBe("none");
      expect(icon.getAttribute("stroke")).toBe("currentColor");
      expect(icon.getAttribute("stroke-width")).toBe("1.5");
    }
    expect(screen.getByTestId("sphere-tile-work").getAttribute("data-has-today")).toBe("true");
    expect(screen.getByTestId("sphere-tile-shopping").getAttribute("data-has-today")).toBe("false");
    expect(screen.getByTestId("sphere-tile-work").getAttribute("href")).toBe(
      `/day/snapshots/${encodeURIComponent(heroSupportive.snapshotId!)}/spheres/work`,
    );
    expect(screen.getByTestId("sphere-tile-shopping").getAttribute("href")).toBe("/day/spheres/shopping");
  });

  it("keeps period context, spheres, and calculation disclosure in rail order", () => {
    renderToday(quietZeroImpulses);
    const rail = screen.getByTestId("today-layout-rail");
    expect(Array.from(rail.children).map((child) => child.getAttribute("data-testid"))).toEqual([
      "period-context",
      "sphere-navigator",
      "how-calculated",
    ]);
  });

  it("renders general-sky marker only for personal=false", () => {
    renderToday(quietGeneralBackground);
    expect(screen.getByTestId("day-general-sky").textContent).toContain("Не персональный прогноз");
    expect(screen.queryByTestId("today-narrative")).toBeNull();
  });
});
// END_BLOCK: TIME_FORMAT
