/**
 * Тесты zod-контрактов.
 *
 * Главная цель: моки и фикстуры ВСЕГДА валидны по контракту.
 * Если мок расходится с контрактом — тест падает ДО того,
 * как фронт упадёт в рантайме.
 */

import { describe, it, expect } from "vitest"

// Contracts
import { AccessInfoSchema } from "./access"
import {
  CitySchema,
} from "./city"
import {
  DayStatusSchema,
} from "./calendar"
import {
  TodayPayloadSchema,
} from "./today"
import {
  NatalReportSchema,
} from "./natal"

// Mocks
import { buildMockAccess } from "../mocks/access"
import { searchMockCities } from "../mocks/cities"
import { buildMockDayStatus } from "../mocks/calendar"
import { buildMockTodayPayload } from "../mocks/today"
import { MOCK_NATAL_REPORT } from "../mocks/natal"

describe("Contract: Access", () => {
  const states = ["trial", "subscription", "expired", "none"] as const

  it.each(states)("buildMockAccess('%s') матчится на AccessInfoSchema", (state) => {
    const info = buildMockAccess(state)
    const result = AccessInfoSchema.safeParse(info)
    if (!result.success) {
      // Полезный вывод при падении, чтобы не лазить в debugger.
      // eslint-disable-next-line no-console
      console.log(`[v0] ${state} info:`, info, result.error.issues)
    }
    expect(result.success).toBe(true)
  })
})

describe("Contract: City", () => {
  it("searchMockCities returns valid City objects", () => {
    const cities = searchMockCities("Москва")
    expect(cities.length).toBeGreaterThan(0)
    for (const city of cities) {
      const result = CitySchema.safeParse(city)
      expect(result.success, `Failed for city: ${city.name}`).toBe(true)
    }
  })

  it("searchMockCities returns empty array for unknown query", () => {
    const cities = searchMockCities("xyz123nonexistent")
    expect(cities).toEqual([])
  })
})

describe("Contract: Calendar", () => {
  it("buildMockDayStatus returns valid DayStatus", () => {
    const status = buildMockDayStatus(new Date(2025, 4, 15))
    const result = DayStatusSchema.safeParse(status)
    expect(result.success).toBe(true)
  })

  it("buildMockDayStatus returns one of expected values", () => {
    const validStatuses = ["even", "supportive", "tense"]
    for (let day = 1; day <= 31; day++) {
      const status = buildMockDayStatus(new Date(2025, 4, day))
      expect(validStatuses).toContain(status)
    }
  })
})

describe("Contract: Today", () => {
  it("buildMockTodayPayload returns valid TodayPayload", () => {
    const payload = buildMockTodayPayload(new Date(2025, 4, 15))
    const result = TodayPayloadSchema.safeParse(payload)
    if (!result.success) {
      console.log("Validation errors:", result.error.issues)
    }
    expect(result.success).toBe(true)
  })

  it("payload has expected structure", () => {
    const payload = buildMockTodayPayload(new Date(2025, 4, 15))
    expect(payload.date).toBe("2025-05-15")
    expect(payload.notes).toBeDefined()
    expect(Array.isArray(payload.notes)).toBe(true)
    expect(payload.reading).toBeDefined()
    expect(payload.why).toBeDefined()
    expect(payload.keyInsight).toBeDefined()
  })
})

describe("Contract: Natal", () => {
  it("MOCK_NATAL_REPORT matches NatalReportSchema", () => {
    const result = NatalReportSchema.safeParse(MOCK_NATAL_REPORT)
    if (!result.success) {
      console.log("Validation errors:", result.error.issues)
    }
    expect(result.success).toBe(true)
  })

  it("all sections have valid structure", () => {
    for (const section of MOCK_NATAL_REPORT.sections) {
      expect(section.id).toBeDefined()
      expect(section.title).toBeDefined()
      expect(section.blocks).toBeInstanceOf(Array)
    }
  })

  it("has required meta fields", () => {
    expect(MOCK_NATAL_REPORT.meta.name).toBeDefined()
    expect(MOCK_NATAL_REPORT.meta.birth.date).toBeDefined()
    expect(MOCK_NATAL_REPORT.meta.birth.time).toBeDefined()
  })
})


