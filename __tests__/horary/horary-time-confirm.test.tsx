
// ############################################################################
// AI_HEADER: MODULE_HORARY_HORARY_TIME_CONFIRM_TEST
// ROLE: Unit tests for horary-time-confirm.test.tsx
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for horary-time-confirmtsx behavior
// owns:
//   - __tests__/horary/horary-time-confirm.test.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent, act } from "@testing-library/react"
import React from "react"
import { HoraryTimeConfirm } from "@/components/readings/horary/horary-time-confirm"
import type { City } from "@/lib/contracts/city"

// ── Mocks ─────────────────────────────────────────────────────────────────────

vi.mock("lucide-react", () => ({
  Calendar: () => <span data-testid="icon-calendar" />,
  Clock: () => <span data-testid="icon-clock" />,
  MapPin: () => <span data-testid="icon-mappin" />,
  Edit2: () => <span data-testid="icon-edit2" />,
}))

vi.mock("@/components/onboarding/city-picker", () => ({
  CityPicker: ({ value, onChange }: { value: City | null; onChange: (_city: City) => void }) => (
    <button
      data-testid="mock-city-picker"
      onClick={() => {
        const mockCity: City = { name: "Санкт-Петербург", country: "Россия", lat: 59.93, lon: 30.32, timezone: "Europe/Moscow" }
        onChange(mockCity)
      }}
    >
      Mock CityPicker (selected: {value ? value.name : "none"})
    </button>
  ),
}))

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderComponent(overrides: Record<string, unknown> = {}) {
  const onChange = vi.fn()
  const props = {
    onChange,
    profileCurrentCity: undefined as string | null | undefined,
    profileCurrentLat: undefined as number | null | undefined,
    profileCurrentLon: undefined as number | null | undefined,
    profileCurrentTz: undefined as string | null | undefined,
    profileBirthCity: undefined as string | null | undefined,
    profileBirthLat: undefined as number | null | undefined,
    profileBirthLon: undefined as number | null | undefined,
    profileBirthTz: undefined as string | null | undefined,
    ...overrides,
  }
  const result = render(<HoraryTimeConfirm {...props} />)
  return { ...result, onChange }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("HoraryTimeConfirm", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // 1. Default city from profileCurrentCity
  it("renders the current city name in the place row", () => {
    renderComponent({
      profileCurrentCity: "Москва, Россия",
      profileCurrentLat: 55.75,
      profileCurrentLon: 37.62,
      profileCurrentTz: "Europe/Moscow",
    })
    // The place row should contain "Москва, Россия"
    expect(screen.getByText(/Москва, Россия/)).toBeTruthy()
  })

  // 2. Fallback to profileBirthCity when no currentCity
  it("falls back to birth city when current city is not provided", () => {
    renderComponent({
      profileBirthCity: "Киев, Украина",
      profileBirthLat: 50.45,
      profileBirthLon: 30.52,
      profileBirthTz: "Europe/Kiev",
    })
    expect(screen.getByText(/Киев, Украина/)).toBeTruthy()
  })

  // 3. No city at all → "не определено"
  it("shows 'не определено' when no city is provided", () => {
    renderComponent()
    expect(screen.getByText("не определено")).toBeTruthy()
  })

  // 4. City with country → "City, Country" format
  it("displays city with country in 'City, Country' format", () => {
    renderComponent({
      profileCurrentCity: "Москва, Россия",
      profileCurrentLat: 55.75,
      profileCurrentLon: 37.62,
      profileCurrentTz: "Europe/Moscow",
    })
    // The strong element should contain "Москва, Россия"
    const strongElements = screen.getAllByText("Москва, Россия")
    expect(strongElements.length).toBeGreaterThanOrEqual(1)
  })

  // 5. City without country → just the city name
  it("displays only city name when there is no country part", () => {
    renderComponent({
      profileCurrentCity: "Москва",
      profileCurrentLat: 55.75,
      profileCurrentLon: 37.62,
      profileCurrentTz: "Europe/Moscow",
    })
    // When the city string is just "Москва" (no comma), country is ""
    // formatCityDisplay should produce "Москва" (no trailing comma)
    expect(screen.getByText("Москва")).toBeTruthy()
  })

  // 6. "Изменить время" button toggles time editor
  it("toggles the time editor when 'Изменить время' button is clicked", () => {
    const { container } = renderComponent()
    // Initially no datetime-local input should be present
    expect(container.querySelector('input[type="datetime-local"]')).toBeNull()

    const timeButton = screen.getByText("Изменить время")
    act(() => {
      fireEvent.click(timeButton)
    })

    // Now the time editor should appear
    expect(container.querySelector('input[type="datetime-local"]')).toBeTruthy()
    expect(screen.getByText("Выбрать другое время")).toBeTruthy()

    // Click again to close
    act(() => {
      fireEvent.click(timeButton)
    })
    expect(container.querySelector('input[type="datetime-local"]')).toBeNull()
  })

  // 7. Place button text depends on whether a city is selected
  it("shows 'Изменить место' when a city is already selected", () => {
    renderComponent({
      profileCurrentCity: "Москва, Россия",
      profileCurrentLat: 55.75,
      profileCurrentLon: 37.62,
      profileCurrentTz: "Europe/Moscow",
    })
    expect(screen.getByText("Изменить место")).toBeTruthy()
  })

  it("shows 'Указать место' when no city is selected", () => {
    renderComponent()
    expect(screen.getByText("Указать место")).toBeTruthy()
  })

  // 8. Only one editor open at a time
  it("closes time editor when place editor is opened and vice versa", () => {
    const { container } = renderComponent()

    // Open time editor
    act(() => {
      fireEvent.click(screen.getByText("Изменить время"))
    })
    expect(container.querySelector('input[type="datetime-local"]')).toBeTruthy()
    expect(screen.queryByText("Поиск города")).toBeNull()

    // Open place editor — should close time editor
    act(() => {
      fireEvent.click(screen.getByText("Указать место"))
    })
    expect(container.querySelector('input[type="datetime-local"]')).toBeNull()
    expect(screen.getByText("Поиск города")).toBeTruthy()

    // Open time editor again — should close place editor
    act(() => {
      fireEvent.click(screen.getByText("Изменить время"))
    })
    expect(container.querySelector('input[type="datetime-local"]')).toBeTruthy()
    expect(screen.queryByText("Поиск города")).toBeNull()
  })

  // 9. onChange callback fires with correct localTime and timezone
  it("calls onChange with localTime and timezone on mount", () => {
    const { onChange } = renderComponent()
    // The component initializes time and timezone in useEffect and calls onChange
    expect(onChange).toHaveBeenCalled()
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1]
    // localTime should be a non-empty ISO-like string
    expect(lastCall[0]).toBeTruthy()
    // timezone should be a non-empty string
    expect(lastCall[1]).toBeTruthy()
  })

  it("calls onChange with lat, lon, and locationName when a city is provided", () => {
    const { onChange } = renderComponent({
      profileCurrentCity: "Москва, Россия",
      profileCurrentLat: 55.75,
      profileCurrentLon: 37.62,
      profileCurrentTz: "Europe/Moscow",
    })

    // Find a call that includes lat/lon/locationName
    const callsWithCoords = onChange.mock.calls.filter((call: unknown[]) => call[2] !== undefined)
    expect(callsWithCoords.length).toBeGreaterThanOrEqual(1)
    const lastCallWithCoords = callsWithCoords[callsWithCoords.length - 1]
    expect(lastCallWithCoords[2]).toBe(55.75)
    expect(lastCallWithCoords[3]).toBe(37.62)
    expect(lastCallWithCoords[4]).toBe("Москва, Россия")
  })

  // 10. Time editor input changes localTime
  it("updates localTime when the datetime-local input is changed", () => {
    const { container, onChange } = renderComponent()

    // Open time editor
    act(() => {
      fireEvent.click(screen.getByText("Изменить время"))
    })

    const input = container.querySelector('input[type="datetime-local"]') as HTMLInputElement
    const newTime = "2025-03-15T10:30"

    act(() => {
      fireEvent.change(input, { target: { value: newTime } })
    })

    expect(input.value).toBe(newTime)
    // onChange should have been called with the new time
    const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1]
    expect(lastCall[0]).toBe(newTime)
  })

  // 11. formatCityDisplay with null → "не определено"
  it("renders 'не определено' when no profile city props are given (null city)", () => {
    renderComponent({
      profileCurrentCity: null,
      profileBirthCity: null,
    })
    expect(screen.getByText("не определено")).toBeTruthy()
  })

  // Additional: CityPicker selection updates the displayed city and closes the editor
  it("updates the displayed city when CityPicker selects a city and closes the place editor", () => {
    renderComponent()

    // Open place editor
    act(() => {
      fireEvent.click(screen.getByText("Указать место"))
    })
    expect(screen.getByTestId("mock-city-picker")).toBeTruthy()

    // Click the mock CityPicker button to select a city
    act(() => {
      fireEvent.click(screen.getByTestId("mock-city-picker"))
    })

    // The place editor should be closed now
    expect(screen.queryByText("Поиск города")).toBeNull()
    // The newly selected city should be displayed
    expect(screen.getByText(/Санкт-Петербург, Россия/)).toBeTruthy()
    // Button text should switch to "Изменить место"
    expect(screen.getByText("Изменить место")).toBeTruthy()
  })
})
