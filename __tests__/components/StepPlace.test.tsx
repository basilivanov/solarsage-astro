import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, act } from "@testing-library/react"
import React from "react"

import { StepPlace } from "@/components/onboarding/step-place"

const { mockSearch } = vi.hoisted(() => ({ mockSearch: vi.fn() }))

vi.mock("@/lib/api/cities", () => ({
  searchCitiesAsync: mockSearch,
  getPopularCities: () => [
    { name: "Москва", country: "Россия", lat: 55.7558, lon: 37.6173, timezone: "Europe/Moscow" },
  ],
}))

describe("StepPlace focus behavior", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Element.prototype.scrollIntoView = vi.fn()
  })
  it("focuses the birth city input automatically, not the current city input", () => {
    render(
      <StepPlace
        birthPlace={null}
        currentCity={null}
        sameAsBirth={false}
        onChangeBirthPlace={vi.fn()}
        onChangeCurrentCity={vi.fn()}
        onChangeSameAsBirth={vi.fn()}
        onBack={vi.fn()}
        onNext={vi.fn()}
      />
    )

    const birthField = screen.getByTestId("onboarding-birth-city-field")
    const birthInput = birthField.querySelector('[data-testid="city-picker-input"]')

    expect(document.activeElement).toBe(birthInput)
  })

  it("selects city into birthPlace when typing in the birth city input", async () => {
    const onChangeBirthPlace = vi.fn()
    const onChangeCurrentCity = vi.fn()
    mockSearch.mockResolvedValue([
      { name: "Москва", country: "Россия", lat: 55.7558, lon: 37.6173, timezone: "Europe/Moscow" },
    ])

    render(
      <StepPlace
        birthPlace={null}
        currentCity={null}
        sameAsBirth={false}
        onChangeBirthPlace={onChangeBirthPlace}
        onChangeCurrentCity={onChangeCurrentCity}
        onChangeSameAsBirth={vi.fn()}
        onBack={vi.fn()}
        onNext={vi.fn()}
      />
    )

    const birthField = screen.getByTestId("onboarding-birth-city-field")
    const birthInput = birthField.querySelector('[data-testid="city-picker-input"]') as HTMLInputElement

    fireEvent.focus(birthInput)
    fireEvent.change(birthInput, { target: { value: "Моск" } })

    await act(async () => {
      await new Promise((r) => setTimeout(r, 450))
    })

    const suggestion = birthField.querySelector('[data-testid="city-picker-suggestion"]') as HTMLElement
    fireEvent.click(suggestion)

    expect(onChangeBirthPlace).toHaveBeenCalledTimes(1)
    expect(onChangeBirthPlace.mock.calls[0][0].name).toBe("Москва")
    expect(onChangeCurrentCity).not.toHaveBeenCalled()
  })
})
