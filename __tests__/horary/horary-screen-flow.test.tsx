
// ############################################################################
// AI_HEADER: MODULE_HORARY_HORARY_SCREEN_FLOW_TEST
// ROLE: Unit tests for horary-screen-flow.test.tsx
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for horary-screen-flowtsx behavior
// owns:
//   - __tests__/horary/horary-screen-flow.test.tsx
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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
  chart: null,
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

describe("HoraryScreen — no-credit copy", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMocks();
  });

  it("does not tell users to buy questions while payment is disabled", async () => {
    mockQuota.mockResolvedValue({
      weeklyFreeAvailable: false,
      weeklyFreeExpiresAt: null,
      nextWeeklyFreeAt: "2026-07-13T00:00:00Z",
      bonusCredits: 0,
      paidCredits: 0,
      canPurchase: false,
    });

    render(
      <React.Suspense fallback={<div>loading</div>}>
        <HoraryScreen />
      </React.Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText(/Хорарный оракул/)).toBeTruthy();
    }, { timeout: 2000 });

    expect(screen.queryByText(/докупите вопросы/i)).toBeNull();
    expect(
      screen.getByText(/Дождитесь следующего бесплатного вопроса или пригласите друга/)
    ).toBeTruthy();
  });
});

describe("HoraryScreen — hooks stability across loading states", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMocks();
  });

  it("renders loading spinner first, then content — no hooks order mismatch", async () => {
    // This test catches Rules of Hooks violations where a hook is placed
    // after an early return (e.g. if (loading) return <Spinner />).
    // In that case, the first render calls N hooks, but after loading=false
    // the component renders more hooks → React crashes.

    // Delay API responses so the component starts in loading=true state
    let resolveQuota: Function, resolveList: Function, resolveProfile: Function;
    mockQuota.mockReturnValue(new Promise((r) => { resolveQuota = r; }));
    mockList.mockReturnValue(new Promise((r) => { resolveList = r; }));
    mockProfile.mockReturnValue(new Promise((r) => { resolveProfile = r; }));

    // Render while still loading
    const { unmount } = render(
      <React.Suspense fallback={<div>loading</div>}>
        <HoraryScreen />
      </React.Suspense>
    );

    // Component should show spinner (loading state)
    // No React error should be thrown here — if a hook was placed after
    // the early return, React would crash on this first render already
    const spinner = document.querySelector('[class*="animate-spin"]') || screen.getByRole("status");
    expect(spinner).toBeTruthy();

    // Now resolve the API calls — component transitions from loading to loaded
    await act(async () => {
      resolveQuota!({
        weeklyFreeAvailable: true,
        weeklyFreeExpiresAt: null,
        nextWeeklyFreeAt: null,
        bonusCredits: 0,
        paidCredits: 0,
        canPurchase: true,
      });
      resolveList!([]);
      resolveProfile!({
        userId: "u1",
        firstName: "Анна",
        gender: "female",
        isOnboarded: true,
        currentLocation: { city: "Москва", lat: 55.75, lon: 37.62, tz: "Europe/Moscow" },
        birth: null,
        birthdayLocation: null,
      });
    });

    // After loading completes, the main content should appear
    // If a hook was placed after the early return, React would have thrown
    // "Rendered more hooks than during the previous render" by this point
    await waitFor(() => {
      expect(screen.getByText(/Хорарный оракул/)).toBeTruthy();
    }, { timeout: 2000 });

    unmount();
  });
});

