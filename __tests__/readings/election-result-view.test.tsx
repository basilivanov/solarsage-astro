import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import React from "react"
import { ElectionResultView } from "@/components/readings/election/election-result-view"
import type { ElectionResult } from "@/lib/contracts/election"

describe("ElectionResultView", () => {
  const sampleResult: ElectionResult = {
    event: "wedding",
    best_days: [
      {
        date: "2026-08-01",
        score: 85,
        label: "great",
        reasons: ["Луна в Тельце — благоприятный знак", "Луна растущая"],
      },
    ],
    avoid_days: [
      {
        date: "2026-08-05",
        score: 10,
        label: "avoid",
        reasons: ["Луна в Скорпионе", "Меркурий ретроградный"],
      },
    ],
  }

  it("renders best and avoid days with labels and reasons", () => {
    render(<ElectionResultView result={sampleResult} />)

    expect(screen.getByTestId("election-result-view")).toBeTruthy()
    expect(screen.getByTestId("election-best-day-2026-08-01")).toBeTruthy()
    expect(screen.getByText("Отличный день")).toBeTruthy()
    expect(screen.getByText("Луна в Тельце — благоприятный знак")).toBeTruthy()

    expect(screen.getByTestId("election-avoid-day-2026-08-05")).toBeTruthy()
    expect(screen.getByText("Не рекомендуется")).toBeTruthy()
    expect(screen.getByText("Меркурий ретроградный")).toBeTruthy()
  })
})
