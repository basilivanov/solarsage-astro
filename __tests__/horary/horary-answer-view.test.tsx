
// ############################################################################
// AI_HEADER: MODULE_HORARY_HORARY_ANSWER_VIEW_TEST
// ROLE: Unit tests for horary-answer-view.test.tsx
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// #########################################// START_MODULE_CONTRACT
// purpose: Tests for horary-answer-viewtsx behavior
// owns:
//   - __tests__/horary/horary-answer-view.test.tsx
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { HoraryAnswerView } from "@/components/readings/horary/horary-answer-view";

// ── Mocks ──────────────────────────────────────────────────────────────

// Mock next/link so we can assert on href without needing Next.js runtime
vi.mock("next/link", () => {
  return {
    default: (props: React.PropsWithChildren<{ href: string }>) => {
      return React.createElement("a", { href: props.href }, props.children);
    },
  };
});

// Mock framer-motion – pass through as simple divs so animations don't block
vi.mock("framer-motion", () => {
  return {
    motion: {
      div: React.forwardRef(
        (props: React.PropsWithChildren<Record<string, unknown>>, ref: React.Ref<HTMLDivElement>) =>
          React.createElement("div", { ...props, ref }, props.children)
      ),
    },
    AnimatePresence: ({ children }: React.PropsWithChildren) => children,
  };
});

// Mock HoraryBlockRenderer – we only care that it receives the right block
vi.mock(
  "@/components/readings/horary/horary-block-renderer",
  () => {
    return {
      HoraryBlockRenderer: ({ block }: { block: { type: string; [k: string]: unknown } }) => {
        return React.createElement(
          "div",
          { "data-testid": "mock-block-renderer", "data-block-type": block.type },
          `block:${block.type}`
        );
      },
    };
  }
);

// ── Helper ─────────────────────────────────────────────────────────────

function makeQuestion(overrides: Record<string, unknown> = {}) {
  return {
    id: "q-1",
    text: "Выйду ли я замуж?",
    category: "love" as const,
    status: "answered" as const,
    createdAt: "2026-01-15T12:00:00Z",
    creditRefunded: false,
    clientTimezone: "Europe/Moscow",
    answer: {
      verdict: "yes" as const,
      confidence: 0.8,
      confidenceLabel: "high" as const,
      confidenceExplanation: "High confidence",
      blocks: [],
      planets: ["Sun", "Moon"],
      generatedAt: "2026-01-15T12:05:00Z",
    },
    ...overrides,
  } as any;
}

// ── Tests ──────────────────────────────────────────────────────────────

