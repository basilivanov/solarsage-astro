// ############################################################################
// AI_HEADER: MODULE_ELECTION_PURCHASE_SHEET
// ROLE: Purchase sheet for election search credit
// ############################################################################

// START_MODULE_CONTRACT: M-ELECTION-PURCHASE-SHEET
// purpose: Render election credit purchase options and process payments.
// owns:
//   - components/readings/election/election-purchase-sheet.tsx
// inputs: open, onClose, onUnlocked
// outputs: ElectionPurchaseSheet React component
// dependencies: lib/api/payment, lib/billing/purchase-flow
// side_effects: Payment checkout flow trigger
// emitted_logs: none
// failure_policy: error alert
// END_MODULE_CONTRACT: M-ELECTION-PURCHASE-SHEET

// START_MODULE_MAP: M-ELECTION-PURCHASE-SHEET
// public_entrypoints:
//   - ElectionPurchaseSheet
// semantic_blocks:
//   - ELECTION_PURCHASE_SHEET_COMPONENT: Purchase modal sheet for election credits
// owned_tests:
//   - __tests__/readings/election-form.test.tsx
// END_MODULE_MAP: M-ELECTION-PURCHASE-SHEET

"use client"

import { useEffect, useState } from "react"
import { X, Sparkles, AlertCircle } from "lucide-react"
import { getPaymentProducts, type Product } from "@/lib/api/payment"
import {
  openProviderCheckout,
  pollPurchaseStatus,
  PurchasePollTimeoutError,
} from "@/lib/billing/purchase-flow"

type Props = {
  open: boolean
  onClose: () => void
  onUnlocked: () => void
}

// START_BLOCK: ELECTION_PURCHASE_SHEET_COMPONENT
export function ElectionPurchaseSheet({ open, onClose, onUnlocked }: Props) {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busySlug, setBusySlug] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    let active = true
    setLoading(true)
    setError(null)

    getPaymentProducts()
      .then((data) => {
        if (!active) return
        const electionProducts = data.products.filter(
          (p) => p.productType === "one_time" && p.slug.startsWith("election_")
        )
        setProducts(electionProducts)
      })
      .catch((err) => {
        if (!active) return
        setError(err instanceof Error ? err.message : "Не удалось загрузить тарифы")
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [open])

  if (!open) return null

  const handleBuy = async (product: Product) => {
    setBusySlug(product.slug)
    setError(null)

    try {
      const { startPurchase } = await import("@/lib/api/payment")
      const startRes = await startPurchase(product.slug as any)
      if (startRes.confirmationUrl) {
        openProviderCheckout(startRes.confirmationUrl)
      }
      await pollPurchaseStatus(startRes.purchaseId)
      onUnlocked()
      onClose()
    } catch (err) {
      if (err instanceof PurchasePollTimeoutError) {
        setError("Оплата обрабатывается. Дождитесь подтверждения.")
      } else {
        setError(err instanceof Error ? err.message : "Ошибка при оплате")
      }
    } finally {
      setBusySlug(null)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm p-0 sm:p-4"
      data-testid="election-purchase-sheet"
    >
      <div className="w-full max-w-md rounded-t-2xl sm:rounded-2xl bg-card border border-border/70 p-6 flex flex-col gap-5 shadow-2xl animate-in slide-in-from-bottom-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-foreground font-serif text-[18px] font-semibold">
            <Sparkles className="h-5 w-5 text-primary" />
            Докупить поиски
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Закрыть"
            className="rounded-full p-1.5 text-muted-foreground hover:bg-secondary transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="flex items-center gap-2 rounded-xl bg-destructive/10 p-3 text-[13px] text-destructive">
            <AlertCircle className="h-4 w-4 flex-none" />
            {error}
          </div>
        )}

        {loading ? (
          <div className="py-8 text-center text-[13px] text-muted-foreground" role="status">
            Загружаем варианты...
          </div>
        ) : products.length === 0 ? (
          <div className="py-6 text-center text-[13px] text-muted-foreground">
            Нет доступных тарифов
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {products.map((p) => {
              const rubles = Math.round(p.priceKopecks / 100)
              const isBusy = busySlug === p.slug
              return (
                <button
                  key={p.slug}
                  type="button"
                  onClick={() => void handleBuy(p)}
                  disabled={!!busySlug}
                  className="flex items-center justify-between rounded-xl border border-border/70 bg-card p-4 text-left transition hover:border-primary/50 active:scale-[0.99] disabled:opacity-50"
                  data-testid={`election-buy-option-${p.slug}`}
                >
                  <div>
                    <div className="text-[14px] font-medium text-foreground">{p.name}</div>
                    {p.description && (
                      <div className="text-[12px] text-muted-foreground mt-0.5">{p.description}</div>
                    )}
                  </div>
                  <div className="text-[15px] font-semibold text-primary">
                    {isBusy ? "Ждём..." : `${rubles} ₽`}
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
// END_BLOCK: ELECTION_PURCHASE_SHEET_COMPONENT
