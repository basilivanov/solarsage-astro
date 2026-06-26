import { describe, it, expect } from "vitest"
import {
  getRetrograde,
  getAllRetrogrades,
  hasAnyRetrograde,
} from "@/lib/retrograde"

describe("lib/retrograde — getRetrograde", () => {
  it("возвращает объект с корректной структурой", () => {
    const result = getRetrograde("Mercury", new Date("2026-06-26T12:00:00Z"))
    expect(result).toHaveProperty("planet")
    expect(result).toHaveProperty("planetRu")
    expect(result).toHaveProperty("symbol")
    expect(result).toHaveProperty("color")
    expect(result).toHaveProperty("isRetrograde")
    expect(result).toHaveProperty("note")
    expect(result).toHaveProperty("interpretation")
  })

  it("isRetrograde — boolean", () => {
    const result = getRetrograde("Mercury", new Date("2026-06-26T12:00:00Z"))
    expect(typeof result.isRetrograde).toBe("boolean")
  })

  it("если retrograde — rxStartedAt и rxEndsAt не null", () => {
    // Перебираем даты, чтобы найти ретроградный Меркурий
    for (let d = 0; d < 365; d++) {
      const date = new Date(2026, 0, 1 + d)
      const result = getRetrograde("Mercury", date)
      if (result.isRetrograde) {
        expect(result.rxStartedAt).not.toBeNull()
        expect(result.rxEndsAt).not.toBeNull()
        expect(result.daysIntoRx).not.toBeNull()
        expect(result.rxDurationDays).not.toBeNull()
        expect(result.nextRxStart).toBeNull()
        return
      }
    }
    // Если не нашли — тоже ок (меркурий ретрограден ~3 раза в год)
  })

  it("если не retrograde — nextRxStart не null", () => {
    for (let d = 0; d < 365; d++) {
      const date = new Date(2026, 0, 1 + d)
      const result = getRetrograde("Mercury", date)
      if (!result.isRetrograde) {
        expect(result.nextRxStart).not.toBeNull()
        expect(result.rxStartedAt).toBeNull()
        expect(result.rxEndsAt).toBeNull()
        return
      }
    }
  })

  it("Mercury ретрограден хотя бы один раз за год", () => {
    let found = false
    for (let d = 0; d < 365; d++) {
      if (getRetrograde("Mercury", new Date(2026, 0, 1 + d)).isRetrograde) {
        found = true
        break
      }
    }
    expect(found).toBe(true)
  })

  it("Venus —Russian name Венера", () => {
    const result = getRetrograde("Venus", new Date("2026-06-26T12:00:00Z"))
    expect(result.planetRu).toBe("Венера")
  })

  it("Mars — Russian name Марс", () => {
    const result = getRetrograde("Mars", new Date("2026-06-26T12:00:00Z"))
    expect(result.planetRu).toBe("Марс")
  })

  it("Mercury — symbol ☿", () => {
    const result = getRetrograde("Mercury", new Date("2026-06-26T12:00:00Z"))
    expect(result.symbol).toBe("☿")
  })

  it("бросает ошибку для неизвестной планеты", () => {
    expect(() => getRetrograde("Pluto" as any, new Date())).toThrow("Unknown planet")
  })

  it("interpretation непустой при retrograde", () => {
    for (let d = 0; d < 365; d++) {
      const date = new Date(2026, 0, 1 + d)
      const result = getRetrograde("Mercury", date)
      if (result.isRetrograde) {
        expect(result.interpretation.length).toBeGreaterThan(10)
        return
      }
    }
  })
})

describe("lib/retrograde — getAllRetrogrades", () => {
  it("возвращает массив из 3 планет", () => {
    const result = getAllRetrogrades(new Date("2026-06-26T12:00:00Z"))
    expect(result).toHaveLength(3)
    expect(result.map((r) => r.planet)).toEqual(["Mercury", "Venus", "Mars"])
  })

  it("каждый элемент имеет корректную структуру", () => {
    const result = getAllRetrogrades(new Date("2026-06-26T12:00:00Z"))
    result.forEach((r) => {
      expect(typeof r.isRetrograde).toBe("boolean")
      expect(typeof r.planetRu).toBe("string")
      expect(typeof r.symbol).toBe("string")
    })
  })
})

describe("lib/retrograde — hasAnyRetrograde", () => {
  it("возвращает boolean", () => {
    const result = hasAnyRetrograde(new Date("2026-06-26T12:00:00Z"))
    expect(typeof result).toBe("boolean")
  })

  it("за год хотя бы раз true (есть ретрограды)", () => {
    let foundAny = false
    for (let d = 0; d < 365; d++) {
      if (hasAnyRetrograde(new Date(2026, 0, 1 + d))) {
        foundAny = true
        break
      }
    }
    expect(foundAny).toBe(true)
  })

  it("за год хотя бы раз false (все прямые)", () => {
    let foundNone = false
    for (let d = 0; d < 365; d++) {
      if (!hasAnyRetrograde(new Date(2026, 0, 1 + d))) {
        foundNone = true
        break
      }
    }
    expect(foundNone).toBe(true)
  })
})
