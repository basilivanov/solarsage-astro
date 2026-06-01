"use client"

import { ChevronLeft, ChevronRight, Lock } from "lucide-react"
import { formatDayMonth } from "@/lib/date"
import { sameDay, TODAY } from "@/lib/today"

type Props = {
  date: Date
  onPrev?: () => void
  onNext?: () => void
  canPrev?: boolean
  canNext?: boolean
  /** Если день вне окна доступа — рендерим маленький замок у подписи. */
  locked?: boolean
}

export function DateHeader({
  date,
  onPrev,
  onNext,
  canPrev = true,
  canNext = true,
  locked = false,
}: Props) {
  const isToday = sameDay(date, TODAY)
  return (
    <header className="flex items-center justify-between px-5 pt-3 pb-4">
      <button
        type="button"
        onClick={onPrev}
        disabled={!canPrev}
        aria-label="Предыдущий день"
        className="flex h-10 w-10 items-center justify-center rounded-full border border-border/70 bg-card text-foreground/70 transition active:scale-95 disabled:cursor-not-allowed disabled:opacity-30"
      >
        <ChevronLeft className="h-4 w-4" strokeWidth={1.75} />
      </button>

      <div className="flex flex-col items-center gap-0.5">
        <span className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          {locked ? (
            <Lock className="h-3 w-3" strokeWidth={1.75} />
          ) : null}
          {isToday ? "Сегодня" : "День"}
        </span>
        <span className="font-serif text-[22px] leading-none text-foreground" data-testid="today-headline">
          {formatDayMonth(date)}
        </span>
      </div>

      <button
        type="button"
        onClick={onNext}
        disabled={!canNext}
        aria-label="Следующий день"
        className="flex h-10 w-10 items-center justify-center rounded-full border border-border/70 bg-card text-foreground/70 transition active:scale-95 disabled:cursor-not-allowed disabled:opacity-30"
      >
        <ChevronRight className="h-4 w-4" strokeWidth={1.75} />
      </button>
    </header>
  )
}
