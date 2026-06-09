"use client"

import type { NatalPreviewPlanet } from "@/lib/contracts/natal"

type Props = {
  planets: NatalPreviewPlanet[]
}

export function PlanetsRow({ planets }: Props) {
  if (!planets.length) return null

  return (
    <section className="space-y-3">
      <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Планеты
      </div>
      <div className="grid grid-cols-2 gap-3">
        {planets.map((planet) => (
          <div key={planet.id} className="rounded-2xl border border-border/70 bg-card p-4">
            <div className="flex items-baseline justify-between gap-2">
              <h2 className="font-serif text-[18px] leading-tight text-foreground">{planet.name}</h2>
              {typeof planet.score === "number" ? (
                <span className="rounded-full bg-primary/10 px-2 py-0.5 font-mono text-[11px] text-primary">
                  {planet.score > 0 ? `+${planet.score}` : planet.score}
                </span>
              ) : null}
            </div>
            {(planet.sign || planet.house) ? (
              <p className="mt-1 text-[12px] leading-snug text-muted-foreground">
                {[planet.sign, planet.house ? `${planet.house} дом` : null].filter(Boolean).join(" · ")}
              </p>
            ) : null}
            <p className="mt-2 text-[12.5px] leading-relaxed text-muted-foreground">{planet.description}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
