
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_NUMFIELD_TEST
// ROLE: Unit tests for NumField.test.tsx
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for NumFieldtsx behavior
// owns:
//   - __tests__/components/NumField.test.tsx
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

vi.mock('@/lib/log', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}))

import { NumField } from '@/components/shared/num-field'

describe('NumField', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders with value', () => {
    render(
      <NumField
        label="Day"
        placeholder="ДД"
        value="15"
        onChange={vi.fn()}
        maxLength={2}
      />,
    )
    const input = screen.getByPlaceholderText('ДД') as HTMLInputElement
    expect(input.value).toBe('15')
    expect(screen.getByText('Day')).toBeTruthy()
  })

  it('calls onChange with stripped non-digits', () => {
    const onChange = vi.fn()
    render(
      <NumField
        label="Year"
        placeholder="ГГГГ"
        value=""
        onChange={onChange}
        maxLength={4}
      />,
    )
    const input = screen.getByPlaceholderText('ГГГГ')
    fireEvent.change(input, { target: { value: '19a8b5' } })
    expect(onChange).toHaveBeenCalledWith('1985')
  })

  it('passes digits through unchanged', () => {
    const onChange = vi.fn()
    render(
      <NumField
        label="Day"
        placeholder="ДД"
        value=""
        onChange={onChange}
        maxLength={2}
      />,
    )
    const input = screen.getByPlaceholderText('ДД')
    fireEvent.change(input, { target: { value: '25' } })
    expect(onChange).toHaveBeenCalledWith('25')
  })

  it('renders disabled input when disabled prop is true', () => {
    render(
      <NumField
        label="Day"
        placeholder="ДД"
        value="10"
        onChange={vi.fn()}
        maxLength={2}
        disabled
      />,
    )
    const input = screen.getByPlaceholderText('ДД') as HTMLInputElement
    expect(input.disabled).toBe(true)
  })

  it('renders wide variant with larger flex', () => {
    const { container } = render(
      <NumField
        label="Year"
        placeholder="ГГГГ"
        value=""
        onChange={vi.fn()}
        maxLength={4}
        wide
      />,
    )
    const label = container.querySelector('label')
    expect(label?.className).toContain('flex-[1.6]')
  })
})
