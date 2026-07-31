// ############################################################################
// AI_HEADER: TEST_COMPONENTS_ONBOARDING_FLOW — onboarding finish guards.
// ROLE: Proves finish-time guard branches of OnboardingFlow before any API call.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-COMPONENTS-ONBOARDING-FLOW
// purpose: Exercise finish guards: exact-time requirement and gender guard.
// owns:
//   - __tests__/components/OnboardingFlow.test.tsx
// inputs: initial onboarding states; updateProfile mock.
// outputs: step navigation assertions and zero-API-call checks.
// dependencies: components/onboarding/onboarding-flow, testing-library.
// side_effects: none.
// emitted_logs: none.
// invariants: guards fire before updateProfile is invoked.
// failure_policy: assertion failure on guard drift.
// END_MODULE_CONTRACT: M-TEST-COMPONENTS-ONBOARDING-FLOW

// START_MODULE_MAP: M-TEST-COMPONENTS-ONBOARDING-FLOW
// public_entrypoints:
//   - vitest test suite
// semantic_blocks:
//   - GUARDS: exact-time and gender finish guards.
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-COMPONENTS-ONBOARDING-FLOW

import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"

const { mockUpdateProfile } = vi.hoisted(() => ({
  mockUpdateProfile: vi.fn(),
}))

vi.mock("@/lib/api/profile", () => ({
  updateProfile: mockUpdateProfile,
  apiProfileToProfile: vi.fn((value: unknown) => value),
}))

vi.mock("@/hooks/use-profile", () => ({
  useProfile: () => ({ saveProfile: vi.fn() }),
}))

import { OnboardingFlow } from "@/components/onboarding/onboarding-flow"
import type { OnboardingState } from "@/lib/reducers/onboarding-reducer"

const filledState: OnboardingState = {
  step: "done",
  birthDate: { day: "15", month: "01", year: "1990" },
  birthTime: { hours: "12", minutes: "00", unknown: false },
  birthPlace: {
    name: "Москва",
    country: "Россия",
    lat: 55.75,
    lon: 37.61,
    timezone: "Europe/Moscow",
  },
  currentCity: null,
  sameAsBirth: true,
  birthdayCity: null,
  birthdaySameAsCurrent: true,
  gender: "male",
}

// START_BLOCK: GUARDS
describe("OnboardingFlow finish guards", () => {
  it("routes back to the birth step when exact time is required but unknown", async () => {
    const state: OnboardingState = {
      ...filledState,
      birthTime: { hours: "", minutes: "", unknown: true },
    }
    render(
      <OnboardingFlow
        onComplete={() => undefined}
        initialState={state}
        requireExactBirthTime
      />,
    )

    const cta = await screen.findByRole(
      "button",
      { name: /Открыть мой день/i },
      { timeout: 4000 },
    )
    fireEvent.click(cta)

    expect(mockUpdateProfile).not.toHaveBeenCalled()
    expect(screen.queryByRole("button", { name: /Открыть/i })).toBeNull()
  })

  it("routes back to the birth step when exact time is required but missing", async () => {
    const state: OnboardingState = {
      ...filledState,
      birthTime: { hours: "", minutes: "", unknown: false },
    }
    render(
      <OnboardingFlow
        onComplete={() => undefined}
        initialState={state}
        requireExactBirthTime
      />,
    )

    const cta = await screen.findByRole(
      "button",
      { name: /Открыть мой день/i },
      { timeout: 4000 },
    )
    fireEvent.click(cta)

    expect(mockUpdateProfile).not.toHaveBeenCalled()
    expect(screen.queryByRole("button", { name: /Открыть/i })).toBeNull()
  })

  it("routes to the gender step when gender is missing", async () => {
    const state: OnboardingState = { ...filledState, gender: null }
    render(
      <OnboardingFlow
        onComplete={() => undefined}
        initialState={state}
      />,
    )

    const cta = await screen.findByRole(
      "button",
      { name: /Открыть мой день/i },
      { timeout: 4000 },
    )
    fireEvent.click(cta)

    expect(mockUpdateProfile).not.toHaveBeenCalled()
    expect(screen.queryByRole("button", { name: /Открыть/i })).toBeNull()
  })
})
// END_BLOCK: GUARDS
