
// ############################################################################
// AI_HEADER: MODULE_TODAY_DATE_HEADER
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TODAY-CALENDAR
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Module: date-header.tsx
// owns:
//   - components/today/date-header.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
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

      <div className="relative flex flex-col items-center gap-0.5">
        {/* soft moon-glow behind the date */}
        <div
          aria-hidden
          className="pointer-events-none absolute -top-2 left-1/2 h-16 w-16 -translate-x-1/2 rounded-full"
          style={{
            background:
              "radial-gradient(circle, oklch(0.85 0.04 260 / 0.18) 0%, transparent 70%)",
          }}
        />
        <span className="relative flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          {locked ? (
            <Lock className="h-3 w-3" strokeWidth={1.75} />
          ) : null}
          {isToday ? "Сегодня" : "День"}
        </span>
        <span
          className="relative font-serif text-[22px] leading-none text-foreground"
          data-testid="today-headline"
        >
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
