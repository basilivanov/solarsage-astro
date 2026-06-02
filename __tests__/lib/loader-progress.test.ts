/**
 * Тесты чистой логики CosmicLoader.
 *
 * Анимацию и DOM не проверяем (vitest здесь в node-окружении) — проверяем
 * инварианты прогресса и выбора подписи, на которых держится лоадер:
 *   - бар не превышает потолок, пока не пришёл `done`;
 *   - после `done` бар монотонно доходит ровно до 100 и не уходит выше;
 *   - подпись циклична, устойчива к пустому/отрицательному индексу;
 *   - при `done` всегда финальная фраза.
 */

import { describe, it, expect } from "vitest"

import {
  captionFor,
  DEFAULT_MESSAGES,
  DONE_MESSAGE,
  DONE_STEP,
  nextMessageIndex,
  nextProgress,
  progressEase,
  PROGRESS_CEILING,
  PROGRESS_START,
} from "@/lib/loader-progress"

// ---------------------------------------------------------------------------
// progressEase
// ---------------------------------------------------------------------------

describe("progressEase", () => {
  it("клампится сверху на 0.12 при коротком ожидании", () => {
    expect(progressEase(100)).toBe(0.12)
  })

  it("даёт меньшую долю при длинном ожидании", () => {
    const ease = progressEase(12000)
    expect(ease).toBeGreaterThan(0)
    expect(ease).toBeLessThan(0.12)
  })

  it("не делит на ноль и не уходит в бесконечность", () => {
    expect(progressEase(0)).toBe(0.12)
    expect(progressEase(-500)).toBe(0.12)
  })
})

// ---------------------------------------------------------------------------
// nextProgress — режим ожидания (done = false)
// ---------------------------------------------------------------------------

describe("nextProgress (ожидание)", () => {
  it("растёт со старта, но не превышает потолок", () => {
    let p = PROGRESS_START
    for (let i = 0; i < 1000; i++) {
      p = nextProgress(p, false, 12000)
      expect(p).toBeLessThanOrEqual(PROGRESS_CEILING)
    }
  })

  it("монотонно не убывает", () => {
    let p = PROGRESS_START
    for (let i = 0; i < 200; i++) {
      const next = nextProgress(p, false, 12000)
      expect(next).toBeGreaterThanOrEqual(p)
      p = next
    }
  })

  it("замирает ровно на потолке, не переваливая за него", () => {
    expect(nextProgress(PROGRESS_CEILING, false, 12000)).toBe(PROGRESS_CEILING)
    expect(nextProgress(PROGRESS_CEILING + 3, false, 12000)).toBe(
      PROGRESS_CEILING,
    )
  })

  it("за разумное число тиков подбирается близко к потолку", () => {
    let p = PROGRESS_START
    for (let i = 0; i < 300; i++) p = nextProgress(p, false, 12000)
    expect(p).toBeGreaterThan(PROGRESS_CEILING - 1)
  })
})

// ---------------------------------------------------------------------------
// nextProgress — режим завершения (done = true)
// ---------------------------------------------------------------------------

describe("nextProgress (done)", () => {
  it("прибавляет фиксированный шаг", () => {
    expect(nextProgress(80, true, 12000)).toBe(80 + DONE_STEP)
  })

  it("дожимает до 100 и не уходит выше", () => {
    let p = PROGRESS_CEILING
    for (let i = 0; i < 50; i++) p = nextProgress(p, true, 12000)
    expect(p).toBe(100)
  })

  it("100 остаётся 100", () => {
    expect(nextProgress(100, true, 12000)).toBe(100)
  })
})

// ---------------------------------------------------------------------------
// captionFor
// ---------------------------------------------------------------------------

describe("captionFor", () => {
  it("возвращает подпись по индексу", () => {
    expect(captionFor(false, 0, DEFAULT_MESSAGES)).toBe(DEFAULT_MESSAGES[0])
    expect(captionFor(false, 2, DEFAULT_MESSAGES)).toBe(DEFAULT_MESSAGES[2])
  })

  it("циклична за пределами длины", () => {
    const len = DEFAULT_MESSAGES.length
    expect(captionFor(false, len, DEFAULT_MESSAGES)).toBe(DEFAULT_MESSAGES[0])
    expect(captionFor(false, len + 1, DEFAULT_MESSAGES)).toBe(
      DEFAULT_MESSAGES[1],
    )
  })

  it("устойчива к отрицательному индексу", () => {
    expect(captionFor(false, -1, DEFAULT_MESSAGES)).toBe(
      DEFAULT_MESSAGES[DEFAULT_MESSAGES.length - 1],
    )
  })

  it("при done всегда финальная фраза, независимо от индекса", () => {
    expect(captionFor(true, 0, DEFAULT_MESSAGES)).toBe(DONE_MESSAGE)
    expect(captionFor(true, 99, DEFAULT_MESSAGES)).toBe(DONE_MESSAGE)
  })

  it("возвращает пустую строку для пустого списка (без done)", () => {
    expect(captionFor(false, 0, [])).toBe("")
  })

  it("использует кастомный список подписей", () => {
    const custom = ["А", "Б", "В"]
    expect(captionFor(false, 4, custom)).toBe("Б")
  })
})

// ---------------------------------------------------------------------------
// nextMessageIndex
// ---------------------------------------------------------------------------

describe("nextMessageIndex", () => {
  it("инкрементит и зацикливается", () => {
    expect(nextMessageIndex(0, 3)).toBe(1)
    expect(nextMessageIndex(2, 3)).toBe(0)
  })

  it("безопасен при нулевой длине", () => {
    expect(nextMessageIndex(5, 0)).toBe(0)
  })
})
