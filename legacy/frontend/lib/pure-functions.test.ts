/**
 * Тесты pure functions — детерминированный код, участвующий в каждом рендере.
 *
 * Если эти функции врут — врёт всё. Тесты не зависят от фикстур.
 */

import { describe, it, expect } from "vitest"

// Date utilities
import {
  toDateParam,
  fromDateParam,
  formatDayMonth,
  formatLong,
  mondayFirstIndex,
  startOfWeek,
  formatWeekRange,
} from "./date"

// Calendar utilities
import { dateKey, monthMatrix, monthDiff, statusLabel } from "./calendar"

// Today utilities
import { stripTime, sameDay, addDays } from "./today"

// Access utilities
import { isDayAccessible } from "./access"

// Profile utilities
import {
  formatBirthDate,
  formatBirthTime,
  isValidBirthDate,
  isValidBirthTime,
} from "./profile"

// ---------------------------------------------------------------------------
// Date utilities
// ---------------------------------------------------------------------------

describe("toDateParam", () => {
  it("serializes date to YYYY-MM-DD", () => {
    expect(toDateParam(new Date(2025, 7, 18))).toBe("2025-08-18")
  })

  it("pads single digit month and day", () => {
    expect(toDateParam(new Date(2025, 0, 5))).toBe("2025-01-05")
  })

  it("handles year boundary", () => {
    expect(toDateParam(new Date(2024, 11, 31))).toBe("2024-12-31")
  })
})

describe("fromDateParam", () => {
  it("parses valid YYYY-MM-DD", () => {
    const date = fromDateParam("2025-08-18")
    expect(date).not.toBeNull()
    expect(date!.getFullYear()).toBe(2025)
    expect(date!.getMonth()).toBe(7) // August
    expect(date!.getDate()).toBe(18)
  })

  it("returns null for invalid format", () => {
    expect(fromDateParam("2025-8-18")).toBeNull()
    expect(fromDateParam("18-08-2025")).toBeNull()
    expect(fromDateParam("invalid")).toBeNull()
    expect(fromDateParam("")).toBeNull()
  })

  it("returns null for invalid date values", () => {
    expect(fromDateParam("2025-13-01")).toBeNull() // month 13
    expect(fromDateParam("2025-02-30")).toBeNull() // Feb 30
    expect(fromDateParam("2025-00-15")).toBeNull() // month 0
  })
})

describe("formatDayMonth", () => {
  it("formats date as 'd месяца'", () => {
    expect(formatDayMonth(new Date(2025, 7, 18))).toBe("18 августа")
    expect(formatDayMonth(new Date(2025, 0, 1))).toBe("1 января")
    expect(formatDayMonth(new Date(2025, 11, 31))).toBe("31 декабря")
  })
})

describe("formatLong", () => {
  it("formats date as 'd месяца year'", () => {
    expect(formatLong(new Date(2025, 7, 18))).toBe("18 августа 2025")
    expect(formatLong(new Date(1990, 5, 15))).toBe("15 июня 1990")
  })
})

describe("mondayFirstIndex", () => {
  it("returns 0 for Monday", () => {
    // 2025-08-18 is Monday
    expect(mondayFirstIndex(new Date(2025, 7, 18))).toBe(0)
  })

  it("returns 6 for Sunday", () => {
    // 2025-08-24 is Sunday
    expect(mondayFirstIndex(new Date(2025, 7, 24))).toBe(6)
  })
})

describe("startOfWeek", () => {
  it("returns Monday of the same week", () => {
    const monday = startOfWeek(new Date(2025, 7, 20)) // Wednesday
    expect(monday.getDate()).toBe(18) // Monday
    expect(monday.getMonth()).toBe(7)
  })

  it("returns same date if already Monday", () => {
    const monday = startOfWeek(new Date(2025, 7, 18))
    expect(monday.getDate()).toBe(18)
  })

  it("handles month boundary", () => {
    const monday = startOfWeek(new Date(2025, 8, 1)) // Sep 1 is Monday? Let's check
    // Sep 1, 2025 is Monday actually
    expect(monday.getMonth()).toBe(8) // September
    expect(monday.getDate()).toBe(1)
  })
})

