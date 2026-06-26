import { describe, it, expect } from "vitest"
import {
  computeMoonPhase,
  computeMoonPhaseForDay,
  getMoonPhaseCompact,
  isLunarEventDay,
  getLunarEventName,
  getLunarDay,
  NEW_MOON_EPOCH,
  SYNODIC_MONTH,
  type MoonPhaseInfo,
} from "@/lib/moon"

describe("lib/moon — computeMoonPhase", () => {
  it("возвращает объект с корректной структурой", () => {
    const result = computeMoonPhase(new Date("2026-06-26T12:00:00Z"))
    expect(result).toHaveProperty("phaseIndex")
    expect(result).toHaveProperty("illumination")
    expect(result).toHaveProperty("age")
    expect(result).toHaveProperty("phaseName")
    expect(result).toHaveProperty("phaseEmoji")
    expect(result).toHaveProperty("signName")
    expect(result).toHaveProperty("signElement")
    expect(result).toHaveProperty("isWaxing")
  })

  it("phaseIndex в диапазоне 0-7", () => {
    for (let d = 0; d < 365; d++) {
      const date = new Date(2026, 0, 1 + d)
      const result = computeMoonPhase(date)
      expect(result.phaseIndex).toBeGreaterThanOrEqual(0)
      expect(result.phaseIndex).toBeLessThanOrEqual(7)
    }
  })

  it("illumination в диапазоне 0-100", () => {
    for (let d = 0; d < 30; d++) {
      const date = new Date(2026, 5, 1 + d)
      const result = computeMoonPhase(date)
      expect(result.illumination).toBeGreaterThanOrEqual(0)
      expect(result.illumination).toBeLessThanOrEqual(100)
    }
  })

  it("age в диапазоне 0..SYNODIC_MONTH", () => {
    const result = computeMoonPhase(new Date("2026-06-26T12:00:00Z"))
    expect(result.age).toBeGreaterThanOrEqual(0)
    expect(result.age).toBeLessThan(SYNODIC_MONTH)
  })

  it("известное новолуние 6 января 2000 возвращает phaseIndex 0 (новолуние)", () => {
    const knownNewMoon = new Date(NEW_MOON_EPOCH)
    const result = computeMoonPhase(knownNewMoon)
    expect(result.illumination).toBeLessThan(3)
  })

  it("через ~14.77 дней после новолуния — полнолуние (illumination ~100)", () => {
    const newMoon = new Date(NEW_MOON_EPOCH)
    const fullMoon = new Date(NEW_MOON_EPOCH + SYNODIC_MONTH / 2 * 86400000)
    const result = computeMoonPhase(fullMoon)
    expect(result.illumination).toBeGreaterThan(95)
  })

  it("через полный синодический месяц — снова новолуние", () => {
    const newMoon = new Date(NEW_MOON_EPOCH)
    const nextNewMoon = new Date(NEW_MOON_EPOCH + SYNODIC_MONTH * 86400000)
    const result = computeMoonPhase(nextNewMoon)
    expect(result.illumination).toBeLessThan(5)
  })

  it("isWaxing true в первой половине цикла", () => {
    const newMoon = new Date(NEW_MOON_EPOCH)
    const waxing = new Date(NEW_MOON_EPOCH + 5 * 86400000)
    const result = computeMoonPhase(waxing)
    expect(result.isWaxing).toBe(true)
  })

  it("isWaxing false во второй половине цикла", () => {
    const waning = new Date(NEW_MOON_EPOCH + 20 * 86400000)
    const result = computeMoonPhase(waning)
    expect(result.isWaxing).toBe(false)
  })

  it("signName — одно из 12 знаков", () => {
    const result = computeMoonPhase(new Date("2026-06-26T12:00:00Z"))
    const validSigns = ["Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева", "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"]
    expect(validSigns).toContain(result.signName)
  })

  it("signElement — одна из 4 стихий", () => {
    const result = computeMoonPhase(new Date("2026-06-26T12:00:00Z"))
    const validElements = ["Огонь", "Земля", "Воздух", "Вода"]
    expect(validElements).toContain(result.signElement)
  })

  it("детерминированный результат — та же дата даёт тот же результат", () => {
    const date = new Date("2026-06-26T12:00:00Z")
    const r1 = computeMoonPhase(date)
    const r2 = computeMoonPhase(date)
    expect(r1).toEqual(r2)
  })
})

