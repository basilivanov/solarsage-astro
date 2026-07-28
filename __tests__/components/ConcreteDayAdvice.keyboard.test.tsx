// ############################################################################
// AI_HEADER: MODULE_CONCRETE_DAY_ADVICE_NAVIGATOR_TEST
// ROLE: Unit acceptance tests for the controlled sphere navigator.
// ############################################################################
// START_MODULE_CONTRACT: M-TEST-CONCRETE-DAY-ADVICE-NAVIGATOR
// purpose: Prove ConcreteDayAdvice renders single-column rows with aria-haspopup="dialog" and calls onSelectedKeyChange.
// owns:
//   - __tests__/components/ConcreteDayAdvice.keyboard.test.tsx
// inputs: canonical ConcreteAdviceBlock fixture.
// outputs: vitest assertions.
// dependencies: components/today/concrete-day-advice, lib/contracts/today.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - No unsafe casts or TypeScript suppression directives.
//   - Rows have aria-haspopup="dialog" to trigger modal sheet.
//   - Honest verdict status indicator rendered only when assessment is present.
// failure_policy: test failure.
// END_MODULE_CONTRACT: M-TEST-CONCRETE-DAY-ADVICE-NAVIGATOR
// START_MODULE_MAP: M-TEST-CONCRETE-DAY-ADVICE-NAVIGATOR
// public_entrypoints: describe/it blocks.
// semantic_blocks:
//   - ARIA_CONTRACT: aria-haspopup="dialog" linkage.
// owned_tests:
//   - __tests__/components/ConcreteDayAdvice.keyboard.test.tsx
// END_MODULE_MAP: M-TEST-CONCRETE-DAY-ADVICE-NAVIGATOR

import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import React from "react"
import { ConcreteDayAdvice } from "@/components/today/concrete-day-advice"
import type { ConcreteAdviceBlock } from "@/lib/contracts/today"

const keys = [
  "work", "money", "documents", "relationships", "sport", "communication",
  "health", "decisions", "travel", "creativity", "study", "shopping",
] as const

const block: ConcreteAdviceBlock = {
  counts: { good: 3, caution: 7, avoid: 0, neutral: 2 },
  rows: keys.map((key, index) => ({
    key,
    label: `Сфера ${index + 1}`,
    iconName: index % 2 ? "building" : "briefcase",
    rank: index + 1,
    verdict: index % 3 === 0 ? "caution" : index % 3 === 1 ? "good" : "neutral",
    confidence: "medium" as const,
    text: `СЕНТИНЕЛ совет ${index + 1}`,
    evidence: index === 0 ? [{ kind: "activation" as const, title: "raw hidden", technique: "transit_to_natal" }] : [],
  })),
}

function renderNavigator(selectedKey: string | null = null) {
  const onSelectedKeyChange = vi.fn()
  const onWhyOpen = vi.fn()
  const result = render(
    <ConcreteDayAdvice
      concreteAdvice={block}
      selectedKey={selectedKey}
      onSelectedKeyChange={onSelectedKeyChange}
      onWhyOpen={onWhyOpen}
    />,
  )
  return { ...result, onSelectedKeyChange, onWhyOpen }
}

describe("ConcreteDayAdvice human-first navigator", () => {
  it("renders all 12 canonical buttons in adapter order with aria-haspopup='dialog'", () => {
    renderNavigator()
    const allButtons = screen.getAllByTestId("concrete-day-advice-row")
    expect(allButtons).toHaveLength(12)
    expect(allButtons.map((button) => button.getAttribute("data-sphere-key"))).toEqual(keys)

    for (const button of allButtons) {
      expect(button.tagName).toBe("BUTTON")
      expect(button.getAttribute("data-selected")).toBe("false")
      expect(button.getAttribute("aria-haspopup")).toBe("dialog")
    }
  })

  it("invokes onSelectedKeyChange when a sphere row is clicked", () => {
    const { onSelectedKeyChange } = renderNavigator()
    const work = screen.getAllByTestId("concrete-day-advice-row")[0]
    fireEvent.click(work)
    expect(onSelectedKeyChange).toHaveBeenCalledWith("work")
  })

  it("renders honest verdict indicator and data-status ONLY when row.assessment is present", () => {
    const blockWithAssessment: ConcreteAdviceBlock = {
      counts: { good: 1, caution: 0, avoid: 0, neutral: 0 },
      rows: [
        {
          key: "work",
          label: "Работа",
          iconName: "briefcase",
          rank: 1,
          verdict: "good",
          confidence: "high",
          text: "Совет",
          evidence: [],
          assessment: {
            sphere: "work",
            assessment: {
              balance: 1,
              confidence: "high",
              effectiveFactorCount: 1,
              factorCount: 1,
              independentFamilyCount: 1,
              key: "work",
              salienceScore: 5,
              supportScore: 5,
              tensionScore: 0,
              verdict: "good",
              verdictRule: "good_support_1_3x",
            },
          },
        },
        {
          key: "money",
          label: "Деньги",
          iconName: "wallet",
          rank: 2,
          verdict: "caution",
          confidence: "high",
          text: "Совет 2",
          evidence: [],
          // no assessment
        },
      ],
    }

    render(
      <ConcreteDayAdvice
        concreteAdvice={blockWithAssessment}
        selectedKey={null}
        onSelectedKeyChange={vi.fn()}
        onWhyOpen={vi.fn()}
      />,
    )

    const rows = screen.getAllByTestId("concrete-day-advice-row")
    expect(rows[0].getAttribute("data-status")).toBe("good")
    expect(screen.getByTestId("concrete-day-advice-row-status").textContent).toBe("Поддержка")

    expect(rows[1].getAttribute("data-status")).toBeNull()
    expect(screen.queryAllByTestId("concrete-day-advice-row-status")).toHaveLength(1)
  })
})