describe("HoraryScreen — DOM contract", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMocks();
  });

  it("loading state has data-testid and role=status", async () => {
    // Delay API so we see loading state
    mockQuota.mockReturnValue(new Promise(() => {}));
    mockList.mockReturnValue(new Promise(() => {}));
    mockProfile.mockReturnValue(new Promise(() => {}));

    render(
      <React.Suspense fallback={<div>loading</div>}>
        <HoraryScreen />
      </React.Suspense>
    );

    const loading = screen.getByTestId("horary-loading");
    expect(loading).toBeTruthy();
    expect(loading.getAttribute("role")).toBe("status");
  });

  it("ready state has data-testid, data-state, and data-has-credit", async () => {
    render(
      <React.Suspense fallback={<div>loading</div>}>
        <HoraryScreen />
      </React.Suspense>
    );

    await waitFor(() => {
      expect(screen.getByTestId("horary-screen")).toBeTruthy();
    }, { timeout: 2000 });

    const screen_ = screen.getByTestId("horary-screen");
    expect(screen_.getAttribute("data-state")).toBe("ready");
    expect(screen_.getAttribute("data-has-credit")).toBe("true");
  });

  it("empty history renders horary-empty-history", async () => {
    mockList.mockResolvedValue([]);

    render(
      <React.Suspense fallback={<div>loading</div>}>
        <HoraryScreen />
      </React.Suspense>
    );

    await waitFor(() => {
      expect(screen.getByTestId("horary-empty-history")).toBeTruthy();
    }, { timeout: 2000 });
  });

  it("no-credit state renders horary-no-credit-card", async () => {
    mockQuota.mockResolvedValue({
      weeklyFreeAvailable: false,
      weeklyFreeExpiresAt: null,
      nextWeeklyFreeAt: null,
      bonusCredits: 0,
      paidCredits: 0,
      canPurchase: false,
    });

    render(
      <React.Suspense fallback={<div>loading</div>}>
        <HoraryScreen />
      </React.Suspense>
    );

    await waitFor(() => {
      expect(screen.getByTestId("horary-no-credit-card")).toBeTruthy();
    }, { timeout: 2000 });

    const card = screen.getByTestId("horary-no-credit-card");
    expect(card.textContent).not.toContain("докупите");
  });
});

describe("HoraryScreen — load error and retry", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders load error with data-state=error and role=alert when API fails", async () => {
    mockQuota.mockRejectedValue(new Error("API error"));
    mockList.mockRejectedValue(new Error("API error"));
    mockProfile.mockRejectedValue(new Error("API error"));

    render(
      <React.Suspense fallback={<div>loading</div>}>
        <HoraryScreen />
      </React.Suspense>
    );

    await waitFor(() => {
      expect(screen.getByTestId("horary-screen")).toBeTruthy();
    }, { timeout: 2000 });

    expect(screen.getByTestId("horary-screen").getAttribute("data-state")).toBe("error");
    const errorEl = screen.getByTestId("horary-load-error");
    expect(errorEl.getAttribute("role")).toBe("alert");
  });

  it("retry button re-calls loadData and recovers to ready state", async () => {
    // Setup: first call rejects, subsequent calls resolve
    const successPayload = {
      weeklyFreeAvailable: true,
      weeklyFreeExpiresAt: null,
      nextWeeklyFreeAt: null,
      bonusCredits: 2,
      paidCredits: 0,
      canPurchase: false,
    };
    const profilePayload = {
      userId: "test",
      firstName: "Test",
      gender: null as string | null,
      isOnboarded: true,
      birth: { birthday: "1990-01-01", birthTime: null as string | null, birthCity: null as string | null, birthLat: null as number | null, birthLon: null as number | null, birthTz: null as string | null },
      currentLocation: null,
      birthdayLocation: null,
    };

    // Use mockImplementationOnce for first-call rejection
    mockQuota.mockImplementationOnce(() => Promise.reject(new Error("API error")))
             .mockImplementation(() => Promise.resolve(successPayload));
    mockList.mockImplementationOnce(() => Promise.reject(new Error("API error")))
            .mockImplementation(() => Promise.resolve([]));
    mockProfile.mockImplementationOnce(() => Promise.reject(new Error("API error")))
              .mockImplementation(() => Promise.resolve(profilePayload));

    render(
      <React.Suspense fallback={<div>loading</div>}>
        <HoraryScreen />
      </React.Suspense>
    );

    // Wait for error state
    await waitFor(() => {
      expect(screen.getByTestId("horary-screen").getAttribute("data-state")).toBe("error");
    }, { timeout: 5000 });

    // Click retry button
    const retryBtn = screen.getByRole("button", { name: /Попробовать снова/ });
    fireEvent.click(retryBtn);

    // Wait for ready state after retry
    await waitFor(() => {
      expect(screen.getByTestId("horary-screen").getAttribute("data-state")).toBe("ready");
    }, { timeout: 5000 });
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
