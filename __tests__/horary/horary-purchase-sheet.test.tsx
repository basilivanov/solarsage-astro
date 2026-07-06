
// ############################################################################
// AI_HEADER: MODULE_HORARY_HORARY_PURCHASE_SHEET_TEST
// ROLE: Unit tests for horary-purchase-sheet.test.tsx
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for horary-purchase-sheettsx behavior
// owns:
//   - __tests__/horary/horary-purchase-sheet.test.tsx
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent, act } from "@testing-library/react"
import React from "react"
import { HoraryPurchaseSheet } from "@/components/readings/horary/horary-purchase-sheet"

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockToast = vi.fn()

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast: mockToast }),
}))

vi.mock("lucide-react", () => ({
  X: () => <span data-testid="icon-x" />,
  Coins: () => <span data-testid="icon-coins" />,
}))

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderSheet(onClose = vi.fn()) {
  return render(<HoraryPurchaseSheet onClose={onClose} />)
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("HoraryPurchaseSheet", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    // jsdom does not implement layout so overflow is just a CSS string;
    // reset before each test so body-scroll-lock tests are independent.
    document.body.style.overflow = ""
  })

  afterEach(() => {
    vi.useRealTimers()
    document.body.style.overflow = ""
  })

  // 1. data-testid
  it('renders with data-testid="horary-purchase-sheet"', () => {
    renderSheet()
    expect(screen.getByTestId("horary-purchase-sheet")).toBeTruthy()
  })

  // 2. aria-modal
  it("has aria-modal=true attribute", () => {
    renderSheet()
    const sheet = screen.getByTestId("horary-purchase-sheet")
    expect(sheet.getAttribute("aria-modal")).toBe("true")
  })

  // 3. role="dialog"
  it('has role="dialog" attribute', () => {
    renderSheet()
    const sheet = screen.getByTestId("horary-purchase-sheet")
    expect(sheet.getAttribute("role")).toBe("dialog")
  })

  // 4. Header label
  it("renders header label for unavailable paid questions", () => {
    renderSheet()
    expect(screen.getByText("Платные вопросы")).toBeTruthy()
  })

  // 5. Title
  it("renders title 'Хорарные вопросы'", () => {
    renderSheet()
    expect(screen.getByText("Хорарные вопросы")).toBeTruthy()
  })

  // 6. Description
  it("renders unavailable description without promising Telegram Stars payment", () => {
    renderSheet()
    expect(screen.getByText(/Оплата и пополнение баланса пока недоступны/)).toBeTruthy()
    expect(screen.queryByText(/Telegram Stars/)).toBeNull()
  })

  // 7. Purchase options hidden
  it("does not render paid packages while fulfillment is unavailable", () => {
    renderSheet()
    expect(screen.queryByTestId("horary-purchase-option-0")).toBeNull()
    expect(screen.queryByTestId("horary-purchase-option-1")).toBeNull()
    expect(screen.queryByTestId("horary-purchase-option-2")).toBeNull()
    expect(screen.queryByTestId("horary-purchase-option-3")).toBeNull()
  })

  // 8. No discount badges
  it("does not render discount badges while fulfillment is unavailable", () => {
    renderSheet()
    expect(screen.queryByText(/Скидка/)).toBeNull()
  })

  // 9. No package quantities
  it("does not render package quantities while fulfillment is unavailable", () => {
    renderSheet()
    expect(screen.queryByText("1 вопрос")).toBeNull()
    expect(screen.queryByText("3 вопроса")).toBeNull()
    expect(screen.queryByText("5 вопросов")).toBeNull()
    expect(screen.queryByText("10 вопросов")).toBeNull()
  })

  // 10. Prices
  it("does not render Telegram Stars prices", () => {
    renderSheet()
    expect(screen.queryByText("50 ★")).toBeNull()
    expect(screen.queryByText("120 ★")).toBeNull()
    expect(screen.queryByText("180 ★")).toBeNull()
    expect(screen.queryByText("300 ★")).toBeNull()
  })

  // 11. Close button click calls onClose after 220 ms delay
  it("calls onClose after 220ms when X close button is clicked", () => {
    const onClose = vi.fn()
    renderSheet(onClose)

    // There are two close buttons; the X-icon one is the second
    const closeButtons = screen.getAllByTestId("horary-purchase-close")
    const xButton = closeButtons[1] // the visible X button (second in DOM)
    fireEvent.click(xButton)

    // onClose should NOT be called immediately
    expect(onClose).not.toHaveBeenCalled()

    // Advance timers past the 220ms delay
    act(() => {
      vi.advanceTimersByTime(220)
    })

    expect(onClose).toHaveBeenCalledTimes(1)
  })

  // 12. Backdrop click triggers close (same behavior)
  it("calls onClose after 220ms when backdrop is clicked", () => {
    const onClose = vi.fn()
    renderSheet(onClose)

    // The backdrop is the first close button (full-screen overlay)
    const closeButtons = screen.getAllByTestId("horary-purchase-close")
    const backdrop = closeButtons[0]
    fireEvent.click(backdrop)

    expect(onClose).not.toHaveBeenCalled()

    act(() => {
      vi.advanceTimersByTime(220)
    })

    expect(onClose).toHaveBeenCalledTimes(1)
  })

  // 13. aria-label="Закрыть" on both close buttons
  it('has aria-label="Закрыть" on both close buttons', () => {
    renderSheet()
    const closeButtons = screen.getAllByTestId("horary-purchase-close")
    expect(closeButtons).toHaveLength(2)
    for (const btn of closeButtons) {
      expect(btn.getAttribute("aria-label")).toBe("Закрыть")
    }
  })

  // 14. data-testid="horary-purchase-close" on both close buttons
  it('has data-testid="horary-purchase-close" on both close buttons', () => {
    renderSheet()
    const closeButtons = screen.getAllByTestId("horary-purchase-close")
    expect(closeButtons).toHaveLength(2)
  })

  // 15. No purchase action
  it("does not expose a purchase action while fulfillment is unavailable", () => {
    renderSheet()
    expect(screen.queryByTestId("horary-purchase-option-0")).toBeNull()
    expect(mockToast).not.toHaveBeenCalled()
  })

  // 16. Body scroll lock applied on mount
  it("locks body scroll on mount", () => {
    renderSheet()
    expect(document.body.style.overflow).toBe("hidden")
  })

  // 17. Body scroll restored on unmount
  it("restores body scroll on unmount", () => {
    const previousOverflow = "auto"
    document.body.style.overflow = previousOverflow

    const { unmount } = renderSheet()
    expect(document.body.style.overflow).toBe("hidden")

    unmount()
    expect(document.body.style.overflow).toBe(previousOverflow)
  })
})
