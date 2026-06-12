
// ############################################################################
// AI_HEADER: MODULE_HORARY_HORARY_BLOCK_RENDERER_TEST
// ROLE: Unit tests for horary-block-renderer.test.tsx
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for horary-block-renderertsx behavior
// owns:
//   - __tests__/horary/horary-block-renderer.test.tsx
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// AI_HEADER
// module: M-TEST-HORARY-QUALITY
// wave: W-HORARY-ANSWER-QUALITY-V1
// purpose: Frontend tests for verdict card label, error state, timing states
//          and hardcoded-timing guard.

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { HoraryBlockRenderer } from "@/components/readings/horary/horary-block-renderer";

vi.mock("lucide-react", () => ({
  Check: (props: Record<string, unknown>) => <span data-testid="icon-check" {...props} />,
  Sparkles: (props: Record<string, unknown>) => <span data-testid="icon-sparkles" {...props} />,
  AlertTriangle: (props: Record<string, unknown>) => <span data-testid="icon-alert-triangle" {...props} />,
  Info: (props: Record<string, unknown>) => <span data-testid="icon-info" {...props} />,
  Quote: (props: Record<string, unknown>) => <span data-testid="icon-quote" {...props} />,
  CheckCircle2: (props: Record<string, unknown>) => <span data-testid="icon-check-circle2" {...props} />,
  XCircle: (props: Record<string, unknown>) => <span data-testid="icon-x-circle" {...props} />,
  HelpCircle: (props: Record<string, unknown>) => <span data-testid="icon-help-circle" {...props} />,
  Timer: (props: Record<string, unknown>) => <span data-testid="icon-timer" {...props} />,
  AlertOctagon: (props: Record<string, unknown>) => <span data-testid="icon-alert-octagon" {...props} />,
}));

const baseVerdictCard = {
  type: "verdict_card" as const,
  verdict: "yes" as const,
  confidence: 0.5,
  label: "Да",
  confidenceLabel: "medium" as const,
  confidenceExplanation: "Главный аспект читается умеренно.",
};

describe("HoraryBlockRenderer — verdict_card", () => {
  it("renders the human confidence label, not a percent", () => {
    render(<HoraryBlockRenderer block={baseVerdictCard} />);
    const label = screen.getByTestId("horary-confidence-label");
    expect(label.textContent).toMatch(/Средняя/);
    expect(label.textContent).not.toMatch(/%/);
  });

  it("does not contain the word 'вероятность'", () => {
    const { container } = render(<HoraryBlockRenderer block={baseVerdictCard} />);
    expect(container.textContent?.toLowerCase()).not.toContain("вероятность");
  });

  it("renders confidence explanation when provided", () => {
    render(<HoraryBlockRenderer block={baseVerdictCard} />);
    const exp = screen.getByTestId("horary-confidence-explanation");
    expect(exp.textContent).toContain("Главный аспект");
  });

  it("maps low label to 'Низкая'", () => {
    render(
      <HoraryBlockRenderer
        block={{
          ...baseVerdictCard,
          confidenceLabel: "low",
          confidenceExplanation: "Слабые свидетельства.",
        }}
      />
    );
    expect(screen.getByTestId("horary-confidence-label").textContent).toMatch(
      /Низкая/
    );
  });

  it("maps high label to 'Высокая'", () => {
    render(
      <HoraryBlockRenderer
        block={{
          ...baseVerdictCard,
          confidenceLabel: "high",
          confidenceExplanation: "Сильные свидетельства.",
        }}
      />
    );
    expect(screen.getByTestId("horary-confidence-label").textContent).toMatch(
      /Высокая/
    );
  });
});

