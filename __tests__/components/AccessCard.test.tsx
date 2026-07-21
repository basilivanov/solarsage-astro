import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import React from "react"

import { AccessCard as ProfileAccessCard, type AccessCardBilling } from "@/components/profile/access-card"
import { AccessCard as MonetizationAccessCard } from "@/components/monetization/access-card"

vi.mock("@/lib/hooks/use-share-invite", () => ({
  useShareInvite: () => vi.fn(),
}))

const access = {
  state: "none" as const,
  hasAccess: false,
  accessStart: null,
  accessEnd: null,
  daysLeft: 0,
}

function billing(overrides: Partial<AccessCardBilling> = {}): AccessCardBilling {
  return {
    ready: true,
    unavailable: false,
    busy: false,
    monthLabel: "Подписка · 99 ₽/мес",
    yearLabel: "Подписка · 999 ₽/год",
    onBuy: vi.fn(),
    onCancel: vi.fn(),
    ...overrides,
  }
}

describe("AccessCard billing contract", () => {
  it("without billing the subscribe CTA is an honest disabled state, never 'скоро появится'", () => {
    render(<ProfileAccessCard access={access} currentState="none" />)
    const primary = screen.getByTestId("access-card-primary")
    expect((primary as HTMLButtonElement).disabled).toBe(true)
    expect(primary.textContent).toContain("Оплата временно недоступна")
    expect(screen.queryByText(/скоро появится/i)).toBeNull()
  })

  it("none state: month/year CTAs call onBuy with the right slugs", () => {
    const b = billing()
    render(<ProfileAccessCard access={access} currentState="none" billing={b} />)
    const primary = screen.getByTestId("access-card-primary")
    expect(primary.textContent).toContain("Подписка · 99 ₽/мес")
    fireEvent.click(primary)
    expect(b.onBuy).toHaveBeenCalledWith("subscription_month")
    fireEvent.click(screen.getByTestId("access-card-secondary"))
    expect(b.onBuy).toHaveBeenCalledWith("subscription_year")
  })

  it("busy state disables both CTAs with a waiting label", () => {
    const b = billing({ busy: true })
    render(<ProfileAccessCard access={access} currentState="none" billing={b} />)
    const primary = screen.getByTestId("access-card-primary")
    expect((primary as HTMLButtonElement).disabled).toBe(true)
    expect(primary.textContent).toContain("Ждём подтверждение оплаты")
    fireEvent.click(primary)
    expect(b.onBuy).not.toHaveBeenCalled()
  })

  it("subscription state: secondary cancels, paid period note kept", () => {
    const b = billing()
    render(
      <ProfileAccessCard
        access={{ ...access, state: "subscription", hasAccess: true }}
        currentState="subscription"
        billing={b}
      />,
    )
    const secondary = screen.getByTestId("access-card-secondary")
    expect(secondary.textContent).toContain("Отменить подписку")
    fireEvent.click(secondary)
    expect(b.onCancel).toHaveBeenCalledTimes(1)
  })

  it("subscription state shows honest non-renewing semantics when renewal is off", () => {
    const b = billing()
    render(
      <ProfileAccessCard
        access={{ ...access, state: "subscription", hasAccess: true }}
        currentState="subscription"
        billing={b}
        renewal={{ renewing: false }}
      />,
    )
    expect(screen.getByText(/Без автопродления/)).toBeTruthy()
    expect(screen.queryByText(/Автопродление активно/)).toBeNull()
  })

  it("subscription state shows auto-renew note when renewal is on", () => {
    const b = billing()
    render(
      <ProfileAccessCard
        access={{ ...access, state: "subscription", hasAccess: true }}
        currentState="subscription"
        billing={b}
        renewal={{ renewing: true }}
      />,
    )
    expect(screen.getByText(/Автопродление активно/)).toBeTruthy()
  })

  it("keeps the test-only monetization stub copy unchanged", () => {
    const onSubscribe = vi.fn()
    render(
      <MonetizationAccessCard
        access={access}
        currentState="none"
        onSubscribe={onSubscribe}
        onInvite={vi.fn()}
      />,
    )
    const button = screen.getByRole("button", { name: /Подписка скоро появится/ })
    fireEvent.click(button)
    expect((button as HTMLButtonElement).disabled).toBe(true)
    expect(onSubscribe).not.toHaveBeenCalled()
  })
})
