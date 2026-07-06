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
import { ArrowRight, ChevronLeft, ChevronRight, Lock, Moon } from "lucide-react"

import { MoodIcon } from "@/components/calendar/mood-icon"
import { LunarCalendarStrip } from "@/components/calendar/lunar-calendar-strip"
import { isDayAccessible, type AccessInfo } from "@/lib/access"
import { getMonthCalendar } from "@/lib/api/calendar"
import { dateKey, monthDiff, monthMatrix, statusLabel } from "@/lib/calendar"
import type {
  BackendDayStatus,
  CalendarDayReadModel,
  CalendarPayloadReadModel,
  DayStatus,
} from "@/lib/contracts/calendar"
import { formatLong, MONTHS_RU_NOM, WEEKDAYS_SHORT } from "@/lib/date"
import { TODAY, sameDay } from "@/lib/today"
import { cn } from "@/lib/utils"

type Props = {
  access: AccessInfo
  onOpenDay?: (_date: Date) => void
}

type ViewMode = "day" | "moon"

function normalizeStatus(status: BackendDayStatus | null | undefined): DayStatus {
  if (status === "supportive" || status === "tense") return status
  return "even"
}

function accessAllowed(day: CalendarDayReadModel | undefined, date: Date, fallback: AccessInfo): boolean {
  if (day?.disabled) return false
  if (day?.access) return day.access.state === "full"
  return isDayAccessible(date, fallback)
}

function canOpen(day: CalendarDayReadModel | undefined): boolean {
  return !day?.disabled
}

function hasLunarData(day: CalendarDayReadModel | undefined): boolean {
  const lunar = day?.lunar
  return Boolean(
    lunar
    && (
      lunar.phase
      || lunar.illumination != null
      || lunar.moonSign
      || lunar.lunarDay != null
      || lunar.voidOfCourse != null
    ),
  )
}

function lunarAria(date: Date, day: CalendarDayReadModel | undefined): string {
  if (!hasLunarData(day)) return `${formatLong(date)}, лунные данные недоступны`

  const parts = [
    formatLong(date),
    day?.lunar.phase,
    day?.lunar.lunarDay != null ? `${day.lunar.lunarDay} лунный день` : null,
    day?.lunar.voidOfCourse === true ? "Луна без курса" : null,
  ].filter(Boolean)

  return parts.join(", ")
}

function allowedBoundary(payload: CalendarPayloadReadModel | null, edge: "from" | "to"): Date | null {
  if (!payload) return null
  const value = payload.allowedRange[edge]
  const [year, month] = value.split("-").map(Number)
  return new Date(year, month - 1, 1)
}

