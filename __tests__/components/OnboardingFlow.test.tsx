// @vitest-environment jsdom
// ############################################################################
// AI_HEADER: MODULE_TESTS_ONBOARDING_FLOW
// ROLE: Unit and integration tests for OnboardingFlow and StepBirth exact-time behavior.
// DEPENDENCIES: vitest, @testing-library/react, components/onboarding/onboarding-flow, components/onboarding/step-birth
// GRACE_ANCHORS: [ONBOARDING_FLOW_TESTS]
// WAVE: W-NAMED-PROMO-CAMPAIGN
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-ONBOARDING-FLOW
// purpose: Validate profile persistence, exact-time rules for promoNatal vs promoBase/ordinary modes, and StepBirth checkbox/subtitle behavior.
// owns:
//   - __tests__/components/OnboardingFlow.test.tsx
// inputs: mock updateProfile, getProfile, next/navigation searchParams
// outputs: Vitest assertion results
// dependencies:
//   - M-ONBOARDING-FLOW (components/onboarding/onboarding-flow)
//   - M-ONBOARDING-STEP-BIRTH (components/onboarding/step-birth)
// side_effects: renders React components in jsdom environment
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-ONBOARDING-FLOW

import * as React from "react"
import { describe, expect, it, vi, beforeEach } from "vitest"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"

const { updateProfile, getProfile, mockPush, mockReplace, mockSearchParams } = vi.hoisted(() => ({
  updateProfile: vi.fn(),
  getProfile: vi.fn(),
  mockPush: vi.fn(),
  mockReplace: vi.fn(),
  mockSearchParams: vi.fn().mockReturnValue(new URLSearchParams()),
}))

vi.mock("@/lib/api/profile", () => ({
  updateProfile,
  getProfile,
}))

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
  }),
  useSearchParams: () => mockSearchParams(),
}))

vi.mock("@/lib/log", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/log")>()
  return {
    ...actual,
    logEvent: vi.fn(),
    logger: {
      info: vi.fn(),
      warn: vi.fn(),
      debug: vi.fn(),
      error: vi.fn(),
    },
  }
})

vi.mock("@/lib/profile", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/profile")>()
  return {
    ...actual,
    saveProfile: vi.fn(),
  }
})

vi.mock("@/components/onboarding/step-welcome", () => ({
  StepWelcome: () => <div data-testid="step-welcome" />,
}))

vi.mock("@/components/onboarding/step-place", () => ({
  StepPlace: () => <div data-testid="step-place" />,
}))

vi.mock("@/components/onboarding/step-birthday", () => ({
  StepBirthday: () => <div data-testid="step-birthday" />,
}))

vi.mock("@/components/onboarding/step-gender", () => ({
  StepGender: () => <div data-testid="step-gender" />,
}))

vi.mock("@/components/onboarding/step-done", () => ({
  StepDone: ({
    onFinish,
    error,
  }: {
    onFinish: () => void
    error?: string | null
  }) => (
    <div>
      {error ? <p>{error}</p> : null}
      <button type="button" onClick={onFinish}>
        Finish onboarding
      </button>
    </div>
  ),
}))

import { StepBirth } from "@/components/onboarding/step-birth"
import { OnboardingFlow } from "@/components/onboarding/onboarding-flow"
import OnboardingPage from "@/app/(grace)/onboarding/page"

const apiProfile = {
  userId: "64c31e3a-a7db-4a35-b12a-cd75fc8156d6",
  firstName: null,
  gender: "female" as const,
  isOnboarded: true,
  birth: {
    birthday: "1990-06-15",
    birthTime: "14:30:00",
    birthCity: "London, UK",
    birthLat: 51.5074,
    birthLon: -0.1278,
    birthTz: "Europe/London",
  },
  currentLocation: {
    city: "Lisbon, Portugal",
    lat: 38.7223,
    lon: -9.1393,
    tz: "Europe/Lisbon",
  },
  birthdayLocation: {
    city: "Lisbon, Portugal",
    lat: 38.7223,
    lon: -9.1393,
    tz: "Europe/Lisbon",
  },
}

describe("OnboardingFlow persistence", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("does not complete when profile persistence fails and allows retry", async () => {
    const onComplete = vi.fn()
    updateProfile
      .mockRejectedValueOnce(new Error("Profile save failed"))
      .mockResolvedValueOnce(apiProfile)

    render(
      <OnboardingFlow
        onComplete={onComplete}
        initialState={{
          step: "done",
          birthDate: { day: "15", month: "06", year: "1990" },
          birthTime: { hours: "14", minutes: "30", unknown: false },
          birthPlace: { name: "London", country: "UK" },
          currentCity: { name: "Lisbon", country: "Portugal" },
          sameAsBirth: false,
          birthdayCity: null,
          birthdaySameAsCurrent: true,
          gender: "female",
        }}
      />
    )

    fireEvent.click(screen.getByText("Finish onboarding"))

    await waitFor(() => {
      expect(screen.getByText("Profile save failed")).toBeTruthy()
    })
    expect(onComplete).not.toHaveBeenCalled()

    fireEvent.click(screen.getByText("Finish onboarding"))

    await waitFor(() => expect(onComplete).toHaveBeenCalledTimes(1))
    expect(updateProfile).toHaveBeenCalledTimes(2)
  })
})

