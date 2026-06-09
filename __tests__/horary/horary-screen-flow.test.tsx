import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import React from "react";
import { HoraryScreen } from "@/components/readings/horary/horary-screen";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/readings/horary",
}));

const mockQuota = vi.fn();
const mockList = vi.fn();
const mockCreate = vi.fn();
const mockGet = vi.fn();
const mockProfile = vi.fn();

vi.mock("@/lib/api/horary", () => ({
  getHoraryQuota: (...args: unknown[]) => mockQuota(...args),
  listHoraryQuestions: (...args: unknown[]) => mockList(...args),
  createHoraryQuestion: (...args: unknown[]) => mockCreate(...args),
  getHoraryQuestion: (...args: unknown[]) => mockGet(...args),
}));

vi.mock("@/lib/api/profile", () => ({
  getProfile: (...args: unknown[]) => mockProfile(...args),
}));

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

const processingQuestion = {
  id: "q-new",
  text: "Выйду ли я замуж в этом году?",
  category: "love",
  status: "processing" as const,
  creditRefunded: false,
  spentCreditSource: "subscription_weekly_free" as const,
  clientTimezone: "Europe/Moscow",
  clientLocalTime: "2026-06-09T14:30",
  questionLocationName: "Москва",
  createdAt: "2026-06-09T14:30:00",
  answer: null,
};

function setupMocks() {
  mockQuota.mockResolvedValue({
    weeklyFreeAvailable: true,
    weeklyFreeExpiresAt: null,
    nextWeeklyFreeAt: null,
    bonusCredits: 0,
    paidCredits: 0,
    canPurchase: true,
  });
  mockList.mockResolvedValue([]);
  mockProfile.mockResolvedValue({
    userId: "u1",
    firstName: "Анна",
    gender: "female",
    isOnboarded: true,
    currentLocation: {
      city: "Москва",
      lat: 55.75,
      lon: 37.62,
      tz: "Europe/Moscow",
    },
    birth: null,
    birthdayLocation: null,
  });
  mockCreate.mockResolvedValue(processingQuestion);
  mockGet.mockResolvedValue(processingQuestion);
}

describe("HoraryScreen — happy path create flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMocks();
  });

  it("loads data, fills form, submits and shows processing card", async () => {
    render(
      <React.Suspense fallback={<div>loading</div>}>
        <HoraryScreen />
      </React.Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText(/Хорарный оракул/)).toBeTruthy();
    }, { timeout: 2000 });

    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: processingQuestion.text } });

    let catButton: HTMLElement | null = null;
    for (const label of ["💕", "Отношения"]) {
      try {
        const el = screen.getByText(label);
        if (el.closest("button")) {
          catButton = el.closest("button");
          break;
        }
      } catch { /* ignore */ }
    }
    if (catButton) {
      fireEvent.click(catButton);
    }

    const submitButton = screen.getByRole("button", { name: /Получить ответ карты/ });
    expect(submitButton).toBeTruthy();

    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledTimes(1);
    }, { timeout: 2000 });

    const callArg = mockCreate.mock.calls[0][0];
    expect(callArg.text).toBe(processingQuestion.text);
    expect(callArg.clientTimezone).toBe("Europe/Moscow");
    expect(callArg.questionLat).toBe(55.75);
    expect(callArg.questionLon).toBe(37.62);
    expect(callArg.idempotencyKey).toBeTruthy();

    await waitFor(() => {
      expect(screen.getByText(/Бережно собираем карту/)).toBeTruthy();
    }, { timeout: 2000 });
  });
});

describe("HoraryScreen — polling starts after create", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMocks();
  });

  it("calls getHoraryQuestion after successful create", async () => {
    render(
      <React.Suspense fallback={<div>loading</div>}>
        <HoraryScreen />
      </React.Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText(/Хорарный оракул/)).toBeTruthy();
    }, { timeout: 2000 });

    const textarea = screen.getByRole("textbox");
    fireEvent.change(textarea, { target: { value: processingQuestion.text } });

    const submitButton = screen.getByRole("button", { name: /Получить ответ карты/ });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledTimes(1);
    }, { timeout: 2000 });

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith("q-new");
    }, { timeout: 5000 });
  });
});
