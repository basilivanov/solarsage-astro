// ############################################################################
// AI_HEADER: MODULE_CONCRETE_DAY_ADVICE_NAVIGATOR_TEST
// ROLE: Unit acceptance tests for the controlled 12-sphere navigator.
// ############################################################################

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
  it("renders all 12 canonical buttons without a list expander or technical chips", () => {
    renderNavigator()
    const buttons = screen.getAllByTestId("concrete-day-advice-row")
    expect(buttons).toHaveLength(12)
    expect(buttons.map((button) => button.getAttribute("data-sphere-key"))).toEqual(keys)
    expect(screen.getByTestId("concrete-day-advice").textContent).not.toMatch(/Показать ещё|все 12 сфер|Транзит/i)
    for (const button of buttons) {
      expect(button.tagName).toBe("BUTTON")
      expect(button.getAttribute("data-status")).toBeTruthy()
      expect(button.getAttribute("data-selected")).toBe("false")
      expect(button.getAttribute("aria-expanded")).toBe("false")
      expect(button.getAttribute("aria-controls")).toBeTruthy()
    }
  })

  it("selects a single sphere, puts details after its two-button row, and keeps row text exact", () => {
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

    const documentButton = screen.getAllByTestId("concrete-day-advice-row")[2]
    expect(work.compareDocumentPosition(details) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(details.compareDocumentPosition(documentButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
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
