import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import React from "react"
import { ElectionForm } from "@/components/readings/election/election-form"

describe("ElectionForm v2", () => {
  it("renders 6 base categories in grid", () => {
    render(<ElectionForm onSubmit={vi.fn()} />)
    expect(screen.getByTestId("election-category-card-relations")).toBeTruthy()
    expect(screen.getByTestId("election-category-card-work")).toBeTruthy()
  })

  it("clicks category to open subcategories, clicks subcategory to fill custom text", () => {
    render(<ElectionForm onSubmit={vi.fn()} />)

    // Click relations category
    fireEvent.click(screen.getByTestId("election-category-card-relations"))
    expect(screen.getByTestId("election-sub-chip-wedding")).toBeTruthy()

    // Click wedding subchip
    fireEvent.click(screen.getByTestId("election-sub-chip-wedding"))
    const customInput = screen.getByTestId("election-custom-input") as HTMLInputElement
    expect(customInput.value).toBe("Свадьба/помолвка")
  })

  it("submits category:sub eventType when category and sub are selected", () => {
    const handleSubmit = vi.fn()
    render(<ElectionForm onSubmit={handleSubmit} />)

    fireEvent.click(screen.getByTestId("election-category-card-relations"))
    fireEvent.click(screen.getByTestId("election-sub-chip-wedding"))

    const submitBtn = screen.getByTestId("election-submit-btn")
    fireEvent.click(submitBtn)

    expect(handleSubmit).toHaveBeenCalledTimes(1)
    expect(handleSubmit.mock.calls[0][0].eventType).toBe("relations:wedding")
  })

  it("validates max 62 days range in custom dates mode", () => {
    render(<ElectionForm onSubmit={vi.fn()} />)
    fireEvent.click(screen.getByTestId("election-category-card-relations"))
    fireEvent.click(screen.getByTestId("election-sub-chip-wedding"))

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
