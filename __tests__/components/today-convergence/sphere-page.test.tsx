// ############################################################################
// AI_HEADER: TEST_SPHERE_PAGE — public contract tests for the static sphere page.
// ROLE: Verifies natal/period layers, honest time states, transport states, and forbidden daily language.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-SPHERE-PAGE
// purpose: Exercise the public DOM contract of the static sphere page and its deterministic period technique explanations.
// owns:
//   - __tests__/components/today-convergence/sphere-page.test.tsx
// inputs: inline generated TodaySpherePagePayload fixtures and transport props.
// outputs: DOM contract assertions for ready, unavailable, empty, bucket, loading, access, and error states.
// dependencies: SpherePage, generated sphere page contract, Testing Library.
// side_effects: local retry callback only.
// emitted_logs: none.
// invariants: tests assert visible structure and absence of daily verdict language.
// failure_policy: fail on payload projection, accessibility, or review-gate drift.
// END_MODULE_CONTRACT: M-TEST-SPHERE-PAGE

// START_MODULE_MAP: M-TEST-SPHERE-PAGE
// public_entrypoints:
//   - ready layer and technique-copy tests
//   - unavailable and bucket tests
//   - transport state tests
// semantic_blocks:
//   - CONTENT_LAYERS
//   - TECHNIQUE_COPY
//   - TIME_AND_LANGUAGE_GATES
//   - TRANSPORT_AND_ACCESS
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-SPHERE-PAGE

import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { TodaySpherePagePayload } from "@/packages/contracts/today-sphere-page";
import { SpherePage } from "@/components/today-convergence/sphere-page";
import {
  PERIOD_TECHNIQUE_COPY,
  PERIOD_TECHNIQUE_FALLBACK,
  PERIOD_TECHNIQUE_KEYS,
  getPeriodTechniqueCopy,
} from "@/components/today-convergence/period-technique-copy";

