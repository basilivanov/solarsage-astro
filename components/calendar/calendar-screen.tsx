// ############################################################################
// AI_HEADER: MODULE_CALENDAR_CALENDAR_SCREEN — legacy calendar layout on calendar/v2.
// ROLE: Loads one generated month and renders the restored day/moon calendar surface.
// ############################################################################

// START_MODULE_CONTRACT: M-CALENDAR-CALENDAR-SCREEN
// purpose: Render the legacy calendar layout with generated calendar/v2 dayState markers, deterministic dayTone dots, lunar facts, and a safe-area-aware top header.
// owns:
//   - components/calendar/calendar-screen.tsx
// inputs: optional access/onOpenDay compatibility props; current local month.
// outputs: calendar-screen root, safe-area-aware month navigation, day/moon toggle, calendar grid, and selected-day action.
// dependencies: getMonthCalendar; lunar presentation components; generated CalendarPayload; date utilities.
// side_effects: Credentialed monthly calendar fetches; onOpenDay callback when the selected day is opened.
// emitted_logs: Delegated ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, frontend.api_response_invalid.
// invariants:
//   - Calendar data is read from generated CalendarPayload; dayState is never projected to valence labels and tone dots render only for a non-null dayTone.
//   - The restored layout owns one month heading and one calendar grid.
//   - Every day cell reserves a fixed marker slot, so day numbers never shift vertically; hero = ring + tone dot, not-computed = empty circle, ordinary = tone dot.
//   - access.state !== full renders a locked day with reduced opacity and a lock icon.
// failure_policy: HTTP/schema failures render the public error state and no partial grid.
// END_MODULE_CONTRACT: M-CALENDAR-CALENDAR-SCREEN

// START_MODULE_MAP: M-CALENDAR-CALENDAR-SCREEN
// public_entrypoints:
//   - CalendarScreen
// semantic_blocks:
//   - CALENDAR_FETCH: month cursor and generated payload lifecycle.
//   - CALENDAR_NAVIGATION: allowed-range previous/next controls and selected-day callback.
//   - CALENDAR_RENDER: restored safe-area-aware header, day/moon toggle, lunar strip, and 7-column grid.
// owned_tests:
//   - __tests__/components/CalendarScreen.test.tsx
//   - e2e/mock-visual/calendar.spec.ts
// END_MODULE_MAP: M-CALENDAR-CALENDAR-SCREEN

"use client"

import { useEffect, useMemo, useState } from "react"
import {
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  Lock,
} from "lucide-react"
import { motion } from "framer-motion"

import { LunarCalendarStrip } from "@/components/calendar/lunar-calendar-strip"
import { PhaseGlyph } from "@/components/calendar/phase-glyph"
import type { AccessInfo } from "@/lib/access"
import { getMonthCalendar, type CalendarPayloadReadModel } from "@/lib/api/calendar"
import { dateKey, monthDiff, monthMatrix } from "@/lib/calendar"
import type { CalendarDayReadModel } from "@/lib/contracts/calendar"
import { formatLong, fromDateParam, MONTHS_RU_NOM, WEEKDAYS_SHORT } from "@/lib/date"
import { lunarPhaseLabel } from "@/lib/lunar-presentation"
import { TODAY, sameDay } from "@/lib/today"
import { cn } from "@/lib/utils"

type Props = {
  access?: AccessInfo
  onOpenDay?: (_date: Date) => void
}

type ViewMode = "day" | "moon"
type LoadState = "loading" | "ready" | "error"
type CalendarDay = CalendarPayloadReadModel["days"][number]
type CalendarDayTone = NonNullable<CalendarDay["dayTone"]>

const DAY_TONE_DOTS: Record<CalendarDayTone, { dotClass: string; label: string }> = {
  steady: { dotClass: "bg-foreground/25", label: "ровный тон дня" },
  supportive: { dotClass: "bg-[#43806d]", label: "поддерживающий тон дня" },
  mixed: { dotClass: "bg-foreground/55", label: "смешанный тон дня" },
  tense: { dotClass: "bg-[#b07b36]", label: "напряжённый тон дня" },
}

function accessAllowed(day: CalendarDay | undefined): boolean {
  if (!day || day.disabled) return false
  return day.access?.state === "full"
}

function canOpen(day: CalendarDay | undefined): boolean {
  return Boolean(day) && day?.disabled !== true
}

