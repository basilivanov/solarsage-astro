// ############################################################################
// AI_HEADER: MODULE_TEST_DAY_SUMMARY_CARD
// ROLE: Vitest unit tests for DaySummaryCard, DayZoneIndicator, and top spheres rotation.
// DEPENDENCIES: vitest, @testing-library/react, @testing-library/jest-dom, components/today/day-summary-card
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-DAY-SUMMARY-CARD
// purpose: Test DaySummaryCard relative day status label fallback, zone indicator rendering, and top spheres.
// owns:
//   - __tests__/today/day-summary-card.test.tsx
// inputs: mock props
// outputs: test assertions
// dependencies: components/today/day-summary-card, lib/api/day
// side_effects: none
// emitted_logs: none
// failure_policy: fails test on rendering mismatches
// END_MODULE_CONTRACT: M-TEST-DAY-SUMMARY-CARD

// START_MODULE_MAP: M-TEST-DAY-SUMMARY-CARD
// public_entrypoints:
//   - day summary card tests
// semantic_blocks: none
// owned_tests:
//   - __tests__/today/day-summary-card.test.tsx
// END_MODULE_MAP: M-TEST-DAY-SUMMARY-CARD

import React from "react"
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { DaySummaryCard } from "@/components/today/day-summary-card"
import type { RelativeDayStatus } from "@/lib/api/day"

describe("DaySummaryCard & Relative Day Status UI", () => {
  const dummyDate = new Date(2026, 6, 27)
  const defaultSummary = {
    statusLabel: "Ровный день",
    statusLine: "Спокойное гармоничное течение дня.",
    facts: [],
  }

  it("renders default status label when relativeStatus is missing (fallback)", () => {
    render(
      <DaySummaryCard
        date={dummyDate}
        dayStatus="steady"
        daySummary={defaultSummary}
      />
    )

    expect(screen.getByTestId("day-summary-card")).toBeDefined()
    expect(screen.getByText("Ровный день")).toBeDefined()
    expect(screen.queryByTestId("day-zone-indicator")).toBeNull()
  })

  it("renders relative status label and zone indicator when relativeStatus mode is relative and days >= 5", () => {
    const relativeStatus: RelativeDayStatus = {
      mode: "relative",
      status: "softer",
      label: "Легче, чем обычно",
      zSupport: 1.2,
      zTension: -0.4,
      supportBand: [40, 70],
      tensionBand: [10, 30],
      supportMarker: 0.8,
      tensionMarker: 0.2,
      baseline: {
        supportMean: 50,
        supportStd: 10,
        tensionMean: 20,
        tensionStd: 5,
        days: 10,
      },
    }

    render(
      <DaySummaryCard
        date={dummyDate}
        dayStatus="supportive"
        daySummary={defaultSummary}
        relativeStatus={relativeStatus}
      />
    )

    const labels = screen.getAllByText("Легче, чем обычно")
    expect(labels.length).toBeGreaterThan(0)
    expect(screen.getByTestId("day-zone-indicator")).toBeDefined()
    expect(screen.getByTestId("day-zone-label").textContent).toContain("Ваша обычная зона")
  })

  it("hides zone indicator when baseline days < 5 (cold start)", () => {
    const coldStartStatus: RelativeDayStatus = {
      mode: "absolute",
      status: "usual",
      label: "Обычный день",
      zSupport: 0,
      zTension: 0,
      supportBand: [0, 100],
      tensionBand: [0, 100],
      supportMarker: 0.5,
      tensionMarker: 0.5,
      baseline: {
        supportMean: 0,
        supportStd: 0.5,
        tensionMean: 0,
        tensionStd: 0.5,
        days: 3,
      },
    }

    render(
      <DaySummaryCard
        date={dummyDate}
        dayStatus="steady"
        daySummary={defaultSummary}
        relativeStatus={coldStartStatus}
      />
    )

    expect(screen.queryByTestId("day-zone-indicator")).toBeNull()
  })

  it("renders top 2 accent spheres (day-top-spheres)", () => {
    const sphereScores = [
      { key: "work", title: "Работа и карьеры", score: 85 },
      { key: "money", title: "Финансы", score: 92 },
      { key: "health", title: "Здоровье", score: 45 },
    ]

    render(
      <DaySummaryCard
        date={dummyDate}
        dayStatus="steady"
        daySummary={defaultSummary}
        sphereScores={sphereScores}
      />
    )

    const topSpheresEl = screen.getByTestId("day-top-spheres")
    expect(topSpheresEl).toBeDefined()
    expect(topSpheresEl.textContent).toContain("Тянет сегодня: Финансы, Работа и карьеры")
  })
})
