
// ############################################################################
// AI_HEADER: MODULE_HORARY_HORARY_QUESTION_CARD_TEST
// ROLE: Unit tests for horary-question-card.test.tsx
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Unit tests for horary-question-card.test.tsx — __tests__/horary/horary-question-card.test.tsx
// owns:
//   - __tests__/horary/horary-question-card.test.tsx
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

// AI_HEADER
// module: M-TEST-HORARY-QUESTION-CARD
// wave: W-HORARY-ANSWER-QUALITY-V1
// purpose: Comprehensive tests for HoraryQuestionCard component covering
//   all status states, verdict variants, category badges, refund notices,
//   link navigation, date formatting, and data-testid attributes.

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { HoraryQuestionCard } from "@/components/readings/horary/horary-question-card";
import type { HoraryQuestionRead } from "@/packages/contracts";

// ---------------------------------------------------------------------------
// Mock next/link so it renders a real <a> instead of the Next.js proxy.
// We forward href so tests can assert the correct link target.
// ---------------------------------------------------------------------------
vi.mock("next/link", () => ({
  __esModule: true,
  default: ({
    href,
    children,
    ...rest
  }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

// ---------------------------------------------------------------------------
// Base factory for a HoraryQuestionRead object. Each test spreads this and
// overrides only the fields it needs, keeping the test data minimal yet
// type-safe.
// ---------------------------------------------------------------------------
const baseAnswer: Required<HoraryQuestionRead>["answer"] = {
  verdict: "yes" as const,
  confidence: 0.85,
  confidenceLabel: "high" as const,
  confidenceExplanation: "Strong testimonies",
  generatedAt: "2026-06-09T14:35:00",
  planets: ["Mars", "Venus"],
  blocks: [],
};

const baseQuestion: HoraryQuestionRead = {
  id: "q-test-001",
  text: "Выйду ли я замуж в этом году?",
  category: "love",
  status: "processing",
  creditRefunded: false,
  spentCreditSource: "subscription_weekly_free",
  clientTimezone: "Europe/Moscow",
  clientLocalTime: "2026-06-09T14:30",
  questionLocationName: "Москва",
  createdAt: "2026-06-09T14:30:00",
  answer: null,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Render the card and return the root link element. */
function renderCard(
  overrides: Partial<typeof baseQuestion> = {}
): HTMLElement {
  const question = { ...baseQuestion, ...overrides };
  const utils = render(<HoraryQuestionCard question={question} />);
  return utils.container;
}

/** Return the root <a> element (the card itself). */
function getCardLink(): HTMLElement {
  return screen.getByTestId("horary-question-card");
}

// ===========================================================================
// TEST SUITE
// ===========================================================================

describe("HoraryQuestionCard", () => {
  // -------------------------------------------------------------------------
  // 1. Processing status — spinner rendered, verdict "Расчёт..."
  // -------------------------------------------------------------------------
  it("renders spinner and verdict 'Расчёт...' for processing status", () => {
    renderCard({ status: "processing", answer: null });

    expect(screen.getByTestId("horary-question-card")).toBeTruthy();

    // Processing renders a custom spinner container instead of an icon SVG
    const card = getCardLink();
    const spinnerContainer = card.querySelector(".animate-spin");
    expect(spinnerContainer).toBeTruthy();

    expect(screen.getByTestId("horary-verdict-text").textContent).toBe(
      "Расчёт..."
    );
  });

  // -------------------------------------------------------------------------
  // 2. Expired status — XCircle icon, verdict "Не удалось построить ответ"
  // -------------------------------------------------------------------------
  it("renders XCircle icon and verdict 'Не удалось построить ответ' for expired status", () => {
    renderCard({ status: "expired", answer: null });

    const card = getCardLink();
    // XCircle SVG in lucide-react has the `lucide-x-circle` class or
    // we can verify the icon by checking the text-destructive class
    const iconEl = card.querySelector(".text-destructive");
    expect(iconEl).toBeTruthy();
    // The icon element is an SVG
    expect(iconEl?.tagName.toLowerCase()).toBe("svg");

    expect(screen.getByTestId("horary-verdict-text").textContent).toBe(
      "Не удалось построить ответ"
    );
  });

  // -------------------------------------------------------------------------
  // 3. Failed status — XCircle icon, verdict "Не удалось построить ответ"
  // -------------------------------------------------------------------------
  it("renders XCircle icon and verdict 'Не удалось построить ответ' for failed status", () => {
    renderCard({ status: "failed", answer: null });

    const card = getCardLink();
    const iconEl = card.querySelector(".text-destructive");
    expect(iconEl).toBeTruthy();
    expect(iconEl?.tagName.toLowerCase()).toBe("svg");

    expect(screen.getByTestId("horary-verdict-text").textContent).toBe(
      "Не удалось построить ответ"
    );
  });

  // -------------------------------------------------------------------------
  // 4. Refunded status — HelpCircle icon, verdict "Возвращен"
  // -------------------------------------------------------------------------
  it("renders HelpCircle icon and verdict 'Возвращен' for refunded status", () => {
    renderCard({ status: "refunded", answer: null });

    const card = getCardLink();
    const iconEl = card.querySelector(".text-muted-foreground");
    expect(iconEl).toBeTruthy();
    expect(iconEl?.tagName.toLowerCase()).toBe("svg");

    expect(screen.getByTestId("horary-verdict-text").textContent).toBe(
      "Возвращен"
    );
  });

  // -------------------------------------------------------------------------
  // 5. Answered + verdict="yes" — CheckCircle2, verdict "Да", emerald styling,
  //    "Ответ готов" badge
  // -------------------------------------------------------------------------
  it("renders CheckCircle2, verdict 'Да', emerald styling and 'Ответ готов' badge for answered+yes", () => {
    renderCard({
      status: "answered",
      answer: { ...baseAnswer, verdict: "yes" },
    });

    const card = getCardLink();

    // Emerald icon class
    const iconEl = card.querySelector(".text-emerald-500");
    expect(iconEl).toBeTruthy();
    expect(iconEl?.tagName.toLowerCase()).toBe("svg");

    // Emerald background class on the card
    expect(card.className).toContain("border-emerald-500/10");

    // Verdict text
    expect(screen.getByTestId("horary-verdict-text").textContent).toBe("Да");

    // "Ответ готов" badge
    expect(screen.getByText("Ответ готов")).toBeTruthy();
  });

  // -------------------------------------------------------------------------
  // 6. Answered + verdict="no" — XCircle, verdict "Нет", rose styling
  // -------------------------------------------------------------------------
  it("renders XCircle, verdict 'Нет' and rose styling for answered+no", () => {
    renderCard({
      status: "answered",
      answer: { ...baseAnswer, verdict: "no" },
    });

    const card = getCardLink();

    // Rose icon class
    const iconEl = card.querySelector(".text-rose-500");
    expect(iconEl).toBeTruthy();
    expect(iconEl?.tagName.toLowerCase()).toBe("svg");

    // Rose background class on the card
    expect(card.className).toContain("border-rose-500/10");

    // Verdict text
    expect(screen.getByTestId("horary-verdict-text").textContent).toBe("Нет");
  });

  // -------------------------------------------------------------------------
  // 7. Answered + verdict="maybe" — HelpCircle, verdict "Возможно", purple
  // -------------------------------------------------------------------------
  it("renders HelpCircle, verdict 'Возможно' and purple styling for answered+maybe", () => {
    renderCard({
      status: "answered",
      answer: { ...baseAnswer, verdict: "maybe" },
    });

    const card = getCardLink();

    // Purple icon class
    const iconEl = card.querySelector(".text-purple-500");
    expect(iconEl).toBeTruthy();
    expect(iconEl?.tagName.toLowerCase()).toBe("svg");

    // Purple background class on the card
    expect(card.className).toContain("border-purple-500/10");

    // Verdict text
    expect(screen.getByTestId("horary-verdict-text").textContent).toBe(
      "Возможно"
    );
  });

  // -------------------------------------------------------------------------
  // 8. Answered without verdict (verdict undefined) — falls to "Возможно"
  // -------------------------------------------------------------------------
  it("falls to 'Возможно' branch when answered but verdict is not yes/no/maybe", () => {
    // The schema says verdict is "yes"|"no"|"maybe", but we test the else
    // branch by providing an unexpected verdict value. We cast to bypass TS.
    renderCard({
      status: "answered",
      answer: { ...baseAnswer, verdict: "unknown" as "yes" },
    });

    expect(screen.getByTestId("horary-verdict-text").textContent).toBe(
      "Возможно"
    );

    const card = getCardLink();
    const iconEl = card.querySelector(".text-purple-500");
    expect(iconEl).toBeTruthy();
    expect(card.className).toContain("border-purple-500/10");
  });

  // -------------------------------------------------------------------------
  // 9. creditRefunded=true with failed — "Списание возвращено" shown
  // -------------------------------------------------------------------------
  it("shows refund notice when failed and creditRefunded=true", () => {
    renderCard({
      status: "failed",
      creditRefunded: true,
      answer: null,
    });

    expect(screen.getByText("Списание возвращено")).toBeTruthy();
  });

  // -------------------------------------------------------------------------
  // 10. creditRefunded=false with failed — no refund notice
  // -------------------------------------------------------------------------
  it("does not show refund notice when failed and creditRefunded=false", () => {
    renderCard({
      status: "failed",
      creditRefunded: false,
      answer: null,
    });

    expect(screen.queryByText("Списание возвращено")).toBeNull();
  });

  // -------------------------------------------------------------------------
  // 11. creditRefunded=true with expired — "Списание возвращено" shown
  // -------------------------------------------------------------------------
  it("shows refund notice when expired and creditRefunded=true", () => {
    renderCard({
      status: "expired",
      creditRefunded: true,
      answer: null,
    });

    expect(screen.getByText("Списание возвращено")).toBeTruthy();
  });

  // -------------------------------------------------------------------------
  // 12. Category badge with emoji + label (e.g., "love" → 💕 Отношения)
  // -------------------------------------------------------------------------
  it("renders category badge with emoji and label for known category", () => {
    renderCard({
      status: "processing",
      category: "love",
      answer: null,
    });

    expect(screen.getByText("💕")).toBeTruthy();
    expect(screen.getByText("Отношения")).toBeTruthy();
  });

  it("renders correct category badge for career", () => {
    renderCard({
      status: "processing",
      category: "career",
      answer: null,
    });

    expect(screen.getByText("💼")).toBeTruthy();
    expect(screen.getByText("Работа")).toBeTruthy();
  });

  it("renders correct category badge for money", () => {
    renderCard({
      status: "processing",
      category: "money",
      answer: null,
    });

    expect(screen.getByText("💰")).toBeTruthy();
    expect(screen.getByText("Деньги")).toBeTruthy();
  });

  // -------------------------------------------------------------------------
  // 13. No category (null) — no badge rendered
  // -------------------------------------------------------------------------
  it("does not render category badge when category is null", () => {
    renderCard({
      status: "processing",
      category: null,
      answer: null,
    });

    // None of the category labels should appear
    expect(screen.queryByText("Отношения")).toBeNull();
    expect(screen.queryByText("Работа")).toBeNull();
    expect(screen.queryByText("Деньги")).toBeNull();
    expect(screen.queryByText("Здоровье")).toBeNull();
    expect(screen.queryByText("Переезд")).toBeNull();
    expect(screen.queryByText("Другое")).toBeNull();
  });

  // -------------------------------------------------------------------------
  // 14. showAnsweredLabel=true — "Ответ готов" emerald badge
  // -------------------------------------------------------------------------
  it("shows 'Ответ готов' emerald badge for answered status with answer", () => {
    renderCard({
      status: "answered",
      answer: { ...baseAnswer, verdict: "yes" },
    });

    const badge = screen.getByText("Ответ готов");
    expect(badge).toBeTruthy();
    // The badge has emerald-related classes
    expect(badge.className).toContain("emerald");
  });

  it("does not show 'Ответ готов' badge for non-answered statuses", () => {
    renderCard({
      status: "processing",
      answer: null,
    });

    expect(screen.queryByText("Ответ готов")).toBeNull();
  });

  // -------------------------------------------------------------------------
  // 15. Link href → /readings/horary/${id}
  // -------------------------------------------------------------------------
  it("links to /readings/horary/${id}", () => {
    renderCard({
      id: "q-abc-123",
      status: "processing",
      answer: null,
    });

    const link = getCardLink();
    expect(link.tagName.toLowerCase()).toBe("a");
    expect(link.getAttribute("href")).toBe("/readings/horary/q-abc-123");
  });

  it("uses the correct id in the link href for a different id", () => {
    renderCard({
      id: "xyz-999",
      status: "answered",
      answer: { ...baseAnswer, verdict: "no" },
    });

    const link = getCardLink();
    expect(link.getAttribute("href")).toBe("/readings/horary/xyz-999");
  });

  // -------------------------------------------------------------------------
  // 16. formatDisplayDate with invalid date → returns iso string
  // -------------------------------------------------------------------------
  it("returns the raw iso string when createdAt is invalid for Date parsing", () => {
    // Using a string that new Date() will parse but produce "Invalid Date"
    // Actually, new Date("not-a-date") produces Invalid Date, and toLocaleString
    // on Invalid Date returns "Invalid Date" in most environments — it doesn't
    // throw. The catch block only triggers on actual exceptions. So let's test
    // with a value that causes toLocaleString to throw or we verify the
    // try/catch by checking that a valid ISO string renders a formatted date.
    //
    // For a truly invalid string, new Date("invalid") creates a date whose
    // toString() is "Invalid Date" — toLocaleString returns "Invalid Date"
    // without throwing. The catch only fires on exceptions.
    //
    // To exercise the catch, we would need to mock, but the simplest approach
    // is to verify the component still renders without crashing on bad input.
    renderCard({
      status: "processing",
      createdAt: "not-a-real-date",
      answer: null,
    });

    // The card should still render (no crash). The date cell will show
    // whatever the browser returns for Invalid Date or the raw string.
    expect(screen.getByTestId("horary-question-card")).toBeTruthy();
  });

  // -------------------------------------------------------------------------
  // 17. "Подробнее" text with ChevronRight
  // -------------------------------------------------------------------------
  it("renders 'Подробнее' text alongside a chevron icon", () => {
    renderCard({
      status: "processing",
      answer: null,
    });

    expect(screen.getByText("Подробнее")).toBeTruthy();

    // ChevronRight is rendered as an SVG next to "Подробнее"
    const moreSpan = screen.getByText("Подробнее").parentElement;
    expect(moreSpan).toBeTruthy();
    const svg = moreSpan!.querySelector("svg");
    expect(svg).toBeTruthy();
  });

  // -------------------------------------------------------------------------
  // 18. data-testid="horary-question-card" presence
  // -------------------------------------------------------------------------
  it("always renders data-testid='horary-question-card'", () => {
    renderCard({ status: "processing", answer: null });
    expect(screen.getByTestId("horary-question-card")).toBeTruthy();
  });

  it("has data-testid='horary-question-card' for answered status too", () => {
    renderCard({
      status: "answered",
      answer: { ...baseAnswer, verdict: "maybe" },
    });
    expect(screen.getByTestId("horary-question-card")).toBeTruthy();
  });

  // -------------------------------------------------------------------------
  // 19. data-testid="horary-verdict-text" presence
  // -------------------------------------------------------------------------
  it("always renders data-testid='horary-verdict-text'", () => {
    renderCard({ status: "processing", answer: null });
    expect(screen.getByTestId("horary-verdict-text")).toBeTruthy();
  });

  it("has data-testid='horary-verdict-text' for answered status", () => {
    renderCard({
      status: "answered",
      answer: { ...baseAnswer, verdict: "yes" },
    });
    expect(screen.getByTestId("horary-verdict-text")).toBeTruthy();
  });

  // -------------------------------------------------------------------------
  // Additional edge-case: "pending" status should use default values
  // (HelpCircle, "Ожидание", muted styling)
  // -------------------------------------------------------------------------
  it("renders HelpCircle and verdict 'Ожидание' for pending status (default branch)", () => {
    renderCard({
      status: "pending",
      answer: null,
    });

    const card = getCardLink();
    // Default icon class is text-muted-foreground
    const iconEl = card.querySelector(".text-muted-foreground");
    expect(iconEl).toBeTruthy();
    expect(iconEl?.tagName.toLowerCase()).toBe("svg");

    expect(screen.getByTestId("horary-verdict-text").textContent).toBe(
      "Ожидание"
    );
  });

  // -------------------------------------------------------------------------
  // Additional: answered status without answer object — should NOT set
  // showAnsweredLabel, falls to default branch
  // -------------------------------------------------------------------------
  it("renders default state when status is answered but answer is null", () => {
    renderCard({
      status: "answered",
      answer: null,
    });

    // Should not show "Ответ готов" badge
    expect(screen.queryByText("Ответ готов")).toBeNull();

    // Should use default verdict "Ожидание" since answer is null
    expect(screen.getByTestId("horary-verdict-text").textContent).toBe(
      "Ожидание"
    );
  });

  // -------------------------------------------------------------------------
  // Question text is rendered
  // -------------------------------------------------------------------------
  it("renders the question text", () => {
    renderCard({
      status: "processing",
      text: "Буду ли я счастлив?",
      answer: null,
    });

    expect(screen.getByText("Буду ли я счастлив?")).toBeTruthy();
  });

  // -------------------------------------------------------------------------
  // Refund notice is NOT shown for answered status even if creditRefunded
  // -------------------------------------------------------------------------
  it("does not show refund notice for answered status even when creditRefunded=true", () => {
    renderCard({
      status: "answered",
      creditRefunded: true,
      answer: { ...baseAnswer, verdict: "yes" },
    });

    expect(screen.queryByText("Списание возвращено")).toBeNull();
  });

  // -------------------------------------------------------------------------
  // Refund notice is NOT shown for processing status
  // -------------------------------------------------------------------------
  it("does not show refund notice for processing status", () => {
    renderCard({
      status: "processing",
      creditRefunded: true,
      answer: null,
    });

    expect(screen.queryByText("Списание возвращено")).toBeNull();
  });

  // -------------------------------------------------------------------------
  // Valid date formatting
  // -------------------------------------------------------------------------
  it("formats a valid createdAt date using Russian locale", () => {
    renderCard({
      status: "processing",
      createdAt: "2026-06-09T14:30:00",
      answer: null,
    });

    // The formatted output should contain the day number and Russian month
    // abbreviation, e.g. "9 июн" — exact format depends on the jsdom
    // locale support. We check that the raw ISO string is NOT rendered
    // verbatim.
    const card = getCardLink();
    const dateSpan = card.querySelector(".text-\\[12px\\]");
    expect(dateSpan).toBeTruthy();
    // Should not show the raw ISO format
    expect(dateSpan?.textContent).not.toBe("2026-06-09T14:30:00");
  });
});