function hasLunarData(day: CalendarDay | undefined): boolean {
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

function lunarAria(date: Date, day: CalendarDay | undefined): string {
  if (!hasLunarData(day)) return `${formatLong(date)}, лунные данные недоступны`

  const parts = [
    formatLong(date),
    lunarPhaseLabel(day?.lunar),
    day?.lunar?.lunarDay != null ? `${day.lunar.lunarDay} лунный день` : null,
    day?.lunar?.voidOfCourse === true ? "Луна без курса" : null,
  ].filter(Boolean)

  return parts.join(", ")
}

function dayTonePresentation(dayTone: CalendarDay["dayTone"]): { dotClass: string; label: string } | null {
  // START_FUNCTION_CONTRACT: F-M-CALENDAR-CALENDAR-SCREEN.dayTonePresentation
  // purpose: Resolve the colored tone dot from the generated dayTone enum.
  // inputs: nullable CalendarDay.dayTone from the validated calendar payload.
  // returns: dot class and aria label for a known tone, or null when the snapshot has no tone.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: no dot is rendered for null; unknown runtime values are ignored.
  // END_FUNCTION_CONTRACT: F-M-CALENDAR-CALENDAR-SCREEN.dayTonePresentation
  if (!dayTone) return null
  return DAY_TONE_DOTS[dayTone] ?? null
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

function withLunarDefaults(days: CalendarDay[]): CalendarDayReadModel[] {
  return days.map((day) => ({
    ...day,
    lunar: day.lunar ?? {},
  }))
}

// START_BLOCK: CALENDAR_FETCH
export function CalendarScreen({ onOpenDay }: Props = {}) {
  // START_FUNCTION_CONTRACT: F-M-CALENDAR-CALENDAR-SCREEN.CalendarScreen
  // purpose: Load the selected month and render the restored calendar lifecycle.
  // inputs: onOpenDay — optional callback for the selected day; access is accepted for route compatibility.
  // returns: calendar-screen DOM contract with dayState cells, dayTone icons, and day/moon presentation modes.
  // side_effects: GET /api/calendar?month=YYYY-MM whenever the cursor changes; invokes onOpenDay on CTA activation.
  // emitted_logs: Delegated ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed, frontend.api_response_invalid.
  // error_behavior: failed requests render role=alert with data-state=error.
  // END_FUNCTION_CONTRACT: F-M-CALENDAR-CALENDAR-SCREEN.CalendarScreen
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
  // END_BLOCK: CALENDAR_FETCH

  // START_BLOCK: CALENDAR_NAVIGATION
  const days = useMemo(() => payload?.days ?? [], [payload?.days])
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
      .filter((day): day is CalendarDay => day !== null)
  }, [dayByDate, days, payload?.month])
  const lunarStripDays = useMemo(() => withLunarDefaults(days), [days])
  const selectedDay = useMemo(
    () => days.find((day) => {
      const dayDate = parseCalendarDayDate(day.date)
      return dayDate ? sameDay(dayDate, selected) : false
    }),
    [days, selected],
  )
  const isSelectedAccessible = accessAllowed(selectedDay)
  const selectedCanOpen = canOpen(selectedDay)
  const hasTerminalUnavailable = !isLoading && (payloadError || days.length === 0)
  const loadState: LoadState = isLoading ? "loading" : hasTerminalUnavailable ? "error" : "ready"

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

  function selectDay(date: Date, day: CalendarDay | undefined) {
    if (!day || day.disabled) return
    setSelected(date)
  }
  // END_BLOCK: CALENDAR_NAVIGATION

  // START_BLOCK: CALENDAR_RENDER
  function renderUnavailableState() {
    return (
      <section
        className="px-5 py-6"
        aria-label="Календарь недоступен"
        data-testid="calendar-error"
        role="alert"
      >
        <div
          className="rounded-[24px] border border-border/40 bg-card px-4 py-5 text-center shadow-(--shadow-card)"
          data-testid="calendar-unavailable"
        >
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
        role="status"
      >
        <div className="rounded-[24px] border border-border/40 bg-card px-4 py-5 text-center shadow-(--shadow-card)">
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
      data-state={loadState}
      data-load-state={loadState}
      data-testid="calendar-screen"
      aria-busy={loadState === "loading" ? true : undefined}
      aria-label="Календарь"
    >
      <header
        className="flex flex-none items-center justify-between px-5 pb-4"
        style={{ paddingTop: "max(var(--tg-content-safe-area-inset-top, 0px), env(safe-area-inset-top), 1.25rem)" }}
        data-testid="calendar-header"
      >
        <button
          type="button"
          onClick={() => go(-1)}
          disabled={!canPrev}
          aria-label="Предыдущий месяц"
          className="flex h-9 w-9 items-center justify-center rounded-full border border-border/50 bg-card text-foreground/70 shadow-(--shadow-card) transition active:scale-95 disabled:cursor-not-allowed disabled:opacity-30"
        >
          <ChevronLeft className="h-4 w-4" strokeWidth={1.75} />
        </button>

        <div className="flex flex-col items-center gap-0.5">
          <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground/80">
            Календарь
          </span>
          <h1
            className="font-serif text-[22px] leading-none tracking-tight text-foreground"
            data-testid="calendar-month-header"
          >
            {monthTitle(payload?.month, cursor)}
          </h1>
        </div>

        <button
          type="button"
          onClick={() => go(1)}
          disabled={!canNext}
          aria-label="Следующий месяц"
          className="flex h-9 w-9 items-center justify-center rounded-full border border-border/50 bg-card text-foreground/70 shadow-(--shadow-card) transition active:scale-95 disabled:cursor-not-allowed disabled:opacity-30"
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
            "relative flex-1 rounded-full px-3 py-1.5 text-[12px] font-medium transition-colors",
            view === "day" ? "text-foreground" : "text-muted-foreground hover:text-foreground/80",
          )}
        >
          {view === "day" ? (
            <motion.span
              layoutId="cal-toggle"
              className="absolute inset-0 rounded-full bg-card shadow-(--shadow-card)"
              transition={{ type: "spring", stiffness: 380, damping: 30 }}
            />
          ) : null}
          <span className="relative">Дни</span>
        </button>
        <button
          type="button"
          onClick={() => setView("moon")}
          aria-pressed={view === "moon"}
          aria-label="Луна"
          data-testid="calendar-view-moon"
          className={cn(
            "relative flex-1 rounded-full px-3 py-1.5 text-[12px] font-medium transition-colors",
            view === "moon" ? "text-foreground" : "text-muted-foreground hover:text-foreground/80",
          )}
        >
          {view === "moon" ? (
            <motion.span
              layoutId="cal-toggle"
              className="absolute inset-0 rounded-full bg-card shadow-(--shadow-card)"
              transition={{ type: "spring", stiffness: 380, damping: 30 }}
            />
          ) : null}
          <span className="relative">Луна</span>
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
          {view === "moon" ? <LunarCalendarStrip days={lunarStripDays} /> : null}

          <ol
            role="grid"
            className="mt-2 grid flex-1 grid-cols-7 gap-y-1 px-3 pb-2"
            data-testid="calendar-grid"
          >
            {displayDays.map((day) => {
              const date = parseCalendarDayDate(day.date)
              if (!date) return null
              const isWeekend = date.getDay() === 0 || date.getDay() === 6
              const isToday = day.isToday || sameDay(date, TODAY)
              const isSelected = sameDay(date, selected)
              const accessible = accessAllowed(day)
              const disabled = day.disabled === true
              const lunar = day.lunar ?? {}
              const tone = dayTonePresentation(day.dayTone)
              const toneLabel = tone ? `, ${tone.label}` : ""

              return (
                <li key={day.date} className="flex items-center justify-center py-1">
                  <button
                    type="button"
                    onClick={() => selectDay(date, day)}
                    disabled={disabled}
                    aria-pressed={isSelected}
                    aria-label={view === "moon"
                      ? `${lunarAria(date, day)}${toneLabel}`
                      : `${formatLong(date)}${toneLabel}${accessible ? "" : ", требуется подписка"}`}
                    data-testid={`calendar-day-${day.date}`}
                    data-day-state={day.dayState}
                    data-day-tone={day.dayTone ?? undefined}
                    className={cn(
                      "relative flex h-11 w-11 flex-col items-center justify-center rounded-full transition-colors",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60",
                      !day.isCurrentMonth && "opacity-30",
                      day.isCurrentMonth && !isSelected && !isToday && (isWeekend ? "text-foreground/60" : "text-foreground/85") + " hover:bg-muted/60",
                      isToday && !isSelected && (isWeekend ? "text-foreground/60" : "text-foreground/85") + " ring-1 ring-border",
                      isSelected && view === "day" && "bg-primary text-primary-foreground shadow-[0_1px_0_rgba(0,0,0,0.04)]",
                      isSelected && view === "moon" && "bg-primary/10 text-foreground ring-2 ring-primary",
                      day.isCurrentMonth && !accessible && "opacity-65",
                      disabled && "cursor-not-allowed opacity-35",
                    )}
                  >
                    {view === "moon" ? (
                      <>
                        <span
                          className={cn(
                            "flex h-5 w-5 items-center justify-center leading-none",
                            !hasLunarData(day) && "opacity-35",
                          )}
                          data-testid={`calendar-moon-glyph-${day.date}`}
                          aria-hidden
                        >
                          <PhaseGlyph phaseIndex={lunar.phaseIndex} size={18} />
                        </span>
                        <span
                          className="mt-0.5 text-[9px] tabular-nums leading-none"
                          data-testid={`calendar-moon-day-${day.date}`}
                        >
                          {lunar.lunarDay != null ? lunar.lunarDay : "—"}
                        </span>
                        {lunar.voidOfCourse === true ? (
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

                        <span className="mt-0.5 flex h-2 items-center justify-center" aria-hidden>
                          {day.isCurrentMonth && day.dayState === "not-computed" ? (
                            <span
                              className="h-1.5 w-1.5 rounded-full border-[1.5px] border-muted-foreground/45"
                              data-testid="calendar-day-not-computed"
                            />
                          ) : null}

                          {day.isCurrentMonth && day.dayState !== "not-computed" && (tone || day.dayState === "hero") ? (
                            <span
                              className="relative flex items-center justify-center"
                              data-testid="calendar-day-tone-icon"
                              data-tone={day.dayTone ?? undefined}
                            >
                              {day.dayState === "hero" ? (
                                <span
                                  className="absolute h-3 w-3 rounded-full border border-foreground/50"
                                  data-testid="calendar-day-hero-dot"
                                />
                              ) : null}
                              <span className={`h-1.5 w-1.5 rounded-full ${tone ? tone.dotClass : "bg-foreground"}`} />
                            </span>
                          ) : null}
                        </span>

                        {day.isCurrentMonth && !accessible ? (
                          <Lock
                            aria-hidden
                            data-testid="calendar-day-lock"
                            className="absolute right-1.5 top-1.5 h-[9px] w-[9px] text-muted-foreground/50"
                            strokeWidth={1.75}
                          />
                        ) : null}
                      </>
                    )}
                  </button>
                </li>
              )
            })}
          </ol>

          <div
            className="flex-none border-t border-border/60 bg-card px-5 pt-4"
            style={{ paddingBottom: "max(env(safe-area-inset-bottom), 1rem)" }}
            data-testid="calendar-selected-summary"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground/80">
                  {sameDay(selected, TODAY) ? "Сегодня" : "Выбранный день"}
                </div>
                <div className="mt-1 truncate font-serif text-[20px] leading-tight tracking-tight text-foreground">
                  {formatLong(selected)}
                </div>
                {view === "moon" ? (
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-[12px] text-muted-foreground">
                    {hasLunarData(selectedDay) ? (
                      <>
                        <PhaseGlyph phaseIndex={selectedDay?.lunar?.phaseIndex} size={16} />
                        {lunarPhaseLabel(selectedDay?.lunar) ? (
                          <span>{lunarPhaseLabel(selectedDay?.lunar)}</span>
                        ) : null}
                        {selectedDay?.lunar?.illumination != null ? (
                          <>
                            <span aria-hidden>·</span>
                            <span className="tabular-nums">{selectedDay.lunar.illumination}%</span>
                          </>
                        ) : null}
                        {selectedDay?.lunar?.lunarDay != null ? (
                          <>
                            <span aria-hidden>·</span>
                            <span>{selectedDay.lunar.lunarDay} лунный день</span>
                          </>
                        ) : null}
                        {selectedDay?.lunar?.voidOfCourse === true ? (
                          <>
                            <span aria-hidden>·</span>
                            <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-400">
                              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                              без курса
                            </span>
                          </>
                        ) : null}
                      </>
                    ) : (
                      <span>Лунные данные недоступны</span>
                    )}
                  </div>
                ) : selectedDay && !isSelectedAccessible ? (
                  <div className="mt-1 flex items-center gap-2 text-[12px] text-muted-foreground">
                    <Lock aria-hidden className="h-3.5 w-3.5" strokeWidth={1.75} />
                    <span>недоступен</span>
                  </div>
                ) : null}
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
                    ? "border-primary bg-primary text-primary-foreground shadow-(--shadow-card) hover:bg-primary/90"
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
  // END_BLOCK: CALENDAR_RENDER
}
