// ############################################################################
// AI_HEADER: MODULE_WHY_TIME_HORIZON_CARD — human-first Why time horizon card.
// ROLE: Presents one preselected long, medium, or fast personal storyline.
// ############################################################################

// START_MODULE_CONTRACT: M-WHY-TIME-HORIZON-CARD
// purpose: Render one human-first time horizon without technical selection logic.
// owns:
//   - components/today/why-time-horizon-card.tsx
// inputs: horizon — presentation-selected horizon with safe why copy and range.
// outputs: Stable why-time-horizon article with visible metadata/title/body.
// dependencies: lib/presentation/today-v2 types.
// side_effects: none.
// emitted_logs: none.
// invariants: technical vocabulary and raw evidence never render in this component.
// failure_policy: uses a neutral structural fallback when safe why copy is absent.
// END_MODULE_CONTRACT: M-WHY-TIME-HORIZON-CARD

// START_MODULE_MAP: M-WHY-TIME-HORIZON-CARD
// public_entrypoints:
//   - WhyTimeHorizonCard
// semantic_blocks:
//   - HORIZON_CARD: visual long/medium/fast presentation.
// owned_tests:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// END_MODULE_MAP: M-WHY-TIME-HORIZON-CARD

import type { WhyTimeHorizon } from "@/lib/presentation/today-v2"

const HORIZON_META = {
  long: { number: "01", label: "Большой сюжет", tone: "border-violet-300/80 bg-violet-100/35 dark:border-violet-400/35 dark:bg-violet-500/10" },
  medium: { number: "02", label: "Активная волна", tone: "border-violet-300 bg-violet-50/75 dark:border-violet-400/45 dark:bg-violet-500/15" },
  fast: { number: "03", label: "Триггер сегодня", tone: "border-violet-200 bg-violet-50/40 dark:border-violet-400/25 dark:bg-violet-500/5" },
} as const

// START_BLOCK: HORIZON_CARD
export function WhyTimeHorizonCard({ horizon }: { horizon: WhyTimeHorizon }) {
  // START_FUNCTION_CONTRACT: F-M-WHY-TIME-HORIZON-CARD.WhyTimeHorizonCard
  // purpose: Render a selected horizon's human copy and visible duration range.
  // inputs: horizon — pure presentation model selected by the parent.
  // returns: Human-first horizon article JSX.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: falls back to neutral copy when backend why copy is missing.
  // END_FUNCTION_CONTRACT: F-M-WHY-TIME-HORIZON-CARD.WhyTimeHorizonCard
  const meta = HORIZON_META[horizon.id]
  const primary = horizon.whyItems[0]
  return (
    <article
      data-testid="why-time-horizon"
      data-horizon={horizon.id}
      data-state="ready"
      className={`relative overflow-hidden rounded-2xl border p-4 ${meta.tone}`}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-violet-700 dark:text-violet-200">
          {meta.number} · {meta.label}
        </p>
        <span data-testid="why-time-horizon-range" className="rounded-full bg-card/85 px-2.5 py-1 text-[11px] font-medium text-muted-foreground shadow-sm">
          {horizon.rangeLabel}
        </span>
      </div>
      <h3 data-testid="why-time-horizon-title" className="mt-4 font-serif text-[23px] leading-[1.22] text-foreground">
        {primary?.title || "Личный сюжет периода"}
      </h3>
      <p data-testid="why-time-horizon-body" className="mt-3 text-[15px] leading-relaxed text-foreground/80">
        {primary?.body || "Эта тема может ощущаться в своём темпе и помогает заметить, на что сейчас стоит опереться."}
      </p>
    </article>
  )
}
// END_BLOCK: HORIZON_CARD
