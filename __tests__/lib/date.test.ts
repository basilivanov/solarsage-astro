
// ############################################################################
// AI_HEADER: MODULE_LIB_DATE_TEST
// ROLE: Unit tests for date.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Unit tests for date.test.ts — __tests__/lib/date.test.ts
// owns:
//   - __tests__/lib/date.test.ts
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

import { describe, it, expect } from 'vitest'
import {
  toDateParam,
  fromDateParam,
  formatDayMonth,
  formatLong,
  mondayFirstIndex,
  startOfWeek,
  formatWeekRange,
} from '../../lib/date'

describe('toDateParam', () => {
  it('formats a regular date as YYYY-MM-DD', () => {
    expect(toDateParam(new Date(2025, 0, 1))).toBe('2025-01-01')
  })

  it('pads single-digit month and day with zero', () => {
    expect(toDateParam(new Date(2025, 4, 8))).toBe('2025-05-08')
  })

  it('handles end-of-year dates', () => {
    expect(toDateParam(new Date(2025, 11, 31))).toBe('2025-12-31')
  })

  it('handles leap year Feb 29', () => {
    expect(toDateParam(new Date(2024, 1, 29))).toBe('2024-02-29')
  })
})

describe('fromDateParam', () => {
  it('parses a valid YYYY-MM-DD string to a Date', () => {
    const result = fromDateParam('2025-06-15')
    expect(result).toBeInstanceOf(Date)
    expect(result!.getFullYear()).toBe(2025)
    expect(result!.getMonth()).toBe(5)
    expect(result!.getDate()).toBe(15)
  })

  it('returns null for an invalid date string format', () => {
    expect(fromDateParam('not-a-date')).toBeNull()
  })

  it('returns null for empty string', () => {
    expect(fromDateParam('')).toBeNull()
  })

  it('returns null for a non-existent date (Feb 30)', () => {
    expect(fromDateParam('2025-02-30')).toBeNull()
  })

  it('returns null for garbage numeric string', () => {
    expect(fromDateParam('9999-99-99')).toBeNull()
  })

  it('returns null for wrong format (DD-MM-YYYY)', () => {
    expect(fromDateParam('15-06-2025')).toBeNull()
  })

  it('parses a valid date at the year 1900 boundary', () => {
    const result = fromDateParam('1900-01-01')
    expect(result).toBeInstanceOf(Date)
    expect(result!.getFullYear()).toBe(1900)
  })
})

describe('formatDayMonth', () => {
  it('formats "15 мая" correctly', () => {
    expect(formatDayMonth(new Date(2025, 4, 15))).toBe('15 мая')
  })

  it('formats "1 января" correctly', () => {
    expect(formatDayMonth(new Date(2025, 0, 1))).toBe('1 января')
  })

  it('formats "31 декабря" correctly', () => {
    expect(formatDayMonth(new Date(2025, 11, 31))).toBe('31 декабря')
  })
})

describe('formatLong', () => {
  it('includes the full year', () => {
    expect(formatLong(new Date(2025, 7, 18))).toBe('18 августа 2025')
  })

  it('handles leap year date', () => {
    expect(formatLong(new Date(2024, 1, 29))).toBe('29 февраля 2024')
  })
})

describe('mondayFirstIndex', () => {
  it('returns 0 for Monday', () => {
    expect(mondayFirstIndex(new Date(2025, 5, 2))).toBe(0)
  })

  it('returns 6 for Sunday', () => {
    expect(mondayFirstIndex(new Date(2025, 5, 1))).toBe(6)
  })

  it('returns 2 for Wednesday', () => {
    expect(mondayFirstIndex(new Date(2025, 5, 4))).toBe(2)
  })
})

describe('startOfWeek', () => {
  it('gives Monday for a Wednesday date', () => {
    const wed = new Date(2025, 5, 4)
    const mon = startOfWeek(wed)
    expect(mon.getDay()).toBe(1)
    expect(mon.getDate()).toBe(2)
  })

  it('returns itself when date is already Monday', () => {
    const mon = new Date(2025, 5, 2)
    const result = startOfWeek(mon)
    expect(result.getFullYear()).toBe(2025)
    expect(result.getMonth()).toBe(5)
    expect(result.getDate()).toBe(2)
  })

  it('goes back to previous month when Sunday is early in the month', () => {
    const sun = new Date(2025, 5, 1)
    const mon = startOfWeek(sun)
    expect(mon.getFullYear()).toBe(2025)
    expect(mon.getMonth()).toBe(4)
    expect(mon.getDate()).toBe(26)
  })
})

describe('formatWeekRange', () => {
  it('formats same-month range: "1 – 7 янв"', () => {
    expect(formatWeekRange(new Date(2025, 0, 1))).toBe('1 – 7 янв')
  })

  it('formats cross-month range: "28 июл – 3 авг"', () => {
    expect(formatWeekRange(new Date(2025, 6, 28))).toBe('28 июл – 3 авг')
  })
})
