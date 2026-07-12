// ############################################################################
// AI_HEADER: MODULE_CONCRETE_DAY_ADVICE_NAVIGATOR_TEST
// ROLE: Unit acceptance tests for the controlled 12-sphere navigator.
// ############################################################################
// START_MODULE_CONTRACT: M-TEST-CONCRETE-DAY-ADVICE-NAVIGATOR
// purpose: Prove ConcreteDayAdvice renders all 12 native buttons, verdict labels,
//   details panel, aria-expanded/controls, and exact compact/details copy.
// owns:
//   - __tests__/components/ConcreteDayAdvice.keyboard.test.tsx
// inputs: canonical ConcreteAdviceBlock fixture.
// outputs: vitest assertions.
// dependencies: components/today/concrete-day-advice, lib/contracts/today.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - No unsafe casts or TypeScript suppression directives.
//   - All verdict keys are valid generated sphere enum members.
//   - data-status stays exact good|caution|avoid|neutral.
// failure_policy: test failure.
// END_MODULE_CONTRACT: M-TEST-CONCRETE-DAY-ADVICE-NAVIGATOR
// START_MODULE_MAP: M-TEST-CONCRETE-DAY-ADVICE-NAVIGATOR
// public_entrypoints: describe/it blocks.
// semantic_blocks:
//   - VERDICT_COPY_MATRIX: proves exact compact and details copy for all 4 verdicts.
//   - ARIA_CONTRACT: aria-expanded/controls/id linkage.
// owned_tests:
//   - __tests__/components/ConcreteDayAdvice.keyboard.test.tsx
// END_MODULE_MAP: M-TEST-CONCRETE-DAY-ADVICE-NAVIGATOR

import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import React from "react"
import { ConcreteDayAdvice } from "@/components/today/concrete-day-advice"
import type { ConcreteAdviceBlock } from "@/lib/contracts/today"

function requireElement<T extends Element>(value: T | null | undefined, label: string): T {
  if (!value) throw new Error(`${label} is missing`)
  return value
}

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

  it("proves all 4 verdict compact + details copy, aria expanded/controls, details data-status unchanged", () => {
    const verdicts = ["good", "caution", "avoid", "neutral"] as const
    const keyByVerdict = { good: "work" as const, caution: "money" as const, avoid: "health" as const, neutral: "relationships" as const }
    const labelByVerdict: Record<string, string> = { good: "Работа", caution: "Деньги", avoid: "Здоровье", neutral: "Отношения" }
    const expectedCompact: Record<string, string> = { good: "Поддерживает", caution: "Требует внимания", avoid: "Лучше отложить", neutral: "Ровный фон" }
    const expectedDetails: Record<string, string> = { good: "Поддерживающий сигнал", caution: "Напряжённый сигнал · требует внимания", avoid: "Сильное напряжение · лучше отложить", neutral: "Нейтральный сигнал" }

    const testBlock: ConcreteAdviceBlock = {
      counts: { good: 1, caution: 1, avoid: 1, neutral: 1 },
      rows: verdicts.map((v) => ({
        key: keyByVerdict[v], label: labelByVerdict[v], iconName: "briefcase",
        rank: 1, verdict: v, confidence: "high" as const, text: `text-${v}`, evidence: [],
      })),
    }

    const onSelect = vi.fn()
    const { rerender } = render(
      <ConcreteDayAdvice concreteAdvice={testBlock} selectedKey={null} onSelectedKeyChange={onSelect} onWhyOpen={vi.fn()} />,
    )

    for (const verdict of verdicts) {
      const rows = screen.getAllByTestId("concrete-day-advice-row")
      const row = requireElement(rows.find((r) => r.getAttribute("data-status") === verdict), `row ${verdict}`)
      const statusBefore = row.getAttribute("data-status")

      // compact copy
      const statusEl = row.querySelector("[data-testid='concrete-day-advice-row-status']")
      expect(statusEl?.textContent).toBe(expectedCompact[verdict])

      // click to select
      fireEvent.click(row)
      expect(onSelect).toHaveBeenCalledWith(keyByVerdict[verdict])
      onSelect.mockClear()

      // rerender with selectedKey
      rerender(
        <ConcreteDayAdvice concreteAdvice={testBlock} selectedKey={keyByVerdict[verdict]} onSelectedKeyChange={onSelect} onWhyOpen={vi.fn()} />,
      )
      const updatedRows = screen.getAllByTestId("concrete-day-advice-row")
      const selectedRow = requireElement(updatedRows.find((r) => r.getAttribute("data-status") === verdict), `selected row ${verdict}`)
      const details = screen.getByTestId("concrete-day-advice-details")

      expect(selectedRow.getAttribute("aria-expanded")).toBe("true")
      expect(selectedRow.getAttribute("aria-controls")).toBe(details.getAttribute("id"))
      expect(selectedRow.getAttribute("data-status")).toBe(statusBefore)
      expect(details.getAttribute("data-sphere-key")).toBe(keyByVerdict[verdict])
      expect(details.getAttribute("data-status")).toBe(verdict)
      expect(details.textContent).toContain(expectedDetails[verdict])
      expect(details.textContent).toContain(`text-${verdict}`)
    }
  })
})
