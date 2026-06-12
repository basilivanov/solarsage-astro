
// ############################################################################
// AI_HEADER: MODULE_LIB_CALENDAR_TEST
// ROLE: Unit tests for calendar.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for calendarts behavior
// owns:
//   - __tests__/lib/calendar.test.ts
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
import { describe, it, expect } from 'vitest'
import { statusLabel, dateKey, monthMatrix, monthDiff } from '../../lib/calendar'

describe('statusLabel', () => {
  it('returns "напряжённый" for "tense"', () => {
    expect(statusLabel('tense')).toBe('напряжённый')
  })

  it('returns "ровный" for "even"', () => {
    expect(statusLabel('even')).toBe('ровный')
  })

  it('returns "поддерживающий" for "supportive"', () => {
    expect(statusLabel('supportive')).toBe('поддерживающий')
  })
})

describe('dateKey', () => {
  it('formats a date as YYYY-MM-DD', () => {
    expect(dateKey(new Date(2025, 0, 1))).toBe('2025-01-01')
  })

  it('pads single-digit month and day', () => {
    expect(dateKey(new Date(2025, 2, 5))).toBe('2025-03-05')
  })

  it('handles December 31', () => {
    expect(dateKey(new Date(2025, 11, 31))).toBe('2025-12-31')
  })
})

describe('monthMatrix', () => {
  it('returns exactly 42 cells', () => {
    const cells = monthMatrix(2025, 5) // June 2025
    expect(cells).toHaveLength(42)
  })

  it('first cell is the correct Monday of the grid', () => {
    const cells = monthMatrix(2025, 5) // June 2025 starts on Sunday
    const first = cells[0]
    // The grid starts on the Monday of the week containing June 1
    expect(first.date.getDay()).toBe(1) // Monday
  })

  it('returns exactly the correct number of inMonth cells', () => {
    const cells = monthMatrix(2025, 0) // January — 31 days
    const inMonth = cells.filter((c) => c.inMonth)
    expect(inMonth).toHaveLength(31)
  })

  it('handles February in a non-leap year (28 days)', () => {
    const cells = monthMatrix(2025, 1) // February 2025
    const inMonth = cells.filter((c) => c.inMonth)
    expect(inMonth).toHaveLength(28)
  })

  it('handles February in a leap year (29 days)', () => {
    const cells = monthMatrix(2024, 1) // February 2024
    const inMonth = cells.filter((c) => c.inMonth)
    expect(inMonth).toHaveLength(29)
  })

  it('inMonth cells are contiguous', () => {
    const cells = monthMatrix(2025, 5)
    const indices = cells
      .map((c, i) => (c.inMonth ? i : -1))
      .filter((i) => i >= 0)
    // check they are consecutive
    for (let i = 1; i < indices.length; i++) {
      expect(indices[i]).toBe(indices[i - 1] + 1)
    }
  })

  it('all dates in the matrix are Date instances', () => {
    const cells = monthMatrix(2025, 5)
    for (const cell of cells) {
      expect(cell.date).toBeInstanceOf(Date)
    }
  })
})

describe('monthDiff', () => {
  it('returns positive diff for dates in different months', () => {
    const a = new Date(2025, 6, 1)
    const b = new Date(2025, 0, 1)
    expect(monthDiff(a, b)).toBe(6)
  })

  it('returns negative diff when first date is earlier', () => {
    const a = new Date(2025, 0, 1)
    const b = new Date(2025, 6, 1)
    expect(monthDiff(a, b)).toBe(-6)
  })

  it('returns 0 for same month', () => {
    const a = new Date(2025, 3, 15)
    const b = new Date(2025, 3, 1)
    expect(monthDiff(a, b)).toBe(0)
  })

  it('handles cross-year diff correctly', () => {
    const a = new Date(2026, 0, 1)
    const b = new Date(2025, 0, 1)
    expect(monthDiff(a, b)).toBe(12)
  })

  it('handles multi-year diff', () => {
    const a = new Date(2027, 10, 1) // Nov 2027
    const b = new Date(2025, 0, 1)  // Jan 2025
    expect(monthDiff(a, b)).toBe(34) // (2027-2025)*12 + (10-0) = 24 + 10 = 34
  })
})
