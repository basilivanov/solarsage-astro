// ############################################################################
// AI_HEADER: MODULE_ACTIVATION_EVIDENCE_CARD_PERSONAL_TEST
// ROLE: Acceptance tests for the human-first personal story card.
// ############################################################################

import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import React from "react"
import { ActivationEvidenceCard } from "@/components/today/activation-evidence-card"
import type { ConcreteAdviceBlock, TodayV2Block } from "@/lib/contracts/today"

const concreteAdvice: ConcreteAdviceBlock = {
  counts: { good: 1, caution: 2, avoid: 0, neutral: 0 },
  rows: [
    { key: "money", label: "Деньги", iconName: "building", rank: 2, verdict: "caution", confidence: "high", text: "СЕНТИНЕЛ главное из денег", evidence: [] },
    { key: "work", label: "Работа", iconName: "briefcase", rank: 1, verdict: "caution", confidence: "high", text: "СЕНТИНЕЛ главное из работы", evidence: [] },
    { key: "relationships", label: "Отношения", iconName: "sparkle", rank: 3, verdict: "good", confidence: "medium", text: "СЕНТИНЕЛ отношения", evidence: [] },
    { key: "travel", label: "Поездки", iconName: "hourglass", rank: 4, verdict: "neutral", confidence: "low", text: "СЕНТИНЕЛ поездки", evidence: [] },
  ],
}

function makeV2(): TodayV2Block {
  return {
    activationSummary: {
      headline: "Сегодня особенно заметен внутренний конфликт между контролем и необходимостью что-то изменить",
      topActivatedTargets: [],
    },
    activationEvidence: [],
    scoreBreakdown: {},
    whyToday: [],
    audit: { available: false, payloadVersion: "today.v2", calculationVersion: "1", scoringVersion: "2", canonVersions: {} },
  }
}

describe("ActivationEvidenceCard human-first", () => {
  it("returns null without V2", () => {
    const { container } = render(
      <ActivationEvidenceCard v2={null} concreteAdvice={concreteAdvice} onSphereSelect={() => {}} onWhyOpen={() => {}} />,
    )
    expect(container.querySelector('[data-testid="activation-evidence-card"]')).toBeNull()
  })

  it("uses V2 headline, the lowest backend rank, and no more than three affected spheres", () => {
    render(<ActivationEvidenceCard v2={makeV2()} concreteAdvice={concreteAdvice} onSphereSelect={() => {}} onWhyOpen={() => {}} />)
    const card = screen.getByTestId("activation-evidence-card")
    expect(card.getAttribute("data-state")).toBe("ready")
    expect(card.textContent).toContain(makeV2().activationSummary.headline)
    expect(card.textContent).toContain("Главное: СЕНТИНЕЛ главное из работы")
    expect(card.textContent).not.toContain("СЕНТИНЕЛ главное из денег")
    expect(screen.getAllByTestId("personal-story-sphere-link")).toHaveLength(3)
    expect(card.querySelector('[data-testid="technique-chip"]')).toBeNull()
    expect(card.textContent).not.toMatch(/Профекция|Фирдар|Транзит|орб/i)
  })

  it("delegates exact sphere and Why callbacks through real buttons", () => {
    const onSphereSelect = vi.fn()
    const onWhyOpen = vi.fn()
    render(
      <ActivationEvidenceCard
        v2={makeV2()}
        concreteAdvice={concreteAdvice}
        onSphereSelect={onSphereSelect}
        onWhyOpen={onWhyOpen}
      />,
    )
    fireEvent.click(screen.getAllByTestId("personal-story-sphere-link")[0])
    expect(onSphereSelect).toHaveBeenCalledWith("work")
    fireEvent.click(screen.getByTestId("personal-story-why-cta"))
    expect(onWhyOpen).toHaveBeenCalledOnce()
  })

  it("uses only a human-safe V2 headline or an explicitly safe backend fallback", () => {
    const technicalV2 = makeV2()
    technicalV2.activationSummary.headline = "Сходимость транзитов и профекции"
    const callbacks = { onSphereSelect: () => {}, onWhyOpen: () => {} }
    const { rerender } = render(
      <ActivationEvidenceCard
        v2={technicalV2}
        concreteAdvice={concreteAdvice}
        headlineFallback="Безопасный заголовок дня"
        {...callbacks}
      />,
    )
    expect(screen.getByTestId("activation-evidence-card").textContent).toContain("Безопасный заголовок дня")
    expect(screen.getByTestId("activation-evidence-card").textContent).not.toMatch(/транзит|профекци|сходимост/i)

    rerender(
      <ActivationEvidenceCard
        v2={technicalV2}
        concreteAdvice={concreteAdvice}
        headlineFallback="Технический аспект дня"
        {...callbacks}
      />,
    )
    expect(screen.queryByTestId("activation-evidence-card")).toBeNull()
  })
})
