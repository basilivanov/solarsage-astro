
// ############################################################################
// AI_HEADER: MODULE_HORARY_HORARY_PURCHASE_SHEET
// ROLE: Real horary top-up sheet: packs with catalog prices from the API,
//       provider checkout redirect and authenticated purchase-status polling.
//       Quota updates only after a CONFIRMED fulfillment.
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Horary purchase bottom-sheet: lists horary_* packs from the live
//   catalog (prices never hardcoded), starts the one-time payment, opens the
//   provider checkout Telegram-safe and polls the authenticated local status.
// owns:
//   - components/readings/horary/horary-purchase-sheet.tsx
// inputs: onClose, onPurchased (quota refresh of the caller).
// outputs: TSX render with loading/ready/error/waiting states.
// dependencies: lib/api/payment, lib/billing/purchase-flow.
// side_effects: credentialed billing API calls, provider checkout open.
// emitted_logs: n/a
// invariants:
//   - Prices/quota labels come only from GET /api/payment/products.
//   - data-testid=horary-purchase-sheet root exposes data-state.
//   - onPurchased fires only after a confirmed succeeded/consumed status.
// failure_policy: inline error with role=alert; sheet stays open.
// END_MODULE_CONTRACT
"use client"

import { useCallback, useEffect, useState } from "react"
import { X, Coins } from "lucide-react"

import {
  PaymentApiError,
  getPaymentProducts,
  startPurchase,
  type OneTimeProductSlug,
} from "@/lib/api/payment"
import {
  PurchasePollTimeoutError,
  openProviderCheckout,
  pollPurchaseStatus,
} from "@/lib/billing/purchase-flow"
import { formatPriceRubles } from "@/lib/hooks/use-subscription-purchase"
import type { ProductRead } from "@/packages/contracts"

type Props = {
  onClose: () => void
  onPurchased: () => void
}

type Phase = "loading" | "ready" | "error" | "waiting"

export function HoraryPurchaseSheet({ onClose, onPurchased }: Props) {
  const [mounted, setMounted] = useState(false)
  const [phase, setPhase] = useState<Phase>("loading")
  const [packs, setPacks] = useState<ProductRead[]>([])
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [activeSlug, setActiveSlug] = useState<string | null>(null)

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

  const loadPacks = useCallback(async () => {
    setPhase("loading")
    setErrorMessage(null)
    try {
      const res = await getPaymentProducts()
      setPacks(
        res.products.filter(
          (p) => p.productType === "one_time" && p.slug.startsWith("horary_")
        )
      )
      setPhase("ready")
    } catch (error) {
      setPhase("error")
      setErrorMessage(
        error instanceof PaymentApiError
          ? error.message
          : "Не удалось загрузить тарифы. Попробуй ещё раз."
      )
    }
  }, [])

  useEffect(() => {
    void loadPacks()
  }, [loadPacks])

  const close = () => {
    setMounted(false)
    window.setTimeout(onClose, 220)
  }

  const buy = async (pack: ProductRead) => {
    setPhase("waiting")
    setActiveSlug(pack.slug)
    setErrorMessage(null)
    try {
      const started = await startPurchase(pack.slug as OneTimeProductSlug)
      if (started.confirmationUrl) {
        openProviderCheckout(started.confirmationUrl)
      }
      const terminal = await pollPurchaseStatus(started.purchaseId)
      if (terminal.status === "consumed" || terminal.status === "succeeded" || terminal.status === "delivered") {
        onPurchased()
        close()
        return
      }
      setPhase("ready")
      setActiveSlug(null)
      setErrorMessage("Оплата не завершена. Попробуй ещё раз, когда будешь готов(а).")
    } catch (error) {
      setPhase("ready")
      setActiveSlug(null)
      if (error instanceof PurchasePollTimeoutError) {
        setErrorMessage(error.message)
      } else if (error instanceof PaymentApiError) {
        setErrorMessage(error.message)
      } else {
        setErrorMessage("Не удалось начать оплату. Попробуй ещё раз.")
      }
    }
  }

  return (
    <div
      className="fixed inset-0 z-50"
      aria-modal="true"
      role="dialog"
      data-testid="horary-purchase-sheet"
      data-state={phase}
    >
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
                Оплата через ЮKassa. Вопросы появятся на балансе сразу после подтверждения платежа.
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
            {phase === "loading" ? (
              <p className="text-[13px] text-muted-foreground" role="status" data-testid="horary-purchase-loading">
                Загружаем тарифы…
              </p>
            ) : null}

            {phase === "error" ? (
              <div role="alert" data-testid="horary-purchase-error">
                <p className="text-[13px] text-destructive">{errorMessage}</p>
                <button
                  type="button"
                  onClick={() => void loadPacks()}
                  className="mt-3 flex h-10 items-center justify-center rounded-full border border-border/70 px-5 text-[13px] font-medium text-foreground/85 transition active:scale-[0.99]"
                >
                  Повторить
                </button>
              </div>
            ) : null}

            {phase === "ready" || phase === "waiting" ? (
              <div className="flex flex-col gap-2" data-testid="horary-purchase-packs">
                {packs.map((pack) => {
                  const isActive = activeSlug === pack.slug
                  return (
                    <button
                      key={pack.slug}
                      type="button"
                      onClick={() => void buy(pack)}
                      disabled={phase === "waiting"}
                      aria-disabled={phase === "waiting"}
                      data-testid={`horary-pack-${pack.slug}`}
                      className="flex items-center gap-3 rounded-2xl border border-border/60 bg-muted/20 p-4 text-left transition active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-55"
                    >
                      <div className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-primary/10 text-primary">
                        <Coins className="h-[18px] w-[18px]" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-[15px] font-medium text-foreground">
                          {pack.name}
                        </div>
                        <p className="mt-0.5 text-[12.5px] text-muted-foreground">
                          {isActive && phase === "waiting"
                            ? "Ждём подтверждение оплаты…"
                            : `${formatPriceRubles(pack.priceKopecks)} ₽`}
                        </p>
                      </div>
                    </button>
                  )
                })}
                {errorMessage ? (
                  <p className="mt-2 text-[12.5px] text-destructive" role="alert" data-testid="horary-purchase-flow-error">
                    {errorMessage}
                  </p>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}
