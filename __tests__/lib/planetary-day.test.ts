import { describe, it, expect } from "vitest"
import {
  getPlanetaryDay,
  getPlanetaryHourTimeline,
  type PlanetaryDayInfo,
  type PlanetaryHourEntry,
} from "@/lib/planetary-day"

describe("lib/planetary-day — getPlanetaryDay", () => {
  it("возвращает объект с корректной структурой", () => {
    const result = getPlanetaryDay(new Date("2026-06-26T12:00:00Z"))
    expect(result).toHaveProperty("dayRuler")
    expect(result).toHaveProperty("dayRulerRu")
    expect(result).toHaveProperty("dayRulerSymbol")
    expect(result).toHaveProperty("dayRulerColor")
    expect(result).toHaveProperty("dayOfWeekRu")
    expect(result).toHaveProperty("hourRuler")
    expect(result).toHaveProperty("hourRulerRu")
    expect(result).toHaveProperty("hourRulerSymbol")
    expect(result).toHaveProperty("dayInterpretation")
    expect(result).toHaveProperty("hourInterpretation")
    expect(result).toHaveProperty("hourType")
  })

  it("воскресенье → Sun управитель", () => {
    // 2026-06-28 — воскресенье
    const sunday = new Date("2026-06-28T12:00:00Z")
    const result = getPlanetaryDay(sunday)
    expect(result.dayRuler).toBe("Sun")
    expect(result.dayRulerRu).toBe("Солнце")
    expect(result.dayOfWeekRu).toBe("Воскресенье")
  })

  it("понедельник → Moon управитель", () => {
    // 2026-06-29 — понедельник
    const monday = new Date("2026-06-29T12:00:00Z")
    const result = getPlanetaryDay(monday)
    expect(result.dayRuler).toBe("Moon")
    expect(result.dayRulerRu).toBe("Луна")
    expect(result.dayOfWeekRu).toBe("Понедельник")
  })

  it("вторник → Mars управитель", () => {
    // 2026-06-30 — вторник
    const tuesday = new Date("2026-06-30T12:00:00Z")
    const result = getPlanetaryDay(tuesday)
    expect(result.dayRuler).toBe("Mars")
    expect(result.dayRulerRu).toBe("Марс")
    expect(result.dayOfWeekRu).toBe("Вторник")
  })

  it("среда → Mercury управитель", () => {
    // 2026-07-01 — среда
    const wednesday = new Date("2026-07-01T12:00:00Z")
    const result = getPlanetaryDay(wednesday)
    expect(result.dayRuler).toBe("Mercury")
    expect(result.dayRulerRu).toBe("Меркурий")
  })

  it("четверг → Jupiter управитель", () => {
    // 2026-07-02 — четверг
    const thursday = new Date("2026-07-02T12:00:00Z")
    const result = getPlanetaryDay(thursday)
    expect(result.dayRuler).toBe("Jupiter")
    expect(result.dayRulerRu).toBe("Юпитер")
  })

  it("пятница → Venus управитель", () => {
    // 2026-06-26 — пятница
    const friday = new Date("2026-06-26T12:00:00Z")
    const result = getPlanetaryDay(friday)
    expect(result.dayRuler).toBe("Venus")
    expect(result.dayRulerRu).toBe("Венера")
  })

  it("суббота → Saturn управитель", () => {
    // 2026-06-27 — суббота
    const saturday = new Date("2026-06-27T12:00:00Z")
    const result = getPlanetaryDay(saturday)
    expect(result.dayRuler).toBe("Saturn")
    expect(result.dayRulerRu).toBe("Сатурн")
  })

  it("hourType — 'day' или 'night'", () => {
    for (let h = 0; h < 24; h++) {
      const date = new Date(2026, 5, 26, h, 0, 0)
      const result = getPlanetaryDay(date)
      expect(["day", "night"]).toContain(result.hourType)
    }
  })

  it("час 12 (день) → hourType 'day'", () => {
    const noon = new Date(2026, 5, 26, 12, 0, 0)
    const result = getPlanetaryDay(noon)
    expect(result.hourType).toBe("day")
  })

  it("час 22 (ночь) → hourType 'night'", () => {
    const night = new Date(2026, 5, 26, 22, 0, 0)
    const result = getPlanetaryDay(night)
    expect(result.hourType).toBe("night")
  })

  it("dayInterpretation непустой", () => {
    const result = getPlanetaryDay(new Date("2026-06-26T12:00:00Z"))
    expect(result.dayInterpretation.length).toBeGreaterThan(10)
  })

  it("hourInterpretation непустой", () => {
    const result = getPlanetaryDay(new Date("2026-06-26T12:00:00Z"))
    expect(result.hourInterpretation.length).toBeGreaterThan(5)
  })
})

describe("lib/planetary-day — getPlanetaryHourTimeline", () => {
  it("возвращает массив из 12 часов", () => {
    const result = getPlanetaryHourTimeline(new Date("2026-06-26T12:00:00Z"))
    expect(result).toHaveLength(12)
  })

  it("каждый час имеет корректную структуру", () => {
    const result = getPlanetaryHourTimeline(new Date("2026-06-26T12:00:00Z"))
    result.forEach((h, i) => {
      expect(h.index).toBe(i)
      expect(typeof h.ruler).toBe("string")
      expect(typeof h.rulerRu).toBe("string")
      expect(typeof h.rulerSymbol).toBe("string")
      expect(h.startsAt).toBeInstanceOf(Date)
      expect(h.endsAt).toBeInstanceOf(Date)
      expect(typeof h.isCurrent).toBe("boolean")
      expect(["day", "night"]).toContain(h.type)
    })
  })

  it("ровно один час помечен как текущий", () => {
    const date = new Date(2026, 5, 26, 14, 30, 0)
    const result = getPlanetaryHourTimeline(date)
    const current = result.filter((h) => h.isCurrent)
    expect(current).toHaveLength(1)
  })

  it("первый час управляется day ruler", () => {
    const friday = new Date(2026, 5, 26, 8, 0, 0) // пятница
    const result = getPlanetaryHourTimeline(friday)
    const dayInfo = getPlanetaryDay(friday)
    expect(result[0].ruler).toBe(dayInfo.dayRuler)
  })

  it("startsAt раньше endsAt для каждого часа", () => {
    const result = getPlanetaryHourTimeline(new Date("2026-06-26T12:00:00Z"))
    result.forEach((h) => {
      expect(h.startsAt.getTime()).toBeLessThan(h.endsAt.getTime())
    })
  })

  it("часы идут последовательно (endsAt[i] === startsAt[i+1])", () => {
    const result = getPlanetaryHourTimeline(new Date("2026-06-26T12:00:00Z"))
    for (let i = 0; i < result.length - 1; i++) {
      expect(result[i].endsAt.getTime()).toBe(result[i + 1].startsAt.getTime())
    }
  })
})
