"use client"

import { useState, useEffect } from "react"
import { X, Coins } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

type Props = {
  onClose: () => void
}

export function HoraryPurchaseSheet({ onClose }: Props) {
  const [mounted, setMounted] = useState(false)
  const { toast } = useToast()

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

  const handlePurchase = (_label: string) => {
    toast({
      description: "Оплата будет доступна в ближайшее время",
    })
  }

  const options = [
    { qty: "1 вопрос", price: "50 ★", discount: null },
    { qty: "3 вопроса", price: "120 ★", discount: "−20%" },
    { qty: "5 вопросов", price: "180 ★", discount: "−28%" },
    { qty: "10 вопросов", price: "300 ★", discount: "−40%" },
  ]

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
                Пополнение баланса
              </div>
              <h2 className="mt-1 font-serif text-[24px] leading-tight tracking-tight text-foreground">
                Хорарные вопросы
              </h2>
              <p className="mt-1.5 text-[13px] leading-snug text-muted-foreground">
                Выберите пакет вопросов. Оплата производится через Telegram Stars.
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
            <div className="grid gap-3">
              {options.map((opt, i) => (
                <button
                  key={i}
                  type="button"
                  data-testid={`horary-purchase-option-${i}`}
                  onClick={() => handlePurchase(opt.qty)}
                  className="flex items-center justify-between rounded-2xl border border-border/60 bg-card p-4 transition active:bg-foreground/5 text-left w-full"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary">
                      <Coins className="h-[18px] w-[18px]" />
                    </div>
                    <div>
                      <span className="block font-sans text-[15px] font-medium text-foreground">
                        {opt.qty}
                      </span>
                      {opt.discount && (
                        <span className="inline-block mt-0.5 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-600">
                          Скидка {opt.discount}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="block font-serif text-[18px] font-semibold text-foreground">
                      {opt.price}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

