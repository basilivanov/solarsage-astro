"use client"

import { Lock } from "lucide-react"
import { cn } from "@/lib/utils"
import {
  WEEKDAYS_MINI,
  formatWeekRange,
  mondayFirstIndex,
  startOfWeek,
} from "@/lib/date"
import { addDays, sameDay } from "@/lib/today"
import { isDayAccessible, type AccessInfo } from "@/lib/access"
import { statusLabel } from "@/lib/calendar"
import { getDayStatus } from "@/lib/api/calendar"
import { MoodIcon } from "@/components/calendar/mood-icon"

type Props = {
  selectedDate: Date
  access: AccessInfo
  onSelect?: (d: Date) => void
}

export function WeekStrip({ selectedDate, access, onSelect }: Props) {
  const start = startOfWeek(selectedDate)
  const days = Array.from({ length: 7 }, (_, i) => addDays(start, i))
  const range = formatWeekRange(start)

  return (
    <section className="px-5" aria-label="Неделя" data-testid="week-strip">
      <div className="mb-3 flex items-baseline justify-between">
        <h3 className="font-serif text-[20px] leading-none tracking-tight">Неделя</h3>
        <span className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground/70">
          {range}
        </span>
      </div>

      <ul className="grid grid-cols-7 gap-[6px]" role="list">
        {days.map((d) => {
          const active = sameDay(d, selectedDate)
          const accessible = isDayAccessible(d, access)
          const status = getDayStatus(d)
          const labelIdx = mondayFirstIndex(d)
          return (
            <li key={d.toISOString()}>
              <button
                type="button"
                onClick={() => onSelect?.(d)}
                aria-label={`${WEEKDAYS_MINI[labelIdx]} ${d.getDate()}, ${statusLabel(status)} день${
                  accessible ? "" : ", требуется доступ"
                }`}
                aria-pressed={active}
                className={cn(
                  "relative flex w-full flex-col items-center gap-1.5 rounded-[12px] border px-0 py-2.5 text-center transition active:scale-[0.96]",
                  active
                    ? "border-primary/50 bg-primary text-primary-foreground shadow-[0_1px_0_0_rgba(0,0,0,0.04)]"
                    : accessible
                      ? "border-border/70 bg-card text-foreground"
                      : "border-border/60 bg-card/60 text-foreground/55",
                )}
              >
                <span
                  className={cn(
                    "text-[9px] font-medium uppercase tracking-[0.08em]",
                    active
                      ? "text-primary-foreground/80"
                      : accessible
                        ? "text-muted-foreground"
                        : "text-muted-foreground/60",
                  )}
                >
                  {WEEKDAYS_MINI[labelIdx]}
                </span>
                <span className="font-serif text-[19px] leading-none">{d.getDate()}</span>
                <span className="flex h-4 items-center justify-center">
                  {accessible ? (
                    <MoodIcon
                      status={status}
                      className={cn(
                        "h-4 w-4",
                        active ? "text-primary-foreground" : "text-foreground",
                      )}
                    />
                  ) : (
                    <Lock
                      aria-hidden
                      className={cn(
                        "h-3 w-3",
                        active ? "text-primary-foreground/80" : "text-muted-foreground/60",
                      )}
                      strokeWidth={1.75}
                    />
                  )}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
