// ############################################################################
// AI_HEADER: MODULE_ACTIVATION_EVIDENCE_CARD_DOWNSTREAM_TEST
// ROLE: W11 frontend tests for ActivationEvidenceCard using committed fixture
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-ACTIVATION-EVIDENCE-CARD-DOWNSTREAM
// purpose: Prove ActivationEvidenceCard renders evidence from committed W11 fixture.
// owns:
//   - __tests__/components/ActivationEvidenceCard.downstream.test.tsx
// inputs: artifacts/audit/2026-07-08/downstream/11_frontend_fixture.json
// outputs: vitest assertions
// dependencies: ActivationEvidenceCard, validateAdaptedTodayPayload
// side_effects: none
// emitted_logs: none
// invariants: no fabricated activation ids
// failure_policy: test fail
// END_MODULE_CONTRACT: M-TEST-ACTIVATION-EVIDENCE-CARD-DOWNSTREAM

// START_MODULE_MAP: M-TEST-ACTIVATION-EVIDENCE-CARD-DOWNSTREAM
// public_entrypoints: describe/it blocks
// END_MODULE_MAP: M-TEST-ACTIVATION-EVIDENCE-CARD-DOWNSTREAM

import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import React from "react"
import fs from "node:fs"
import path from "node:path"
import { ActivationEvidenceCard } from "@/components/today/activation-evidence-card"
import { validateAdaptedTodayPayload } from "@/lib/contracts/today"

const fixturePath = path.join(
  process.cwd(),
  "artifacts/audit/2026-07-08/downstream/11_frontend_fixture.json",
)

describe("ActivationEvidenceCard downstream fixture", () => {
  it("validates committed fixture and renders evidence text", () => {
    const raw = JSON.parse(fs.readFileSync(fixturePath, "utf8"))
    const payload = validateAdaptedTodayPayload(raw.payload)
    expect(raw.assertions.has_v2).toBe(true)
    expect(payload.v2).toBeTruthy()
    render(<ActivationEvidenceCard v2={payload.v2} />)
    expect(screen.getByTestId("activation-evidence-card")).toBeTruthy()
    const first = payload.v2!.activationEvidence[0]
    expect(first?.id).toBeTruthy()
    expect(screen.getAllByText(first.evidence).length).toBeGreaterThan(0)
  })
})
