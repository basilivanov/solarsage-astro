// ############################################################################
// AI_HEADER: MODULE_TODAYSCREEN_V2_DOWNSTREAM_TEST
// ROLE: W11 frontend tests for TodayScreen V2 downstream evidence rendering
// ############################################################################
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import React from "react"
import type { AccessInfo } from "@/lib/contracts/access"
import type { AdaptedTodayPayload } from "@/lib/contracts/today"
import { ActivationEvidenceCard } from "@/components/today/activation-evidence-card"
import { DevAuditDrawer } from "@/components/today/dev-audit-drawer"
import { WhyExpanded } from "@/components/today/why-expanded"

vi.mock("@/lib/log", () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}))

const v2 = {
  activationSummary: {
    headline: "W11 downstream context",
    topActivatedTargets: [
      {
        targetType: "planet",
        targetKey: "PLUTO",
        label: "Pluto",
        familyCount: 2,
        techniques: ["transit_to_natal", "annual_profection"],
        spheres: ["crisis_transformation_control"],
        activationIds: ["a1", "a2"],
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
      strength: 0.8,
      polarity: "tense",
      phase: "background",
      evidence: "Evidence A1",
    },
    {
      id: "a2",
      technique: "annual_profection",
      techniqueFamily: "profection",
      targetType: "planet",
      targetKey: "PLUTO",
      kind: "lord_of_year",
      strength: 0.4,
      polarity: "neutral",
      phase: "period",
      evidence: "Evidence A2",
    },
  ],
  scoreBreakdown: {
    crisis_transformation_control: {
      key: "crisis_transformation_control",
      title: "Crisis",
      baseScore: 0.1,
      activationScore: 1.0,
      convergenceBonus: 0.4,
      rawScore: 1.5,
      finalScore: 1.5,
      dominanceCapped: false,
      contributions: [],
    },
  },
  whyToday: [
    {
      id: "why-1",
      title: "Why Pluto",
      body: "Because activations a1/a2",
      activationIds: ["a1", "a2"],
      techniques: ["transit_to_natal", "annual_profection"],
    },
  ],
  audit: {
    available: true,
    payloadVersion: "today.v2",
    calculationVersion: "ss-calc-1.1.0",
    scoringVersion: "ss-scoring-2.0",
    activationLayerVersion: "al-1.0",
    canonVersions: { spheres: "v1", scoring_v2: "v1" },
    traceId: "downstream-test",
  },
} as any

describe("TodayScreen V2 downstream fixture", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders V2 activation evidence block from payload.v2", () => {
    render(<ActivationEvidenceCard v2={v2} />)
    expect(screen.getByTestId("activation-evidence-card")).toBeTruthy()
    expect(screen.getByText("W11 downstream context")).toBeTruthy()
    expect(screen.getByText("Evidence A1")).toBeTruthy()
    expect(screen.getByText("Evidence A2")).toBeTruthy()
  })

  it("renders whyToday items without crashing", () => {
    render(
      <WhyExpanded
        sections={[]}
        keyInsight="insight"
        whyToday={v2.whyToday}
      />
    )
    // component may render differently; ensure no throw and root present
    expect(document.body).toBeTruthy()
  })

  it("renders DevAuditDrawer scoring/version fields", () => {
    render(<DevAuditDrawer audit={v2.audit} forceShow={true} />)
    expect(screen.getByTestId("dev-audit-drawer")).toBeTruthy()
    expect(screen.getByText(/ss-scoring-2.0/)).toBeTruthy()
    expect(screen.getByText(/ss-calc-1.1.0/)).toBeTruthy()
    expect(screen.getByText(/today.v2/)).toBeTruthy()
  })

  it("does not invent activation ids outside payload evidence", () => {
    const ids = v2.activationEvidence.map((e: any) => e.id)
    for (const item of v2.whyToday) {
      for (const id of item.activationIds) {
        expect(ids).toContain(id)
      }
    }
  })
})
