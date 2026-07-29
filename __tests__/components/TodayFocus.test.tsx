// ############################################################################
// AI_HEADER: MODULE_TODAY_FOCUS_CARD_TEST
// ROLE: Unit acceptance tests for TodayFocusCard component (W4-F1).
// ############################################################################

import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import React from "react"
import { TodayFocusCard } from "@/components/today/today-focus"
import { SphereDetailsSheet } from "@/components/today/sphere-details-sheet"
import type { TodayFocus } from "@/lib/contracts/today"

function makeFocus(overrides?: Partial<TodayFocus>): TodayFocus {
  return {
    state: "convergence_today",
    convergence: {
      id: "conv:1",
      themeKey: "NEPTUNE",
      title: "Что сошлось именно сегодня",
      summary: "Несколько факторов задевают тему выбора.",
      independentFactorCount: 2,
      techniqueFamilies: ["transit"],
      sourceActivationIds: ["act-1", "act-2"],
      backgroundFactors: [
        {
          id: "f:act-3",
          role: "supporting",
          humanTitle: "Венера в гармонии с твоим Нептуном",
          technicalTitle: "Венера тригон Нептун",
          sourceActivationIds: ["act-3"],
        },
        {
          id: "f:act-4",
          role: "background",
          humanTitle: "Лунар: Плутон — тема месяца",
          technicalTitle: "Лунар: Плутон на углу (4 дом)",
          sourceActivationIds: ["act-4"],
        },
      ],
    },
    events: [
      {
        id: "ev:1",
        kind: "exact",
        occursAt: "2026-07-28T19:52:00Z",
        localDate: "2026-07-28",
        timezone: "Europe/Moscow",
        precision: "minute",
        humanTitle: "Марс напротив твоего Нептуна",
        technicalTitle: "Марс оппозиция Нептун",
        meaning: "Проверь факты перед решением.",
        sourceActivationIds: ["act-1"],
      },
      {
        id: "ev:2",
        kind: "building",
        occursAt: "2026-07-29T00:49:00Z",
        localDate: "2026-07-28",
        timezone: "Europe/Moscow",
        precision: "minute",
        humanTitle: "Марс в напряжении с твоим Сатурном",
        technicalTitle: "Марс квадратура Сатурн",
        meaning: "Влияние нарастает к полуночи.",
        sourceActivationIds: ["act-2"],
      },
    ],
    featuredSpheres: [
      {
        key: "work",
        relevanceRank: 1,
        state: "convergence_today",
        summary: "На работе возможна смена планов.",
        action: "Проверь документы перед отправкой.",
        convergenceId: "conv:1",
        sourceEventIds: ["ev:1"],
        sourceActivationIds: ["act-1"],
      },
    ],
    contentState: "ready",
    ...overrides,
  }
}

