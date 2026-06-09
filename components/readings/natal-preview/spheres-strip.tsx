"use client"

import { useState } from "react"
import { ChevronDown, ChevronUp } from "lucide-react"
import type { NatalPreviewSphere } from "@/lib/contracts/natal"

type Props = {
  spheres: NatalPreviewSphere[]
}

export function SpheresStrip({ spheres }: Props) {
  const [expanded, setExpanded] = useState(false)
  if (!spheres.length) return null

  const visible = expanded ? spheres : spheres.slice(0, 3)

  return (
    <section className="space-y-3">
      <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Сильнее всего у тебя проявлены
      </div>
      <div className="grid grid-cols-1 gap-3">
        {visible.map((sphere) => (
          <div key={sphere.id} className="rounded-2xl border border-border/70 bg-card p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-serif text-[18px] leading-tight text-foreground">
                {sphere.title}
              </h3>
              <span className="text-[12px] font-medium text-primary">{sphere.score.toFixed(1)}</span>
            </div>
            <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted-foreground">
              {sphere.description}
            </p>
          </div>
        ))}
      </div>
      {spheres.length > 3 && (
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
              Показать все сферы
            </>
          )}
        </button>
      )}
    </section>
  )
}
