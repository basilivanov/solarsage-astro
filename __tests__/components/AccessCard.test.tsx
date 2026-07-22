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

  it("shows the recurring-consent copy with exact amounts before the buy click", () => {
    const b = billing({
      consent:
        "Подписка с автопродлением: 99 ₽ каждый месяц или 999 ₽ в год. Отменить можно в любой момент в профиле — уже оплаченный период сохранится.",
    })
    render(<ProfileAccessCard access={access} currentState="none" billing={b} />)
    const consent = screen.getByTestId("access-card-recurring-consent")
    expect(consent.textContent).toContain("99 ₽ каждый месяц")
    expect(consent.textContent).toContain("999 ₽ в год")
    expect(consent.textContent).toContain("Отменить можно в любой момент")
  })

  it("hides the consent line when billing is unavailable or consent is null", () => {
    const b = billing({ unavailable: true })
    render(<ProfileAccessCard access={access} currentState="none" billing={b} />)
    expect(screen.queryByTestId("access-card-recurring-consent")).toBeNull()

    const b2 = billing({ consent: null })
    render(<ProfileAccessCard access={access} currentState="none" billing={b2} />)
    expect(screen.queryByTestId("access-card-recurring-consent")).toBeNull()
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

  it("subscription state: secondary cancels when cancelable, paid period note kept", () => {
    const b = billing()
    render(
      <ProfileAccessCard
        access={{ ...access, state: "subscription", hasAccess: true }}
        currentState="subscription"
        billing={b}
        renewal={{ renewing: true, cancelable: true }}
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
        renewal={{ renewing: false, cancelable: false }}
      />,
    )
    expect(screen.getByText(/Без автопродления/)).toBeTruthy()
    expect(screen.queryByText(/Автопродление активно/)).toBeNull()
  })

  it("subscription state hides cancel for non-renewing (cancelable=false) with an honest disabled secondary", () => {
    const b = billing()
    render(
      <ProfileAccessCard
        access={{ ...access, state: "subscription", hasAccess: true }}
        currentState="subscription"
        billing={b}
        renewal={{ renewing: false, cancelable: false }}
      />,
    )
    expect(screen.queryByText("Отменить подписку")).toBeNull()
    const primary = screen.getByTestId("access-card-primary")
    const secondary = screen.getByTestId("access-card-secondary")
    // Never two identical invite CTAs.
    expect(secondary.textContent).not.toBe(primary.textContent)
    expect(secondary.textContent).toContain("Автопродление отключено")
    expect((secondary as HTMLButtonElement).disabled).toBe(true)
    // Semantic contract: exact data attributes drive tests, not CSS.
    const root = primary.closest("[data-renewal]") as HTMLElement
    expect(root.getAttribute("data-renewal")).toBe("non-renewing")
    expect(root.getAttribute("data-cancelable")).toBe("false")
  })

  it("subscription state shows auto-renew note and cancel when renewal is on (cancelable)", () => {
    const b = billing()
    render(
      <ProfileAccessCard
        access={{ ...access, state: "subscription", hasAccess: true }}
        currentState="subscription"
        billing={b}
        renewal={{ renewing: true, cancelable: true }}
      />,
    )
    expect(screen.getByText(/Автопродление активно/)).toBeTruthy()
    const secondary = screen.getByTestId("access-card-secondary")
    expect(secondary.textContent).toContain("Отменить подписку")
    const root = secondary.closest("[data-renewal]") as HTMLElement
    expect(root.getAttribute("data-renewal")).toBe("renewing")
    expect(root.getAttribute("data-cancelable")).toBe("true")
    fireEvent.click(secondary)
    expect(b.onCancel).toHaveBeenCalledTimes(1)
  })

  it("subscription state with unknown flags checks renewal instead of offering actions", () => {
    const b = billing()
    render(
      <ProfileAccessCard
        access={{ ...access, state: "subscription", hasAccess: true }}
        currentState="subscription"
        billing={b}
      />,
    )
    const secondary = screen.getByTestId("access-card-secondary")
    expect(secondary.textContent).toContain("Проверяем автопродление")
    expect((secondary as HTMLButtonElement).disabled).toBe(true)
    const root = secondary.closest("[data-renewal]") as HTMLElement
    expect(root.getAttribute("data-renewal")).toBe("loading")
    expect(root.getAttribute("data-cancelable")).toBe("false")
  })

  it("subscription state with tariffs still loading also checks renewal, never a fake label", () => {
    const b = billing({ ready: false })
    render(
      <ProfileAccessCard
        access={{ ...access, state: "subscription", hasAccess: true }}
        currentState="subscription"
        billing={b}
      />,
    )
    const secondary = screen.getByTestId("access-card-secondary")
    expect(secondary.textContent).toContain("Проверяем автопродление")
    expect(secondary.textContent).not.toContain("Загружаем тарифы")
    expect((secondary as HTMLButtonElement).disabled).toBe(true)
  })

  it("subscription state with unavailable billing shows an honest unavailable secondary", () => {
    const b = billing({ unavailable: true })
    render(
      <ProfileAccessCard
        access={{ ...access, state: "subscription", hasAccess: true }}
        currentState="subscription"
        billing={b}
      />,
    )
    const secondary = screen.getByTestId("access-card-secondary")
    expect(secondary.textContent).toContain("Управление подпиской недоступно")
    expect((secondary as HTMLButtonElement).disabled).toBe(true)
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
