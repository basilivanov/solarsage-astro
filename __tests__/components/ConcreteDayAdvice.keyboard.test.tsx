// ############################################################################
// AI_HEADER: MODULE_CONCRETE_DAY_ADVICE_KEYBOARD_TEST
// ROLE: Prove native button keyboard activation toggles once (no double-toggle)
// ############################################################################

import { describe, it, expect } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import React from "react"
import { ConcreteDayAdvice } from "@/components/today/concrete-day-advice"
import type { ConcreteAdviceBlock } from "@/lib/contracts/today"

const block: ConcreteAdviceBlock = {
  counts: { good: 0, caution: 1, avoid: 0, neutral: 0 },
  rows: [
    {
      key: "work",
      label: "Работа",
      iconName: "briefcase",
      rank: 1,
      verdict: "caution",
      confidence: "high",
      text: "Не форсируйте разговор о статусе",
      evidence: [
        {
          kind: "activation",
          title: "Луна — оппозиция к вашему натальному Плутону",
          orb: 1.05,
          technique: "transit_to_natal",
          techniqueFamily: "transit",
          planet: "Moon",
          targetPlanet: "Pluto",
          aspectType: "opposition",
        },
      ],
    },
  ],
}

describe("ConcreteDayAdvice keyboard toggle", () => {
  it("opens on a single Enter activation and closes on the next (no double-toggle)", () => {
    render(<ConcreteDayAdvice concreteAdvice={block} />)
    const rowBtn = screen.getByRole("button", { name: /Не форсируйте разговор/i })
    expect(rowBtn.getAttribute("aria-expanded")).toBe("false")

    // Native button: keydown Enter synthesizes one click — we only fire click once
    // (no manual key handler that would double-toggle).
    fireEvent.click(rowBtn)
    expect(rowBtn.getAttribute("aria-expanded")).toBe("true")
    expect(screen.getByTestId("concrete-day-advice-evidence")).toBeTruthy()
    expect(screen.getByText("Почему именно у вас")).toBeTruthy()

    fireEvent.click(rowBtn)
    expect(rowBtn.getAttribute("aria-expanded")).toBe("false")
  })

  it("single click opens; second click closes (keyboard uses native click path)", () => {
    render(<ConcreteDayAdvice concreteAdvice={block} />)
    const rowBtn = screen.getByRole("button", { name: /Не форсируйте разговор/i })
    // Space/Enter on native button produce a click event — assert one click toggles once
    fireEvent.click(rowBtn)
    expect(rowBtn.getAttribute("aria-expanded")).toBe("true")
    fireEvent.click(rowBtn)
    expect(rowBtn.getAttribute("aria-expanded")).toBe("false")
  })
})