describe("formatWeekRange", () => {
  it("formats week in same month", () => {
    const result = formatWeekRange(new Date(2025, 7, 18))
    expect(result).toBe("18 – 24 авг")
  })

  it("formats week across months", () => {
    const result = formatWeekRange(new Date(2025, 6, 28)) // Jul 28
    expect(result).toBe("28 июл – 3 авг")
  })
})

// ---------------------------------------------------------------------------
// Calendar utilities
// ---------------------------------------------------------------------------

describe("dateKey", () => {
  it("returns ISO YYYY-MM-DD format", () => {
    expect(dateKey(new Date(2025, 7, 18))).toBe("2025-08-18")
    expect(dateKey(new Date(2025, 0, 1))).toBe("2025-01-01")
  })
})

describe("monthMatrix", () => {
  it("returns 42 cells", () => {
    const cells = monthMatrix(2025, 7) // August 2025
    expect(cells).toHaveLength(42)
  })

  it("starts with Monday", () => {
    const cells = monthMatrix(2025, 7)
    // First cell should be a Monday
    expect(mondayFirstIndex(cells[0].date)).toBe(0)
  })

  it("marks cells correctly as in/out of month", () => {
    const cells = monthMatrix(2025, 7) // August 2025
    // August 1, 2025 is Friday, so first 4 cells are from July
    const augustCells = cells.filter((c) => c.inMonth)
    expect(augustCells.length).toBe(31) // August has 31 days
  })

  it("handles February in leap year", () => {
    const cells = monthMatrix(2020, 1) // February 2020
    const febCells = cells.filter((c) => c.inMonth)
    expect(febCells.length).toBe(29)
  })

  it("handles February in non-leap year", () => {
    const cells = monthMatrix(2019, 1) // February 2019
    const febCells = cells.filter((c) => c.inMonth)
    expect(febCells.length).toBe(28)
  })
})

describe("monthDiff", () => {
  it("returns 0 for same month", () => {
    expect(monthDiff(new Date(2025, 7, 1), new Date(2025, 7, 15))).toBe(0)
  })

  it("returns positive for later month", () => {
    expect(monthDiff(new Date(2025, 10, 1), new Date(2025, 7, 1))).toBe(3)
  })

  it("returns negative for earlier month", () => {
    expect(monthDiff(new Date(2025, 7, 1), new Date(2025, 10, 1))).toBe(-3)
  })

  it("handles year boundary", () => {
    expect(monthDiff(new Date(2026, 1, 1), new Date(2025, 11, 1))).toBe(2)
  })
})

describe("statusLabel", () => {
  it("returns correct Russian labels", () => {
    expect(statusLabel("tense")).toBe("напряжённый")
    expect(statusLabel("even")).toBe("ровный")
    expect(statusLabel("supportive")).toBe("поддерживающий")
  })
})

// ---------------------------------------------------------------------------
// Today utilities
// ---------------------------------------------------------------------------

describe("stripTime", () => {
  it("removes time component", () => {
    const date = new Date(2025, 7, 18, 14, 30, 45)
    const stripped = stripTime(date)
    expect(stripped.getHours()).toBe(0)
    expect(stripped.getMinutes()).toBe(0)
    expect(stripped.getSeconds()).toBe(0)
    expect(stripped.getMilliseconds()).toBe(0)
    expect(stripped.getDate()).toBe(18)
  })
})

describe("sameDay", () => {
  it("returns true for same day different times", () => {
    const a = new Date(2025, 7, 18, 10, 0)
    const b = new Date(2025, 7, 18, 22, 30)
    expect(sameDay(a, b)).toBe(true)
  })

  it("returns false for different days", () => {
    const a = new Date(2025, 7, 18)
    const b = new Date(2025, 7, 19)
    expect(sameDay(a, b)).toBe(false)
  })

  it("returns false for same day different month", () => {
    const a = new Date(2025, 7, 18)
    const b = new Date(2025, 8, 18)
    expect(sameDay(a, b)).toBe(false)
  })
})

