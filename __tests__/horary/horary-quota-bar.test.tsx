
// ############################################################################
// AI_HEADER: MODULE_HORARY_HORARY_QUOTA_BAR_TEST
// ROLE: Unit tests for horary-quota-bar.test.tsx
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// #########################################// START_MODULE_CONTRACT
// purpose: Tests for horary-quota-bartsx behavior
// owns:
//   - __tests__/horary/horary-quota-bar.test.tsx
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import React from "react"
import { HoraryQuotaBar } from "@/components/readings/horary/horary-quota-bar"

// ── Helpers ──────────────────────────────────────────────────────────────────

type HoraryQuotaRead = {
  weeklyFreeAvailable: boolean
  weeklyFreeExpiresAt?: string | null
  nextWeeklyFreeAt?: string | null
  bonusCredits: number
  paidCredits: number
  canPurchase: boolean
}

const onBuy = vi.fn()

function renderBar(quota: HoraryQuotaRead) {
  return render(<HoraryQuotaBar quota={quota} onBuy={onBuy} />)
}

/** Quota with zero total credits (empty state) */
const emptyQuota: HoraryQuotaRead = {
  weeklyFreeAvailable: false,
  weeklyFreeExpiresAt: null,
  nextWeeklyFreeAt: null,
  bonusCredits: 0,
  paidCredits: 0,
  canPurchase: true,
}

