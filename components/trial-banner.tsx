// AI_HEADER
// module: M-COMPONENTS-TRIAL-BANNER
// wave: W-2.7
// purpose: TrialBanner component (migrated from legacy)

import { Sparkles } from "lucide-react"

function pluralizeDays(n: number): string {
  const abs = Math.abs(n) % 100
  const lastDigit = abs % 10
  if (abs >= 11 && abs <= 19) return "дней"
  if (lastDigit === 1) return "день"
  if (lastDigit >= 2 && lastDigit <= 4) return "дня"
  return "дней"
}

export function TrialBanner({ daysLeft }: { daysLeft: number }) {
  return (
    <div className="mx-5 flex items-center gap-3 rounded-xl border border-border/70 bg-secondary/40 px-4 py-3">
      <div className="flex h-8 w-8 flex-none items-center justify-center rounded-full bg-accent text-accent-foreground">
        <Sparkles className="h-4 w-4" strokeWidth={1.75} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[12px] font-medium text-foreground">
          14 дней бесплатного доступа
        </div>
        <div className="text-[11.5px] text-muted-foreground">
          Осталось {daysLeft} {pluralizeDays(daysLeft)}
        </div>
      </div>
      <button
        type="button"
        className="rounded-full border border-border/70 bg-card px-3 py-1.5 text-[11px] font-medium text-foreground transition active:scale-[0.97]"
      >
        Подписка
      </button>
    </div>
  )
}
