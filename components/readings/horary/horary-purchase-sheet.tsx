
// ############################################################################
// AI_HEADER: MODULE_HORARY_HORARY_PURCHASE_SHEET
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI horary-purchase-sheet — component
// owns:
//   - components/readings/horary/horary-purchase-sheet.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { useState, useEffect } from "react"
import { X, Coins } from "lucide-react"

type Props = {
  onClose: () => void
}

export function HoraryPurchaseSheet({ onClose }: Props) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    const raf = requestAnimationFrame(() => setMounted(true))
    return () => cancelAnimationFrame(raf)
  }, [])

  // Lock body scroll
  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => {
      document.body.style.overflow = prev
    }
  }, [])

  const close = () => {
    setMounted(false)
    window.setTimeout(onClose, 220)
  }

  return (
    <div className="fixed inset-0 z-50" aria-modal="true" role="dialog" data-testid="horary-purchase-sheet">
      {/* Backdrop */}
      <button
        type="button"
        aria-label="Закрыть"
        onClick={close}
        data-testid="horary-purchase-close"
        className={`absolute inset-0 bg-black/40 transition-opacity duration-200 ${
          mounted ? "opacity-100" : "opacity-0"
        }`}
      />
      {/* Container */}
      <div className="pointer-events-none absolute inset-0 mx-auto flex max-w-md flex-col">
        {/* Sheet */}
        <div
          className={`pointer-events-auto relative mt-auto flex max-h-[85dvh] w-full flex-col overflow-hidden rounded-t-3xl border-x border-t border-border/70 bg-background shadow-2xl transition-transform duration-200 ease-out ${
            mounted ? "translate-y-0" : "translate-y-full"
          }`}
        >
          <div className="mx-auto mt-2.5 h-1 w-10 flex-none rounded-full bg-border" />

          <div className="flex items-start justify-between px-5 pt-4">
            <div className="min-w-0 pr-3">
              <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Платные вопросы
              </div>
              <h2 className="mt-1 font-serif text-[24px] leading-tight tracking-tight text-foreground">
                Хорарные вопросы
              </h2>
              <p className="mt-1.5 text-[13px] leading-snug text-muted-foreground">
                Оплата и пополнение баланса пока недоступны: сначала подключим реальное подтверждение платежа и выдачу вопросов.
              </p>
            </div>
            <button
              type="button"
              onClick={close}
              aria-label="Закрыть"
              data-testid="horary-purchase-close"
              className="flex h-9 w-9 flex-none items-center justify-center rounded-full border border-border/70 bg-card text-foreground/70 transition active:scale-95"
            >
              <X className="h-4 w-4" strokeWidth={1.75} />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-5 pb-8 pt-6">
            <div className="rounded-2xl border border-border/60 bg-muted/20 p-4">
              <div className="flex items-start gap-3">
                <div className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-primary/10 text-primary">
                  <Coins className="h-[18px] w-[18px]" />
                </div>
                <div>
                  <div className="text-[15px] font-medium text-foreground">
                    Пополнение скоро появится
                  </div>
                  <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
                    Сейчас можно использовать еженедельный бесплатный вопрос и бонусы за приглашения.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
