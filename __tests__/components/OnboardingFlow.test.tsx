import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"

const { updateProfile } = vi.hoisted(() => ({
  updateProfile: vi.fn(),
}))

vi.mock("@/lib/api/profile", () => ({
  updateProfile,
}))

vi.mock("@/lib/log", () => ({
  logEvent: vi.fn(),
}))

vi.mock("@/lib/profile", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/profile")>()
  return {
    ...actual,
    saveProfile: vi.fn(),
  }
})

vi.mock("@/components/onboarding/step-welcome", () => ({
  StepWelcome: () => <div />,
}))
vi.mock("@/components/onboarding/step-birth", () => ({
  StepBirth: () => <div />,
}))
vi.mock("@/components/onboarding/step-place", () => ({
  StepPlace: () => <div />,
}))
vi.mock("@/components/onboarding/step-birthday", () => ({
  StepBirthday: () => <div />,
}))
vi.mock("@/components/onboarding/step-gender", () => ({
  StepGender: () => <div />,
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

vi.mock("@/lib/reducers/onboarding-reducer", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/lib/reducers/onboarding-reducer")>()
  const state = {
    ...actual.initialOnboardingState,
    step: "done" as const,
    birthDate: { day: "15", month: "06", year: "1990" },
    birthTime: { hours: "14", minutes: "30", unknown: false },
    birthPlace: {
      name: "London",
      country: "UK",
      lat: 51.5074,
      lon: -0.1278,
      timezone: "Europe/London",
    },
    currentCity: {
      name: "Lisbon",
      country: "Portugal",
      lat: 38.7223,
      lon: -9.1393,
      timezone: "Europe/Lisbon",
    },
    sameAsBirth: false,
    birthdayCity: null,
    birthdaySameAsCurrent: true,
    gender: "female" as const,
  }
  return {
    ...actual,
    initialOnboardingState: state,
    onboardingReducer: (currentState: typeof state) => currentState,
  }
})

import { OnboardingFlow } from "@/components/onboarding/onboarding-flow"

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
  it("does not complete when profile persistence fails and allows retry", async () => {
    const onComplete = vi.fn()
    updateProfile
      .mockRejectedValueOnce(new Error("Profile save failed"))
      .mockResolvedValueOnce(apiProfile)

    render(<OnboardingFlow onComplete={onComplete} />)

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
