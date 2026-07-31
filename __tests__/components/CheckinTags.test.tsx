// ############################################################################
// AI_HEADER: TEST_COMPONENTS_CHECKIN_TAGS — check-in tags selector contract.
// ROLE: Proves toggle behaviour and selected-state rendering of CheckinTags.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-COMPONENTS-CHECKIN-TAGS
// purpose: Exercise CheckinTags select/deselect and rendering branches.
// owns:
//   - __tests__/components/CheckinTags.test.tsx
// inputs: selected tags and onChange spy.
// outputs: DOM assertions on tag buttons and emitted selection.
// dependencies: components/checkin/checkin-tags, testing-library.
// side_effects: none.
// emitted_logs: none.
// invariants: DOM contract via data-testid only.
// failure_policy: assertion failure on behaviour drift.
// END_MODULE_CONTRACT: M-TEST-COMPONENTS-CHECKIN-TAGS

// START_MODULE_MAP: M-TEST-COMPONENTS-CHECKIN-TAGS
// public_entrypoints:
//   - vitest test suite
// semantic_blocks:
//   - TOGGLE: select and deselect paths.
//   - RENDER: selected vs unselected presentation.
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-COMPONENTS-CHECKIN-TAGS

import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"

import { CheckinTags } from "@/components/checkin/checkin-tags"
import { TAG_OPTIONS } from "@/lib/contracts/checkin"

// START_BLOCK: TOGGLE
describe("CheckinTags", () => {
  it("renders every option and adds an unselected tag on click", () => {
    const onChange = vi.fn()
    render(<CheckinTags selected={[]} onChange={onChange} />)

    expect(screen.getAllByRole("button")).toHaveLength(TAG_OPTIONS.length)
    const first = TAG_OPTIONS[0].value
    fireEvent.click(screen.getByTestId(`tag-${first}`))

    expect(onChange).toHaveBeenCalledWith([first])
  })

  it("removes an already selected tag on click", () => {
    const onChange = vi.fn()
    const first = TAG_OPTIONS[0].value
    const second = TAG_OPTIONS[1].value
    render(<CheckinTags selected={[first, second]} onChange={onChange} />)

    fireEvent.click(screen.getByTestId(`tag-${first}`))

    expect(onChange).toHaveBeenCalledWith([second])
  })
// END_BLOCK: TOGGLE

// START_BLOCK: RENDER
  it("marks selected tags with a check icon state", () => {
    const first = TAG_OPTIONS[0].value
    const second = TAG_OPTIONS[1].value
    render(<CheckinTags selected={[first]} onChange={() => undefined} />)

    const selectedButton = screen.getByTestId(`tag-${first}`)
    const plainButton = screen.getByTestId(`tag-${second}`)

    expect(selectedButton.className).not.toBe(plainButton.className)
  })
})
// END_BLOCK: RENDER
