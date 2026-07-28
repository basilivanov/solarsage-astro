// ############################################################################
// AI_HEADER: MODULE_FOCUS_EVENT_SHEET_TEST
// ROLE: Unit acceptance tests for FocusEventSheet component (Slice E2).
// DEPENDENCIES: vitest, @testing-library/react, components/today/focus-event-sheet
// ############################################################################

import { describe, expect, it, vi, beforeEach, afterEach } from "vitest"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import React from "react"
import { FocusEventSheet } from "@/components/today/focus-event-sheet"
import type { TodayFocusEvent, FocusEventDrilldown } from "@/lib/contracts/today"

const event: TodayFocusEvent = {
  id: "ev:act:t2n__MOON__SQUARE__PLUTO",
  kind: "exact",
  occursAt: "2026-07-28T13:31:00Z",
  localDate: "2026-07-28",
  timezone: "Europe/Moscow",
  precision: "minute",
  humanTitle: "Луна в напряжении с твоим Плутоном",
  technicalTitle: "Луна квадратура Плутон",
  meaning: "Реакция может быть глубже обычного — не принимай её за решение.",
  sourceActivationIds: ["act-moon-sq-pluto"],
}

const drilldownFixture: FocusEventDrilldown = {
  eventId: "ev:act:t2n__MOON__SQUARE__PLUTO",
  humanTitle: "Луна в напряжении с твоим Плутоном",
  technicalTitle: "Луна квадратура Плутон",
  kind: "exact",
  kindLabel: "точный пик",
  occursAt: "2026-07-28T13:31:00Z",
  localTime: "16:31",
  timezone: "Europe/Moscow",
  meaning: "Реакция может быть глубже обычного — не принимай её за решение.",
  techniqueLabel: "Транзит к твоей натальной карте",
  source: {
    planetKey: "MOON",
    label: "Луна",
    frameLabel: "транзитная",
    functionText: "эмоции и привычки",
  },
  target: {
    planetKey: "PLUTO",
    label: "Плутон",
    frameLabel: "твой натальный",
    functionText: "глубокая трансформация и эмоциональная интенсивность",
  },
  aspectLabel: "Квадрат",
  aspectSymbol: "□",
  aspectTone: "tense",
  aspectMechanics: "Динамический вызов и трение, требующие роста.",
  numbers: [
    { label: "Орб", value: "0°19′" },
    { label: "Точное время", value: "16:31 · Europe/Moscow" },
    { label: "Фаза", value: "точный" },
    { label: "Сила влияния", value: "72%" },
    { label: "Полюс", value: "напряжённый" },
  ],
  sourceActivationIds: ["act-moon-sq-pluto"],
}

describe("FocusEventSheet", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it("fetches and renders ready state with all required sections and camelCase fields", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => drilldownFixture,
    } as Response)

    render(<FocusEventSheet date="2026-07-28" event={event} onClose={() => {}} />)

    const sheet = screen.getByTestId("focus-event-sheet")
    expect(sheet.getAttribute("data-state")).toBe("loading")

    await waitFor(() => {
      expect(sheet.getAttribute("data-state")).toBe("ready")
    })

    expect(screen.getByTestId("focus-event-title").textContent).toBe("Луна в напряжении с твоим Плутоном")
    expect(screen.getByTestId("focus-event-kind").textContent).toContain("точный пик · 16:31")

    const planets = screen.getByTestId("focus-event-planets")
    expect(planets.textContent).toContain("Луна")
    expect(planets.textContent).toContain("транзитная")
    expect(planets.textContent).toContain("Плутон")
    expect(planets.textContent).toContain("твой натальный")

    const mechanics = screen.getByTestId("focus-event-mechanics")
    expect(mechanics.textContent).toContain("Как работает Квадрат")
    expect(mechanics.textContent).toContain("□")
    expect(mechanics.textContent).toContain("Динамический вызов и трение, требующие роста.")

    const meaning = screen.getByTestId("focus-event-meaning")
    expect(meaning.textContent).toContain("Реакция может быть глубже обычного — не принимай её за решение.")

    const numbers = screen.getByTestId("focus-event-numbers")
    expect(numbers.textContent).toContain("Орб")
    expect(numbers.textContent).toContain("0°19′")
    expect(numbers.textContent).toContain("Точное время")
    expect(numbers.textContent).toContain("16:31 · Europe/Moscow")

    const tech = screen.getByTestId("focus-event-technique")
    expect(tech.textContent).toBe("Транзит к твоей натальной карте")
  })

  it("handles HTTP 500 error state with role='alert' and retries on button click", async () => {
    let callCount = 0
    const fetchSpy = vi.spyOn(global, "fetch").mockImplementation(async () => {
      callCount++
      if (callCount === 1) {
        return { ok: false, status: 500 } as Response
      }
      return {
        ok: true,
        status: 200,
        json: async () => drilldownFixture,
      } as Response
    })

    render(<FocusEventSheet date="2026-07-28" event={event} onClose={() => {}} />)

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeTruthy()
    })
    expect(screen.getByRole("alert").textContent).toContain("Не удалось загрузить разбор события")

    const retryBtn = screen.getByTestId("focus-event-retry")
    fireEvent.click(retryBtn)

    await waitFor(() => {
      expect(screen.getByTestId("focus-event-sheet").getAttribute("data-state")).toBe("ready")
    })
    expect(fetchSpy).toHaveBeenCalledTimes(2)
  })

  it("caches response in ref and avoids second fetch when re-opening same event", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => drilldownFixture,
    } as Response)

    const { rerender } = render(<FocusEventSheet date="2026-07-28" event={event} onClose={() => {}} />)

    await waitFor(() => {
      expect(screen.getByTestId("focus-event-sheet").getAttribute("data-state")).toBe("ready")
    })
    expect(fetchSpy).toHaveBeenCalledTimes(1)

    // Close
    rerender(<FocusEventSheet date="2026-07-28" event={null} onClose={() => {}} />)

    // Re-open same event
    rerender(<FocusEventSheet date="2026-07-28" event={event} onClose={() => {}} />)

    await waitFor(() => {
      expect(screen.getByTestId("focus-event-sheet").getAttribute("data-state")).toBe("ready")
    })
    expect(fetchSpy).toHaveBeenCalledTimes(1) // Still 1 fetch!
  })
})
