import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import React from "react"
import { ElectionForm } from "@/components/readings/election/election-form"

describe("ElectionForm", () => {
  it("renders event chips and date preset buttons", () => {
    render(<ElectionForm onSubmit={vi.fn()} />)
    expect(screen.getByTestId("election-event-chip-wedding")).toBeTruthy()
    expect(screen.getByTestId("election-preset-14d")).toBeTruthy()
  })

  it("submits selected event and dates", () => {
    const handleSubmit = vi.fn()
    render(<ElectionForm onSubmit={handleSubmit} />)

    // Select wedding chip
    const chip = screen.getByTestId("election-event-chip-wedding")
    fireEvent.click(chip)

    // Submit button should be enabled now
    const submitBtn = screen.getByTestId("election-submit-btn")
    expect((submitBtn as HTMLButtonElement).disabled).toBe(false)

    fireEvent.click(submitBtn)
    expect(handleSubmit).toHaveBeenCalledTimes(1)
    expect(handleSubmit.mock.calls[0][0].eventType).toBe("wedding")
  })

  it("disables submit when no event selected or when disabled prop is true", () => {
    render(<ElectionForm onSubmit={vi.fn()} disabled={true} disabledReason="No credits" />)
    const chip = screen.getByTestId("election-event-chip-wedding")
    fireEvent.click(chip)

    const submitBtn = screen.getByTestId("election-submit-btn")
    expect((submitBtn as HTMLButtonElement).disabled).toBe(true)
    expect(screen.getByText("No credits")).toBeTruthy()
  })

  it("validates max 62 days range in custom dates mode", () => {
    render(<ElectionForm onSubmit={vi.fn()} />)
    const customPreset = screen.getByTestId("election-preset-custom")
    fireEvent.click(customPreset)

    const dateFrom = screen.getByTestId("election-date-from")
    const dateTo = screen.getByTestId("election-date-to")

    fireEvent.change(dateFrom, { target: { value: "2026-08-01" } })
    fireEvent.change(dateTo, { target: { value: "2026-11-01" } }) // > 62 days

    expect(screen.getByTestId("election-date-error")).toBeTruthy()
    expect(screen.getByText("Максимальный интервал подбора — 62 дня")).toBeTruthy()
  })
})
