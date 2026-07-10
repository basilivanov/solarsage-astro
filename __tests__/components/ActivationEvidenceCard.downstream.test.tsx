// ############################################################################
// AI_HEADER: MODULE_ACTIVATION_EVIDENCE_CARD_DOWNSTREAM_TEST
// ROLE: W11 frontend tests for ActivationEvidenceCard using committed fixture
// ############################################################################

import { describe, it, expect } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import React from "react"
import fs from "node:fs"
import path from "node:path"
import { ActivationEvidenceCard } from "@/components/today/activation-evidence-card"
import { validateAdaptedTodayPayload } from "@/lib/contracts/today"
import { formatActivationEvidenceTitle, getTechniqueLabel } from "@/lib/presentation/today-v2"

const fixturePath = path.join(
  process.cwd(),
  "artifacts/audit/2026-07-08/downstream/11_frontend_fixture.json",
)

describe("ActivationEvidenceCard downstream fixture", () => {
  it("validates committed fixture and renders headline, techniques, expanded human evidence", () => {
    const raw = JSON.parse(fs.readFileSync(fixturePath, "utf8"))
    const payload = validateAdaptedTodayPayload(raw.payload)
    expect(raw.assertions.has_v2).toBe(true)
    expect(payload.v2).toBeTruthy()
    render(<ActivationEvidenceCard v2={payload.v2} />)
    expect(screen.getByTestId("activation-evidence-card")).toBeTruthy()

    const headline = payload.v2!.activationSummary.headline
    expect(screen.getAllByText(headline).length).toBeGreaterThan(0)

    const top = payload.v2!.activationSummary.topActivatedTargets[0]
    expect(top).toBeTruthy()
    expect(screen.getAllByTestId("technique-chip").length).toBeGreaterThan(0)
    for (const tech of top.techniques.slice(0, 3)) {
      const chips = screen.getAllByTestId("technique-chip")
      const match = chips.some(
        (el) =>
          el.getAttribute("title") === tech ||
          el.textContent?.includes(getTechniqueLabel(tech)),
      )
      expect(match).toBe(true)
    }

    fireEvent.click(screen.getByTestId("activation-evidence-toggle"))
    const first = payload.v2!.activationEvidence[0]
    const human = formatActivationEvidenceTitle(first)
    expect(screen.getAllByText(human).length).toBeGreaterThan(0)
  })
})
