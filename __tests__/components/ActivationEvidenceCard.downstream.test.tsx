// ############################################################################
// AI_HEADER: MODULE_ACTIVATION_EVIDENCE_CARD_DOWNSTREAM_TEST
// ROLE: W11 frontend tests for ActivationEvidenceCard using committed fixture
// ############################################################################

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
  it("validates committed fixture and renders the human-first headline and ranked areas", () => {
    const raw = JSON.parse(fs.readFileSync(fixturePath, "utf8"))
    const payload = validateAdaptedTodayPayload(raw.payload)
    expect(raw.assertions.has_v2).toBe(true)
    expect(payload.v2).toBeTruthy()
    render(
      <ActivationEvidenceCard
        v2={payload.v2}
        concreteAdvice={payload.concreteAdvice}
        headlineFallback={payload.headline}
        onSphereSelect={() => {}}
        onWhyOpen={() => {}}
      />,
    )
    expect(screen.getByTestId("activation-evidence-card")).toBeTruthy()

    expect(screen.getByTestId("activation-evidence-card").textContent).toContain(payload.headline)

    const expectedAreaCount = Math.min(payload.concreteAdvice.rows.length, 3)
    expect(screen.queryAllByTestId("personal-story-sphere-link")).toHaveLength(expectedAreaCount)
    expect(screen.queryByTestId("technique-chip")).toBeNull()
    expect(screen.getByTestId("activation-evidence-card").querySelector('[data-testid="technique-chip"]')).toBeNull()
    expect(screen.getByTestId("activation-evidence-card").textContent).not.toMatch(/Профекция|Фирдар|Транзит|орб|сходимост|техник/i)
  })
})
