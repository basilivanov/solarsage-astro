import { describe, it, expect } from "vitest"
import { getLunarNodes, type LunarNodeInfo } from "@/lib/lunar-nodes"

describe("lib/lunar-nodes — getLunarNodes", () => {
  it("возвращает объект с корректной структурой", () => {
    const result = getLunarNodes(new Date("2026-06-26T12:00:00Z"))
    expect(result).toHaveProperty("northNodeSign")
    expect(result).toHaveProperty("northNodeSignRu")
    expect(result).toHaveProperty("northNodeSymbol")
    expect(result).toHaveProperty("southNodeSign")
    expect(result).toHaveProperty("southNodeSignRu")
    expect(result).toHaveProperty("southNodeSymbol")
    expect(result).toHaveProperty("northNodeHouse")
    expect(result).toHaveProperty("southNodeHouse")
    expect(result).toHaveProperty("northNodeInterpretation")
    expect(result).toHaveProperty("southNodeInterpretation")
    expect(result).toHaveProperty("yearsUntilSignChange")
  })

  it("northNodeSign в диапазоне 0-11", () => {
    const result = getLunarNodes(new Date("2026-06-26T12:00:00Z"))
    expect(result.northNodeSign).toBeGreaterThanOrEqual(0)
    expect(result.northNodeSign).toBeLessThanOrEqual(11)
  })

  it("southNodeSign — противоположный northNodeSign", () => {
    const result = getLunarNodes(new Date("2026-06-26T12:00:00Z"))
    expect(result.southNodeSign).toBe((result.northNodeSign + 6) % 12)
  })

  it("northNodeSymbol = ☊", () => {
    const result = getLunarNodes(new Date("2026-06-26T12:00:00Z"))
    expect(result.northNodeSymbol).toBe("☊")
  })

  it("southNodeSymbol = ☋", () => {
    const result = getLunarNodes(new Date("2026-06-26T12:00:00Z"))
    expect(result.southNodeSymbol).toBe("☋")
  })

  it("northNodeSignRu — валидный знак", () => {
    const validSigns = ["Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева", "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"]
    const result = getLunarNodes(new Date("2026-06-26T12:00:00Z"))
    expect(validSigns).toContain(result.northNodeSignRu)
  })

  it("southNodeSignRu — валидный знак и противоположный", () => {
    const validSigns = ["Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева", "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"]
    const result = getLunarNodes(new Date("2026-06-26T12:00:00Z"))
    expect(validSigns).toContain(result.southNodeSignRu)
    // South должен быть противоположным North
    const northIdx = validSigns.indexOf(result.northNodeSignRu)
    const southIdx = validSigns.indexOf(result.southNodeSignRu)
    expect(southIdx).toBe((northIdx + 6) % 12)
  })

  it("northNodeHouse в диапазоне 1-12", () => {
    const result = getLunarNodes(new Date("2026-06-26T12:00:00Z"))
    expect(result.northNodeHouse).toBeGreaterThanOrEqual(1)
    expect(result.northNodeHouse).toBeLessThanOrEqual(12)
  })

  it("southNodeHouse в диапазоне 1-12", () => {
    const result = getLunarNodes(new Date("2026-06-26T12:00:00Z"))
    expect(result.southNodeHouse).toBeGreaterThanOrEqual(1)
    expect(result.southNodeHouse).toBeLessThanOrEqual(12)
  })

  it("northNodeInterpretation непустой", () => {
    const result = getLunarNodes(new Date("2026-06-26T12:00:00Z"))
    expect(result.northNodeInterpretation.length).toBeGreaterThan(10)
  })

  it("southNodeInterpretation непустой", () => {
    const result = getLunarNodes(new Date("2026-06-26T12:00:00Z"))
    expect(result.southNodeInterpretation.length).toBeGreaterThan(10)
  })

  it("yearsUntilSignChange неотрицательный", () => {
    const result = getLunarNodes(new Date("2026-06-26T12:00:00Z"))
    // Может быть 0 если узел очень близко к границе знака
    expect(result.yearsUntilSignChange).toBeGreaterThanOrEqual(0)
    expect(result.yearsUntilSignChange).toBeLessThanOrEqual(2) // ~1.5 года на знак
  })

  it("детерминированный результат", () => {
    const date = new Date("2026-06-26T12:00:00Z")
    const r1 = getLunarNodes(date)
    const r2 = getLunarNodes(date)
    expect(r1).toEqual(r2)
  })
})