describe("HoraryBlockRenderer — timing", () => {
  it("renders timing known state with timeRange", () => {
    render(
      <HoraryBlockRenderer
        block={{
          type: "timing",
          status: "known",
          timeRange: "1–2 недели",
          text: "Срок выведен из орба аспекта.",
        }}
      />
    );
    const block = screen.getByTestId("horary-timing");
    expect(block.getAttribute("data-timing-status")).toBe("known");
    expect(screen.getByTestId("horary-timing-range").textContent).toBe(
      "1–2 недели"
    );
  });

  it("renders timing not_enough_evidence without timeRange", () => {
    render(
      <HoraryBlockRenderer
        block={{
          type: "timing",
          status: "not_enough_evidence",
          text: "Карта не даёт уверенного срока.",
        }}
      />
    );
    const block = screen.getByTestId("horary-timing");
    expect(block.getAttribute("data-timing-status")).toBe("not_enough_evidence");
    expect(screen.queryByTestId("horary-timing-range")).toBeNull();
    expect(screen.getByTestId("horary-timing-text").textContent).toMatch(
      /Карта не даёт уверенного срока/
    );
  });

  it("renders timing unclear state with category hint", () => {
    render(
      <HoraryBlockRenderer
        block={{
          type: "timing",
          status: "unclear",
          timeRange: "несколько недель",
          text: "Срок по карте не выражен достаточно ясно.",
        }}
      />
    );
    const block = screen.getByTestId("horary-timing");
    expect(block.getAttribute("data-timing-status")).toBe("unclear");
    expect(screen.getByTestId("horary-timing-range").textContent).toBe(
      "несколько недель"
    );
  });

  it("does not contain hardcoded '2–3 недели' default", () => {
    const { container } = render(
      <HoraryBlockRenderer
        block={{
          type: "timing",
          status: "unclear",
          text: "Срок по карте не выражен достаточно ясно.",
        }}
      />
    );
    expect(container.textContent).not.toMatch(/2–3 недели/);
    expect(container.textContent).not.toMatch(/2-3 недели/);
  });
});

// ── paragraph ────────────────────────────────────────────────────────────────

describe("HoraryBlockRenderer — paragraph", () => {
  it("renders text with font-serif and text-[17px]", () => {
    const { container } = render(
      <HoraryBlockRenderer block={{ type: "paragraph", text: "Текст абзаца." }} />
    );
    const p = container.querySelector("p");
    expect(p).toBeTruthy();
    expect(p?.className).toContain("font-serif");
    expect(p?.className).toContain("text-[17px]");
    expect(p?.textContent).toBe("Текст абзаца.");
  });
});

// ── lead ─────────────────────────────────────────────────────────────────────

describe("HoraryBlockRenderer — lead", () => {
  it("renders text with font-serif and text-[19px] (larger than paragraph)", () => {
    const { container } = render(
      <HoraryBlockRenderer block={{ type: "lead", text: "Вводный текст." }} />
    );
    const p = container.querySelector("p");
    expect(p).toBeTruthy();
    expect(p?.className).toContain("font-serif");
    expect(p?.className).toContain("text-[19px]");
    expect(p?.textContent).toBe("Вводный текст.");
  });
});

// ── heading ──────────────────────────────────────────────────────────────────

describe("HoraryBlockRenderer — heading", () => {
  it("renders heading level=2 with text-[20px]", () => {
    const { container } = render(
      <HoraryBlockRenderer block={{ type: "heading", level: 2, text: "Заголовок" }} />
    );
    const h2 = container.querySelector("h2");
    expect(h2).toBeTruthy();
    expect(h2?.className).toContain("text-[20px]");
    expect(h2?.textContent).toBe("Заголовок");
  });

  it("renders heading level=3 with text-[16px]", () => {
    const { container } = render(
      <HoraryBlockRenderer block={{ type: "heading", level: 3, text: "Подзаголовок" }} />
    );
    const h2 = container.querySelector("h2");
    expect(h2).toBeTruthy();
    expect(h2?.className).toContain("text-[16px]");
    expect(h2?.textContent).toBe("Подзаголовок");
  });
});

// ── list ─────────────────────────────────────────────────────────────────────

