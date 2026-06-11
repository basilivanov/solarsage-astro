
// ############################################################################
// AI_HEADER: MODULE_NATAL-PREVIEW_CALCULATION_DEPTH
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// #########################################// START_MODULE_CONTRACT
// purpose: Module: calculation-depth.tsx
// owns:
//   - components/readings/natal-preview/calculation-depth.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import type { NatalCalculationStats } from "@/lib/contracts/natal"

type Props = {
  stats: NatalCalculationStats
}

export function CalculationDepth({ stats }: Props) {
  return (
    <section className="rounded-2xl border border-border/50 bg-card px-4 py-3.5">
      <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Глубина расчёта
      </div>
      {stats.displayLabel ? (
        <p className="mt-1.5 text-[14px] font-medium text-foreground">
          {stats.displayLabel}
        </p>
      ) : null}
      <ul className="mt-2 space-y-1.5">
        <li className="flex items-center gap-2 text-[12.5px] text-foreground/75">
          <span className="h-1 w-1 rounded-full bg-primary/50 flex-none" />
          планеты и дома
        </li>
        <li className="flex items-center gap-2 text-[12.5px] text-foreground/75">
          <span className="h-1 w-1 rounded-full bg-primary/50 flex-none" />
          аспекты и акценты карты
        </li>
        <li className="flex items-center gap-2 text-[12.5px] text-foreground/75">
          <span className="h-1 w-1 rounded-full bg-primary/50 flex-none" />
          приоритетные жизненные сферы
        </li>
        <li className="flex items-center gap-2 text-[12.5px] text-foreground/75">
          <span className="h-1 w-1 rounded-full bg-primary/50 flex-none" />
          сильные и напряжённые зоны
        </li>
      </ul>
    </section>
  )
}
