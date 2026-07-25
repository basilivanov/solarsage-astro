
// ############################################################################
// AI_HEADER: MODULE_HORARY_HORARY_QUOTA_BAR
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Module: horary-quota-bar.tsx
// owns:
//   - components/readings/horary/horary-quota-bar.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// public_entrypoints:
//   - HoraryQuotaBar
// semantic_blocks:
//   - HORARY_QUOTA_BAR: Horary quota status bar component
// owned_tests:
//   - __tests__/horary/horary-quota-bar.test.tsx
// END_MODULE_MAP

"use client"

import { Coins } from "lucide-react"
import type { HoraryQuotaRead } from "@/packages/contracts"

type Props = {
  quota: HoraryQuotaRead
  onBuy: () => void
}

// START_BLOCK: HORARY_QUOTA_BAR
export function HoraryQuotaBar({ quota, onBuy }: Props) {
  const {
    weeklyFreeAvailable,
    weeklyFreeExpiresAt,
    nextWeeklyFreeAt,
    bonusCredits,
    paidCredits,
  } = quota

  const totalCredits = (weeklyFreeAvailable ? 1 : 0) + bonusCredits + paidCredits
  const canPurchase = quota.canPurchase === true

  const formatDate = (isoStr?: string | null) => {
    if (!isoStr) return ""
    try {
      const d = new Date(isoStr)
      return d.toLocaleDateString("ru-RU", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      })
    } catch {
      return isoStr
    }
  }

  if (totalCredits === 0) {
    return (
      <div className="rounded-xl border border-destructive/20 bg-destructive/[0.03] p-4 flex items-center justify-between gap-4" data-testid="horary-quota-bar">
        <div>
          <h4 className="font-serif text-[16px] font-semibold text-destructive">
            Вопросы закончились
          </h4>
          {nextWeeklyFreeAt ? (
            <p className="text-[12.5px] text-muted-foreground mt-0.5">
              Новый бесплатный вопрос начислится {formatDate(nextWeeklyFreeAt)}
            </p>
          ) : (
            <p className="text-[12.5px] text-muted-foreground mt-0.5">
              Платное пополнение пока недоступно. Используй еженедельный бесплатный вопрос или бонусы за приглашения.
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={canPurchase ? onBuy : undefined}
          disabled={!canPurchase}
          aria-disabled={!canPurchase}
          className="flex-none rounded-full bg-destructive px-4 py-2 text-[13px] font-medium text-destructive-foreground transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-45 disabled:active:scale-100"
          data-testid="horary-buy-btn"
        >
          {canPurchase ? "Докупить" : "Скоро"}
        </button>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-border/70 bg-card p-4 flex flex-col gap-3.5" data-testid="horary-quota-bar">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Coins className="h-[18px] w-[18px]" />
          </div>
          <div>
            <div className="text-[13px] text-foreground/80">
              Доступно вопросов: <strong className="text-foreground">{totalCredits}</strong>
            </div>
            <div className="flex flex-col gap-0.5 text-[11px] text-muted-foreground mt-0.5">
              {weeklyFreeAvailable ? (
                <span>
                  • Еженедельный бесплатный: <strong className="text-foreground">доступен</strong>
                  {weeklyFreeExpiresAt && ` (сгорит ${formatDate(weeklyFreeExpiresAt)})`}
                </span>
              ) : (
                <span>• Еженедельный бесплатный: использован</span>
              )}
              {paidCredits > 0 && (
                <span>
                  • Купленные: <strong className="text-foreground">{paidCredits}</strong> (не сгорают)
                </span>
              )}
              {bonusCredits > 0 && (
                <span>
                  • Бонусные: <strong className="text-foreground">{bonusCredits}</strong>
                </span>
              )}
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={canPurchase ? onBuy : undefined}
          disabled={!canPurchase}
          aria-disabled={!canPurchase}
          className="rounded-full border border-border/70 bg-card px-3.5 py-1.5 text-[12.5px] font-medium text-foreground transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-45 disabled:active:scale-100"
          data-testid="horary-buy-btn"
        >
          {canPurchase ? "Докупить" : "Скоро"}
        </button>
      </div>
    </div>
  )
}
// END_BLOCK: HORARY_QUOTA_BAR