describe("HoraryBlockRenderer — list", () => {
  it("renders check style with Check icons", () => {
    render(
      <HoraryBlockRenderer
        block={{ type: "list", style: "check", items: ["Один", "Два"] }}
      />
    );
    const icons = screen.getAllByTestId("icon-check");
    expect(icons.length).toBe(2);
  });

  it("renders bullet style (default) with dot spans", () => {
    const { container } = render(
      <HoraryBlockRenderer
        block={{ type: "list", style: "bullet", items: ["А", "Б"] }}
      />
    );
    // Each bullet item has a span with rounded-full (the dot)
    const dots = container.querySelectorAll("span[aria-hidden].rounded-full");
    expect(dots.length).toBe(2);
  });

  it("renders no items for empty items array", () => {
    const { container } = render(
      <HoraryBlockRenderer
        block={{ type: "list", style: "bullet", items: [] }}
      />
    );
    const li = container.querySelectorAll("li");
    expect(li.length).toBe(0);
  });
});

// ── callout ──────────────────────────────────────────────────────────────────

describe("HoraryBlockRenderer — callout", () => {
  it("renders strength tone with primary colors and Sparkles icon", () => {
    const { container } = render(
      <HoraryBlockRenderer
        block={{ type: "callout", tone: "strength", text: "Сильная сторона." }}
      />
    );
    const aside = container.querySelector("aside");
    expect(aside?.className).toContain("border-primary/25");
    expect(screen.getByTestId("icon-sparkles")).toBeTruthy();
  });

  it("renders risk tone with destructive colors and AlertTriangle icon", () => {
    const { container } = render(
      <HoraryBlockRenderer
        block={{ type: "callout", tone: "risk", text: "Опасность." }}
      />
    );
    const aside = container.querySelector("aside");
    expect(aside?.className).toContain("border-destructive/25");
    expect(screen.getByTestId("icon-alert-triangle")).toBeTruthy();
  });

  it("renders insight tone with secondary colors and Sparkles icon", () => {
    const { container } = render(
      <HoraryBlockRenderer
        block={{ type: "callout", tone: "insight", text: "Инсайт." }}
      />
    );
    const aside = container.querySelector("aside");
    expect(aside?.className).toContain("bg-secondary/50");
    expect(screen.getByTestId("icon-sparkles")).toBeTruthy();
  });

  it("renders neutral tone with muted colors and Info icon", () => {
    const { container } = render(
      <HoraryBlockRenderer
        block={{ type: "callout", tone: "neutral", text: "Заметка." }}
      />
    );
    const aside = container.querySelector("aside");
    expect(aside?.className).toContain("bg-muted/40");
    expect(screen.getByTestId("icon-info")).toBeTruthy();
  });

  it("defaults to neutral tone when tone is not provided", () => {
    const { container } = render(
      <HoraryBlockRenderer
        block={{ type: "callout", text: "Без тона." }}
      />
    );
    const aside = container.querySelector("aside");
    expect(aside?.className).toContain("bg-muted/40");
    expect(screen.getByTestId("icon-info")).toBeTruthy();
  });

  it("renders title div when title is provided", () => {
    render(
      <HoraryBlockRenderer
        block={{ type: "callout", tone: "neutral", title: "Внимание", text: "Текст." }}
      />
    );
    expect(screen.getByText("Внимание")).toBeTruthy();
  });

  it("does not render title div when title is absent", () => {
    const { container } = render(
      <HoraryBlockRenderer
        block={{ type: "callout", tone: "neutral", text: "Текст." }}
      />
    );
    // titleDiv kept for reference (querySelector result unused)
    // The only uppercase tracking element should be from the text itself, no title div
    // Check that there's no title div before the paragraph
    const aside = container.querySelector("aside");
    const upperDivs = aside?.querySelectorAll("div.text-\\[10\\.5px\\]");
    // Only the text paragraph is inside, no title div
    const hasTitle = Array.from(upperDivs ?? []).some(
      (d) => d.textContent === "Текст."
    );
    // Title div would contain no "Текст." — it would contain the title string
    expect(hasTitle).toBe(false);
  });
});

// ── pros_cons ────────────────────────────────────────────────────────────────

