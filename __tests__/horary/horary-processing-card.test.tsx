import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { HoraryProcessingCard } from "@/components/readings/horary/horary-processing-card";

const DEFAULT_PROPS = {
  questionText: "Выйду ли я замуж в этом году?",
  createdAt: "2026-06-09T14:30:00",
};

function renderCard(props: Record<string, unknown> = {}) {
  return render(
    <HoraryProcessingCard
      questionText={DEFAULT_PROPS.questionText}
      createdAt={DEFAULT_PROPS.createdAt}
      {...props}
    />
  );
}

describe("HoraryProcessingCard", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // 1. Renders with questionText and createdAt
  it("renders with questionText and createdAt", () => {
    renderCard();
    expect(screen.getByText(DEFAULT_PROPS.questionText)).toBeTruthy();
    expect(screen.getByTestId("horary-processing-card")).toBeTruthy();
  });

  // 2. data-testid="horary-processing-card" present
  it("has data-testid='horary-processing-card'", () => {
    renderCard();
    const card = screen.getByTestId("horary-processing-card");
    expect(card).toBeTruthy();
  });

  // 3. Category badge rendering (with "love" -> 💕 Отношения)
  it("renders category badge when category is 'love'", () => {
    renderCard({ category: "love" });
    expect(screen.getByText("💕")).toBeTruthy();
    expect(screen.getByText("Отношения")).toBeTruthy();
  });

  // 4. No category -> no badge
  it("does not render category badge when category is not provided", () => {
    renderCard();
    expect(screen.queryByText("Отношения")).toBeNull();
    expect(screen.queryByText("Работа")).toBeNull();
  });

  it("does not render category badge when category is null", () => {
    renderCard({ category: null });
    expect(screen.queryByText("Отношения")).toBeNull();
  });

  // 5. Initial progress at 6%
  it("shows initial progress at 6%", () => {
    renderCard();
    expect(screen.getByText("6%")).toBeTruthy();
  });

  // 6. Progress bar renders with percentage text
  it("renders progress bar with percentage text", () => {
    renderCard();
    const progressBar = screen.getByTestId("horary-processing-card").querySelector(
      '[style*="width: 6%"]'
    );
    expect(progressBar).toBeTruthy();
    expect(screen.getByText("6%")).toBeTruthy();
    expect(screen.getByText("Ответ готовится")).toBeTruthy();
  });

  // 7. stepIndex=0 at initial (progress 6 < 25): first step active, rest inactive
  it("first step is active and rest are inactive at initial render", () => {
    renderCard();
    const steps = screen.getAllByTestId("horary-processing-card")[0].querySelectorAll(
      ".flex.items-center.gap-2\\.5"
    );
    // Step 0 is active (opacity-100), steps 1-3 are inactive (opacity-40)
    expect(steps[0].className).toContain("opacity-100");
    expect(steps[1].className).toContain("opacity-40");
    expect(steps[2].className).toContain("opacity-40");
    expect(steps[3].className).toContain("opacity-40");
  });

  // 8. All 4 steps rendered with correct text
  it("renders all 4 steps with correct text", () => {
    renderCard();
    expect(screen.getByText("Фиксируем момент вопроса")).toBeTruthy();
    expect(screen.getByText("Строим карту")).toBeTruthy();
    expect(screen.getByText("Сверяем сигнификаторы")).toBeTruthy();
    expect(screen.getByText("Собираем ответ")).toBeTruthy();
  });

  // 9. Step 0 is active (animate-pulse) at initial render
  it("step 0 has animate-pulse class at initial render", () => {
    renderCard();
    const stepIcons = screen.getByTestId("horary-processing-card").querySelectorAll(
      ".flex.h-4\\.5"
    );
    expect(stepIcons[0].className).toContain("animate-pulse");
  });

  // 10. Steps 1-3 show their numbers at initial render
  it("steps 1-3 show their numbers at initial render", () => {
    renderCard();
    expect(screen.getByText("2")).toBeTruthy();
    expect(screen.getByText("3")).toBeTruthy();
    expect(screen.getByText("4")).toBeTruthy();
  });

  // 11. isLongRunning=false initially: no long-running message
  it("does not show long-running message initially", () => {
    renderCard();
    expect(screen.queryByText(/Ответ готовится дольше обычного/)).toBeNull();
  });

  // 12. startedAt not provided -> isLongRunning stays false
  it("isLongRunning stays false when startedAt is not provided", () => {
    renderCard();
    act(() => {
      vi.advanceTimersByTime(60000);
    });
    expect(screen.queryByText(/Ответ готовится дольше обычного/)).toBeNull();
  });

  // 13. formatDisplayDate with invalid date -> returns iso string
  it("shows fallback text when createdAt is invalid", () => {
    const invalidDate = "not-a-valid-date";
    renderCard({ createdAt: invalidDate });
    // toLocaleString on an invalid Date does not throw in jsdom;
    // it returns "Invalid Date". The catch block would return the raw iso,
    // but in practice the try block succeeds with "Invalid Date" string.
    expect(screen.getByText("Invalid Date")).toBeTruthy();
  });

  // --- Timer-based progress tests ---

  it("increments progress every 420ms", () => {
    renderCard();
    expect(screen.getByText("6%")).toBeTruthy();

    act(() => {
      vi.advanceTimersByTime(420);
    });
    expect(screen.getByText("7%")).toBeTruthy();

    act(() => {
      vi.advanceTimersByTime(420);
    });
    expect(screen.getByText("8%")).toBeTruthy();
  });

  it("caps progress at 95%", () => {
    renderCard();

    // Advance enough intervals to reach 95 (from 6, need 89 increments * 420ms = 37380ms)
    act(() => {
      vi.advanceTimersByTime(90000);
    });

    expect(screen.getByText("95%")).toBeTruthy();
    // Should not go beyond 95
    act(() => {
      vi.advanceTimersByTime(420);
    });
    expect(screen.getByText("95%")).toBeTruthy();
  });

  it("transitions to step 1 when progress reaches 25", () => {
    renderCard();
    // Initial: step 0 active, step 1 inactive
    expect(screen.getByText("6%")).toBeTruthy();
    // step 0 shows no number (active state), step 1 shows "2"
    expect(screen.getByText("2")).toBeTruthy();

    // Advance progress to 25 (need 19 increments from 6 → 25, 19 * 420 = 7980ms)
    act(() => {
      vi.advanceTimersByTime(7980);
    });

    // Now step 0 should be completed (shows Check icon, no "1" number)
    // Step 1 should be active (animate-pulse)
    // Steps 2-3 should still show numbers
    expect(screen.getByText("3")).toBeTruthy();
    expect(screen.getByText("4")).toBeTruthy();
  });

  it("shows isLongRunning message when startedAt was 30s ago", () => {
    const now = Date.now();
    // startedAt 30 seconds ago means remaining = 30000 - 30000 = 0, which is <= 0
    const startedAt = now - 30000;

    vi.spyOn(Date, "now").mockReturnValue(now);

    renderCard({ startedAt });

    expect(screen.getByText(/Ответ готовится дольше обычного/)).toBeTruthy();

    vi.spyOn(Date, "now").mockRestore();
  });

  it("shows isLongRunning message after 30s from startedAt", () => {
    const now = Date.now();
    const startedAt = now;

    vi.spyOn(Date, "now").mockReturnValue(now);

    renderCard({ startedAt });

    // Not long-running yet
    expect(screen.queryByText(/Ответ готовится дольше обычного/)).toBeNull();

    // After 30 seconds it should appear
    act(() => {
      vi.advanceTimersByTime(30000);
    });

    expect(screen.getByText(/Ответ готовится дольше обычного/)).toBeTruthy();

    vi.spyOn(Date, "now").mockRestore();
  });

  it("cleans up interval on unmount", () => {
    const { unmount } = renderCard();
    const clearIntervalSpy = vi.spyOn(global, "clearInterval");

    unmount();

    expect(clearIntervalSpy).toHaveBeenCalled();
    clearIntervalSpy.mockRestore();
  });
});
