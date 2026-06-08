"use client"

import { Coins } from "lucide-react"
import type { HoraryQuota } from "@/lib/contracts/horary"

type Props = {
  quota: HoraryQuota
  onBuy: () => void
}

export function HoraryQuotaBar({ quota, onBuy }: Props) {
  const {
    weeklyFreeAvailable,
    weeklyFreeExpiresAt,
    nextWeeklyFreeAt,
    bonusCredits,
    paidCredits,
  } = quota

  const totalCredits = (weeklyFreeAvailable ? 1 : 0) + bonusCredits + paidCredits

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
      <div className="rounded-xl border border-destructive/20 bg-destructive/[0.03] p-4 flex items-center justify-between gap-4">
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
              Оформи подписку или пригласи друга, чтобы получить новые вопросы.
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={onBuy}
          className="flex-none rounded-full bg-destructive text-destructive-foreground px-4 py-2 text-[13px] font-medium transition active:scale-[0.98]"
        >
          Докупить
        </button>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-border/70 bg-card p-4 flex flex-col gap-3.5">
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
          onClick={onBuy}
          className="rounded-full border border-border/70 bg-card px-3.5 py-1.5 text-[12.5px] font-medium text-foreground transition active:scale-[0.98]"
        >
          Докупить
        </button>
      </div>
    </div>
  )
}
