"use client"

import { useState } from "react"
import { ChevronDown, ChevronUp } from "lucide-react"
import type { NatalPreviewPlanet } from "@/lib/contracts/natal"

type Props = {
  planets: NatalPreviewPlanet[]
}

export function PlanetsRow({ planets }: Props) {
  const [expanded, setExpanded] = useState(false)
  if (!planets.length) return null

  const visible = expanded ? planets : planets.slice(0, 3)

  return (
    <section className="space-y-3">
      <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Планеты
      </div>
      <div className="grid grid-cols-1 gap-3">
        {visible.map((planet) => (
          <div key={planet.id} className="rounded-2xl border border-border/70 bg-card p-4">
            <div className="flex items-center justify-between gap-2">
              <h3 className="font-serif text-[17px] leading-tight text-foreground">
                {planet.name}
              </h3>
              {typeof planet.score === "number" && (
                <span className="rounded-full bg-primary/10 px-2 py-0.5 font-mono text-[11px] text-primary">
                  {planet.score > 0 ? `+${planet.score.toFixed(2)}` : planet.score.toFixed(2)}
                </span>
              )}
            </div>
            {(planet.sign || planet.house) ? (
              <p className="mt-0.5 text-[12px] leading-snug text-muted-foreground">
                {[planet.sign, planet.house ? `${planet.house} дом` : null].filter(Boolean).join(" · ")}
              </p>
            ) : null}
            <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted-foreground">
              {planet.description}
            </p>
          </div>
        ))}
      </div>
      {planets.length > 3 && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-border/60 bg-card py-2.5 text-[12.5px] font-medium text-muted-foreground hover:text-foreground transition active:scale-[0.99]"
        >
          {expanded ? (
            <>
              <ChevronUp className="h-3.5 w-3.5" />
              Скрыть
            </>
          ) : (
            <>
              <ChevronDown className="h-3.5 w-3.5" />
              Показать все планеты
            </>
          )}
        </button>
      )}
    </section>
  )
}