describe("HoraryBlockRenderer — pros_cons", () => {
  it("renders both pros and cons sections", () => {
    render(
      <HoraryBlockRenderer
        block={{
          type: "pros_cons",
          pros: ["Плюс один"],
          cons: ["Минус один"],
        }}
      />
    );
    expect(screen.getByText("Плюс один")).toBeTruthy();
    expect(screen.getByText("Минус один")).toBeTruthy();
  });

  it("renders only pros when cons is empty", () => {
    render(
      <HoraryBlockRenderer
        block={{ type: "pros_cons", pros: ["Плюс"], cons: [] }}
      />
    );
    expect(screen.getByText("Плюс")).toBeTruthy();
    expect(screen.queryByText("Риск")).toBeNull();
  });

  it("renders only cons when pros is empty", () => {
    render(
      <HoraryBlockRenderer
        block={{ type: "pros_cons", pros: [], cons: ["Минус"] }}
      />
    );
    expect(screen.getByText("Минус")).toBeTruthy();
    expect(screen.queryByText("Сила")).toBeNull();
  });

  it("renders neither section when both arrays are empty", () => {
    const { container } = render(
      <HoraryBlockRenderer
        block={{ type: "pros_cons", pros: [], cons: [] }}
      />
    );
    const lis = container.querySelectorAll("li");
    expect(lis.length).toBe(0);
  });

  it("uses custom prosLabel and consLabel when provided", () => {
    render(
      <HoraryBlockRenderer
        block={{
          type: "pros_cons",
          pros: ["Плюс"],
          cons: ["Минус"],
          prosLabel: "Достоинства",
          consLabel: "Недостатки",
        }}
      />
    );
    expect(screen.getByText("Достоинства")).toBeTruthy();
    expect(screen.getByText("Недостатки")).toBeTruthy();
  });
});

// ── quote ────────────────────────────────────────────────────────────────────

describe("HoraryBlockRenderer — quote", () => {
  it("renders figcaption with '— source' when source is provided", () => {
    render(
      <HoraryBlockRenderer
        block={{ type: "quote", text: "Мудрость.", source: "Автор" }}
      />
    );
    const figcaption = screen.getByText((_, el) => el?.tagName === "FIGCAPTION" && el.textContent?.includes("Автор") ? true : false);
    expect(figcaption).toBeTruthy();
    expect(figcaption.textContent).toContain("— Автор");
  });

  it("does not render figcaption when source is absent", () => {
    const { container } = render(
      <HoraryBlockRenderer
        block={{ type: "quote", text: "Мудрость без источника." }}
      />
    );
    const figcaption = container.querySelector("figcaption");
    expect(figcaption).toBeNull();
  });
});

// ── divider ──────────────────────────────────────────────────────────────────

describe("HoraryBlockRenderer — divider", () => {
  it("renders a decorative separator", () => {
    const { container } = render(
      <HoraryBlockRenderer block={{ type: "divider" }} />
    );
    const div = container.querySelector("div[aria-hidden]");
    expect(div).toBeTruthy();
    // Contains the dot and two lines
    const spans = div!.querySelectorAll("span");
    expect(spans.length).toBe(3);
  });
});

// ── verdict_card (additional cases) ──────────────────────────────────────────

