// ############################################################################
// AI_HEADER: MODULE_PROMO_CONFIRMATION_SHEET
// ROLE: Presentational bottom sheet for named promo campaign offer confirmation.
// DEPENDENCIES: react, lucide-react, packages/contracts
// GRACE_ANCHORS: [PROMO_CONFIRMATION_SHEET]
// WAVE: W-NAMED-PROMO-CAMPAIGN
// ############################################################################

// START_MODULE_CONTRACT: M-PROMO-CONFIRMATION-SHEET
// purpose: Render stateless confirmation bottom sheet displaying campaign display name and conditional benefit rows.
// owns:
//   - components/promo/promo-confirmation-sheet.tsx
// inputs:
//   - PromoConfirmationSheetProps (offer, phase, errorMessage, onActivate, onDismiss, onRetry)
// outputs:
//   - PromoConfirmationSheet React component
// dependencies:
//   - M-CONTRACTS (PromoOffer type)
// side_effects: none (pure presentational component)
// emitted_logs: none
// invariants:
//   - receives only safe offer/phase props; token/campaign ID/hash are not in props or DOM
//   - renders root element with role="dialog", aria-modal="true", data-testid="promo-confirmation-sheet", data-state={phase}
//   - title element has data-testid="promo-offer-name"
//   - benefit list has data-testid="promo-benefits" and conditional items promo-benefit-access, promo-benefit-credits, promo-benefit-natal
//   - primary activate button has data-testid="promo-activate"; while redeeming it sets disabled, aria-disabled="true", aria-busy="true"
//   - secondary dismiss button has data-testid="promo-dismiss"
//   - error state renders data-testid="promo-error" with role="alert" and optional "Повторить" retry button
// failure_policy: none
// END_MODULE_CONTRACT: M-PROMO-CONFIRMATION-SHEET

// START_MODULE_MAP: M-PROMO-CONFIRMATION-SHEET
// public_entrypoints:
//   - PromoConfirmationSheet
//   - PromoConfirmationSheetProps
// semantic_blocks:
//   - SHEET_COMPONENT: PromoConfirmationSheet presentational component
// owned_tests:
//   - __tests__/components/PromoConfirmationSheet.test.tsx
// END_MODULE_MAP: M-PROMO-CONFIRMATION-SHEET

import * as React from "react"
import { X, Calendar, MessageSquare, Sparkles } from "lucide-react"
import type { PromoOffer } from "@/packages/contracts"

export type PromoConfirmationSheetProps = {
  offer: PromoOffer
  phase: "ready" | "redeeming" | "error" | "success"
  errorMessage?: string | null
  onActivate: () => void
  onDismiss: () => void
  onRetry?: () => void
}

function formatAccessDays(days: number): string {
  const mod10 = days % 10
  const mod100 = days % 100
  if (mod10 === 1 && mod100 !== 11) {
    return `${days} день полного доступа`
  }
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return `${days} дня полного доступа`
  }
  return `${days} дней полного доступа`
}

function formatBonusCredits(credits: number): string {
  const mod10 = credits % 10
  const mod100 = credits % 100
  if (mod10 === 1 && mod100 !== 11) {
    return `${credits} бонусный вопрос`
  }
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return `${credits} бонусных вопроса`
  }
  return `${credits} бонусных вопросов`
}

export function PromoConfirmationSheet({
  offer,
  phase,
  errorMessage,
  onActivate,
  onDismiss,
  onRetry,
}: PromoConfirmationSheetProps) {
  // START_FUNCTION_CONTRACT: F-M-PROMO-CONFIRMATION-SHEET.PromoConfirmationSheet
  // purpose: Render stateless promo confirmation bottom sheet.
  // inputs: PromoConfirmationSheetProps
  // returns: JSX.Element
  // side_effects: none
  // emitted_logs: none
  // error_behavior: none
  // END_FUNCTION_CONTRACT: F-M-PROMO-CONFIRMATION-SHEET.PromoConfirmationSheet

  const isRedeeming = phase === "redeeming"

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-xs transition-opacity animate-in fade-in-0 duration-200">
      {/* Backdrop click handler */}
      <div
        className="absolute inset-0"
        onClick={onDismiss}
        aria-hidden="true"
      />

      <div
        role="dialog"
        aria-modal="true"
        data-testid="promo-confirmation-sheet"
        data-state={phase}
        className="relative z-10 w-full max-w-md bg-background border border-border rounded-t-2xl sm:rounded-2xl p-6 shadow-2xl transition-transform animate-in slide-in-from-bottom-5 duration-200"
      >
        {/* Close Button */}
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Закрыть"
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground p-1 rounded-full hover:bg-accent transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header Eyebrow & Title */}
        <div className="space-y-1 mb-4 pr-6">
          <span className="text-xs font-semibold uppercase tracking-wider text-primary">
            Промокод
          </span>
          <h2
            data-testid="promo-offer-name"
            className="text-xl font-bold text-foreground leading-tight"
          >
            {offer.displayName}
          </h2>
          <p className="text-sm text-muted-foreground pt-1">
            По промокоду вам доступно:
          </p>
        </div>

        {/* Benefits List */}
        <ul
          data-testid="promo-benefits"
          className="space-y-3 mb-6 bg-accent/40 rounded-xl p-4 border border-border/50"
        >
          {offer.accessDays > 0 && (
            <li
              data-testid="promo-benefit-access"
              className="flex items-center gap-3 text-sm font-medium text-foreground"
            >
              <Calendar className="w-4 h-4 text-primary shrink-0" />
              <span>{formatAccessDays(offer.accessDays)}</span>
            </li>
          )}
          {offer.bonusCredits > 0 && (
            <li
              data-testid="promo-benefit-credits"
              className="flex items-center gap-3 text-sm font-medium text-foreground"
            >
              <MessageSquare className="w-4 h-4 text-primary shrink-0" />
              <span>{formatBonusCredits(offer.bonusCredits)}</span>
            </li>
          )}
          {offer.unlockNatal && (
            <li
              data-testid="promo-benefit-natal"
              className="flex items-center gap-3 text-sm font-medium text-foreground"
            >
              <Sparkles className="w-4 h-4 text-primary shrink-0" />
              <span>Полный натальный разбор</span>
            </li>
          )}
        </ul>

        {/* Error Alert */}
        {phase === "error" && errorMessage && (
          <div
            role="alert"
            data-testid="promo-error"
            className="mb-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm flex flex-col gap-2"
          >
            <span>{errorMessage}</span>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="self-start text-xs font-semibold underline hover:no-underline text-destructive"
              >
                Повторить
              </button>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-col gap-2 pt-2">
          <button
            type="button"
            data-testid="promo-activate"
            onClick={onActivate}
            disabled={isRedeeming}
            aria-disabled={isRedeeming ? "true" : undefined}
            aria-busy={isRedeeming ? "true" : undefined}
            className="w-full h-11 rounded-xl bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition-all disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2"
          >
            {isRedeeming ? "Активация..." : "Активировать"}
          </button>

          <button
            type="button"
            data-testid="promo-dismiss"
            onClick={onDismiss}
            disabled={isRedeeming}
            className="w-full h-10 rounded-xl text-muted-foreground hover:text-foreground hover:bg-accent transition-colors font-medium text-sm"
          >
            Не сейчас
          </button>
        </div>
      </div>
    </div>
  )
}
