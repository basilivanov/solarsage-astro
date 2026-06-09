// AI_HEADER
// module: M-TEST-HORARY-ERROR-STATE
// wave: W-HORARY-ANSWER-QUALITY-V1
// purpose: Tests the failed/error question page state.

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import React from "react";
import HoraryAnswerPage from "@/app/(grace)/readings/horary/[id]/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/readings/horary/123",
}));

const mockGet = vi.fn();
vi.mock("@/lib/api/horary", () => ({
  getHoraryQuestion: (...args: unknown[]) => mockGet(...args),
}));

async function renderAndAwait(id: string) {
  let rendered: ReturnType<typeof render> | null = null;
  await act(async () => {
    rendered = render(
      <React.Suspense fallback={<div data-testid="suspense-fallback">loading</div>}>
        <HoraryAnswerPage params={Promise.resolve({ id })} />
      </React.Suspense>
    );
    // Allow microtasks (the use() to settle, the useEffect to fire and the
    // mocked fetch to resolve).
    await Promise.resolve();
    await Promise.resolve();
  });
  // Flush any further microtasks triggered by the mock resolution.
  await act(async () => {
    await Promise.resolve();
  });
  return rendered!;
}

describe("HoraryAnswerPage — failed/error state", () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it("shows the honest error message and refund notice when failed with credit refund", async () => {
    mockGet.mockResolvedValue({
      id: "q1",
      text: "Will I win?",
      category: "other",
      status: "failed",
      creditRefunded: true,
      spentCreditSource: "paid",
      clientTimezone: "UTC",
      clientLocalTime: null,
      questionLocationName: null,
      createdAt: "2026-06-09T12:00:00",
      answer: null,
    });

    await renderAndAwait("q1");

    await waitFor(
      () => {
        expect(screen.getByTestId("horary-error-state")).toBeTruthy();
      },
      { timeout: 2000 }
    );
    expect(screen.getByTestId("horary-refund-notice").textContent).toMatch(
      /Списание возвращено/
    );
    expect(screen.getAllByText(/Не удалось построить ответ/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Мы не будем показывать общий текст/)).toBeTruthy();
  });

  it("does not render the refund notice when creditRefunded is false", async () => {
    mockGet.mockResolvedValue({
      id: "q2",
      text: "Will I win?",
      category: "other",
      status: "failed",
      creditRefunded: false,
      spentCreditSource: null,
      clientTimezone: "UTC",
      clientLocalTime: null,
      questionLocationName: null,
      createdAt: "2026-06-09T12:00:00",
      answer: null,
    });

    await renderAndAwait("q2");

    await waitFor(
      () => {
        expect(screen.getByTestId("horary-error-state")).toBeTruthy();
      },
      { timeout: 2000 }
    );
    expect(screen.queryByTestId("horary-refund-notice")).toBeNull();
  });

  it("treats expired status the same as failed", async () => {
    mockGet.mockResolvedValue({
      id: "q3",
      text: "Will I win?",
      category: "other",
      status: "expired",
      creditRefunded: false,
      spentCreditSource: null,
      clientTimezone: "UTC",
      clientLocalTime: null,
      questionLocationName: null,
      createdAt: "2026-06-09T12:00:00",
      answer: null,
    });

    await renderAndAwait("q3");

    await waitFor(
      () => {
        expect(screen.getByTestId("horary-error-state")).toBeTruthy();
      },
      { timeout: 2000 }
    );
  });
});
