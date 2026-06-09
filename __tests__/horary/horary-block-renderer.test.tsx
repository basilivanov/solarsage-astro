// AI_HEADER
// module: M-TEST-HORARY-QUALITY
// wave: W-HORARY-ANSWER-QUALITY-V1
// purpose: Frontend tests for verdict card label, error state, timing states
//          and hardcoded-timing guard.

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { HoraryBlockRenderer } from "@/components/readings/horary/horary-block-renderer";

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
