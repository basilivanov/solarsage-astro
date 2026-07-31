// ############################################################################
// AI_HEADER: TEST_COMPONENTS_STEP_BIRTHDAY — onboarding birthday-city step.
// ROLE: Proves validity gating and same-city toggle of StepBirthday.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-COMPONENTS-STEP-BIRTHDAY
// purpose: Exercise StepBirthday validity and same-as-current branches.
// owns:
//   - __tests__/components/StepBirthday.test.tsx
// inputs: city props and handler spies.
// outputs: DOM assertions on CTA state and checkbox behaviour.
// dependencies: components/onboarding/step-birthday, testing-library.
// side_effects: none.
// emitted_logs: none.
// invariants: CTA disabled state derives only from validity rule.
// failure_policy: assertion failure on behaviour drift.
// END_MODULE_CONTRACT: M-TEST-COMPONENTS-STEP_BIRTHDAY

// START_MODULE_MAP: M-TEST-COMPONENTS-STEP_BIRTHDAY
// public_entrypoints:
//   - vitest test suite
// semantic_blocks:
//   - VALIDITY: CTA gating on same/city combinations.
//   - TOGGLE: same-as-current checkbox callback.
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-COMPONENTS-STEP_BIRTHDAY

import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"

import { StepBirthday } from "@/components/onboarding/step-birthday"

const moscow = {
  id: 1,
  name: "Москва",
  country: "Россия",
  lat: 55.75,
  lon: 37.61,
  timezone: "Europe/Moscow",
}

const baseProps = {
  onChangeBirthdayCity: () => undefined,
  onChangeSameAsCurrent: () => undefined,
  onBack: () => undefined,
  onNext: () => undefined,
}

// START_BLOCK: VALIDITY
describe("StepBirthday", () => {
  it("keeps CTA disabled without same-city and without a picked city", () => {
    render(
      <StepBirthday
        {...baseProps}
        currentCity={moscow}
        birthdayCity={null}
        sameAsCurrent={false}
      />,
    )

    expect((screen.getByRole("button", { name: "Далее" }) as HTMLButtonElement).disabled).toBe(true)
  })

  it("enables CTA when same-as-current is checked", () => {
    render(
      <StepBirthday
        {...baseProps}
        currentCity={moscow}
        birthdayCity={null}
        sameAsCurrent
      />,
    )

    expect((screen.getByRole("button", { name: "Далее" }) as HTMLButtonElement).disabled).toBe(false)
  })

  it("enables CTA when a different birthday city is picked", () => {
    render(
      <StepBirthday
        {...baseProps}
        currentCity={moscow}
        birthdayCity={moscow}
        sameAsCurrent={false}
      />,
    )

    expect((screen.getByRole("button", { name: "Далее" }) as HTMLButtonElement).disabled).toBe(false)
  })
// END_BLOCK: VALIDITY

// START_BLOCK: TOGGLE
  it("emits the same-as-current toggle value", () => {
    const onChangeSameAsCurrent = vi.fn()
    render(
      <StepBirthday
        {...baseProps}
        onChangeSameAsCurrent={onChangeSameAsCurrent}
        currentCity={moscow}
        birthdayCity={null}
        sameAsCurrent={false}
      />,
    )

    fireEvent.click(screen.getByRole("checkbox"))

    expect(onChangeSameAsCurrent).toHaveBeenCalledWith(true)
  })

  it("renders the current city label and fallback dash", () => {
    const { rerender } = render(
      <StepBirthday
        {...baseProps}
        currentCity={moscow}
        birthdayCity={null}
        sameAsCurrent={false}
      />,
    )
    expect(screen.getByText("Москва, Россия")).toBeTruthy()

    rerender(
      <StepBirthday
        {...baseProps}
        currentCity={null}
        birthdayCity={null}
        sameAsCurrent={false}
      />,
    )
    expect(screen.getByText("—")).toBeTruthy()
  })
})
// END_BLOCK: TOGGLE
