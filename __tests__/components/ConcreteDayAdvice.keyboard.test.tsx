// ############################################################################
// AI_HEADER: MODULE_CONCRETE_DAY_ADVICE_NAVIGATOR_TEST
// ROLE: Unit acceptance tests for the controlled sphere navigator.
// ############################################################################
// START_MODULE_CONTRACT: M-TEST-CONCRETE-DAY-ADVICE-NAVIGATOR
// purpose: Prove ConcreteDayAdvice renders single-column top-3 rows with expansion, details panel, aria-expanded/controls, and guidance text.
// owns:
//   - __tests__/components/ConcreteDayAdvice.keyboard.test.tsx
// inputs: canonical ConcreteAdviceBlock fixture.
// outputs: vitest assertions.
// dependencies: components/today/concrete-day-advice, lib/contracts/today.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - No unsafe casts or TypeScript suppression directives.
//   - Top-3 rows rendered initially; show-all expands to all.
//   - Verdict badges and data-status are omitted.
// failure_policy: test failure.
// END_MODULE_CONTRACT: M-TEST-CONCRETE-DAY-ADVICE-NAVIGATOR
// START_MODULE_MAP: M-TEST-CONCRETE-DAY-ADVICE-NAVIGATOR
// public_entrypoints: describe/it blocks.
// semantic_blocks:
//   - ARIA_CONTRACT: aria-expanded/controls/id linkage.
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
  it("renders top 3 canonical buttons initially and expands to all 12 on show-all click", () => {
    renderNavigator()
    const initialButtons = screen.getAllByTestId("concrete-day-advice-row")
    expect(initialButtons).toHaveLength(3)

    const showAllBtn = screen.getByTestId("concrete-day-advice-show-all")
    expect(showAllBtn.textContent).toContain("Все 12 сфер")

    fireEvent.click(showAllBtn)
    const allButtons = screen.getAllByTestId("concrete-day-advice-row")
    expect(allButtons).toHaveLength(12)
    expect(allButtons.map((button) => button.getAttribute("data-sphere-key"))).toEqual(keys)

    for (const button of allButtons) {
      expect(button.tagName).toBe("BUTTON")
      expect(button.getAttribute("data-selected")).toBe("false")
      expect(button.getAttribute("aria-expanded")).toBe("false")
      expect(button.getAttribute("aria-controls")).toBeTruthy()
    }
  })

  it("selects a single sphere, puts details after its row, and keeps guidance text exact", () => {
    const { rerender, onSelectedKeyChange, onWhyOpen } = renderNavigator()
    const work = screen.getAllByTestId("concrete-day-advice-row")[0]
    fireEvent.click(work)
    expect(onSelectedKeyChange).toHaveBeenCalledWith("work")

    rerender(
      <ConcreteDayAdvice concreteAdvice={block} selectedKey="work" onSelectedKeyChange={onSelectedKeyChange} onWhyOpen={onWhyOpen} />,
    )
    const details = screen.getByTestId("concrete-day-advice-details")
    expect(details.getAttribute("data-sphere-key")).toBe("work")
    expect(details.textContent).toContain("СЕНТИНЕЛ совет 1")
    expect(details.textContent).not.toMatch(/Транзит|орб|raw hidden/i)
    expect(screen.getAllByTestId("concrete-day-advice-details")).toHaveLength(1)

    fireEvent.click(screen.getByTestId("sphere-why-cta"))
    expect(onWhyOpen).toHaveBeenCalledOnce()
  })

  it("uses native button activation without a double-toggle path", () => {
    const { onSelectedKeyChange } = renderNavigator("work")
    const work = screen.getAllByTestId("concrete-day-advice-row")[0]
    expect(work.getAttribute("aria-expanded")).toBe("true")
    fireEvent.click(work)
    expect(onSelectedKeyChange).toHaveBeenCalledTimes(1)
    expect(onSelectedKeyChange).toHaveBeenLastCalledWith(null)
  })
})
