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
      <div className="mt-2 font-serif text-[24px] leading-tight text-foreground">{stats.displayLabel}</div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-[12.5px] text-muted-foreground">
        <div className="rounded-xl bg-background/70 px-3 py-2">Планет: {stats.planetsCount}</div>
        <div className="rounded-xl bg-background/70 px-3 py-2">Домов: {stats.housesCount}</div>
        <div className="rounded-xl bg-background/70 px-3 py-2">Аспектов: {stats.aspectsCount}</div>
        <div className="rounded-xl bg-background/70 px-3 py-2">Факторов: {stats.totalFactorsCount}</div>
      </div>
    </section>
  )
}
