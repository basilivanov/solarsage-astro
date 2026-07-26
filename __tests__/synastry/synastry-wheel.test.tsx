import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { SynastryWheel } from "@/components/synastry/synastry-wheel"
import type { SynastryAspectItem, SynastryPlanetPoint } from "@/lib/api/synastry"

describe("SynastryWheel", () => {
  const sampleOwnerPlanets: SynastryPlanetPoint[] = [
    {
      id: "owner_sun",
      owner: "user",
      planet: "Sun",
      longitude: 120.0,
      sign: "Leo",
      retrograde: false,
      house: null,
      houseReliable: false,
    },
  ]

  const samplePartnerPlanets: SynastryPlanetPoint[] = [
    {
      id: "partner_moon",
      owner: "partner",
      planet: "Moon",
      longitude: 0.0,
      sign: "Aries",
      retrograde: false,
      house: 5,
      houseReliable: true,
    },
  ]

  const sampleAspects: SynastryAspectItem[] = [
    {
      id: "sun_trine_moon",
      title: "Солнце трин Луна",
      tone: "good",
      score: 90,
      description: "Гармония",
      techSignature: "Sun trine Moon",
      ownerPlanetKey: "owner_sun",
      partnerPlanetKey: "partner_moon",
      aspectSymbol: "△",
      orbDegrees: 1.0,
      orbLabel: "1°00′",
    },
  ]

  it("renders fluid SVG wheel with role=img and planet nodes", () => {
    const onPlanetSelect = vi.fn()
    const onAspectSelect = vi.fn()
    const onAspectOpen = vi.fn()

    render(
      <SynastryWheel
        ownerPlanets={sampleOwnerPlanets}
        partnerPlanets={samplePartnerPlanets}
        aspects={sampleAspects}
        precision="exact"
        partnerName="Максим"
        selection={{ selectedPlanetId: null, selectedAspectId: null }}
        onPlanetSelect={onPlanetSelect}
        onAspectSelect={onAspectSelect}
        onAspectOpen={onAspectOpen}
      />
    )

    const svg = screen.getByRole("img", { name: /Карта взаимодействия с Максим/i })
    expect(svg).toBeDefined()

    const ownerPlanetBtn = screen.getByRole("button", { name: /Твоё Солнце в Льве/i })
    expect(ownerPlanetBtn).toBeDefined()

    const partnerPlanetBtn = screen.getByRole("button", { name: /Луна партнёра в Овне/i })
    expect(partnerPlanetBtn).toBeDefined()
  })

  it("selecting a planet node calls onPlanetSelect", () => {
    const onPlanetSelect = vi.fn()

    render(
      <SynastryWheel
        ownerPlanets={sampleOwnerPlanets}
        partnerPlanets={samplePartnerPlanets}
        aspects={sampleAspects}
        precision="exact"
        partnerName="Максим"
        selection={{ selectedPlanetId: null, selectedAspectId: null }}
        onPlanetSelect={onPlanetSelect}
        onAspectSelect={vi.fn()}
        onAspectOpen={vi.fn()}
      />
    )

    const ownerPlanetBtn = screen.getByRole("button", { name: /Твоё Солнце в Льве/i })
    fireEvent.click(ownerPlanetBtn)

    expect(onPlanetSelect).toHaveBeenCalledWith("owner_sun")
  })

  it("renders animated planet popover when a planet is selected", () => {
    render(
      <SynastryWheel
        ownerPlanets={sampleOwnerPlanets}
        partnerPlanets={samplePartnerPlanets}
        aspects={sampleAspects}
        precision="exact"
        partnerName="Максим"
        selection={{ selectedPlanetId: "owner_sun", selectedAspectId: null }}
        onPlanetSelect={vi.fn()}
        onAspectSelect={vi.fn()}
        onAspectOpen={vi.fn()}
      />
    )

    const popover = screen.getByTestId("synastry-planet-popover")
    expect(popover).toBeDefined()
    expect(screen.getByText(/Твоё Солнце/i)).toBeDefined()
    expect(screen.getByText(/Ядро личности/i)).toBeDefined()
  })

  it("selecting an aspect line calls onAspectSelect and onAspectOpen to trigger drilldown modal", () => {
    const onAspectSelect = vi.fn()
    const onAspectOpen = vi.fn()

    render(
      <SynastryWheel
        ownerPlanets={sampleOwnerPlanets}
        partnerPlanets={samplePartnerPlanets}
        aspects={sampleAspects}
        precision="exact"
        partnerName="Максим"
        selection={{ selectedPlanetId: null, selectedAspectId: null }}
        onPlanetSelect={vi.fn()}
        onAspectSelect={onAspectSelect}
        onAspectOpen={onAspectOpen}
      />
    )

    const aspectBtn = screen.getByRole("button", { name: /Солнце.*Луна/i })
    fireEvent.click(aspectBtn)

    expect(onAspectSelect).toHaveBeenCalledWith("sun_trine_moon")
    expect(onAspectOpen).toHaveBeenCalledWith("sun_trine_moon")
  })
})
