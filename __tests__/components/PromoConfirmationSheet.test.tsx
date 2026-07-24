// @vitest-environment jsdom
// ############################################################################
// AI_HEADER: MODULE_TESTS_PROMO_CONFIRMATION_SHEET
// ROLE: Unit tests for PromoConfirmationSheet presentational component.
// DEPENDENCIES: vitest, @testing-library/react, components/promo/promo-confirmation-sheet
// GRACE_ANCHORS: [PROMO_CONFIRMATION_SHEET_TESTS]
// WAVE: W-NAMED-PROMO-CAMPAIGN
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-PROMO-CONFIRMATION-SHEET
// purpose: Validate custom display names rendering, benefit row condition matrix, button click handlers, redeeming disabled state & aria attributes, error role/alert/retry, dialog semantic contract, and absence of token strings.
// owns:
//   - __tests__/components/PromoConfirmationSheet.test.tsx
// inputs: mock props and event handler mocks
// outputs: Vitest assertion results
// dependencies:
//   - M-PROMO-CONFIRMATION-SHEET (components/promo/promo-confirmation-sheet)
// side_effects: renders React components in jsdom environment
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-PROMO-CONFIRMATION-SHEET

// START_MODULE_MAP: M-TESTS-PROMO-CONFIRMATION-SHEET
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - DISPLAY_NAME_TESTS: test rendering of custom campaign names without hardcoded fallback
//   - BENEFIT_MATRIX_TESTS: test conditional rendering of access, credits, natal benefits
//   - INTERACTION_TESTS: test activate, dismiss, close and retry handlers
//   - REDEEMING_STATE_TESTS: test disabled, aria-disabled, aria-busy during redeeming
//   - ERROR_STATE_TESTS: test error alert role, text, and retry button
//   - SEMANTIC_CONTRACT_TESTS: test role=dialog, aria-modal=true, data-state, and data-testid attributes
// owned_tests:
//   - __tests__/components/PromoConfirmationSheet.test.tsx
// END_MODULE_MAP: M-TESTS-PROMO-CONFIRMATION-SHEET

import * as React from "react"
import { describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { PromoConfirmationSheet } from "@/components/promo/promo-confirmation-sheet"
import type { PromoOffer } from "@/packages/contracts"

describe("PromoConfirmationSheet", () => {
  const defaultOffer: PromoOffer = {
    displayName: "Пакет тестера",
    accessDays: 30,
    bonusCredits: 50,
    unlockNatal: true,
  }

  const defaultProps = {
    offer: defaultOffer,
    phase: "ready" as const,
    onActivate: vi.fn(),
    onDismiss: vi.fn(),
  }

  it("renders custom campaign displayName without hardcoded fallback", () => {
    const { rerender } = render(<PromoConfirmationSheet {...defaultProps} />)

    const titleEl = screen.getByTestId("promo-offer-name")
    expect(titleEl.textContent).toContain("Пакет тестера")

    rerender(
      <PromoConfirmationSheet
        {...defaultProps}
        offer={{
          displayName: "Для друзей",
          accessDays: 7,
          bonusCredits: 0,
          unlockNatal: false,
        }}
      />
    )
    expect(screen.getByTestId("promo-offer-name").textContent).toContain("Для друзей")
  })

  it("renders exact conditional benefit matrix", () => {
    // 1. Access only
    const { rerender } = render(
      <PromoConfirmationSheet
        {...defaultProps}
        offer={{
          displayName: "Только Доступ",
          accessDays: 14,
          bonusCredits: 0,
          unlockNatal: false,
        }}
      />
    )
    expect(screen.getByTestId("promo-benefit-access")).toBeDefined()
    expect(screen.queryByTestId("promo-benefit-credits")).toBeNull()
    expect(screen.queryByTestId("promo-benefit-natal")).toBeNull()

    // 2. Credits + Natal only
    rerender(
      <PromoConfirmationSheet
        {...defaultProps}
        offer={{
          displayName: "Вопросы и Натал",
          accessDays: 0,
          bonusCredits: 25,
          unlockNatal: true,
        }}
      />
    )
    expect(screen.queryByTestId("promo-benefit-access")).toBeNull()
    expect(screen.getByTestId("promo-benefit-credits")).toBeDefined()
    expect(screen.getByTestId("promo-benefit-natal")).toBeDefined()

    // 3. All benefits
    rerender(<PromoConfirmationSheet {...defaultProps} />)
    expect(screen.getByTestId("promo-benefit-access")).toBeDefined()
    expect(screen.getByTestId("promo-benefit-credits")).toBeDefined()
    expect(screen.getByTestId("promo-benefit-natal")).toBeDefined()
  })

  it("calls onActivate, onDismiss, and close button handlers", () => {
    const onActivate = vi.fn()
    const onDismiss = vi.fn()

    render(
      <PromoConfirmationSheet
        {...defaultProps}
        onActivate={onActivate}
        onDismiss={onDismiss}
      />
    )

    fireEvent.click(screen.getByTestId("promo-activate"))
    expect(onActivate).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByTestId("promo-dismiss"))
    expect(onDismiss).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole("button", { name: "Закрыть" }))
    expect(onDismiss).toHaveBeenCalledTimes(2)
  })

  it("disables primary button and sets aria-disabled and aria-busy when phase is redeeming", () => {
    const onActivate = vi.fn()

    render(
      <PromoConfirmationSheet
        {...defaultProps}
        phase="redeeming"
        onActivate={onActivate}
      />
    )

    const sheet = screen.getByTestId("promo-confirmation-sheet")
    expect(sheet.getAttribute("data-state")).toBe("redeeming")

    const activateBtn = screen.getByTestId("promo-activate") as HTMLButtonElement
    expect(activateBtn.disabled).toBe(true)
    expect(activateBtn.getAttribute("aria-disabled")).toBe("true")
    expect(activateBtn.getAttribute("aria-busy")).toBe("true")

    fireEvent.click(activateBtn)
    expect(onActivate).not.toHaveBeenCalled()
  })

  it("renders error state with role=alert, error message, and retry button", () => {
    const onRetry = vi.fn()

    render(
      <PromoConfirmationSheet
        {...defaultProps}
        phase="error"
        errorMessage="Срок действия промокода истёк"
        onRetry={onRetry}
      />
    )

    const sheet = screen.getByTestId("promo-confirmation-sheet")
    expect(sheet.getAttribute("data-state")).toBe("error")

    const errorAlert = screen.getByTestId("promo-error")
    expect(errorAlert.getAttribute("role")).toBe("alert")
    expect(errorAlert.textContent).toContain("Срок действия промокода истёк")

    const retryBtn = screen.getByRole("button", { name: "Повторить" })
    fireEvent.click(retryBtn)
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it("satisfies all semantic contract attributes", () => {
    render(<PromoConfirmationSheet {...defaultProps} phase="ready" />)

    const sheet = screen.getByTestId("promo-confirmation-sheet")
    expect(sheet.getAttribute("role")).toBe("dialog")
    expect(sheet.getAttribute("aria-modal")).toBe("true")
    expect(sheet.getAttribute("data-state")).toBe("ready")

    expect(screen.getByTestId("promo-offer-name")).toBeDefined()
    expect(screen.getByTestId("promo-benefits")).toBeDefined()
    expect(screen.getByTestId("promo-activate")).toBeDefined()
    expect(screen.getByTestId("promo-dismiss")).toBeDefined()
  })
})
