
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_PAYWALL
// ROLE: Locked-content paywall with the REAL subscription purchase flow:
//       catalog price from the API, provider checkout redirect and
//       authenticated status polling. No "coming soon" stubs.
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Paywall component: offers the month subscription with the exact
//   catalog price and unlocks only after a CONFIRMED active status poll.
// owns:
//   - components/paywall.tsx
// inputs: title/description/compact/className, optional onUnlocked.
// outputs: TSX render; purchase flow side effects via the shared hook.
// dependencies: useShareInvite, useSubscriptionPurchase.
// side_effects: credentialed billing API calls, provider checkout open.
// emitted_logs: n/a
// invariants:
//   - The CTA is disabled while tariffs load or billing is unavailable —
//     never a fake price, never "скоро появится".
//   - Returning from the provider page is never treated as success.
// failure_policy: inline error text with role=alert.
// END_MODULE_CONTRACT

"use client"

import { Lock, Crown, UserPlus } from "lucide-react"
import { cn } from "@/lib/utils"
import { useShareInvite } from "@/lib/hooks/use-share-invite"
import {
  formatPriceRubles,
  useSubscriptionPurchase,
} from "@/lib/hooks/use-subscription-purchase"

type Props = {
  title?: string
  description?: string
  compact?: boolean
  className?: string
  onUnlocked?: () => void
}

export function Paywall({
  title = "Твой персональный разбор уже готов",
  description = "Полный текст и блок «Почему так у меня» доступны по подписке — или пригласи друга, и вы оба получите 14 дней.",
  compact = false,
  className,
  onUnlocked,
}: Props) {
  const share = useShareInvite()
  const flow = useSubscriptionPurchase(
    onUnlocked ?? (() => window.location.reload())
  )
  const busy = flow.phase === "starting" || flow.phase === "waiting"

  const ctaLabel = busy
    ? "Ждём подтверждение оплаты…"
    : flow.unavailable
      ? "Оплата временно недоступна"
      : !flow.ready
        ? "Загружаем тарифы…"
        : flow.month
          ? `Подписка · ${formatPriceRubles(flow.month.priceKopecks)} ₽/мес`
          : "Подписка недоступна"
  const ctaDisabled = busy || flow.unavailable || !flow.ready || !flow.month

  return (
    <section
      aria-label="Открыть доступ"
      className={cn(
        "mx-5 overflow-hidden rounded-2xl border border-border/70 bg-card",
        compact ? "p-5" : "p-6",
        className,
      )}
      data-testid="paywall"
      data-billing={busy ? "busy" : flow.unavailable ? "unavailable" : flow.ready ? "ready" : "loading"}
    >
      <div className="flex flex-col items-center text-center">
        <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-full border border-border/70 bg-secondary/60 text-muted-foreground">
          <Lock className="h-[18px] w-[18px]" strokeWidth={1.5} />
        </div>
        <h3 className="text-balance font-serif text-[22px] leading-tight tracking-tight text-foreground">
          {title}
        </h3>
        {description ? (
          <p className="mt-2 max-w-[30ch] text-pretty text-[13.5px] leading-relaxed text-muted-foreground">
            {description}
          </p>
        ) : null}
      </div>

      <div className="mt-5 flex flex-col gap-2">
        <button
          type="button"
          onClick={ctaDisabled ? undefined : () => void flow.buy("subscription_month")}
          disabled={ctaDisabled}
          aria-disabled={ctaDisabled}
          data-testid="paywall-subscribe-cta"
          className="inline-flex h-11 items-center justify-center gap-2 rounded-full bg-primary px-5 text-[13px] font-medium text-primary-foreground transition active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-55 disabled:active:scale-100"
        >
          <Crown className="h-4 w-4" strokeWidth={1.75} />
          {ctaLabel}
        </button>
        {flow.errorMessage ? (
          <p className="text-center text-[12px] text-destructive" role="alert" data-testid="paywall-billing-error">
            {flow.errorMessage}
          </p>
        ) : null}
        <button
          type="button"
          onClick={share}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-full border border-border/70 bg-card px-5 text-[13px] font-medium text-foreground transition active:scale-[0.99]"
        >
          <UserPlus className="h-4 w-4" strokeWidth={1.75} />
          Пригласить друга · +14 дней
        </button>
      </div>
    </section>
  )
}
