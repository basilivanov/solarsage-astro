
// ############################################################################
// AI_HEADER: MODULE_TODAY_WEEK_STRIP
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TODAY-CALENDAR
// ############################################################################
// START_MODULE_CONTRACT: M-TODAY-WEEK-STRIP
// purpose: UI week-strip — component
// owns:
//   - components/today/week-strip.tsx
// inputs: selectedDate, access, onSelect, optional disableRemoteStatusFetch
// outputs: TSX render / values
// dependencies: local modules
// side_effects: Fetches one remote day status per explicit user intent (pointer
//   hover/enter or keyboard focus on an accessible, inactive day); at most one
//   request per date per mount; logging via v2 logging spine; React state management
// emitted_logs: system.error
// invariants:
//   - No mount-time or week-change batch status load; warmup happens only on
//     explicit user intent for an accessible, non-active, unlocked day.
//   - Idempotent: at most one status request per date per mount; hover and
//     focus for the same day never duplicate it; locked and active days are
//     never prefetched; disableRemoteStatusFetch disables warmup entirely.
// failure_policy: per-day failure -> unknown; unexpected failure logs and
//                 keeps the week UI usable; no exception is intentionally raised
// END_MODULE_CONTRACT: M-TODAY-WEEK-STRIP

// START_MODULE_MAP: M-TODAY-WEEK-STRIP
// public_entrypoints:
//   - WeekStrip
// semantic_blocks:
//   - STATUS_FETCH: default remote week-status loading or local fixture suppression.
//   - WEEK_RENDER: accessible seven-day navigation.
// owned_tests:
//   - e2e/dev-timing-fixture.spec.ts
// END_MODULE_MAP: M-TODAY-WEEK-STRIP
"use client"

import { useMemo, useRef, useState } from "react"
import { Lock, Minus } from "lucide-react"
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
import { getDayStatus, type DayStatus } from "@/lib/api/calendar"
import { logEvent } from "@/lib/log"
import { MoodIcon } from "@/components/calendar/mood-icon"

type Props = {
  selectedDate: Date
  access: AccessInfo
  onSelect?: (_d: Date) => void
  disableRemoteStatusFetch?: boolean
}

type WeekStatus = DayStatus | "unknown"

// START_BLOCK: WEEK_RENDER
export function WeekStrip({ selectedDate, access, onSelect, disableRemoteStatusFetch = false }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-WEEK-STRIP.WeekStrip
  // purpose: Render a horizontal calendar strip for seven days of the current week.
  // inputs: selectedDate, access state, onSelect date callback, disableRemoteStatusFetch flag.
  // returns: Calendar strip JSX.
  // side_effects: Warms one day status per explicit user intent (hover/pointer-enter or keyboard focus) for an accessible inactive day; never a mount-time batch load.
  // emitted_logs: system.error if a warmup request fails.
  // error_behavior: per-day fetch failure becomes unknown; unexpected failure logs system.error and leaves week UI usable; no exception is intentionally raised.
  // END_FUNCTION_CONTRACT: F-M-TODAY-WEEK-STRIP.WeekStrip
  const startKey = startOfWeek(selectedDate).getTime()
  const days = useMemo(() => {
    const weekStart = new Date(startKey)
    return Array.from({ length: 7 }, (_, index) => addDays(weekStart, index))
  }, [startKey])
  const range = formatWeekRange(new Date(startKey))

  const [statuses, setStatuses] = useState<Record<string, WeekStatus>>({})
  const requestedDates = useRef<Set<string>>(new Set())

  // START_BLOCK: INTENT_WARMUP
  // User-intent status warmup: fires only on explicit hover/pointer-enter or
  // keyboard focus of an accessible, inactive, unlocked day. At most one
  // request per date per mount; hover+focus never duplicates; locked and
  // active days are never prefetched.
  function warmDay(d: Date, accessible: boolean, active: boolean) {
    if (disableRemoteStatusFetch) return
    if (!accessible || active) return
    const key = d.toDateString()
    if (requestedDates.current.has(key)) return
    requestedDates.current.add(key)
    getDayStatus(d)
      .then((value) => {
        setStatuses((prev) => ({ ...prev, [key]: value ?? "unknown" }))
      })
      .catch((err) => {
        logEvent("system.error", { error: String(err) }, { msg: "Failed to warm day status", slice: "W-DAY", module: "M-WEEK-STRIP", block: "INTENT_WARMUP" })
        setStatuses((prev) => ({ ...prev, [key]: "unknown" }))
      })
  }
  // END_BLOCK: INTENT_WARMUP

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
          const status = statuses[d.toDateString()] ?? "unknown"
          const statusText = status === "unknown" ? "статус недоступен" : `${statusLabel(status)} день`
          const labelIdx = mondayFirstIndex(d)
          return (
            <li key={d.toISOString()}>
              <button
                type="button"
                onClick={() => onSelect?.(d)}
                onPointerEnter={() => warmDay(d, accessible, active)}
                onFocus={() => warmDay(d, accessible, active)}
                aria-label={`${WEEKDAYS_MINI[labelIdx]} ${d.getDate()}, ${statusText}${
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
                  {accessible && status !== "unknown" ? (
                    <MoodIcon
                      status={status}
                      className={cn(
                        "h-4 w-4",
                        active ? "text-primary-foreground" : "text-foreground",
                      )}
                    />
                  ) : accessible ? (
                    <Minus
                      aria-hidden
                      className={cn(
                        "h-4 w-4",
                        active ? "text-primary-foreground/75" : "text-muted-foreground/70",
                      )}
                      strokeWidth={1.75}
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
// END_BLOCK: WEEK_RENDER
