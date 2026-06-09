"use client"

import type { NatalPreviewSphere } from "@/lib/contracts/natal"

type Props = {
  spheres: NatalPreviewSphere[]
}

export function SpheresStrip({ spheres }: Props) {
  if (!spheres.length) return null

  return (
    <section className="space-y-3">
      <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Сферы жизни
      </div>
      <div className="grid grid-cols-1 gap-3">
        {spheres.slice(0, 3).map((sphere) => (
          <div key={sphere.id} className="rounded-2xl border border-border/70 bg-card p-4">
            <div className="flex items-baseline justify-between gap-3">
              <h2 className="font-serif text-[20px] leading-tight text-foreground">{sphere.title}</h2>
              <span className="font-mono text-[12px] text-primary">#{sphere.rank}</span>
            </div>
            <div className="mt-2 text-[13px] text-primary">{sphere.score.toFixed(1)} балла</div>
            <p className="mt-2 text-[13px] leading-relaxed text-muted-foreground">{sphere.description}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
