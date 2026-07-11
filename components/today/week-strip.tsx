
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
// side_effects: Fetches remote day statuses by default; logging via v2 logging spine; React state management
// emitted_logs: system.error
// invariants:
//   - disableRemoteStatusFetch defaults to false; a local fixture can opt out without changing ordinary requests
// failure_policy: per-day failure -> unknown; unexpected batch failure logs and
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

import { useEffect, useState } from "react"
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
  // side_effects: Fetches day statuses on mount or when week starts unless fetch is disabled.
  // emitted_logs: system.error if status fetch fails.
  // error_behavior: per-day fetch failure becomes unknown; unexpected batch failure logs system.error and leaves week UI usable; no exception is intentionally raised.
  // END_FUNCTION_CONTRACT: F-M-TODAY-WEEK-STRIP.WeekStrip
  const start = startOfWeek(selectedDate)
  const days = Array.from({ length: 7 }, (_, i) => addDays(start, i))
  const range = formatWeekRange(start)

  const [statuses, setStatuses] = useState<Record<string, WeekStatus>>({})

  const startKey = start.getTime()

  useEffect(() => {
    if (disableRemoteStatusFetch) {
      setStatuses({})
      return
    }
    let active = true
    async function load() {
      try {
        const results = await Promise.all(
          days.map(async (d) => {
            const status = await getDayStatus(d)
              .then((value) => value ?? "unknown" as const)
              .catch(() => "unknown" as const)
            return { key: d.toDateString(), status }
          })
        )
        if (!active) return
        const map: Record<string, WeekStatus> = {}
        for (const r of results) {
          map[r.key] = r.status
        }
        setStatuses(map)
      } catch (err) {
        logEvent("system.error", { error: String(err) }, { msg: "Failed to load week strip statuses", slice: "W-DAY", module: "M-WEEK-STRIP", block: "LOAD_STATUSES" })
      }
    }
    load()
    return () => {
      active = false
    }
  }, [disableRemoteStatusFetch, startKey])

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
