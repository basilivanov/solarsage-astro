// ############################################################################
// AI_HEADER: MODULE_ACTIVATION_EVIDENCE_CARD_PERSONAL_TEST
// ROLE: Unit tests for redesigned personal V2 ActivationEvidenceCard
// ############################################################################

import { describe, it, expect } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import React from "react"
import { ActivationEvidenceCard } from "@/components/today/activation-evidence-card"
import type { TodayV2Block } from "@/lib/contracts/today"

function makeV2(overrides: Partial<TodayV2Block> = {}): TodayV2Block {
  return {
    activationSummary: {
      headline:
        "Сегодня особенно заметен внутренний конфликт между контролем и необходимостью что-то изменить",
      topActivatedTargets: [
        {
          targetType: "planet",
          targetKey: "PLUTO",
          label: "Плутон",
          familyCount: 3,
          techniques: ["transit_to_natal", "annual_profection", "firdar_major"],
          spheres: [
            "crisis_transformation_control",
            "money_security_resources",
            "inner_background_unconscious",
          ],
          activationIds: ["a1", "a2", "a3", "a4"],
        },
      ],
    },
    activationEvidence: [
      {
        id: "a1",
        technique: "transit_to_natal",
        techniqueFamily: "transit",
        targetType: "planet",
        targetKey: "PLUTO",
        kind: "aspect",
        active: true,
        sourcePlanet: "Moon",
        targetPlanet: "Pluto",
        aspect: "opposition",
        orb: 1.05,
        phase: "separating",
        polarity: "tense",
        strength: 0.72,
        evidence: "Transit Moon opposition natal Pluto raw english",
        debug: { secret: true },
      },
      {
        id: "a2",
        technique: "transit_to_natal",
        techniqueFamily: "transit",
        targetType: "planet",
        targetKey: "SATURN",
        kind: "aspect",
        active: true,
        sourcePlanet: "Pluto",
        targetPlanet: "Saturn",
        aspect: "trine",
        orb: 0.01,
        phase: "exact",
        polarity: "supportive",
        strength: 0.8,
        evidence: "Pluto trine natal Saturn",
        debug: {},
      },
      {
        id: "a3",
        technique: "annual_profection",
        techniqueFamily: "profection",
        targetType: "planet",
        targetKey: "PLUTO",
        kind: "period",
        active: true,
        phase: "period",
        polarity: "mixed",
        strength: 0.6,
        evidence: "Annual profection",
        debug: {},
      },
      {
        id: "a4",
        technique: "firdar_major",
        techniqueFamily: "firdar",
        targetType: "planet",
        targetKey: "PLUTO",
        kind: "period",
        active: true,
        phase: "period",
        polarity: "neutral",
        strength: 0.5,
        evidence: "Firdar major",
        debug: {},
      },
    ],
    scoreBreakdown: {},
    whyToday: [],
    audit: {
      available: false,
      payloadVersion: "today.v2",
      calculationVersion: "ss-calc-1.1.0",
      scoringVersion: "ss-scoring-2.0",
      canonVersions: {},
    },
    ...overrides,
  }
}

describe("ActivationEvidenceCard personal V2", () => {
  it("returns null when v2 is null", () => {
    const { container } = render(<ActivationEvidenceCard v2={null} />)
    expect(container.querySelector('[data-testid="activation-evidence-card"]')).toBeNull()
  })

  it("does not claim multi-cycle convergence for familyCount=1", () => {
    const v2 = makeV2()
    v2.activationSummary.topActivatedTargets[0].familyCount = 1
    render(<ActivationEvidenceCard v2={v2} />)
    const card = screen.getByTestId("activation-evidence-card")
    expect(card.textContent).not.toMatch(/СХОДИМОСТЬ/i)
    expect(card.textContent).not.toMatch(/НЕЗАВИСИМЫХ ЦИКЛА/i)
    expect(card.textContent).toMatch(/ПЕРСОНАЛЬНЫЙ ТРАНЗИТ ДНЯ/i)
  })

  it("toggles aria-expanded and shows at most three evidence items", () => {
    render(<ActivationEvidenceCard v2={makeV2()} />)
    const toggle = screen.getByTestId("activation-evidence-toggle")
    expect(toggle.getAttribute("aria-expanded")).toBe("false")
    fireEvent.click(toggle)
    expect(toggle.getAttribute("aria-expanded")).toBe("true")
    const items = screen.getAllByTestId("activation-evidence-item")
    expect(items.length).toBeLessThanOrEqual(3)
    expect(items.length).toBe(3)
  })

  it("does not expose raw English evidence, debug JSON, or raw strength", () => {
    render(<ActivationEvidenceCard v2={makeV2()} />)
    fireEvent.click(screen.getByTestId("activation-evidence-toggle"))
    const card = screen.getByTestId("activation-evidence-card")
    const text = card.textContent || ""
    expect(text).not.toContain("Transit Moon opposition natal Pluto raw english")
    expect(text).not.toContain('"secret"')
    expect(text).not.toMatch(/\b0\.72\b/)
    expect(text).not.toMatch(/source_frame|target_frame/i)
    expect(text).toContain("Луна")
    expect(text).toContain("оппозиция")
    expect(text).toContain("Плутону")
    expect(text).not.toMatch(/натальному Плутон(?:\s|$)/)
  })
})
