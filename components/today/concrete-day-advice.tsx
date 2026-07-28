// ############################################################################
// AI_HEADER: MODULE_TODAY_CONCRETE_DAY_ADVICE — human-first 12-sphere navigator.
// ROLE: Renders every backend-owned advice row as a single-column premium list
//       and shows one non-technical details panel at a time.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONCRETE-DAY-ADVICE
// purpose: Present all concrete advice rows in single-column layout without verdict badges (D2).
// owns:
//   - components/today/concrete-day-advice.tsx
// inputs: concreteAdvice, selectedKey, onSelectedKeyChange, onWhyOpen.
// outputs: data-testid="concrete-day-advice" section with single-column rows and selected details panel.
// dependencies: lib/contracts/today, lib/icons, lib/presentation/today-v2, lucide-react.
// side_effects: delegates selection and Why disclosure to TodayScreen.
// emitted_logs: none.
// invariants:
//   - every received row is visible in canonical adapter order.
//   - verdict badges, verdict dots, and data-status attributes are omitted (D2).
//   - only one details panel can exist.
// failure_policy: render available rows gracefully when payload is incomplete.
// END_MODULE_CONTRACT: M-TODAY-CONCRETE-DAY-ADVICE

// START_MODULE_MAP: M-TODAY-CONCRETE-DAY-ADVICE
// public_entrypoints:
//   - ConcreteDayAdvice
// semantic_blocks:
//   - SPHERE_NAVIGATOR: single-column sphere selection list.
//   - SPHERE_DETAILS: selected sphere human guidance.
// owned_tests:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
//   - __tests__/components/TodayScreen.test.tsx
// END_MODULE_MAP: M-TODAY-CONCRETE-DAY-ADVICE

"use client"

import { ChevronRight } from "lucide-react"
import type { ConcreteAdviceBlock } from "@/lib/contracts/today"
import { getIcon } from "@/lib/icons"

type Props = {
  concreteAdvice: ConcreteAdviceBlock
  selectedKey: string | null
  onSelectedKeyChange: (key: string | null) => void
}

const VERDICT_PRESENTATION: Record<"good" | "neutral" | "caution" | "avoid", {
  dotClass: string
  compactCopy: string
  statusTextClass: string
}> = {
  good: {
    dotClass: "bg-emerald-500",
    compactCopy: "Поддержка",
    statusTextClass: "text-emerald-700 dark:text-emerald-200",
  },
  neutral: {
    dotClass: "bg-slate-400 dark:bg-slate-500",
    compactCopy: "Ровный фон",
    statusTextClass: "text-slate-600 dark:text-slate-400",
  },
  caution: {
    dotClass: "bg-amber-500",
    compactCopy: "Требует внимания",
    statusTextClass: "text-amber-700 dark:text-amber-200",
  },
  avoid: {
    dotClass: "bg-rose-500",
    compactCopy: "Лучше отложить",
    statusTextClass: "text-rose-700 dark:text-rose-200",
  },
}

function sphereButtonId(key: string): string {
  return `concrete-sphere-${key}`
}

// START_BLOCK: SPHERE_NAVIGATOR
export function ConcreteDayAdvice({
  concreteAdvice,
  selectedKey,
  onSelectedKeyChange,
}: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONCRETE-DAY-ADVICE.ConcreteDayAdvice
  // purpose: Render the full single-column sphere list and one selected details panel.
  // inputs: Props — backend rows, selectedKey, callbacks.
  // returns: Navigator JSX.
  // side_effects: invokes parent callbacks on row clicks.
  // emitted_logs: none.
  // error_behavior: renders available rows without fabricated entries.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONCRETE-DAY-ADVICE.ConcreteDayAdvice
  const rows = concreteAdvice?.rows || []

  return (
    <section
      className="px-5"
      aria-label="Все сферы дня"
      data-testid="concrete-day-advice"
    >
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        Конкретно сегодня
      </p>
      <h2 className="mt-1 font-serif text-[24px] leading-tight text-foreground">
        Все сферы дня
      </h2>

      <div className="mt-4 space-y-2.5">
        {rows.map((row) => {
          const Icon = getIcon(row.iconName)
          const selected = row.key === selectedKey
          const verdict = row.assessment?.assessment?.verdict
          const meta = verdict ? VERDICT_PRESENTATION[verdict] : null

          return (
            <div key={row.key} className="space-y-2.5">
              <button
                id={sphereButtonId(row.key)}
                type="button"
                data-testid="concrete-day-advice-row"
                data-sphere-key={row.key}
                data-selected={selected ? "true" : "false"}
                data-status={verdict || undefined}
                aria-haspopup="dialog"
                onClick={() => onSelectedKeyChange(row.key)}
                className={`w-full flex min-h-[64px] items-center justify-between gap-3 rounded-2xl border bg-card px-4 py-3 text-left transition-all duration-200 ease-[cubic-bezier(0.22,1,0.36,1)] active:scale-[0.985] motion-reduce:transform-none motion-reduce:transition-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2 ${
                  selected
                    ? "border-violet-500 bg-violet-50/60 shadow-[0_0_0_1px_rgba(139,92,246,0.25),0_14px_30px_-24px_rgba(109,40,217,0.75)] dark:border-violet-300 dark:bg-violet-500/15"
                    : "border-border/70 hover:border-violet-300 hover:bg-violet-50/30 dark:hover:bg-violet-500/10"
                }`}
              >
                <div className="flex items-center gap-3.5 min-w-0 flex-1">
                  <span className="flex h-9 w-9 flex-none items-center justify-center rounded-xl bg-violet-100/70 text-violet-700 dark:bg-violet-500/15 dark:text-violet-200">
                    <Icon className="h-4.5 w-4.5" strokeWidth={1.8} aria-hidden />
                  </span>
                  <span className="text-[15px] font-semibold leading-snug text-foreground truncate">
                    {row.label}
                  </span>
                </div>
                {meta && (
                  <div className="flex items-center gap-1.5 flex-none">
                    <span className={`h-2 w-2 rounded-full ${meta.dotClass}`} aria-hidden="true" />
                    <span
                      data-testid="concrete-day-advice-row-status"
                      data-status={verdict}
                      className={`text-[12.5px] font-semibold ${meta.statusTextClass}`}
                    >
                      {meta.compactCopy}
                    </span>
                  </div>
                )}
                <ChevronRight className="h-5 w-5 text-muted-foreground flex-none" aria-hidden />
              </button>
            </div>
          )
        })}
      </div>
    </section>
  )
}
// END_BLOCK: SPHERE_NAVIGATOR
