import { describe, it, expect } from 'vitest'
import { stripTime, sameDay, addDays } from '../../lib/today'

describe('stripTime', () => {
  it('zeros out hours, minutes, seconds and milliseconds', () => {
    const d = new Date(2025, 5, 15, 14, 30, 45, 500)
    const result = stripTime(d)
    expect(result.getFullYear()).toBe(2025)
    expect(result.getMonth()).toBe(5)
    expect(result.getDate()).toBe(15)
    expect(result.getHours()).toBe(0)
    expect(result.getMinutes()).toBe(0)
    expect(result.getSeconds()).toBe(0)
    expect(result.getMilliseconds()).toBe(0)
  })

  it('returns a new Date instance', () => {
    const d = new Date(2025, 0, 1, 10, 30, 45, 500)
    const result = stripTime(d)
    expect(result).not.toBe(d)
    expect(result.getHours()).toBe(0)
    expect(result.getMinutes()).toBe(0)
    expect(result.getSeconds()).toBe(0)
    expect(result.getMilliseconds()).toBe(0)
  })
})

describe('sameDay', () => {
  it('returns true for the same calendar day ignoring time', () => {
    const a = new Date(2025, 5, 15, 0, 0, 0, 0)
    const b = new Date(2025, 5, 15, 23, 59, 59, 999)
    expect(sameDay(a, b)).toBe(true)
  })

  it('returns false for different days in the same month', () => {
    const a = new Date(2025, 5, 15)
    const b = new Date(2025, 5, 16)
    expect(sameDay(a, b)).toBe(false)
  })

  it('returns false for different months same day number', () => {
    const a = new Date(2025, 5, 15)
    const b = new Date(2025, 6, 15)
    expect(sameDay(a, b)).toBe(false)
  })

  it('returns false for different years', () => {
    const a = new Date(2025, 5, 15)
    const b = new Date(2024, 5, 15)
    expect(sameDay(a, b)).toBe(false)
  })

  it('returns true for two Date instances created differently for the same day', () => {
    const a = stripTime(new Date(2025, 5, 15, 10, 30))
    const b = stripTime(new Date(2025, 5, 15, 22, 0))
    expect(sameDay(a, b)).toBe(true)
  })
})

describe('addDays', () => {
  it('adds a positive number of days', () => {
    const result = addDays(new Date(2025, 0, 1), 5)
    expect(result.getFullYear()).toBe(2025)
    expect(result.getMonth()).toBe(0)
    expect(result.getDate()).toBe(6)
  })

  it('adds zero days and returns a new instance', () => {
    const d = new Date(2025, 0, 1)
    const result = addDays(d, 0)
    expect(result).not.toBe(d)
    expect(result.getFullYear()).toBe(2025)
    expect(result.getMonth()).toBe(0)
    expect(result.getDate()).toBe(1)
  })

  it('handles month boundary crossing', () => {
    const result = addDays(new Date(2025, 0, 31), 1)
    expect(result.getFullYear()).toBe(2025)
    expect(result.getMonth()).toBe(1)
    expect(result.getDate()).toBe(1)
  })

  it('handles negative days', () => {
    const result = addDays(new Date(2025, 0, 1), -1)
    expect(result.getFullYear()).toBe(2024)
    expect(result.getMonth()).toBe(11)
    expect(result.getDate()).toBe(31)
  })
})
