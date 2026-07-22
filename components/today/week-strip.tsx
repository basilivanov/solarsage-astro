
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
// inputs: selectedDate, access, onSelect
// outputs: TSX render / values
// dependencies: local modules
// side_effects: NONE (pure render + onSelect callback). The component never
//   calls /api/day — no mount-time load, no hover/focus warmup. A full day is
//   fetched ONLY by explicit navigation after a click (page flow owns it).
// emitted_logs: none
// invariants:
//   - Zero remote calls on mount, on pointer enter and on keyboard focus.
//   - Click invokes onSelect at most once per click; the component itself
//     never fetches.
//   - Public semantic contract preserved: data-testid, aria labels/pressed,
//     lock for inaccessible days.
// failure_policy: pure render; nothing to fail.
// END_MODULE_CONTRACT: M-TODAY-WEEK-STRIP

// START_MODULE_MAP: M-TODAY-WEEK-STRIP
// public_entrypoints:
//   - WeekStrip
// semantic_blocks:
//   - WEEK_RENDER: accessible seven-day navigation (no fetching).
// owned_tests:
//   - __tests__/components/WeekStrip.test.tsx
// END_MODULE_MAP: M-TODAY-WEEK-STRIP
"use client"

import { useMemo } from "react"
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

type Props = {
  selectedDate: Date
  access: AccessInfo
  onSelect?: (_d: Date) => void
}

// START_BLOCK: WEEK_RENDER
export function WeekStrip({ selectedDate, access, onSelect }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-WEEK-STRIP.WeekStrip
  // purpose: Render a horizontal calendar strip for seven days of the current week.
  // inputs: selectedDate, access state, onSelect date callback.
  // returns: Calendar strip JSX.
  // side_effects: none — the component never calls /api/day (no mount load,
  //   no hover/focus warmup); full days load only via explicit navigation.
  // emitted_logs: none.
  // error_behavior: pure render; nothing to fail.
  // END_FUNCTION_CONTRACT: F-M-TODAY-WEEK-STRIP.WeekStrip
  const startKey = startOfWeek(selectedDate).getTime()
  const days = useMemo(() => {
    const weekStart = new Date(startKey)
    return Array.from({ length: 7 }, (_, index) => addDays(weekStart, index))
  }, [startKey])
  const range = formatWeekRange(new Date(startKey))

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
          // No remote warmup: per-day status loads only on explicit navigation.
          const statusText = "статус недоступен"
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
                  {accessible ? (
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
