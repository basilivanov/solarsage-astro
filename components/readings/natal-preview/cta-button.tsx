
// ############################################################################
// AI_HEADER: MODULE_NATAL-PREVIEW_CTA_BUTTON
// ROLE: Full natal report CTA: watch a ready report, buy it via the real
//       YooKassa flow (catalog price), or an honest disabled state while the
//       feature is off. Never a fake price, never a bare "coming soon" when
//       the purchase is actually available.
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Natal full-report CTA button with buy/watch/disabled states.
// owns:
//   - components/readings/natal-preview/cta-button.tsx
// inputs: priceKopecks (from API), hasReport, busy, errorMessage, onClick, disabled.
// outputs: TSX render.
// dependencies: local modules.
// side_effects: none (pure render; flow lives in the page).
// emitted_logs: n/a (pure)
// invariants:
//   - The priced label renders only from the API price (no literals).
//   - disabled means "feature off / not purchasable": honest stub, no CTA.
// failure_policy: errorMessage rendered with role=alert.
// END_MODULE_CONTRACT
"use client"

import { Sparkles } from "lucide-react"

type Props = {
  priceKopecks: number
  hasReport?: boolean
  busy?: boolean
  errorMessage?: string | null
  onClick?: () => void
  disabled?: boolean
}

export function CtaButton({
  priceKopecks,
  hasReport = false,
  busy = false,
  errorMessage = null,
  onClick,
  disabled = false,
}: Props) {
  const price = Math.round(priceKopecks / 100)
  const isDisabled = disabled || busy
  const label = busy
    ? "Ждём подтверждение оплаты…"
    : disabled
      ? "Полный отчёт скоро появится"
      : hasReport
        ? "Смотреть полный отчёт"
        : `Полный отчёт за ${price} ₽`
  const description = disabled
    ? "Оплата и доступ откроются после подключения выдачи."
    : "Разбор по точным данным рождения · 13 разделов"

  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={isDisabled ? undefined : onClick}
        disabled={isDisabled}
        aria-disabled={isDisabled}
        data-testid="natal-full-report-cta-button"
        data-state={busy ? "busy" : disabled ? "disabled" : "ready"}
        className="group relative w-full overflow-hidden rounded-2xl bg-primary px-4 py-4 text-center transition active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-55 disabled:active:scale-100"
      >
        <div className="absolute inset-0 bg-gradient-to-r from-primary to-primary/90" />
        <div className="relative flex items-center justify-center gap-2">
          <Sparkles className="h-4 w-4 text-primary-foreground/80" />
          <span className="text-[16px] font-semibold text-primary-foreground">
            {label}
          </span>
        </div>
      </button>
      {errorMessage ? (
        <p className="text-center text-[12px] text-destructive" role="alert" data-testid="natal-cta-error">
          {errorMessage}
        </p>
      ) : null}
      <p className="text-center text-[11px] text-muted-foreground/60">
        {description}
      </p>
    </div>
  )
}
