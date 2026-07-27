import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { HoraryCard } from "@/components/profile/horary-card"

describe("HoraryCard / Shared Credits Card", () => {
  it("renders credits card with header 'Кредиты на разборы', total counts, breakdown, and 3-service subtext", () => {
    render(
      <HoraryCard
        horary={{
          weeklyFreeAvailable: true,
          weeklyFreeExpiresAt: "2026-08-01T00:00:00Z",
          nextWeeklyFreeAt: null,
          bonusCredits: 2,
          paidCredits: 1,
          canPurchase: true,
        }}
      />
    )

    const card = screen.getByTestId("credits-card")
    expect(card).toBeDefined()

    expect(screen.getByText("Кредиты на разборы")).toBeDefined()
    expect(screen.getByText(/Осталось 4 разбора/i)).toBeDefined()
    expect(screen.getByText(/Бесплатный еженедельный: активен/i)).toBeDefined()
    expect(screen.getByText(/Бонусные: 2/i)).toBeDefined()
    expect(screen.getByText(/Платные: 1/i)).toBeDefined()
    expect(
      screen.getByText("Общие кредиты для хорарных вопросов, выбора дат и синастрии")
    ).toBeDefined()
  })

  it("renders spent weekly free status and next weekly free date", () => {
    render(
      <HoraryCard
        horary={{
          weeklyFreeAvailable: false,
          weeklyFreeExpiresAt: null,
          nextWeeklyFreeAt: "2026-08-05T00:00:00Z",
          bonusCredits: 0,
          paidCredits: 0,
          canPurchase: true,
        }}
      />
    )

    expect(screen.getByText(/Осталось 0 разборов/i)).toBeDefined()
    expect(screen.getByText(/Бесплатный еженедельный: потрачен/i)).toBeDefined()
    expect(screen.getByText(/Следующий бесплатный:/i)).toBeDefined()
  })
})
