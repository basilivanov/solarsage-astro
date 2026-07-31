// ############################################################################
// AI_HEADER: TEST_COMPONENTS_CHECKIN_SELECTORS — mood/energy/accuracy selectors.
// ROLE: Proves option rendering and selection callbacks of check-in selectors.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-COMPONENTS-CHECKIN-SELECTORS
// purpose: Exercise MoodSelector, EnergySelector and AccuracySelector branches.
// owns:
//   - __tests__/components/CheckinSelectors.test.tsx
// inputs: current value and onChange spies.
// outputs: DOM assertions on options and emitted values.
// dependencies: components/checkin/*-selector, testing-library.
// side_effects: none.
// emitted_logs: none.
// invariants: DOM contract via data-testid only.
// failure_policy: assertion failure on behaviour drift.
// END_MODULE_CONTRACT: M-TEST-COMPONENTS-CHECKIN-SELECTORS

// START_MODULE_MAP: M-TEST-COMPONENTS-CHECKIN-SELECTORS
// public_entrypoints:
//   - vitest test suite
// semantic_blocks:
//   - MOOD: options and selection.
//   - ENERGY: options and selection.
//   - ACCURACY: options and selection.
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-COMPONENTS-CHECKIN-SELECTORS

import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"

import { MoodSelector } from "@/components/checkin/mood-selector"
import { EnergySelector } from "@/components/checkin/energy-selector"
import { AccuracySelector } from "@/components/checkin/accuracy-selector"
import {
  MOOD_OPTIONS,
  ENERGY_OPTIONS,
  ACCURACY_OPTIONS,
} from "@/lib/contracts/checkin"

// START_BLOCK: MOOD
describe("check-in selectors", () => {
  it("MoodSelector renders all options and selects one", () => {
    const onChange = vi.fn()
    render(<MoodSelector value={null} onChange={onChange} />)

    expect(screen.getAllByRole("button")).toHaveLength(MOOD_OPTIONS.length)
    const first = MOOD_OPTIONS[0].value
    fireEvent.click(screen.getByTestId(`mood-${first}`))

    expect(onChange).toHaveBeenCalledWith(first)
  })
// END_BLOCK: MOOD

// START_BLOCK: ENERGY
  it("EnergySelector renders all options and selects one", () => {
    const onChange = vi.fn()
    render(<EnergySelector value={null} onChange={onChange} />)

    expect(screen.getAllByRole("button")).toHaveLength(ENERGY_OPTIONS.length)
    const first = ENERGY_OPTIONS[0].value
    fireEvent.click(screen.getByTestId(`energy-${first}`))

    expect(onChange).toHaveBeenCalledWith(first)
  })
// END_BLOCK: ENERGY

// START_BLOCK: ACCURACY
  it("AccuracySelector renders all options and selects one", () => {
    const onChange = vi.fn()
    render(<AccuracySelector value={null} onChange={onChange} />)

    expect(screen.getAllByRole("button")).toHaveLength(ACCURACY_OPTIONS.length)
    const first = ACCURACY_OPTIONS[0].value
    fireEvent.click(screen.getByTestId(`accuracy-${first}`))

    expect(onChange).toHaveBeenCalledWith(first)
  })

  it("selected option differs in presentation from unselected", () => {
    const first = MOOD_OPTIONS[0].value
    const second = MOOD_OPTIONS[1].value
    render(<MoodSelector value={first as never} onChange={() => undefined} />)

    expect(
      screen.getByTestId(`mood-${first}`).className,
    ).not.toBe(screen.getByTestId(`mood-${second}`).className)
  })
})
// END_BLOCK: ACCURACY