describe("addDays", () => {
  it("adds positive days", () => {
    const date = new Date(2025, 7, 18)
    const result = addDays(date, 5)
    expect(result.getDate()).toBe(23)
  })

  it("subtracts with negative days", () => {
    const date = new Date(2025, 7, 18)
    const result = addDays(date, -3)
    expect(result.getDate()).toBe(15)
  })

  it("handles month rollover", () => {
    const date = new Date(2025, 7, 30)
    const result = addDays(date, 5)
    expect(result.getMonth()).toBe(8) // September
    expect(result.getDate()).toBe(4)
  })

  it("does not mutate original date", () => {
    const date = new Date(2025, 7, 18)
    addDays(date, 5)
    expect(date.getDate()).toBe(18)
  })
})

// ---------------------------------------------------------------------------
// Access utilities
// ---------------------------------------------------------------------------

describe("isDayAccessible", () => {
  const accessInfo = {
    hasAccess: true,
    accessStart: new Date(2025, 7, 15),
    accessEnd: new Date(2025, 7, 25),
    daysLeft: 10,
    state: "trial" as const,
  }

  it("returns true for date within access window", () => {
    expect(isDayAccessible(new Date(2025, 7, 18), accessInfo)).toBe(true)
    expect(isDayAccessible(new Date(2025, 7, 15), accessInfo)).toBe(true) // start
    expect(isDayAccessible(new Date(2025, 7, 25), accessInfo)).toBe(true) // end
  })

  it("returns false for date outside access window", () => {
    expect(isDayAccessible(new Date(2025, 7, 14), accessInfo)).toBe(false)
    expect(isDayAccessible(new Date(2025, 7, 26), accessInfo)).toBe(false)
  })

  it("returns false when hasAccess is false", () => {
    const noAccess = { ...accessInfo, hasAccess: false }
    expect(isDayAccessible(new Date(2025, 7, 18), noAccess)).toBe(false)
  })

  it("returns false when accessStart/End is null", () => {
    const partial = { ...accessInfo, accessStart: null }
    expect(isDayAccessible(new Date(2025, 7, 18), partial as any)).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Profile utilities
// ---------------------------------------------------------------------------

describe("formatBirthDate", () => {
  it("formats valid date", () => {
    expect(formatBirthDate({ day: "15", month: "06", year: "1990" })).toBe(
      "15 июня 1990"
    )
  })

  it("returns 'Не указано' for invalid month", () => {
    expect(formatBirthDate({ day: "15", month: "13", year: "1990" })).toBe(
      "Не указано"
    )
  })

  it("returns 'Не указано' for non-numeric values", () => {
    expect(formatBirthDate({ day: "xx", month: "06", year: "1990" })).toBe(
      "Не указано"
    )
  })
})

describe("formatBirthTime", () => {
  it("formats valid time", () => {
    expect(formatBirthTime({ hours: "14", minutes: "30", unknown: false })).toBe(
      "14:30"
    )
  })

  it("pads single digits", () => {
    expect(formatBirthTime({ hours: "8", minutes: "5", unknown: false })).toBe(
      "08:05"
    )
  })

  it("returns 'Не знаю' when unknown is true", () => {
    expect(formatBirthTime({ hours: "", minutes: "", unknown: true })).toBe(
      "Не знаю"
    )
  })
})

// `isValidBirthDate` / `isValidBirthTime` существуют в двух местах:
// `lib/profile.ts` (BirthDateParts) и `lib/reducers/onboarding-reducer.ts`
// (BirthDate). Полное покрытие — в reducers.test.ts; здесь только smoke,
// чтобы поймать падение публичного API из `lib/profile.ts`.

describe("isValidBirthDate (profile)", () => {
  it("happy + invalid", () => {
    expect(isValidBirthDate({ day: "15", month: "06", year: "1990" })).toBe(true)
    expect(isValidBirthDate({ day: "32", month: "06", year: "1990" })).toBe(false)
  })
})

describe("isValidBirthTime (profile)", () => {
  it("happy + invalid + unknown", () => {
    expect(
      isValidBirthTime({ hours: "14", minutes: "30", unknown: false }),
    ).toBe(true)
    expect(
      isValidBirthTime({ hours: "25", minutes: "30", unknown: false }),
    ).toBe(false)
    expect(isValidBirthTime({ hours: "", minutes: "", unknown: true })).toBe(true)
  })
})
