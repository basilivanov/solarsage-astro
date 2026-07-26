import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { SynastryPartnerCard } from "@/components/synastry/synastry-partner-card"
import type { SynastryPartnerListItem } from "@/lib/api/synastry"

describe("SynastryPartnerCard", () => {
  const samplePartner: SynastryPartnerListItem = {
    id: "p-1",
    name: "Максим",
    relationType: "romantic",
    birthDate: "1987-09-09",
    precision: "exact",
    score: 89,
    status: "good",
    summary: "Отличная совместимость и понимание.",
    counters: { good: 8, mid: 2, bad: 2 },
    reportState: "ready",
    createdAt: "2026-07-26T12:00:00Z",
  }

  it("renders partner card with score, status pill, summary, and counters", () => {
    const onSelect = vi.fn()
    const onDelete = vi.fn()

    render(
      <SynastryPartnerCard
        partner={samplePartner}
        isBestMatch={true}
        onSelect={onSelect}
        onDelete={onDelete}
      />
    )

    const card = screen.getByTestId("synastry-card")
    expect(card).toBeDefined()
    expect(card.getAttribute("data-status")).toBe("good")

    expect(screen.getByTestId("synastry-best-match-ribbon")).toBeDefined()
    expect(screen.getByText("Максим")).toBeDefined()
    expect(screen.getByText("Романтические отношения")).toBeDefined()
    expect(screen.getByText("89")).toBeDefined()
    expect(screen.getByText("Хорошо подходит")).toBeDefined()
    expect(screen.getByText("8 поддерживают")).toBeDefined()
  })

  it("renders precision note when precision is approximate", () => {
    const approxPartner = { ...samplePartner, precision: "approximate" as const }
    render(
      <SynastryPartnerCard
        partner={approxPartner}
        onSelect={vi.fn()}
        onDelete={vi.fn()}
      />
    )

    expect(screen.getByTestId("synastry-precision-note")).toBeDefined()
    expect(screen.getByText(/без домов партнёра/i)).toBeDefined()
  })

  it("triggers onSelect and onDelete cleanly", () => {
    const onSelect = vi.fn()
    const onDelete = vi.fn()

    render(
      <SynastryPartnerCard
        partner={samplePartner}
        onSelect={onSelect}
        onDelete={onDelete}
      />
    )

    const mainClick = screen.getByTestId("synastry-card-click")
    fireEvent.click(mainClick)
    expect(onSelect).toHaveBeenCalledWith("p-1")

    const deleteBtn = screen.getByTestId("synastry-delete-btn")
    fireEvent.click(deleteBtn)
    expect(onDelete).toHaveBeenCalledWith("p-1")
  })
})
