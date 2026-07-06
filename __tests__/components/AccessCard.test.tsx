import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import React from "react"

import { AccessCard as ProfileAccessCard } from "@/components/profile/access-card"
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

describe("AccessCard payment gating", () => {
  it("disables profile subscription CTA until real fulfillment exists", () => {
    const onSubscribe = vi.fn()

    render(
      <ProfileAccessCard
        access={access}
        currentState="none"
        onSubscribe={onSubscribe}
      />,
    )

    const button = screen.getByRole("button", { name: /Подписка скоро появится/ })
    fireEvent.click(button)

    expect((button as HTMLButtonElement).disabled).toBe(true)
    expect(onSubscribe).not.toHaveBeenCalled()
    expect(screen.queryByRole("button", { name: /Оформить подписку/ })).toBeNull()
  })

  it("disables profile manage-subscription CTA until real fulfillment exists", () => {
    const onSubscribe = vi.fn()

    render(
      <ProfileAccessCard
        access={{ ...access, state: "subscription", hasAccess: true }}
        currentState="subscription"
        onSubscribe={onSubscribe}
      />,
    )

    const button = screen.getByRole("button", { name: /Управление подпиской скоро появится/ })
    fireEvent.click(button)

    expect((button as HTMLButtonElement).disabled).toBe(true)
    expect(onSubscribe).not.toHaveBeenCalled()
    expect(screen.queryByRole("button", { name: /Управление подпиской$/ })).toBeNull()
  })

  it("disables monetization subscription CTA until real fulfillment exists", () => {
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
    expect(screen.queryByRole("button", { name: /Оформить подписку/ })).toBeNull()
  })
})
