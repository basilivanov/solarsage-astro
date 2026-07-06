import { beforeAll, describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import type { City } from "@/lib/contracts/city"

vi.mock("@/components/onboarding/city-picker", () => ({
  CityPicker: ({
    value,
    onChange,
  }: {
    value: City | null
    onChange: (_city: City | null) => void
  }) => (
    <div>
      <div data-testid="city-picker-value">
        {value ? `${value.name}|${value.country}` : "none"}
      </div>
      <button
        type="button"
        onClick={() =>
          onChange({
            name: "Berlin",
            country: "Germany",
            lat: 52.52,
            lon: 13.405,
            timezone: "Europe/Berlin",
          })
        }
      >
        Select Berlin
      </button>
    </div>
  ),
}))

import { EditSheet } from "@/components/profile/edit-sheet"

beforeAll(() => {
  vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
    cb(0)
    return 1
  })
  vi.stubGlobal("cancelAnimationFrame", vi.fn())
})

describe("EditSheet city editor", () => {
  it("preserves exact backend city display when saving without a new selection", () => {
    const onSave = vi.fn()
    render(
      <EditSheet
        field="birthPlace"
        initial={{
          city: "Washington, DC, USA",
          lat: 38.9072,
          lon: -77.0369,
          timezone: "America/New_York",
        }}
        onClose={vi.fn()}
        onSave={onSave}
      />,
    )

    expect(screen.getByTestId("city-picker-value").textContent).toBe(
      "Washington, DC, USA|",
    )
    fireEvent.click(screen.getByText("Сохранить"))

    expect(onSave).toHaveBeenCalledWith({
      city: "Washington, DC, USA",
      lat: 38.9072,
      lon: -77.0369,
      timezone: "America/New_York",
    })
  })

  it("persists selected city display and metadata after a new selection", () => {
    const onSave = vi.fn()
    render(
      <EditSheet
        field="currentCity"
        initial={{
          city: "London",
          lat: 51.5074,
          lon: -0.1278,
          timezone: "Europe/London",
        }}
        onClose={vi.fn()}
        onSave={onSave}
      />,
    )

    fireEvent.click(screen.getByText("Select Berlin"))
    fireEvent.click(screen.getByText("Сохранить"))

    expect(onSave).toHaveBeenCalledWith({
      city: "Berlin, Germany",
      lat: 52.52,
      lon: 13.405,
      timezone: "Europe/Berlin",
    })
  })
})
