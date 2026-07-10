// ############################################################################
// AI_HEADER: MODULE_ACTIVATION_EVIDENCE_CARD_DOWNSTREAM_TEST
// ROLE: W11 frontend tests for ActivationEvidenceCard downstream fixture rendering
// ############################################################################
import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import React from "react"
import { ActivationEvidenceCard } from "@/components/today/activation-evidence-card"
import type { TodayV2Block } from "@/lib/contracts/today"

const v2Fixture: TodayV2Block = {
  activationSummary: {
    headline: "Downstream fixture headline",
    topActivatedTargets: [
      {
        targetType: "planet",
        targetKey: "PLUTO",
        label: "Pluto",
        familyCount: 1,
        techniques: ["transit_to_natal"],
        spheres: ["crisis_transformation_control"],
        activationIds: ["t2n__MOON__PLUTO"],
      },
    ],
  },
  activationEvidence: [
    {
      id: "t2n__MOON__PLUTO",
      technique: "transit_to_natal",
      techniqueFamily: "transit",
      targetType: "planet",
      targetKey: "PLUTO",
      kind: "aspect",
      strength: 0.8,
      polarity: "tense",
      phase: "background",
      evidence: "Transit Moon square natal Pluto",
    } as any,
  ],
  scoreBreakdown: {},
  whyToday: [
    {
      id: "why-1",
      title: "Why today",
      body: "body",
      activationIds: ["t2n__MOON__PLUTO"],
      techniques: ["transit_to_natal"],
    } as any,
  ],
  audit: {
    available: true,
    payloadVersion: "today.v2",
    calculationVersion: "ss-calc-1.1.0",
    scoringVersion: "ss-scoring-2.0",
    activationLayerVersion: "al-1.0",
    canonVersions: { spheres: "v1" },
  } as any,
}

describe("ActivationEvidenceCard downstream", () => {
  it("renders technique targets and evidence text from fixture", () => {
    render(<ActivationEvidenceCard v2={v2Fixture} />)
    expect(screen.getByTestId("activation-evidence-card")).toBeTruthy()
    expect(screen.getByText("Downstream fixture headline")).toBeTruthy()
    expect(screen.getByText("Pluto")).toBeTruthy()
    expect(screen.getByText("Transit Moon square natal Pluto")).toBeTruthy()
  })

  it("does not fabricate activation evidence when v2 is null", () => {
    const { container } = render(<ActivationEvidenceCard v2={null} />)
    expect(container.querySelector('[data-testid="activation-evidence-card"]')).toBeNull()
  })
})