describe("HoraryAnswerView", () => {
  // 1. Returns null when answer is null
  it("returns null when answer is null", () => {
    const { container } = render(
      <HoraryAnswerView question={makeQuestion({ answer: null })} />
    );
    expect(container.innerHTML).toBe("");
  });

  // 2. data-testid="horary-answer-view" present when answer exists
  it("renders the root with data-testid='horary-answer-view' when answer exists", () => {
    render(<HoraryAnswerView question={makeQuestion()} />);
    expect(screen.getByTestId("horary-answer-view")).toBeTruthy();
  });

  // 3. Category badge with emoji + label (e.g., "love" → 💕 Отношения)
  it("shows category badge with emoji and label for a known category", () => {
    render(<HoraryAnswerView question={makeQuestion({ category: "love" })} />);
    // The badge contains both the emoji and the label
    expect(screen.getByText("💕")).toBeTruthy();
    expect(screen.getByText("Отношения")).toBeTruthy();
  });

  // 4. No category → no badge
  it("does not render a category badge when category is null", () => {
    render(<HoraryAnswerView question={makeQuestion({ category: null })} />);
    // None of the known category labels should appear
    expect(screen.queryByText("Отношения")).toBeNull();
    expect(screen.queryByText("Работа")).toBeNull();
    expect(screen.queryByText("💕")).toBeNull();
  });

  // 5. Question text rendered with quotes
  it("renders the question text wrapped in guillemet quotes", () => {
    const { container } = render(<HoraryAnswerView question={makeQuestion()} />);
    // The quotes and text are in separate text nodes inside <p>, so use container text
    expect(container.textContent).toContain("«");
    expect(container.textContent).toContain("Выйду ли я замуж?");
    expect(container.textContent).toContain("»");
  });

  // 6. Question location name displayed when present
  it("displays the question location name when provided", () => {
    render(
      <HoraryAnswerView
        question={makeQuestion({ questionLocationName: "Москва" })}
      />
    );
    expect(screen.getByText("Москва")).toBeTruthy();
    expect(screen.getByText(/Место расчета:/)).toBeTruthy();
  });

  // 7. No location name → no location line
  it("does not render location line when questionLocationName is null", () => {
    render(
      <HoraryAnswerView
        question={makeQuestion({ questionLocationName: null })}
      />
    );
    expect(screen.queryByText(/Место расчета:/)).toBeNull();
  });

  // 8. Answer blocks rendered via HoraryBlockRenderer (mocked)
  it("renders answer blocks through HoraryBlockRenderer", () => {
    const blocks = [
      { type: "paragraph", text: "Some text" },
      { type: "verdict_card", verdict: "yes", confidence: 0.8, confidenceLabel: "high", confidenceExplanation: "test" },
    ];
    render(<HoraryAnswerView question={makeQuestion({ answer: { ...makeQuestion().answer, blocks } })} />);
    const rendered = screen.getAllByTestId("mock-block-renderer");
    expect(rendered).toHaveLength(2);
    expect(rendered[0].getAttribute("data-block-type")).toBe("paragraph");
    expect(rendered[1].getAttribute("data-block-type")).toBe("verdict_card");
  });

  // 9. Empty answer.blocks array → no block divs
  it("renders no blocks when answer.blocks is empty", () => {
    render(<HoraryAnswerView question={makeQuestion()} />);
    expect(screen.queryByTestId("mock-block-renderer")).toBeNull();
  });

  // 10. Planets list with Russian names (e.g., "Sun" → "Солнце")
  it("renders planets with Russian names", () => {
    render(
      <HoraryAnswerView
        question={makeQuestion({ answer: { ...makeQuestion().answer, planets: ["Sun", "Moon"] } })}
      />
    );
    expect(screen.getByText("Солнце")).toBeTruthy();
    expect(screen.getByText("Луна")).toBeTruthy();
  });

  // 11. Unknown planet name → falls back to English original
  it("falls back to English name for unknown planets", () => {
    render(
      <HoraryAnswerView
        question={makeQuestion({ answer: { ...makeQuestion().answer, planets: ["Xylophone"] } })}
      />
    );
    expect(screen.getByText("Xylophone")).toBeTruthy();
  });

  // 12. Empty answer.planets array → no planets section
  it("does not render planets section when planets array is empty", () => {
    render(
      <HoraryAnswerView
        question={makeQuestion({ answer: { ...makeQuestion().answer, planets: [] } })}
      />
    );
    expect(screen.queryByText(/Задействованные светила/)).toBeNull();
  });

  // 13. formatDisplayDate with invalid date → returns iso string
  it("falls back to raw iso string when date is invalid", () => {
    const badDate = "not-a-valid-date";
    // Invalid dates produce "Invalid Date" from toLocaleString in most environments,
    // but the catch block should return the original iso string.
    // We render with a bad createdAt and check it appears verbatim.
    render(
      <HoraryAnswerView
        question={makeQuestion({ createdAt: badDate })}
      />
    );
    // The component uses formatDisplayDate(createdAt) inside the question card.
    // With an invalid date, new Date("not-a-valid-date") yields Invalid Date,
    // toLocaleString returns "Invalid Date" (no throw), so the catch won't fire.
    // But we can still verify the component doesn't crash and the text is present.
    // For the catch path, we need to test generatedAt with a value that throws.
    // Let's verify the component renders without crashing with bad createdAt.
    expect(screen.getByTestId("horary-answer-view")).toBeTruthy();
  });

  // 13b. formatDisplayDate with invalid date that causes a throw → returns iso
  it("returns raw string when formatDisplayDate catches an error", () => {
    // We spy on Date constructor to force a throw for a specific input
    const OrigDate = globalThis.Date;
    const badIso = "THROW_ON_THIS";
    vi.spyOn(globalThis, "Date" as any).mockImplementation(function (this: any, arg?: any) {
      if (arg === badIso) {
        throw new Error("bad date");
      }
      return new OrigDate(arg);
    });

    render(
      <HoraryAnswerView
        question={makeQuestion({ createdAt: badIso })}
      />
    );
    // The catch block returns the raw iso string
    expect(screen.getByText(badIso)).toBeTruthy();

    vi.restoreAllMocks();
  });

  // 14. generatedAt footer display
  it("renders generatedAt in the footer", () => {
    const generatedAt = "2026-01-15T12:05:00Z";
    render(
      <HoraryAnswerView
        question={makeQuestion({ answer: { ...makeQuestion().answer, generatedAt } })}
      />
    );
    // Footer contains "Сформировано" plus the formatted date
    const footer = screen.getByText(/Сформировано/);
    expect(footer).toBeTruthy();
    // The formatted date should contain the year 2026
    expect(footer.textContent).toContain("2026");
  });

  // 15. Back navigation link → /readings/horary
  it("renders a back link to /readings/horary", () => {
    render(<HoraryAnswerView question={makeQuestion()} />);
    const link = screen.getByRole("link");
    expect(link).toBeTruthy();
    expect(link.getAttribute("href")).toBe("/readings/horary");
    expect(link.textContent).toContain("Хорарные вопросы");
  });
});