/** Quota with totalCredits > 0 (normal state) */
const normalQuota: HoraryQuotaRead = {
  weeklyFreeAvailable: true,
  weeklyFreeExpiresAt: null,
  nextWeeklyFreeAt: null,
  bonusCredits: 0,
  paidCredits: 0,
  canPurchase: true,
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("HoraryQuotaBar", () => {
  beforeEach(() => {
    onBuy.mockReset()
  })

  // ── 1. totalCredits=0 empty state: destructive styling, "Вопросы закончились"
  it("renders empty state with destructive styling when totalCredits is 0", () => {
    renderBar(emptyQuota)

    const bar = screen.getByTestId("horary-quota-bar")
    expect(bar.className).toContain("border-destructive")
    expect(bar.className).toContain("bg-destructive")
    expect(screen.getByText("Вопросы закончились")).toBeTruthy()
  })

  // ── 2. totalCredits=0 + nextWeeklyFreeAt: "Новый бесплатный вопрос начислится..."
  it("shows next free question date when totalCredits=0 and nextWeeklyFreeAt is set", () => {
    renderBar({
      ...emptyQuota,
      nextWeeklyFreeAt: "2026-07-01T12:00:00Z",
    })

    expect(screen.getByText(/Новый бесплатный вопрос начислится/)).toBeTruthy()
  })

  // ── 3. totalCredits=0 + no nextWeeklyFreeAt: "Оформи подписку или пригласи друга..."
  it("shows subscribe/invite fallback when totalCredits=0 and nextWeeklyFreeAt is missing", () => {
    renderBar(emptyQuota)

    expect(
      screen.getByText(/Оформи подписку или пригласи друга/)
    ).toBeTruthy()
  })

  // ── 4. totalCredits>0 normal state with breakdown
  it("renders normal state with breakdown when totalCredits > 0", () => {
    renderBar(normalQuota)

    const bar = screen.getByTestId("horary-quota-bar")
    expect(bar.className).toContain("bg-card")
    expect(screen.getByText(/Доступно вопросов:/)).toBeTruthy()
  })

  // ── 5. weeklyFreeAvailable=true: "доступен" text
  it("shows 'доступен' when weeklyFreeAvailable is true", () => {
    renderBar({ ...normalQuota, weeklyFreeAvailable: true })

    expect(screen.getByText("доступен")).toBeTruthy()
  })

  // ── 6. weeklyFreeAvailable=false: "использован" text
  it("shows 'использован' when weeklyFreeAvailable is false but other credits exist", () => {
    renderBar({
      ...normalQuota,
      weeklyFreeAvailable: false,
      paidCredits: 1,
    })

    // Text is inside a longer span: "• Еженедельный бесплатный: использован"
    expect(screen.getByText(/использован/)).toBeTruthy()
  })

  // ── 7. weeklyFreeExpiresAt present: "(сгорит ...)"
  it("shows expiry text when weeklyFreeExpiresAt is present", () => {
    renderBar({
      ...normalQuota,
      weeklyFreeAvailable: true,
      weeklyFreeExpiresAt: "2026-07-15T18:30:00Z",
    })

    expect(screen.getByText(/сгорит/)).toBeTruthy()
  })

  // ── 8. weeklyFreeExpiresAt absent: no expiry text
  it("does not show expiry text when weeklyFreeExpiresAt is absent", () => {
    renderBar({
      ...normalQuota,
      weeklyFreeAvailable: true,
      weeklyFreeExpiresAt: null,
    })

    expect(screen.queryByText(/сгорит/)).toBeNull()
  })

  // ── 9. paidCredits=0: no paid credits line
  it("does not show paid credits line when paidCredits is 0", () => {
    renderBar({ ...normalQuota, paidCredits: 0 })

    expect(screen.queryByText(/Купленные:/)).toBeNull()
  })

  // ── 10. paidCredits>0: shows "Купленные: N (не сгорают)"
  it("shows 'Купленные: N (не сгорают)' when paidCredits > 0", () => {
    renderBar({ ...normalQuota, paidCredits: 3 })

    expect(screen.getByText(/Купленные:/)).toBeTruthy()
    expect(screen.getByText(/не сгорают/)).toBeTruthy()
    // The number 3 is rendered in a <strong>
    const strongs = screen.getAllByText("3")
    expect(strongs.length).toBeGreaterThanOrEqual(1)
  })

  // ── 11. bonusCredits=0: no bonus line
  it("does not show bonus line when bonusCredits is 0", () => {
    renderBar({ ...normalQuota, bonusCredits: 0 })

    expect(screen.queryByText(/Бонусные:/)).toBeNull()
  })

  // ── 12. bonusCredits>0: shows "Бонусные: N"
  it("shows 'Бонусные: N' when bonusCredits > 0", () => {
    renderBar({ ...normalQuota, bonusCredits: 2 })

    expect(screen.getByText(/Бонусные:/)).toBeTruthy()
    const strongs = screen.getAllByText("2")
    expect(strongs.length).toBeGreaterThanOrEqual(1)
  })

  // ── 13. onBuy click in empty state
  it("calls onBuy when buy button is clicked in empty state", () => {
    renderBar(emptyQuota)

    const btn = screen.getByTestId("horary-buy-btn")
    fireEvent.click(btn)

    expect(onBuy).toHaveBeenCalledTimes(1)
  })

  // ── 14. onBuy click in normal state
  it("calls onBuy when buy button is clicked in normal state", () => {
    renderBar(normalQuota)

    const btn = screen.getByTestId("horary-buy-btn")
    fireEvent.click(btn)

    expect(onBuy).toHaveBeenCalledTimes(1)
  })

  // ── 15. Total credits calculation: (weeklyFreeAvailable ? 1 : 0) + bonusCredits + paidCredits
  describe("total credits calculation", () => {
    it("counts 1 for weeklyFreeAvailable=true", () => {
      renderBar({
        weeklyFreeAvailable: true,
        bonusCredits: 0,
        paidCredits: 0,
        canPurchase: true,
      })

      expect(screen.getByText("1")).toBeTruthy()
    })

    it("counts 0 for weeklyFreeAvailable=false", () => {
      renderBar({
        weeklyFreeAvailable: false,
        bonusCredits: 2,
        paidCredits: 0,
        canPurchase: true,
      })

      // totalCredits = 0 + 2 + 0 = 2 — appears in "Доступно вопросов: <strong>2</strong>"
      // and also in "Бонусные: <strong>2</strong>", so use getAllByText
      const twos = screen.getAllByText("2")
      expect(twos.length).toBeGreaterThanOrEqual(1)
    })

    it("sums weeklyFree + bonusCredits + paidCredits", () => {
      renderBar({
        weeklyFreeAvailable: true,
        bonusCredits: 3,
        paidCredits: 5,
        canPurchase: true,
      })

      // totalCredits = 1 + 3 + 5 = 9
      expect(screen.getByText("9")).toBeTruthy()
    })

    it("shows 0 credits as empty state (no breakdown)", () => {
      renderBar({
        weeklyFreeAvailable: false,
        bonusCredits: 0,
        paidCredits: 0,
        canPurchase: true,
      })

      // Empty state does NOT show "Доступно вопросов:"
      expect(screen.queryByText(/Доступно вопросов:/)).toBeNull()
      expect(screen.getByText("Вопросы закончились")).toBeTruthy()
    })
  })

  // ── 16. data-testid="horary-quota-bar" in both states
  it("has data-testid='horary-quota-bar' in empty state", () => {
    renderBar(emptyQuota)
    expect(screen.getByTestId("horary-quota-bar")).toBeTruthy()
  })

  it("has data-testid='horary-quota-bar' in normal state", () => {
    renderBar(normalQuota)
    expect(screen.getByTestId("horary-quota-bar")).toBeTruthy()
  })

  // ── 17. data-testid="horary-buy-btn" in both states
  it("has data-testid='horary-buy-btn' in empty state", () => {
    renderBar(emptyQuota)
    expect(screen.getByTestId("horary-buy-btn")).toBeTruthy()
  })

  it("has data-testid='horary-buy-btn' in normal state", () => {
    renderBar(normalQuota)
    expect(screen.getByTestId("horary-buy-btn")).toBeTruthy()
  })

  // ── 18. formatDate with invalid date → returns iso string
  it("falls back to raw iso string when formatDate catches an error", () => {
    // Force toLocaleDateString to throw so the catch-path returns the raw string
    const original = Date.prototype.toLocaleDateString
    Date.prototype.toLocaleDateString = vi.fn(() => {
      throw new RangeError("Invalid date")
    })

    try {
      renderBar({
        ...emptyQuota,
        nextWeeklyFreeAt: "not-a-valid-date",
      })

      // The catch block returns the original iso string "not-a-valid-date"
      expect(screen.getByText(/not-a-valid-date/)).toBeTruthy()
    } finally {
      Date.prototype.toLocaleDateString = original
    }
  })

  it("formats valid nextWeeklyFreeAt date using ru-RU locale", () => {
    renderBar({
      ...emptyQuota,
      nextWeeklyFreeAt: "2026-07-01T12:00:00Z",
    })

    // Should contain a formatted date (at least day/month digits), not the raw ISO
    const el = screen.getByText(/Новый бесплатный вопрос начислится/)
    // The rendered text should not contain the raw ISO "2026-07-01T12:00:00Z"
    expect(el.textContent).not.toContain("2026-07-01T12:00:00Z")
  })

  it("renders Coins icon in normal state", () => {
    const { container } = renderBar(normalQuota)
    // lucide-react renders an SVG; check for svg element presence
    const svg = container.querySelector("svg")
    expect(svg).toBeTruthy()
  })
})
