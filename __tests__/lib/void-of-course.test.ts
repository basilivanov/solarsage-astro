import { describe, it, expect } from "vitest"
import { getVoidOfCourse, type VoidOfCourseInfo } from "@/lib/moon"

describe("lib/moon — getVoidOfCourse", () => {
  it("возвращает объект с корректной структурой", () => {
    const result = getVoidOfCourse(new Date("2026-06-26T12:00:00Z"))
    expect(result).toHaveProperty("isVoid")
    expect(result).toHaveProperty("startedAt")
    expect(result).toHaveProperty("endsAt")
    expect(result).toHaveProperty("durationHours")
    expect(result).toHaveProperty("note")
    expect(result).toHaveProperty("recommendation")
  })

  it("isVoid — boolean", () => {
    const result = getVoidOfCourse(new Date("2026-06-26T12:00:00Z"))
    expect(typeof result.isVoid).toBe("boolean")
  })

  it("если isVoid=true — startedAt и endsAt не null", () => {
    for (let d = 0; d < 60; d++) {
      const date = new Date(2026, 0, 1 + d)
      const result = getVoidOfCourse(date)
      if (result.isVoid) {
        expect(result.startedAt).not.toBeNull()
        expect(result.endsAt).not.toBeNull()
        expect(result.durationHours).not.toBeNull()
        expect(typeof result.durationHours).toBe("number")
        expect(result.recommendation.length).toBeGreaterThan(10)
        return
      }
    }
  })

  it("если isVoid=false — startedAt и endsAt null", () => {
    for (let d = 0; d < 60; d++) {
      const date = new Date(2026, 0, 1 + d)
      const result = getVoidOfCourse(date)
      if (!result.isVoid) {
        expect(result.startedAt).toBeNull()
        expect(result.endsAt).toBeNull()
        expect(result.durationHours).toBeNull()
        expect(result.note).toBe("Луна активна")
        return
      }
    }
  })

  it("за 60 дней хотя бы раз isVoid=true", () => {
    let found = false
    for (let d = 0; d < 60; d++) {
      if (getVoidOfCourse(new Date(2026, 0, 1 + d)).isVoid) {
        found = true
        break
      }
    }
    // VoC ~6-7% времени, за 60 дней ~4 дня
    expect(found).toBe(true)
  })

  it("за 60 дней хотя бы раз isVoid=false", () => {
    let found = false
    for (let d = 0; d < 60; d++) {
      if (!getVoidOfCourse(new Date(2026, 0, 1 + d)).isVoid) {
        found = true
        break
      }
    }
    expect(found).toBe(true)
  })

  it("endsAt позже startedAt при isVoid", () => {
    for (let d = 0; d < 60; d++) {
      const date = new Date(2026, 0, 1 + d)
      const result = getVoidOfCourse(date)
      if (result.isVoid && result.startedAt && result.endsAt) {
        expect(result.endsAt.getTime()).toBeGreaterThan(result.startedAt.getTime())
        return
      }
    }
  })

  it("durationHours положительный при isVoid", () => {
    for (let d = 0; d < 60; d++) {
      const date = new Date(2026, 0, 1 + d)
      const result = getVoidOfCourse(date)
      if (result.isVoid && result.durationHours !== null) {
        expect(result.durationHours).toBeGreaterThan(0)
        return
      }
    }
  })
})