describe("TodayFocusCard visual system", () => {
  it("renders convergence_today state with hero card, time column, kind labels, featured spheres, and action pill", () => {
    const onSphereSelect = vi.fn()
    const focus = makeFocus()

    render(<TodayFocusCard focus={focus} onSphereSelect={onSphereSelect} />)

    const section = screen.getByTestId("today-focus")
    expect(section.getAttribute("data-state")).toBe("convergence_today")
    expect(section.getAttribute("data-content-state")).toBe("ready")

    expect(section.textContent).toContain("СОШЛОСЬ СЕГОДНЯ")
    expect(section.textContent).toContain("02 ▸")
    expect(section.textContent).toContain("Что сошлось именно сегодня")
    expect(section.textContent).toContain("Несколько факторов задевают тему выбора.")

    const events = screen.getAllByTestId("today-focus-event")
    expect(events).toHaveLength(2)

    // Check data-event-id, data-event-kind, data-event-relation machine attributes (doc 28 §4)
    expect(events[0].getAttribute("data-event-id")).toBe("ev:1")
    expect(events[0].getAttribute("data-event-kind")).toBe("exact")
    expect(events[0].getAttribute("data-event-relation")).toBe("convergence_event")

    expect(events[1].getAttribute("data-event-id")).toBe("ev:2")
    expect(events[1].getAttribute("data-event-kind")).toBe("building")
    expect(events[1].getAttribute("data-event-relation")).toBe("convergence_event")

    // Kind labels
    expect(events[0].textContent).toContain("точный пик")
    expect(events[1].textContent).toContain("пик завтра")
    // "пик завтра" has opacity-60
    expect(events[1].className).toContain("opacity-60")

    // Featured sphere
    const featured = screen.getAllByTestId("today-featured-sphere")
    expect(featured).toHaveLength(1)
    expect(featured[0].getAttribute("data-sphere-key")).toBe("work")

    // Action pill
    expect(section.textContent).toContain("Проверь документы перед отправкой.")

    // Click featured sphere
    fireEvent.click(featured[0])
    expect(onSphereSelect).toHaveBeenCalledWith("work")
  })

  it("renders single_impulses state with compact card, eyebrow 'СОБЫТИЯ ДНЯ', without convergence title/summary/featured/action", () => {
    const focus = makeFocus({
      state: "single_impulses",
      convergence: null,
      featuredSpheres: [],
    })

    render(<TodayFocusCard focus={focus} onSphereSelect={() => {}} />)

    const section = screen.getByTestId("today-focus")
    expect(section.getAttribute("data-state")).toBe("single_impulses")

    expect(section.textContent).toContain("СОБЫТИЯ ДНЯ")
    expect(section.textContent).not.toContain("СОШЛОСЬ СЕГОДНЯ")
    expect(section.textContent).not.toContain("Что сошлось именно сегодня")
    expect(screen.queryAllByTestId("today-featured-sphere")).toHaveLength(0)

    const events = screen.getAllByTestId("today-focus-event")
    expect(events[0].getAttribute("data-event-relation")).toBe("independent_event")
  })

  it("renders background_only state as a quiet muted string without hero card", () => {
    const focus = makeFocus({ state: "background_only", convergence: null, events: [], featuredSpheres: [] })

    render(<TodayFocusCard focus={focus} onSphereSelect={() => {}} />)

    const section = screen.getByTestId("today-focus")
    expect(section.getAttribute("data-state")).toBe("background_only")
    expect(section.textContent).toContain("Фон периода: активны длительные астрологические факторы года.")
    expect(screen.queryAllByTestId("today-focus-event")).toHaveLength(0)
  })

  it("renders no_accent state as a quiet muted string", () => {
    const focus = makeFocus({ state: "no_accent", convergence: null, events: [], featuredSpheres: [] })

    render(<TodayFocusCard focus={focus} onSphereSelect={() => {}} />)

    const section = screen.getByTestId("today-focus")
    expect(section.getAttribute("data-state")).toBe("no_accent")
    expect(section.textContent).toContain("Сегодня нет выраженного схождения нескольких факторов.")
  })

  it("renders unavailable state with quiet message and retry button", () => {
    const onRetry = vi.fn()
    const focus = makeFocus({ state: "unavailable", convergence: null, events: [], featuredSpheres: [] })

    render(<TodayFocusCard focus={focus} onSphereSelect={() => {}} onRetry={onRetry} />)

    const section = screen.getByTestId("today-focus")
    expect(section.getAttribute("data-state")).toBe("unavailable")
    expect(section.textContent).toContain("Не удалось рассчитать акценты дня. Попробуй обновить позже.")

    const retryBtn = screen.getByTestId("today-focus-retry")
    fireEvent.click(retryBtn)
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it("handles contentState='pending' with deterministic pulse placeholders and role='status'", () => {
    const focus = makeFocus({ contentState: "pending" })

    render(<TodayFocusCard focus={focus} onSphereSelect={() => {}} />)

    const section = screen.getByTestId("today-focus")
    expect(section.getAttribute("data-content-state")).toBe("pending")

    const statusPlaceholders = screen.getAllByRole("status")
    expect(statusPlaceholders.length).toBeGreaterThan(0)
    for (const el of statusPlaceholders) {
      expect(el.getAttribute("aria-busy")).toBe("true")
    }
  })

  it("handles contentState='unavailable' showing 'Персональный разбор пока не готов'", () => {
    const focus = makeFocus({ contentState: "unavailable" })

    render(<TodayFocusCard focus={focus} onSphereSelect={() => {}} />)

    const section = screen.getByTestId("today-focus")
    expect(section.getAttribute("data-content-state")).toBe("unavailable")
    expect(section.textContent).toContain("Персональный разбор пока не готов")
  })

  it("toggles technical disclosure showing clean technical titles without raw Transit_/Natal_ prefixes", () => {
    const focus = makeFocus()

    render(<TodayFocusCard focus={focus} onSphereSelect={() => {}} />)

    const toggle = screen.getByTestId("today-focus-technical-toggle")
    expect(toggle.getAttribute("aria-expanded")).toBe("false")

    fireEvent.click(toggle)
    expect(toggle.getAttribute("aria-expanded")).toBe("true")

    const content = screen.getByTestId("today-focus-technical-content")
    expect(content.textContent).toContain("Марс оппозиция Нептун")
    expect(content.textContent).not.toContain("Transit_")
    expect(content.textContent).not.toContain("Natal_")
  })

  it("invokes onEventSelect when an event row is clicked", () => {
    const onEventSelect = vi.fn()
    const focus = makeFocus()

    render(<TodayFocusCard focus={focus} onSphereSelect={() => {}} onEventSelect={onEventSelect} />)

    const eventButtons = screen.getAllByTestId("today-focus-event")
    expect(eventButtons[0].tagName).toBe("BUTTON")
    expect(eventButtons[0].getAttribute("aria-haspopup")).toBe("dialog")

    fireEvent.click(eventButtons[0])
    expect(onEventSelect).toHaveBeenCalledWith(focus.events![0])
  })
})

describe("TodayFocusCard drilldown and sphere details", () => {
  it("renders 'Почему сегодня' section in SphereDetailsSheet for featured sphere and invokes onFocusOpen on link click", () => {
    const onFocusOpen = vi.fn()
    const onClose = vi.fn()

    const featuredSphere = {
      key: "work",
      relevanceRank: 1,
      state: "convergence_today" as const,
      summary: "На работе важный день для фокуса.",
      action: "Проверь контракт перед ответом.",
      convergenceId: "conv:1",
      sourceEventIds: ["ev:1"],
      sourceActivationIds: ["act-1"],
    }

    const row = {
      key: "work" as const,
      label: "Работа",
      iconName: "briefcase",
      rank: 1,
      verdict: "good" as const,
      confidence: "high" as const,
      text: "Совет для работы",
      evidence: [],
    }

    render(
      <SphereDetailsSheet
        row={row}
        featured={featuredSphere}
        onClose={onClose}
        onFocusOpen={onFocusOpen}
      />,
    )

    const section = screen.getByTestId("sphere-focus-section")
    expect(section.textContent).toContain("Почему сегодня")
    expect(section.textContent).toContain("На работе важный день для фокуса.")
    expect(section.textContent).toContain("Проверь контракт перед ответом.")

    const link = screen.getByTestId("sphere-focus-link")
    fireEvent.click(link)
    expect(onClose).toHaveBeenCalledOnce()
    expect(onFocusOpen).toHaveBeenCalledOnce()
  })

  it("lists event factors and non-event factors with human titles and role badges, never machine keys", () => {
    render(<TodayFocusCard focus={makeFocus()} onSphereSelect={() => {}} />)

    fireEvent.click(screen.getByTestId("today-focus-technical-toggle"))
    const content = screen.getByTestId("today-focus-technical-content")

    const items = screen.getAllByTestId("today-focus-factor-item")
    // 2 events + 2 background factors
    expect(items).toHaveLength(4)

    expect(content.textContent).toContain("Марс оппозиция Нептун")
    expect(content.textContent).toContain("сегодня · точный пик")
    expect(content.textContent).toContain("Венера тригон Нептун")
    expect(content.textContent).toContain("усиливает")
    expect(content.textContent).toContain("Лунар: Плутон на углу (4 дом)")
    expect(content.textContent).toContain("фон")

    // No machine leakage
    expect(content.textContent).not.toContain("transit_to_natal")
    expect(content.textContent).not.toContain("lunar_return")
    expect(content.textContent).not.toContain("(exact)")
  })

  it("handles null occursAt displaying no time string (no fake 00:00)", () => {
    const focus = makeFocus({
      events: [
        {
          id: "ev:nulltime",
          kind: "building",
          occursAt: null,
          localDate: "2026-07-28",
          timezone: "Europe/Moscow",
          precision: "window",
          humanTitle: "Марс в напряжении с твоим Сатурном",
          technicalTitle: "Марс квадратура Сатурн",
          meaning: "Тестовое событие без точного времени.",
          sourceActivationIds: ["act-2"],
        },
      ],
    })

    render(<TodayFocusCard focus={focus} onSphereSelect={() => {}} />)

    const events = screen.getAllByTestId("today-focus-event")
    expect(events[0].textContent).not.toContain("00:00")
    expect(events[0].textContent).not.toContain("весь день")
  })
})
