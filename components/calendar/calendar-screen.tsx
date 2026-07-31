// ############################################################################
// AI_HEADER: MODULE_CALENDAR_CALENDAR_SCREEN — active calendar/v2 screen.
// ROLE: Loads one generated month and projects its dayState markers into the public calendar DOM contract.
// ############################################################################

// START_MODULE_CONTRACT: M-CALENDAR-CALENDAR-SCREEN
// purpose: Render a calendar/v2 month grid with explicit loading, ready, and error states.
// owns:
//   - components/calendar/calendar-screen.tsx
// inputs: optional access/onOpenDay compatibility props; current local month.
// outputs: calendar-screen root, navigation controls, and CalendarGrid dayState selectors.
// dependencies: getMonthCalendar; CalendarGrid; TODAY.
// side_effects: credentialed monthly calendar fetches and browser navigation through CalendarMonth links.
// emitted_logs: delegated to the calendar API facade.
// invariants:
//   - data-day-state is projected unchanged from generated CalendarPayload.days.
//   - hero, ordinary, and not-computed marker semantics remain owned by CalendarMonth.
//   - data-state and data-load-state expose the same transport state for accessibility/tests.
// failure_policy: HTTP/schema failures render an alert state and no partial grid.
// END_MODULE_CONTRACT: M-CALENDAR-CALENDAR-SCREEN

// START_MODULE_MAP: M-CALENDAR-CALENDAR-SCREEN
// public_entrypoints:
//   - CalendarScreen
// semantic_blocks:
//   - CALENDAR_FETCH: month cursor and generated payload lifecycle.
//   - CALENDAR_NAVIGATION: allowed-range previous/next controls.
//   - CALENDAR_RENDER: root state and v2 grid composition.
// owned_tests:
//   - __tests__/components/CalendarScreen.test.tsx
//   - e2e/mock-visual/calendar.spec.ts
// END_MODULE_MAP: M-CALENDAR-CALENDAR-SCREEN

"use client"

import { useEffect, useMemo, useState } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"

import { CalendarGrid } from "@/components/grace/CalendarGrid"
import { getMonthCalendar, type CalendarPayloadReadModel } from "@/lib/api/calendar"
import { MONTHS_RU_NOM } from "@/lib/date"
import { TODAY } from "@/lib/today"
import type { AccessInfo } from "@/lib/access"

type Props = {
  access?: AccessInfo
  onOpenDay?: (_date: Date) => void
}

type LoadState = "loading" | "ready" | "error"

function monthTitle(month: string | null | undefined, fallback: Date): string {
  if (month) {
    const [year, monthNumber] = month.split("-").map(Number)
    if (Number.isInteger(year) && Number.isInteger(monthNumber) && monthNumber >= 1 && monthNumber <= 12) {
      return `${MONTHS_RU_NOM[monthNumber - 1]} ${year}`
    }
  }
  return `${MONTHS_RU_NOM[fallback.getMonth()]} ${fallback.getFullYear()}`
}

function monthStart(value: string): Date | null {
  const [year, month] = value.split("-").map(Number)
  if (!Number.isInteger(year) || !Number.isInteger(month) || month < 1 || month > 12) return null
  return new Date(year, month - 1, 1)
}

function sameMonth(left: Date, right: Date): boolean {
  return left.getFullYear() === right.getFullYear() && left.getMonth() === right.getMonth()
}

