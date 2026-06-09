"use client"

import type { NatalCalculationStats } from "@/lib/contracts/natal"

type Props = {
  stats: NatalCalculationStats
}

export function CalculationDepth({ stats }: Props) {
  return (
    <section className="rounded-2xl border border-border/70 bg-card p-4">
      <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Глубина расчёта
      </div>
      <p className="mt-2 text-[13px] leading-relaxed text-muted-foreground">
        В разборе учитываются:
      </p>
      <ul className="mt-2 space-y-1.5">
        <li className="flex items-center gap-2 text-[13px] text-foreground/85">
          <span className="h-1 w-1 rounded-full bg-primary/60 flex-none" />
          планеты и дома
        </li>
        <li className="flex items-center gap-2 text-[13px] text-foreground/85">
          <span className="h-1 w-1 rounded-full bg-primary/60 flex-none" />
          аспекты и акценты карты
        </li>
        <li className="flex items-center gap-2 text-[13px] text-foreground/85">
          <span className="h-1 w-1 rounded-full bg-primary/60 flex-none" />
          приоритетные жизненные сферы
        </li>
        <li className="flex items-center gap-2 text-[13px] text-foreground/85">
          <span className="h-1 w-1 rounded-full bg-primary/60 flex-none" />
          сильные и напряжённые зоны
        </li>
      </ul>
    </section>
  )
}
