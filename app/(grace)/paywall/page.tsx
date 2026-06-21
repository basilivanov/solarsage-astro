"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Crown, Gift, ArrowRight, Check } from "lucide-react"
import { YookassaPaywall } from "@/components/subscription/yookassa-paywall"
import { useShareInvite } from "@/lib/hooks/use-share-invite"

export default function PaywallPage() {
  const router = useRouter()
  const share = useShareInvite()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    const raf = requestAnimationFrame(() => setMounted(true))
    return () => cancelAnimationFrame(raf)
  }, [])

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto flex min-h-screen max-w-md flex-col px-5 py-8">
        {/* Header */}
        <div className="text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <Crown className="h-8 w-8 text-primary" strokeWidth={1.5} />
          </div>
          <h1 className="mt-4 font-serif text-[28px] leading-tight tracking-tight text-foreground">
            Полный доступ к разборам
          </h1>
          <p className="mt-2 text-[14px] leading-relaxed text-muted-foreground">
            Подпишись, чтобы открыть все разборы дней, хорарные вопросы и натальную карту.
          </p>
        </div>

        {/* Benefits */}
        <div className="mt-8 space-y-3">
          {[
            "Ежедневный разбор с транзитами и аспектами",
            "Доступ к прошлым и будущим дням",
            "Хорарные вопросы — задай любой вопрос астрологу",
            "Полная натальная карта с разбором сфер",
            "Календарь с дневным статусом на месяц",
          ].map((benefit, i) => (
            <div key={i} className="flex items-start gap-3">
              <div className="flex h-5 w-5 flex-none items-center justify-center rounded-full bg-emerald-500/10 mt-0.5">
                <Check className="h-3 w-3 text-emerald-600" strokeWidth={2.5} />
              </div>
              <span className="text-[14px] leading-relaxed text-foreground/85">{benefit}</span>
            </div>
          ))}
        </div>

        {/* Pricing */}
        <div className="mt-8 rounded-2xl border border-border/70 bg-card p-5">
          <div className="flex items-baseline justify-between">
            <div>
              <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Подписка
              </div>
              <div className="mt-1 font-serif text-[24px] leading-tight text-foreground">
                199 ₽ / месяц
              </div>
            </div>
            <div className="text-right">
              <div className="text-[11px] text-muted-foreground">или</div>
              <div className="font-serif text-[18px] text-foreground">1990 ₽ / год</div>
              <div className="text-[10px] text-emerald-600">−17%</div>
            </div>
          </div>
        </div>

        {/* CTAs */}
        <div className="mt-6 flex flex-col gap-2">
          <YookassaPaywall
            label="Оформить подписку · 199 ₽/мес"
            className="flex h-12 items-center justify-center gap-2 rounded-full bg-foreground px-6 text-[14px] font-medium text-background transition active:scale-[0.99]"
            onSuccess={() => router.push("/day/today")}
          />
          <button
            type="button"
            onClick={share}
            className="flex h-12 items-center justify-center gap-2 rounded-full border border-border/70 bg-card px-6 text-[14px] font-medium text-foreground/85 transition active:scale-[0.99]"
          >
            <Gift className="h-4 w-4" strokeWidth={1.75} />
            Пригласить друга · +14 дней бесплатно
          </button>
        </div>

        {/* Footnote */}
        <p className="mt-6 text-center text-[11px] leading-relaxed text-muted-foreground">
          Автопродление можно отключить в любой момент. Доступ сохранится до конца оплаченного периода.
        </p>
      </div>
    </main>
  )
}