vi.mock("@/components/paywall", () => ({
  Paywall: ({ title }: { title?: string }) => <section data-testid="paywall">{title}</section>,
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const readyPayload: TodaySpherePagePayload = {
  birthTimeMode: "exact",
  housesAvailable: true,
  natal: {
    state: "ready",
    paragraphs: [
      {
        sourceFactIds: ["natal-work-1", "natal-work-2"],
        text: "Натальная опора связана с последовательным развитием навыка и ясной ролью в команде.",
      },
      {
        sourceFactIds: ["natal-work-3"],
        text: "Длинные задачи лучше раскрываются через ритм, который можно поддерживать без рывков.",
      },
    ],
  },
  period: [
    {
      id: "period-work-1",
      technique: "annual_profection",
      title: "Годовая тема профессионального роста",
      activeFrom: "2026-01-01",
      activeUntil: "2026-12-31",
    },
  ],
  periodIdentity: "period-work-v1",
  periodUnavailable: false,
  sphere: "work",
};

// START_BLOCK: CONTENT_LAYERS
describe("SpherePage content layers", () => {
  it("renders natal paragraphs, source bindings, and period end dates", () => {
    render(<SpherePage payload={readyPayload} sphereKey="work" />);

    const root = screen.getByTestId("sphere-page");
    expect(root.getAttribute("data-sphere")).toBe("work");
    expect(root.getAttribute("data-state")).toBe("ready");
    expect(root.getAttribute("data-birth-time-mode")).toBe("exact");
    expect(screen.getByRole("heading", { name: "Работа" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "В твоей карте" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Сейчас действует" })).toBeTruthy();

    const paragraph = screen.getByTestId("sphere-natal-paragraph-0");
    expect(paragraph.textContent).toContain("Натальная опора");
    expect(paragraph.getAttribute("data-source-fact-ids")).toBe("natal-work-1,natal-work-2");

    const period = screen.getByTestId("sphere-period-period-work-1");
    expect(period.textContent).toContain("Годовая тема профессионального роста");
    expect(period.textContent).toContain("до 31 декабря 2026 г.");
    expect(period.querySelector("time")?.getAttribute("dateTime")).toBe("2026-12-31");
  });

  it("renders an honest natal unavailable state and an empty period state", () => {
    const payload: TodaySpherePagePayload = {
      ...readyPayload,
      natal: { state: "unavailable", paragraphs: null },
      period: [],
      periodUnavailable: true,
    };

    render(<SpherePage payload={payload} sphereKey="work" />);

    expect(screen.getByTestId("sphere-natal-unavailable").textContent).toBe("Разбор сферы готовится");
    expect(screen.getByTestId("sphere-period-empty").textContent).toBe(
      "Периодический контекст пока недоступен",
    );
    expect(within(screen.getByTestId("sphere-natal")).queryByRole("button")).toBeNull();
  });

  it("renders the three static explanation parts for every supported period technique", () => {
    const periods = PERIOD_TECHNIQUE_KEYS.map((technique, index) => ({
      ...readyPayload.period[0],
      id: `period-${technique}`,
      technique,
      title: `${getPeriodTechniqueCopy(technique).label}: исходное название ${index + 1}`,
      activeUntil: "2026-12-31",
    }));

    render(<SpherePage payload={{ ...readyPayload, period: periods }} sphereKey="work" />);

    for (const technique of PERIOD_TECHNIQUE_KEYS) {
      const period = periods.find((item) => item.technique === technique);
      if (!period) throw new Error(`missing period fixture for ${technique}`);
      const copy = PERIOD_TECHNIQUE_COPY[technique];
      const item = screen.getByTestId(`sphere-period-${period.id}`);

      expect(item.getAttribute("data-technique")).toBe(technique);
      expect(screen.getByTestId(`sphere-period-title-${period.id}`).textContent).toContain(period.title);
      expect(item.textContent).toContain("до 31 декабря 2026 г.");
      expect(screen.getByTestId(`sphere-period-technique-copy-${period.id}`).textContent).toContain(copy.label);
      expect(screen.getByTestId(`sphere-period-what-it-is-${period.id}`).textContent).toBe(copy.whatItIs);
      expect(screen.getByTestId(`sphere-period-how-it-affects-now-${period.id}`).textContent).toBe(copy.howItAffectsNow);
      expect(screen.getByTestId(`sphere-period-what-you-may-notice-${period.id}`).textContent).toBe(copy.whatYouMayNotice);
    }
  });

  it("uses neutral technique copy for an absent or future runtime enum", () => {
    const futureTechnique = "future_period_technique";
    const payload = {
      ...readyPayload,
      period: [
        {
          ...readyPayload.period[0],
          technique: futureTechnique as TodaySpherePagePayload["period"][number]["technique"],
        },
      ],
    };

    render(<SpherePage payload={payload} sphereKey="work" />);

    const explanation = screen.getByTestId("sphere-period-technique-copy-period-work-1");
    expect(explanation.getAttribute("data-technique")).toBe(futureTechnique);
    expect(explanation.textContent).toContain(PERIOD_TECHNIQUE_FALLBACK.label);
    expect(screen.getByTestId("sphere-period-what-it-is-period-work-1").textContent).toBe(
      PERIOD_TECHNIQUE_FALLBACK.whatItIs,
    );
    expect(getPeriodTechniqueCopy(undefined)).toBe(PERIOD_TECHNIQUE_FALLBACK);
  });
});
// END_BLOCK: CONTENT_LAYERS

// START_BLOCK: TIME_AND_LANGUAGE_GATES
describe("SpherePage review gates", () => {
  it("shows the truthful house notice for bucket time and no house-derived content", () => {
    const payload: TodaySpherePagePayload = {
      ...readyPayload,
      birthTimeMode: "bucket",
      housesAvailable: false,
    };

    render(<SpherePage payload={payload} sphereKey="work" />);

    const root = screen.getByTestId("sphere-page");
    expect(root.getAttribute("data-birth-time-mode")).toBe("bucket");
    expect(root.getAttribute("data-houses-available")).toBe("false");
    expect(screen.getByTestId("sphere-houses-unavailable").textContent).toBe(
      "Дома и точные часы скрыты: время рождения не указано",
    );
    expect(screen.queryByTestId("sphere-house-content")).toBeNull();
    expect(screen.queryByTestId("sphere-asc")).toBeNull();
    expect(screen.queryByTestId("sphere-lot")).toBeNull();
  });

  it("does not render forbidden daily words or daily verdict markers", () => {
    render(<SpherePage payload={readyPayload} sphereKey="work" />);

    const root = screen.getByTestId("sphere-page");
    const text = root.textContent?.toLowerCase() ?? "";
    expect(text.includes("сегодня")).toBe(false);
    expect(text.includes("завтра")).toBe(false);
    expect(root.querySelector('[data-polarity]')).toBeNull();
    expect(root.querySelector('[data-testid*="verdict"]')).toBeNull();
  });
});
// END_BLOCK: TIME_AND_LANGUAGE_GATES

// START_BLOCK: TRANSPORT_AND_ACCESS
describe("SpherePage transport and access", () => {
  it("renders loading, 403 paywall, and 422 unavailable states", () => {
    const { rerender } = render(<SpherePage sphereKey="work" screenState="loading" />);
    const root = screen.getByTestId("sphere-page");
    expect(root.getAttribute("data-state")).toBe("loading");
    expect(root.getAttribute("aria-busy")).toBe("true");
    expect(screen.getByRole("status")).toBeTruthy();

    rerender(<SpherePage sphereKey="work" screenState="error" errorStatus={403} />);
    expect(root.getAttribute("data-state")).toBe("locked");
    expect(screen.getByTestId("sphere-page-access")).toBeTruthy();
    expect(screen.getByTestId("paywall")).toBeTruthy();

    const onRetry = vi.fn();
    rerender(
      <SpherePage sphereKey="work" screenState="error" errorStatus={422} onRetry={onRetry} />,
    );
    expect(root.getAttribute("data-state")).toBe("error");
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.getByText("Страница недоступна")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Повторить" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
// END_BLOCK: TRANSPORT_AND_ACCESS