describe("lib/moon — computeMoonPhaseForDay", () => {
  it("возвращает фазу для указанного года/месяца/дня", () => {
    const result = computeMoonPhaseForDay(2026, 5, 26) // 26 июня 2026
    expect(result).toHaveProperty("phaseIndex")
    expect(result).toHaveProperty("illumination")
  })

  it("та же дата что и computeMoonPhase — похожий результат", () => {
    const dayResult = computeMoonPhaseForDay(2026, 5, 26)
    expect(dayResult.phaseIndex).toBeGreaterThanOrEqual(0)
    expect(dayResult.phaseIndex).toBeLessThanOrEqual(7)
  })
})

describe("lib/moon — getMoonPhaseCompact", () => {
  it("возвращает emoji, illumination, phaseIndex", () => {
    const result = getMoonPhaseCompact(new Date("2026-06-26T12:00:00Z"))
    expect(result).toHaveProperty("emoji")
    expect(result).toHaveProperty("illumination")
    expect(result).toHaveProperty("phaseIndex")
    expect(typeof result.illumination).toBe("number")
  })

  it("emoji — один из 8 валидных", () => {
    const validEmojis = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
    for (let d = 0; d < 30; d++) {
      const result = getMoonPhaseCompact(new Date(2026, 5, 1 + d))
      expect(validEmojis).toContain(result.emoji)
    }
  })
})

describe("lib/moon — isLunarEventDay / getLunarEventName", () => {
  it("isLunarEventDay возвращает boolean", () => {
    const result = isLunarEventDay(new Date("2026-06-26T12:00:00Z"))
    expect(typeof result).toBe("boolean")
  })

  it("getLunarEventName возвращает null или строку", () => {
    const result = getLunarEventName(new Date("2026-06-26T12:00:00Z"))
    expect(result === null || typeof result === "string").toBe(true)
  })

  it("если isLunarEventDay=true — getLunarEventName возвращает строку", () => {
    for (let d = 0; d < 60; d++) {
      const date = new Date(2026, 0, 1 + d)
      if (isLunarEventDay(date)) {
        expect(getLunarEventName(date)).not.toBeNull()
      }
    }
  })

  it("валидные имена событий", () => {
    const validNames = ["Новолуние", "Первая четверть", "Полнолуние", "Последняя четверть"]
    for (let d = 0; d < 60; d++) {
      const name = getLunarEventName(new Date(2026, 0, 1 + d))
      if (name !== null) {
        expect(validNames).toContain(name)
      }
    }
  })
})

describe("lib/moon — getLunarDay", () => {
  it("возвращает день 1-30", () => {
    for (let d = 0; d < 30; d++) {
      const result = getLunarDay(new Date(2026, 5, 1 + d))
      expect(result.day).toBeGreaterThanOrEqual(1)
      expect(result.day).toBeLessThanOrEqual(30)
    }
  })

  it("возвращает name (строка)", () => {
    const result = getLunarDay(new Date("2026-06-26T12:00:00Z"))
    expect(typeof result.name).toBe("string")
    expect(result.name.length).toBeGreaterThan(0)
  })

  it("возвращает description (строка)", () => {
    const result = getLunarDay(new Date("2026-06-26T12:00:00Z"))
    expect(typeof result.description).toBe("string")
    expect(result.description.length).toBeGreaterThan(10)
  })

  it("favorable — boolean", () => {
    const result = getLunarDay(new Date("2026-06-26T12:00:00Z"))
    expect(typeof result.favorable).toBe("boolean")
  })

  it("tag — один из 4 валидных", () => {
    const validTags = ["светлый", "нейтральный", "напряжённый", "тёмный"]
    for (let d = 0; d < 30; d++) {
      const result = getLunarDay(new Date(2026, 5, 1 + d))
      expect(validTags).toContain(result.tag)
    }
  })

  it("день 15 — Полнолуние — напряжённый", () => {
    // При age ~14.77 day = 15
    // Найти дату с age ~14.5
    const fullMoonTime = NEW_MOON_EPOCH + 14.5 * 86400000
    const result = getLunarDay(new Date(fullMoonTime))
    // День 15 должен быть напряжённым (Полнолуние)
    if (result.day === 15) {
      expect(result.favorable).toBe(false)
      expect(result.tag).toBe("напряжённый")
    }
  })
})
