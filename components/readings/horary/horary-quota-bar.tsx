"use client"

import { Coins, HelpCircle } from "lucide-react"
import type { HoraryQuota } from "@/lib/contracts/horary"

type Props = {
  quota: HoraryQuota
  onBuy: () => void
}

export function HoraryQuotaBar({ quota, onBuy }: Props) {
  const { left, nextInDays } = quota

  if (left === 0) {
    return (
      <div className="rounded-xl border border-destructive/20 bg-destructive/[0.03] p-4 flex items-center justify-between gap-4">
        <div>
          <h4 className="font-serif text-[16px] font-semibold text-destructive">
            Вопросы закончились
          </h4>
          <p className="text-[12.5px] text-muted-foreground mt-0.5">
            Новый вопрос начислится через {nextInDays} {pluralDays(nextInDays)}
          </p>
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
    <div className="rounded-xl border border-border/70 bg-card p-4 flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Coins className="h-[18px] w-[18px]" />
        </div>
        <div>
          <div className="text-[13px] text-foreground/80">
            Хорарные вопросы: <strong className="text-foreground">{left}</strong>
          </div>
          <p className="text-[12px] text-muted-foreground mt-0.5">
            Следующий через {nextInDays} {pluralDays(nextInDays)}
          </p>
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
  )
}

function pluralDays(n: number) {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return "день"
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return "дня"
  return "дней"
}
