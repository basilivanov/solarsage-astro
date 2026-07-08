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
import { ArrowRight, ChevronLeft, ChevronRight, Lock, Minus } from "lucide-react"

import { MoodIcon } from "@/components/calendar/mood-icon"
import { LunarCalendarStrip } from "@/components/calendar/lunar-calendar-strip"
import type { AccessInfo } from "@/lib/access"
import { getMonthCalendar } from "@/lib/api/calendar"
import { dateKey, monthDiff, monthMatrix, statusLabel } from "@/lib/calendar"
import type {
  BackendDayStatus,
  CalendarDayReadModel,
  CalendarPayloadReadModel,
  DayStatus,
} from "@/lib/contracts/calendar"
import { formatLong, fromDateParam, MONTHS_RU_NOM, WEEKDAYS_SHORT } from "@/lib/date"
import { lunarPhaseGlyph, lunarPhaseLabel } from "@/lib/lunar-presentation"
import { TODAY, sameDay } from "@/lib/today"
import { cn } from "@/lib/utils"

type Props = {
  access: AccessInfo
  onOpenDay?: (_date: Date) => void
}

type ViewMode = "day" | "moon"
type CalendarTone = DayStatus | "unknown"

function normalizeStatus(status: BackendDayStatus | null | undefined): CalendarTone {
  if (status === "supportive" || status === "tense") return status
  if (status === "steady") return "even"
  return "unknown"
}

function statusText(status: CalendarTone): string {
  return status === "unknown" ? "Статус недоступен" : statusLabel(status)
}

function statusAriaText(status: CalendarTone): string {
  return status === "unknown" ? "статус недоступен" : statusLabel(status)
}

function accessAllowed(day: CalendarDayReadModel | undefined): boolean {
  if (!day || day.disabled) return false
  return day.access?.state === "full"
}

function canOpen(day: CalendarDayReadModel | undefined): boolean {
  return Boolean(day) && day?.disabled !== true
}

function hasLunarData(day: CalendarDayReadModel | undefined): boolean {
  const lunar = day?.lunar
  return Boolean(
    lunar
    && (
      lunar.phase
      || lunar.phaseIndex != null
      || lunar.phaseLabel
      || lunar.illumination != null
      || lunar.moonSign
      || lunar.moonSignLabel
      || lunar.lunarDay != null
      || lunar.voidOfCourse != null
    ),
  )
}

function lunarAria(date: Date, day: CalendarDayReadModel | undefined): string {
  if (!hasLunarData(day)) return `${formatLong(date)}, лунные данные недоступны`

  const parts = [
    formatLong(date),
    lunarPhaseLabel(day?.lunar),
    day?.lunar.lunarDay != null ? `${day.lunar.lunarDay} лунный день` : null,
    day?.lunar.voidOfCourse === true ? "Луна без курса" : null,
  ].filter(Boolean)

  return parts.join(", ")
}

function parseCalendarDayDate(raw: string): Date | null {
  return fromDateParam(raw)
}

function allowedBoundary(payload: CalendarPayloadReadModel | null, edge: "from" | "to"): Date | null {
  if (!payload) return null
  const value = payload.allowedRange[edge]
  const [year, month] = value.split("-").map(Number)
  return new Date(year, month - 1, 1)
}

function monthTitle(month: string | null | undefined, fallback: Date): string {
  if (month) {
    const [year, monthNumber] = month.split("-").map(Number)
    if (Number.isInteger(year) && Number.isInteger(monthNumber) && monthNumber >= 1 && monthNumber <= 12) {
      return `${MONTHS_RU_NOM[monthNumber - 1]} ${year}`
    }
  }
  return `${MONTHS_RU_NOM[fallback.getMonth()]} ${fallback.getFullYear()}`
}