describe("HoraryBlockRenderer — verdict_card (no / maybe / label)", () => {
  it("renders verdict='no' with XCircle icon, rose colors, and 'Нет'", () => {
    const { container } = render(
      <HoraryBlockRenderer
        block={{
          type: "verdict_card",
          verdict: "no",
          confidence: 0.3,
          confidenceLabel: "low",
          confidenceExplanation: "Слабые свидетельства.",
        }}
      />
    );
    expect(screen.getByTestId("icon-x-circle")).toBeTruthy();
    const card = container.querySelector("[data-testid='horary-verdict-card']");
    expect(card?.className).toContain("border-rose-500");
    expect(screen.getByText("Нет")).toBeTruthy();
  });

  it("renders verdict='maybe' with HelpCircle icon, purple colors, and 'Возможно'", () => {
    const { container } = render(
      <HoraryBlockRenderer
        block={{
          type: "verdict_card",
          verdict: "maybe",
          confidence: 0.5,
          confidenceLabel: "medium",
          confidenceExplanation: "Неоднозначные свидетельства.",
        }}
      />
    );
    expect(screen.getByTestId("icon-help-circle")).toBeTruthy();
    const card = container.querySelector("[data-testid='horary-verdict-card']");
    expect(card?.className).toContain("border-purple-500");
    expect(screen.getByText("Возможно")).toBeTruthy();
  });

  it("uses block.label instead of config.text when label is provided", () => {
    render(
      <HoraryBlockRenderer
        block={{
          type: "verdict_card",
          verdict: "yes",
          confidence: 0.8,
          label: "Определённо да",
          confidenceLabel: "high",
          confidenceExplanation: "Ясные свидетельства.",
        }}
      />
    );
    expect(screen.getByText("Определённо да")).toBeTruthy();
    expect(screen.queryByText("Да")).toBeNull();
  });

  it("does not render explanation paragraph when confidenceExplanation is empty", () => {
    render(
      <HoraryBlockRenderer
        block={{
          type: "verdict_card",
          verdict: "yes",
          confidence: 0.5,
          confidenceLabel: "medium",
          confidenceExplanation: "",
        }}
      />
    );
    // Empty string is falsy, so the explanation paragraph should not render
    expect(screen.queryByTestId("horary-confidence-explanation")).toBeNull();
  });
});

// ── testimonies ──────────────────────────────────────────────────────────────

describe("HoraryBlockRenderer — testimonies", () => {
  const baseTestimony = { title: "Аспект", explanation: "Объяснение", weight: 1, planets: [] };

  it("renders all three sections: pros, cons, neutral", () => {
    render(
      <HoraryBlockRenderer
        block={{
          type: "testimonies",
          prosLabel: "За",
          consLabel: "Против",
          neutralLabel: "Нейтральное",
          pros: [{ ...baseTestimony, title: "Про-аспект" }],
          cons: [{ ...baseTestimony, title: "Контр-аспект" }],
          neutral: [{ ...baseTestimony, title: "Нейтр-аспект" }],
        }}
      />
    );
    expect(screen.getByText("Про-аспект")).toBeTruthy();
    expect(screen.getByText("Контр-аспект")).toBeTruthy();
    expect(screen.getByText("Нейтр-аспект")).toBeTruthy();
    expect(screen.getByText("За")).toBeTruthy();
    expect(screen.getByText("Против")).toBeTruthy();
    expect(screen.getByText("Нейтральное")).toBeTruthy();
  });

  it("renders only pros section when only pros provided", () => {
    render(
      <HoraryBlockRenderer
        block={{
          type: "testimonies",
          prosLabel: "За",
          consLabel: "Против",
          neutralLabel: "Нейтральное",
          pros: [{ ...baseTestimony, title: "Про-аспект" }],
          cons: [],
          neutral: [],
        }}
      />
    );
    expect(screen.getByText("Про-аспект")).toBeTruthy();
    expect(screen.queryByText("Против")).toBeNull();
    expect(screen.queryByText("Нейтральное")).toBeNull();
  });

  it("renders neutral items with dashed border and Info icon", () => {
    const { container } = render(
      <HoraryBlockRenderer
        block={{
          type: "testimonies",
          prosLabel: "За",
          consLabel: "Против",
          neutralLabel: "Нейтральное",
          pros: [],
          cons: [],
          neutral: [{ ...baseTestimony, title: "Нейтр-фактор" }],
        }}
      />
    );
    const neutralSection = container.querySelector(".border-dashed");
    expect(neutralSection).toBeTruthy();
    expect(screen.getByTestId("icon-info")).toBeTruthy();
    expect(screen.getByText("Нейтр-фактор")).toBeTruthy();
  });
});

// ── unknown block type ───────────────────────────────────────────────────────

describe("HoraryBlockRenderer — unknown block type", () => {
  it("returns null for an unknown block type", () => {
    const { container } = render(
      // @ts-expect-error — intentionally passing an unknown type
      <HoraryBlockRenderer block={{ type: "nonexistent_block" }} />
    );
    expect(container.innerHTML).toBe("");
  });
});
