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
        Ключевые планеты
      </div>
      <div className="space-y-2">
        {visible.map((planet) => (
          <div key={planet.id} className="flex items-center gap-3 rounded-xl border border-border/50 bg-card px-3.5 py-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline gap-2">
                <span className="text-[14px] font-medium text-foreground">{planet.name}</span>
                {(planet.sign || planet.house) ? (
                  <span className="text-[12px] text-muted-foreground">
                    {[planet.sign, planet.house ? `${planet.house} дом` : null].filter(Boolean).join(" · ")}
                  </span>
                ) : null}
              </div>
              <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">
                {planet.description}
              </p>
            </div>
          </div>
        ))}
      </div>
      {planets.length > 3 && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-border/50 bg-card py-2 text-[12px] font-medium text-muted-foreground hover:text-foreground transition active:scale-[0.99]"
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