export function CalendarScreen({ access, onOpenDay }: Props) {
  const [cursor, setCursor] = useState(
    () => new Date(TODAY.getFullYear(), TODAY.getMonth(), 1),
  )
  const [selected, setSelected] = useState<Date>(TODAY)
  const [payload, setPayload] = useState<CalendarPayloadReadModel | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [payloadError, setPayloadError] = useState(false)
  const [view, setView] = useState<ViewMode>("day")

  useEffect(() => {
    let alive = true
    setIsLoading(true)
    setPayload(null)
    setPayloadError(false)
    getMonthCalendar(cursor.getFullYear(), cursor.getMonth())
      .then((next) => {
        if (alive) {
          setPayload(next)
          setPayloadError(false)
          setIsLoading(false)
        }
      })
      .catch(() => {
        if (alive) {
          setPayload(null)
          setPayloadError(true)
          setIsLoading(false)
        }
      })
    return () => {
      alive = false
    }
  }, [cursor])

  const days = payload?.days ?? []
  const dayByDate = useMemo(() => new Map(days.map((day) => [day.date, day])), [days])
  const displayDays = useMemo(() => {
    const sourceMonth = payload?.month
    if (!sourceMonth) return days
    const [year, monthNumber] = sourceMonth.split("-").map(Number)
    if (!Number.isInteger(year) || !Number.isInteger(monthNumber)) {
      return days.filter((day) => day.isCurrentMonth)
    }
    return monthMatrix(year, monthNumber - 1)
      .map(({ date }) => dayByDate.get(dateKey(date)) ?? null)
      .filter((day): day is CalendarDayReadModel => day !== null)
  }, [dayByDate, days, payload?.month])
  const selectedDay = useMemo(
    () => days.find((day) => {
      const dayDate = parseCalendarDayDate(day.date)
      return dayDate ? sameDay(dayDate, selected) : false
    }),
    [days, selected],
  )
  const selectedStatus = normalizeStatus(selectedDay?.dayStatus)
  const isSelectedAccessible = accessAllowed(selectedDay)
  const selectedCanOpen = canOpen(selectedDay)
  const hasTerminalUnavailable = !isLoading && (payloadError || days.length === 0)
  const loadState = isLoading ? "loading" : hasTerminalUnavailable ? "error" : "ready"

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
    setIsLoading(true)
    setPayload(null)
    setPayloadError(false)
    setCursor(next)
  }

  function selectDay(date: Date, day: CalendarDayReadModel | undefined) {
    if (!day || day.disabled) return
    setSelected(date)
  }

  function renderUnavailableState() {
    return (
      <section
        className="px-5 py-6"
        aria-label="Календарь недоступен"
        data-testid="calendar-unavailable"
      >
        <div className="rounded-lg border border-border/60 bg-card/70 px-4 py-5 text-center">
          <p className="text-sm font-medium text-foreground">Календарь недоступен</p>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            Backend не вернул полные данные месяца. Открытие дней временно недоступно.
          </p>
        </div>
      </section>
    )
  }

  function renderLoadingState() {
    return (
      <section
        className="px-5 py-6"
        aria-label="Загрузка календаря"
        data-testid="calendar-loading"
      >
        <div className="rounded-lg border border-border/60 bg-card/70 px-4 py-5 text-center">
          <p className="text-sm font-medium text-foreground">Загружаем календарь</p>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            Ждём реальные данные месяца от backend.
          </p>
        </div>
      </section>
    )
  }

  return (
    <div
      className="flex h-full w-full flex-col"
      data-load-state={loadState}
      data-testid="calendar-screen"
    >
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
          <h1 className="font-serif text-[22px] leading-none tracking-tight text-foreground" data-testid="calendar-month-header">
            {monthTitle(payload?.month, cursor)}
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
          aria-label="Дни"
          data-testid="calendar-view-day"
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
          aria-label="Луна"
          data-testid="calendar-view-moon"
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

      {isLoading ? (
        renderLoadingState()
      ) : hasTerminalUnavailable ? (
        renderUnavailableState()
      ) : (
        <>
          {view === "day" ? <LunarCalendarStrip days={days} /> : null}

          <ol
            role="grid"
            className="mt-2 grid flex-1 grid-cols-7 gap-y-1 px-3 pb-2"
            data-testid="calendar-grid"
          >
            {displayDays.map((day) => {
              const date = parseCalendarDayDate(day.date)
              if (!date) return null
              const isToday = day.isToday || sameDay(date, TODAY)
              const isSelected = sameDay(date, selected)
              const accessible = accessAllowed(day)
              const status = normalizeStatus(day.dayStatus)
              const disabled = day.disabled === true

              return (
                <li key={day.date} className="flex items-center justify-center py-1">
                  <button
                    type="button"
                    onClick={() => selectDay(date, day)}
                    disabled={disabled}
                    aria-pressed={isSelected}
                    aria-label={
                      view === "moon"
                        ? lunarAria(date, day)
                        : `${formatLong(date)}, ${statusAriaText(status)}${accessible ? "" : ", требуется подписка"}`
                    }
                    data-testid={`calendar-day-${day.date}`}
                    className={cn(
                      "relative flex h-11 w-11 flex-col items-center justify-center rounded-full transition-colors",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60",
                      !day.isCurrentMonth && "text-muted-foreground/35",
                      day.isCurrentMonth && !isSelected && !isToday && "text-foreground/85 hover:bg-muted/60",
                      isToday && !isSelected && "text-foreground ring-1 ring-border",
                      isSelected && view === "day" && "bg-primary text-primary-foreground shadow-[0_1px_0_rgba(0,0,0,0.04)]",
                      isSelected && view === "moon" && "bg-primary/10 text-foreground ring-2 ring-primary/50",
                      day.isCurrentMonth && !accessible && !isSelected && "opacity-65",
                      disabled && "cursor-not-allowed opacity-35",
                    )}
                  >
                    {view === "moon" ? (
                      <>
                        <span
                          className={cn(
                            "text-[15px] leading-none",
                            hasLunarData(day) ? "text-primary" : "text-muted-foreground/35",
                          )}
                          data-testid={`calendar-moon-glyph-${day.date}`}
                          aria-hidden
                        >
                          {lunarPhaseGlyph(day.lunar)}
                        </span>
                        <span
                          className="mt-0.5 text-[9px] tabular-nums leading-none"
                          data-testid={`calendar-moon-day-${day.date}`}
                        >
                          {day.lunar.lunarDay != null ? day.lunar.lunarDay : "—"}
                        </span>
                        {day.lunar.voidOfCourse === true ? (
                          <span
                            className="absolute right-1 top-1 h-1.5 w-1.5 rounded-full bg-amber-500"
                            aria-hidden
                          />
                        ) : null}
                        {isToday ? (
                          <span
                            className="absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full bg-amber-500"
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
                          {day.dayNumber}
                        </span>

                        {day.isCurrentMonth && accessible && status !== "unknown" ? (
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
                        ) : null}

                        {day.isCurrentMonth && accessible && status === "unknown" ? (
                          <Minus
                            aria-hidden
                            className={cn(
                              "mt-0.5 h-3 w-3",
                              isSelected ? "text-primary-foreground/85" : "text-muted-foreground/45",
                            )}
                            strokeWidth={1.75}
                          />
                        ) : null}

                        {day.isCurrentMonth && !accessible && !isSelected && (
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
            data-testid="calendar-selected-summary"
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
                        <span className="text-[14px] leading-none" aria-hidden>{lunarPhaseGlyph(selectedDay?.lunar)}</span>
                        {lunarPhaseLabel(selectedDay?.lunar) ? <span>{lunarPhaseLabel(selectedDay?.lunar)}</span> : null}
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
                ) : selectedDay ? (
                  <div className="mt-1 flex items-center gap-2 text-[12px] text-muted-foreground">
                    <MoodIcon
                      status={selectedStatus === "unknown" ? "even" : selectedStatus}
                      className={cn(
                        "h-3.5 w-3.5",
                        selectedStatus === "unknown"
                          ? "hidden"
                          : selectedStatus === "tense"
                            ? "text-foreground/70"
                            : selectedStatus === "supportive"
                              ? "text-primary"
                              : "text-foreground/45",
                      )}
                    />
                    {selectedStatus === "unknown" ? (
                      <Minus
                        aria-hidden
                        className="h-3.5 w-3.5 text-muted-foreground/45"
                        strokeWidth={1.75}
                      />
                    ) : null}
                    <span>{statusText(selectedStatus)}</span>
                    {!isSelectedAccessible ? (
                      <span className="inline-flex items-center gap-1 text-muted-foreground/80">
                        <span aria-hidden>·</span>
                        <Lock className="h-3 w-3" strokeWidth={1.75} />
                        <span>недоступен</span>
                      </span>
                    ) : null}
                  </div>
                ) : (
                  <div className="mt-1 text-[12px] text-muted-foreground">
                    Данные дня недоступны
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
                    <span>{selectedDay ? "Открыть превью" : "Недоступно"}</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