// START_BLOCK: CALENDAR_FETCH
export function CalendarScreen(_props: Props = {}) {
  // START_FUNCTION_CONTRACT: F-M-CALENDAR-CALENDAR-SCREEN.CalendarScreen
  // purpose: Load the selected month and render the active calendar/v2 grid lifecycle.
  // inputs: compatibility props are accepted by the route but navigation is owned by CalendarMonth links.
  // returns: calendar-screen DOM contract with generated dayState cells.
  // side_effects: GET /api/calendar?month=YYYY-MM whenever the cursor changes.
  // emitted_logs: delegated ui.fetch_started/ui.fetch_succeeded/ui.fetch_failed.
  // error_behavior: failed requests render role=alert with data-state=error.
  // END_FUNCTION_CONTRACT: F-M-CALENDAR-CALENDAR-SCREEN.CalendarScreen
  const [cursor, setCursor] = useState(() => new Date(TODAY.getFullYear(), TODAY.getMonth(), 1))
  const [payload, setPayload] = useState<CalendarPayloadReadModel | null>(null)
  const [loadState, setLoadState] = useState<LoadState>("loading")

  useEffect(() => {
    let active = true
    setLoadState("loading")
    setPayload(null)
    getMonthCalendar(cursor.getFullYear(), cursor.getMonth())
      .then((nextPayload) => {
        if (!active) return
        setPayload(nextPayload)
        setLoadState("ready")
      })
      .catch(() => {
        if (!active) return
        setPayload(null)
        setLoadState("error")
      })

    return () => {
      active = false
    }
  }, [cursor])
  // END_BLOCK: CALENDAR_FETCH

  // START_BLOCK: CALENDAR_NAVIGATION
  const bounds = useMemo(() => {
    const from = payload ? monthStart(payload.allowedRange.from) : null
    const to = payload ? monthStart(payload.allowedRange.to) : null
    return { from, to }
  }, [payload])

  const canPrev = bounds.from ? cursor > bounds.from : true
  const canNext = bounds.to ? cursor < bounds.to : true

  function moveMonth(delta: number): void {
    if (delta < 0 && !canPrev) return
    if (delta > 0 && !canNext) return
    setCursor((current) => new Date(current.getFullYear(), current.getMonth() + delta, 1))
  }
  // END_BLOCK: CALENDAR_NAVIGATION

  // START_BLOCK: CALENDAR_RENDER
  const title = monthTitle(payload?.month, cursor)
  return (
    <main
      data-testid="calendar-screen"
      data-state={loadState}
      data-load-state={loadState}
      role={loadState === "error" ? "alert" : undefined}
      aria-busy={loadState === "loading" ? true : undefined}
      aria-label="Календарь"
      className="min-h-full w-full bg-background text-foreground"
    >
      <header
        className="mx-auto flex w-full max-w-5xl items-center justify-between px-5 pb-4 pt-5"
        data-testid="calendar-header"
      >
        <button
          type="button"
          onClick={() => moveMonth(-1)}
          disabled={!canPrev}
          aria-label="Предыдущий месяц"
          className="flex h-10 w-10 items-center justify-center rounded-full border border-border/70 bg-card text-foreground/70 transition disabled:cursor-not-allowed disabled:opacity-30"
        >
          <ChevronLeft className="h-4 w-4" strokeWidth={1.75} />
        </button>
        <h1 className="font-serif text-[22px] leading-none tracking-tight" data-testid="calendar-month-header">
          {title}
        </h1>
        <button
          type="button"
          onClick={() => moveMonth(1)}
          disabled={!canNext}
          aria-label="Следующий месяц"
          className="flex h-10 w-10 items-center justify-center rounded-full border border-border/70 bg-card text-foreground/70 transition disabled:cursor-not-allowed disabled:opacity-30"
        >
          <ChevronRight className="h-4 w-4" strokeWidth={1.75} />
        </button>
      </header>

      {loadState === "loading" ? (
        <section data-testid="calendar-loading" role="status" aria-label="Загрузка календаря" className="mx-auto max-w-5xl px-5 py-12 text-center text-sm text-muted-foreground">
          Загружаем календарь…
        </section>
      ) : null}

      {loadState === "error" ? (
        <section data-testid="calendar-error" role="alert" className="mx-auto max-w-5xl px-5 py-12 text-center">
          <h2 className="font-serif text-xl">Календарь недоступен</h2>
          <p className="mt-2 text-sm text-muted-foreground">Не удалось загрузить данные месяца.</p>
        </section>
      ) : null}

      {loadState === "ready" && payload ? (
        <CalendarGrid payload={payload} />
      ) : null}

      {loadState === "ready" && payload && sameMonth(cursor, TODAY) ? (
        <p className="sr-only" data-testid="calendar-current-month">Текущий месяц</p>
      ) : null}
    </main>
  )
  // END_BLOCK: CALENDAR_RENDER
}
