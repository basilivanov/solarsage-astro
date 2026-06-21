
// ############################################################################
// AI_HEADER: MODULE_CALENDAR_CALENDAR_SCREEN
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TODAY-CALENDAR
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI calendar-screen — component
// owns:
//   - components/calendar/calendar-screen.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { useEffect, useMemo, useState } from "react"
import { ChevronLeft, ChevronRight, Lock, ArrowRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { MONTHS_RU_NOM, WEEKDAYS_SHORT, formatLong } from "@/lib/date"
import { TODAY, sameDay } from "@/lib/today"
import { isDayAccessible, type AccessInfo } from "@/lib/access"
import { dateKey, monthMatrix, monthDiff, statusLabel } from "@/lib/calendar"
import { getMonthStatuses } from "@/lib/api/calendar"
import { MoodIcon } from "@/components/calendar/mood-icon"

type Props = {
  access: AccessInfo
  onOpenDay?: (_date: Date) => void
}

export function CalendarScreen({ access, onOpenDay }: Props) {
  const [cursor, setCursor] = useState(
    () => new Date(TODAY.getFullYear(), TODAY.getMonth(), 1),
  )
  const [selected, setSelected] = useState<Date>(TODAY)

  // Навигация по месяцам: для MVP разрешаем ±1 месяц от сегодняшнего
  const diff = monthDiff(
    cursor,
    new Date(TODAY.getFullYear(), TODAY.getMonth(), 1),
  )
  const canPrev = diff > -1
  const canNext = diff < 1

  const cells = useMemo(
    () => monthMatrix(cursor.getFullYear(), cursor.getMonth()),
    [cursor],
  )

  // Статусы дней приходят пакетом на месяц через API-фасад.
  const [statuses, setStatuses] = useState<Record<string, "supportive" | "tense" | "even">>({})

  useEffect(() => {
    getMonthStatuses(cursor.getFullYear(), cursor.getMonth())
      .then(setStatuses)
      .catch(() => setStatuses({}))
  }, [cursor])

  const selectedStatus = statuses[dateKey(selected)] ?? "even"
  const isSelectedAccessible = isDayAccessible(selected, access)

  function go(delta: number) {
    const next = new Date(cursor)
    next.setMonth(cursor.getMonth() + delta)
    const clampDiff = monthDiff(
      next,
      new Date(TODAY.getFullYear(), TODAY.getMonth(), 1),
    )
    if (clampDiff < -1 || clampDiff > 1) return
    setCursor(next)
  }

  return (
    <div className="flex h-full w-full flex-col">
      <header
        className="flex flex-none items-center justify-between px-5 pb-4"
        style={{ paddingTop: "max(env(safe-area-inset-top), 1.25rem)" }}
      >
        <button
          type="button"
          onClick={() => go(-1)}
          disabled={!canPrev}
          aria-label="Предыдущий месяц"
          className="flex h-10 w-10 items-center justify-center rounded-full border border-border/70 bg-card text-foreground/70 transition active:scale-95 disabled:cursor-not-allowed disabled:opacity-30"
        >
          <ChevronLeft className="h-4 w-4" strokeWidth={1.75} />
        </button>

        <div className="flex flex-col items-center gap-0.5">
          <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Календарь
          </span>
          <h1 className="font-serif text-[22px] leading-none tracking-tight text-foreground">
            {MONTHS_RU_NOM[cursor.getMonth()]} {cursor.getFullYear()}
          </h1>
        </div>

        <button
          type="button"
          onClick={() => go(1)}
          disabled={!canNext}
          aria-label="Следующий месяц"
          className="flex h-10 w-10 items-center justify-center rounded-full border border-border/70 bg-card text-foreground/70 transition active:scale-95 disabled:cursor-not-allowed disabled:opacity-30"
        >
          <ChevronRight className="h-4 w-4" strokeWidth={1.75} />
        </button>
      </header>

      <div className="mx-5 h-px flex-none bg-border/60" />

      <div className="mt-4 grid flex-none grid-cols-7 px-5">
        {WEEKDAYS_SHORT.map((w, i) => (
          <div
            key={w}
            className={cn(
              "text-center text-[10px] uppercase tracking-[0.14em]",
              i >= 5 ? "text-muted-foreground/60" : "text-muted-foreground/80",
            )}
          >
            {w}
          </div>
        ))}
      </div>

      <ol
        role="grid"
        className="mt-2 grid flex-1 grid-cols-7 gap-y-1 px-3 pb-2"
      >
        {cells.map(({ date, inMonth }) => {
          const isToday = sameDay(date, TODAY)
          const isSelected = sameDay(date, selected)
          const accessible = isDayAccessible(date, access)
          const status = statuses[dateKey(date)] ?? "even"

          return (
            <li
              key={date.toISOString()}
              className="flex items-center justify-center py-1"
            >
              <button
                type="button"
                onClick={() => {
                  setSelected(date)
                  // Тап по дню всегда ведёт на /day/:date.
                  // TodayScreen сам решит, показать полный разбор или
                  // preview с paywall — календарь в этом не участвует.
                  // Это убирает дублирование логики доступа.
                  onOpenDay?.(date)
                }}
                aria-pressed={isSelected}
                aria-label={`${formatLong(date)}, ${statusLabel(status)}${
                  accessible ? "" : ", требуется подписка"
                }`}
                className={cn(
                  "relative flex h-11 w-11 flex-col items-center justify-center rounded-full text-[15px] transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60",
                  !inMonth && "text-muted-foreground/35",
                  inMonth &&
                    !isSelected &&
                    !isToday &&
                    "text-foreground/85 hover:bg-muted/60",
                  isToday && !isSelected && "text-foreground ring-1 ring-border",
                  isSelected &&
                    "bg-primary text-primary-foreground shadow-[0_1px_0_rgba(0,0,0,0.04)]",
                  inMonth && !accessible && !isSelected && "opacity-65",
                )}
              >
                <span
                  className={cn(
                    "font-serif leading-none",
                    isSelected ? "text-[16px]" : "text-[15px]",
                  )}
                >
                  {date.getDate()}
                </span>

                {inMonth && accessible && (
                  <MoodIcon
                    status={status}
                    className={cn(
                      "mt-0.5 h-3 w-3",
                      isSelected
                        ? "text-primary-foreground"
                        : status === "tense"
                          ? "text-foreground/65"
                          : status === "supportive"
                            ? "text-primary"
                            : "text-foreground/40",
                    )}
                  />
                )}

                {inMonth && !accessible && !isSelected && (
                  <Lock
                    aria-hidden
                    className="absolute right-1.5 top-1.5 h-[9px] w-[9px] text-muted-foreground/50"
                    strokeWidth={1.75}
                  />
                )}
              </button>
            </li>
          )
        })}
      </ol>

      <div
        className="flex-none border-t border-border/60 bg-card/60 px-5 pt-4"
        style={{ paddingBottom: "max(env(safe-area-inset-bottom), 1rem)" }}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              {sameDay(selected, TODAY) ? "Сегодня" : "Выбранный день"}
            </div>
            <div className="mt-1 truncate font-serif text-[20px] leading-tight tracking-tight text-foreground">
              {formatLong(selected)}
            </div>
            <div className="mt-1 flex items-center gap-2 text-[12px] text-muted-foreground">
              <MoodIcon
                status={selectedStatus}
                className={cn(
                  "h-3.5 w-3.5",
                  selectedStatus === "tense"
                    ? "text-foreground/70"
                    : selectedStatus === "supportive"
                      ? "text-primary"
                      : "text-foreground/45",
                )}
              />
              <span>{statusLabel(selectedStatus)}</span>
              {!isSelectedAccessible ? (
                <span className="inline-flex items-center gap-1 text-muted-foreground/80">
                  <span aria-hidden>·</span>
                  <Lock className="h-3 w-3" strokeWidth={1.75} />
                  <span>недоступен</span>
                </span>
              ) : null}
            </div>
          </div>

          <button
            type="button"
            onClick={() => onOpenDay?.(selected)}
            className={cn(
              "inline-flex shrink-0 items-center gap-2 rounded-full border px-4 py-2 text-[12px] font-medium transition-colors",
              isSelectedAccessible
                ? "border-foreground/85 bg-foreground text-background hover:bg-foreground/90"
                : "border-border/70 bg-card text-foreground",
            )}
          >
            {isSelectedAccessible ? (
              <>
                <span>Открыть день</span>
                <ArrowRight className="h-3.5 w-3.5" strokeWidth={1.8} />
              </>
            ) : (
              <>
                <Lock className="h-3.5 w-3.5" strokeWidth={1.8} />
                <span>Открыть превью</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

