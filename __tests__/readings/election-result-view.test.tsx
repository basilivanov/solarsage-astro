import { describe, it, expect } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import React from "react"
import { ElectionResultView } from "@/components/readings/election/election-result-view"
import type { ElectionResult } from "@/lib/contracts/election"

describe("ElectionResultView v2", () => {
  const sampleResult: ElectionResult = {
    event: "relations:wedding",
    best_days: [
      {
        date: "2026-08-01",
        score: 85,
        label: "great",
        reasons: ["Луна в Тельце — благоприятный знак"],
        moon_sign_ru: "Телец",
        phase_pct: 75,
        voc_intervals: ["10:00-14:00"],
      },
    ],
    avoid_days: [
      {
        date: "2026-08-05",
        score: 10,
        label: "avoid",
        reasons: ["Меркурий ретроградный"],
      },
    ],
    days: [
      {
        date: "2026-08-01",
        score: 85,
        label: "great",
        reasons: ["Луна в Тельце"],
      },
      {
        date: "2026-08-05",
        score: 10,
        label: "avoid",
        reasons: ["Меркурий ретроградный"],
      },
    ],
    facts: {
      event: { category: "relations", sub: "wedding", label: "Свадьба" },
      personal: { natal_moon_sign_ru: "Телец", resonates: true },
    },
    narrative: {
      hero_reason: "Идеальный день для создания союза.",
      hero_personal: "Совпадает с вашей натальной Луной.",
      hero_plain: "Телец отвечает за стабильность.",
      hero_hours: "Лучшие часы: до 14:00 UTC",
      day_notes: [{ date: "2026-08-01", note: "Замечательный выбор." }],
      avoid_notes: [{ date: "2026-08-05", note: "Риск путаницы." }],
    },
  }

  it("renders hero card, best days, avoid days, and window calendar", () => {
    render(<ElectionResultView result={sampleResult} />)

    expect(screen.getByTestId("election-result-view")).toBeTruthy()
    expect(screen.getByTestId("election-hero")).toBeTruthy()
    expect(screen.getByText("Идеальный день для создания союза.")).toBeTruthy()
    expect(screen.getByText("Лучшие часы: до 14:00 UTC")).toBeTruthy()

    expect(screen.getByTestId("election-avoid-day-2026-08-05")).toBeTruthy()
    expect(screen.getByText("Риск путаницы.")).toBeTruthy()

    expect(screen.getByTestId("election-calendar")).toBeTruthy()
    expect(screen.getByTestId("election-calendar-day-2026-08-01")).toBeTruthy()
  })

  it("clicking calendar day shows the day note under the calendar", () => {
    render(<ElectionResultView result={sampleResult} />)

    const dayBtn = screen.getByTestId("election-calendar-day-2026-08-01")
    fireEvent.click(dayBtn)

    expect(screen.getByText("Замечательный выбор.")).toBeTruthy()
  })
})
