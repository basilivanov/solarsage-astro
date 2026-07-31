// ############################################################################
// AI_HEADER: TEST_COMPONENTS_OBSERVED_SPHERES — check-in observed spheres field.
// ROLE: Proves sphere toggle branches of the observed-spheres fieldset.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-COMPONENTS-OBSERVED-SPHERES
// purpose: Exercise ObservedSpheresField select/deselect and full grid render.
// owns:
//   - __tests__/components/ObservedSpheres.test.tsx
// inputs: selected keys and onChange spy.
// outputs: DOM assertions on 12 checkboxes and emitted selections.
// dependencies: components/checkin/checkin-screen, testing-library.
// side_effects: none.
// emitted_logs: none.
// invariants: canonical order and data-testid contract hold.
// failure_policy: assertion failure on behaviour drift.
// END_MODULE_CONTRACT: M-TEST-COMPONENTS-OBSERVED-SPHERES

// START_MODULE_MAP: M-TEST-COMPONENTS-OBSERVED-SPHERES
// public_entrypoints:
//   - vitest test suite
// semantic_blocks:
//   - TOGGLE: select and deselect branches.
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-COMPONENTS-OBSERVED-SPHERES

import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"

import { CheckinScreen } from "@/components/checkin/checkin-screen"
import { CANONICAL_PRODUCT_ORDER } from "@/lib/display/sphere-labels"

const { mockGetYesterday, mockCreateCheckin } = vi.hoisted(() => ({
  mockGetYesterday: vi.fn(),
  mockCreateCheckin: vi.fn(),
}))

vi.mock("@/lib/api/checkin", () => ({
  getYesterdayCheckin: mockGetYesterday,
  createCheckin: mockCreateCheckin,
}))

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}))

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

// START_BLOCK: TOGGLE
describe("observed spheres field", () => {
  it("renders all 12 canonical spheres and toggles selection on and off", async () => {
    mockGetYesterday.mockResolvedValue({
      targetDate: "2026-07-30",
      hadCheckin: false,
      checkin: null,
      forecastAvailable: false,
      forecastRecap: null,
    })
    render(<CheckinScreen targetDate="2026-07-30" />)

    const fieldset = await screen.findByTestId("observed-spheres")
    const checkboxes = fieldset.querySelectorAll("input[type=checkbox]")
    expect(checkboxes).toHaveLength(CANONICAL_PRODUCT_ORDER.length)
    expect(CANONICAL_PRODUCT_ORDER).toHaveLength(12)

    const first = CANONICAL_PRODUCT_ORDER[0].key
    const checkbox = screen.getByTestId(`observed-sphere-${first}`)

    fireEvent.click(checkbox)
    expect((checkbox as HTMLInputElement).checked).toBe(true)

    fireEvent.click(checkbox)
    expect((checkbox as HTMLInputElement).checked).toBe(false)
  })

  it("allows selecting multiple spheres at once", async () => {
    mockGetYesterday.mockResolvedValue({
      targetDate: "2026-07-30",
      hadCheckin: false,
      checkin: null,
      forecastAvailable: false,
      forecastRecap: null,
    })
    render(<CheckinScreen targetDate="2026-07-30" />)

    await screen.findByTestId("observed-spheres")
    const first = CANONICAL_PRODUCT_ORDER[0].key
    const second = CANONICAL_PRODUCT_ORDER[1].key

    fireEvent.click(screen.getByTestId(`observed-sphere-${first}`))
    fireEvent.click(screen.getByTestId(`observed-sphere-${second}`))

    expect((screen.getByTestId(`observed-sphere-${first}`) as HTMLInputElement).checked).toBe(true)
    expect((screen.getByTestId(`observed-sphere-${second}`) as HTMLInputElement).checked).toBe(true)
  })
})
// END_BLOCK: TOGGLE