export function CalendarScreen({ access, onOpenDay }: Props) {
  const [cursor, setCursor] = useState(
    () => new Date(TODAY.getFullYear(), TODAY.getMonth(), 1),
  )
  const [selected, setSelected] = useState<Date>(TODAY)
  const [payload, setPayload] = useState<CalendarPayloadReadModel | null>(null)
  const [view, setView] = useState<ViewMode>("day")

  const cells = useMemo(
    () => monthMatrix(cursor.getFullYear(), cursor.getMonth()),
    [cursor],
  )

  useEffect(() => {
    let alive = true
    getMonthCalendar(cursor.getFullYear(), cursor.getMonth())
      .then((next) => {
        if (alive) setPayload(next)
      })
      .catch(() => {
        if (alive) setPayload(null)
      })
    return () => {
      alive = false
    }
  }, [cursor])

  const daysByDate = useMemo(() => {
    const entries = (payload?.days ?? []).map((day) => [day.date, day] as const)
    return new Map(entries)
  }, [payload])

  const selectedDay = daysByDate.get(dateKey(selected))
  const selectedStatus = normalizeStatus(selectedDay?.dayStatus)
  const isSelectedAccessible = accessAllowed(selectedDay, selected, access)
  const selectedCanOpen = canOpen(selectedDay)

  const minMonth = allowedBoundary(payload, "from")
  const maxMonth = allowedBoundary(payload, "to")
  const baselineMonth = new Date(TODAY.getFullYear(), TODAY.getMonth(), 1)
  const fallbackDiff = monthDiff(cursor, baselineMonth)
  const canPrev = minMonth ? monthDiff(cursor, minMonth) > 0 : fallbackDiff > -1
  const canNext = maxMonth ? monthDiff(cursor, maxMonth) < 0 : fallbackDiff < 1

  function go(delta: number) {
    const next = new Date(cursor)
    next.setMonth(cursor.getMonth() + delta)
    if (delta < 0 && !canPrev) return
    if (delta > 0 && !canNext) return
    setCursor(next)
  }

  function selectDay(date: Date, day: CalendarDayReadModel | undefined) {
    setSelected(date)
    if (canOpen(day)) onOpenDay?.(date)
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
            {payload?.title || `${MONTHS_RU_NOM[cursor.getMonth()]} ${cursor.getFullYear()}`}
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

      <div className="toggle-track mx-5 mt-3 flex flex-none items-center gap-1 rounded-full p-1">
        <button
          type="button"
          onClick={() => setView("day")}
          aria-pressed={view === "day"}
          className={cn(
            "flex-1 rounded-full px-3 py-1.5 text-[12px] font-medium transition-colors",
            view === "day" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground",
          )}
        >
          Дни
        </button>
        <button
          type="button"
          onClick={() => setView("moon")}
          aria-pressed={view === "moon"}
          className={cn(
            "flex-1 rounded-full px-3 py-1.5 text-[12px] font-medium transition-colors",
            view === "moon" ? "bg-card text-foreground shadow-sm" : "text-muted-foreground",
          )}
        >
          Луна
        </button>
      </div>

      <div className="mt-4 grid flex-none grid-cols-7 px-5">
        {WEEKDAYS_SHORT.map((weekday, index) => (
          <div
            key={weekday}
            className={cn(
              "text-center text-[10px] uppercase tracking-[0.14em]",
              index >= 5 ? "text-muted-foreground/60" : "text-muted-foreground/80",
            )}
          >
            {weekday}
          </div>
        ))}
      </div>

      {view === "day" ? <LunarCalendarStrip days={payload?.days ?? []} /> : null}

      <ol
        role="grid"
        className="mt-2 grid flex-1 grid-cols-7 gap-y-1 px-3 pb-2"
        data-testid="calendar-grid"
      >
        {cells.map(({ date, inMonth }) => {
          const key = dateKey(date)
          const day = daysByDate.get(key)
          const isToday = day?.isToday ?? sameDay(date, TODAY)
          const isSelected = sameDay(date, selected)
          const accessible = accessAllowed(day, date, access)
          const status = normalizeStatus(day?.dayStatus)
          const disabled = !inMonth || day?.disabled === true

          return (
            <li key={key} className="flex items-center justify-center py-1">
              <button
                type="button"
                onClick={() => selectDay(date, day)}
                disabled={disabled}
                aria-pressed={isSelected}
                aria-label={
                  view === "moon"
                    ? lunarAria(date, day)
                    : `${formatLong(date)}, ${statusLabel(status)}${accessible ? "" : ", требуется подписка"}`
                }
                data-testid={`calendar-day-${key}`}
                className={cn(
                  "relative flex h-11 w-11 flex-col items-center justify-center rounded-full transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60",
                  !inMonth && "text-muted-foreground/35",
                  inMonth && !isSelected && !isToday && "text-foreground/85 hover:bg-muted/60",
                  isToday && !isSelected && "text-foreground ring-1 ring-border",
                  isSelected && view === "day" && "bg-primary text-primary-foreground shadow-[0_1px_0_rgba(0,0,0,0.04)]",
                  isSelected && view === "moon" && "bg-primary/10 text-foreground ring-2 ring-primary/50",
                  inMonth && !accessible && !isSelected && "opacity-65",
                  disabled && "cursor-not-allowed opacity-35",
                )}
              >
                {view === "moon" ? (
                  <>
                    <Moon
                      aria-hidden
                      className={cn(
                        "h-4 w-4",
                        hasLunarData(day) ? "text-primary" : "text-muted-foreground/35",
                      )}
                      strokeWidth={1.75}
                    />
                    <span className="mt-0.5 text-[9px] tabular-nums leading-none">
                      {day?.lunar.lunarDay ?? date.getDate()}
                    </span>
                    {day?.lunar.voidOfCourse === true ? (
                      <span
                        className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-amber-500"
                        aria-hidden
                      />
                    ) : null}
                  </>
                ) : (
                  <>
                    <span
                      className={cn(
                        "font-serif leading-none",
                        isSelected ? "text-[16px]" : "text-[15px]",
                      )}
                    >
                      {day?.dayNumber ?? date.getDate()}
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
                  </>
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
            {view === "moon" ? (
              <div className="mt-1 flex flex-wrap items-center gap-2 text-[12px] text-muted-foreground">
                {hasLunarData(selectedDay) ? (
                  <>
                    {selectedDay?.lunar.phase ? <span>{selectedDay.lunar.phase}</span> : null}
                    {selectedDay?.lunar.illumination != null ? (
                      <span className="tabular-nums">{selectedDay.lunar.illumination}%</span>
                    ) : null}
                    {selectedDay?.lunar.lunarDay != null ? (
                      <span>{selectedDay.lunar.lunarDay} лунный день</span>
                    ) : null}
                    {selectedDay?.lunar.voidOfCourse === true ? <span>Луна без курса</span> : null}
                  </>
                ) : (
                  <span>Лунные данные недоступны</span>
                )}
              </div>
            ) : (
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
            )}
          </div>

          <button
            type="button"
            disabled={!selectedCanOpen}
            onClick={() => {
              if (selectedCanOpen) onOpenDay?.(selected)
            }}
            className={cn(
              "inline-flex shrink-0 items-center gap-2 rounded-full border px-4 py-2 text-[12px] font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
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