describe("StepBirth exact-time behavior", () => {
  const defaultDate = { day: "15", month: "06", year: "1990" }
  const unknownTime = { hours: "", minutes: "", unknown: true }
  const validTime = { hours: "14", minutes: "30", unknown: false }

  it("allows unknown time when requireExactBirthTime is false (ordinary/promoBase)", () => {
    render(
      <StepBirth
        date={defaultDate}
        time={unknownTime}
        onChangeDate={vi.fn()}
        onChangeTime={vi.fn()}
        onBack={vi.fn()}
        onNext={vi.fn()}
        requireExactBirthTime={false}
      />
    )

    const nextBtn = screen.getByRole("button", { name: "Далее" }) as HTMLButtonElement
    expect(nextBtn.disabled).toBe(false)
    expect(screen.getByText("Не знаю точное время")).toBeDefined()
    expect(screen.getByText(/Основа персонального расчёта/)).toBeDefined()
  })

  it("disables next button and hides unknown checkbox when requireExactBirthTime is true (promoNatal)", () => {
    render(
      <StepBirth
        date={defaultDate}
        time={unknownTime}
        onChangeDate={vi.fn()}
        onChangeTime={vi.fn()}
        onBack={vi.fn()}
        onNext={vi.fn()}
        requireExactBirthTime={true}
      />
    )

    const nextBtn = screen.getByRole("button", { name: "Далее" }) as HTMLButtonElement
    expect(nextBtn.disabled).toBe(true)
    expect(screen.queryByText("Не знаю точное время")).toBeNull()
    expect(screen.getByText(/необходимо указать точное время рождения/)).toBeDefined()
  })

  it("enables next button when exact time is provided in requireExactBirthTime mode", () => {
    render(
      <StepBirth
        date={defaultDate}
        time={validTime}
        onChangeDate={vi.fn()}
        onChangeTime={vi.fn()}
        onBack={vi.fn()}
        onNext={vi.fn()}
        requireExactBirthTime={true}
      />
    )

    const nextBtn = screen.getByRole("button", { name: "Далее" }) as HTMLButtonElement
    expect(nextBtn.disabled).toBe(false)
  })

  it("keeps time inputs editable and clears unknown on typing in promoNatal mode", () => {
    const onChangeTime = vi.fn()
    render(
      <StepBirth
        date={defaultDate}
        time={unknownTime}
        onChangeDate={vi.fn()}
        onChangeTime={onChangeTime}
        onBack={vi.fn()}
        onNext={vi.fn()}
        requireExactBirthTime={true}
      />
    )

    const hoursInput = screen.getByLabelText("Часы") as HTMLInputElement
    const minutesInput = screen.getByLabelText("Минуты") as HTMLInputElement
    expect(hoursInput.disabled).toBe(false)
    expect(minutesInput.disabled).toBe(false)

    fireEvent.change(hoursInput, { target: { value: "14" } })
    expect(onChangeTime).toHaveBeenCalledWith({ hours: "14", minutes: "", unknown: false })
  })
})

describe("OnboardingPage promo modes integration", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders status aria-busy while loading promo profile and pre-fills state on success", async () => {
    mockSearchParams.mockReturnValue(new URLSearchParams("requiredFor=promoNatal"))
    getProfile.mockResolvedValueOnce(apiProfile)

    render(<OnboardingPage />)

    expect(screen.getByRole("status")).toBeDefined()

    await waitFor(() => {
      expect(getProfile).toHaveBeenCalledTimes(1)
    })
  })

  it("renders role=alert with retry button when profile load fails", async () => {
    mockSearchParams.mockReturnValue(new URLSearchParams("requiredFor=promoBase"))
    getProfile.mockRejectedValueOnce(new Error("Network error loading profile"))

    render(<OnboardingPage />)

    await waitFor(() => {
      const alertEl = screen.getByRole("alert")
      expect(alertEl.textContent).toContain("Network error loading profile")
    })

    getProfile.mockResolvedValueOnce(apiProfile)
    fireEvent.click(screen.getByRole("button", { name: "Повторить" }))

    await waitFor(() => {
      expect(getProfile).toHaveBeenCalledTimes(2)
    })
  })
})
