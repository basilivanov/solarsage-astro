
// ############################################################################
// AI_HEADER: MODULE_NATAL-PREVIEW_SPHERES_STRIP
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/readings/natal-preview/spheres-strip.tsx
// owns:
//   - components/readings/natal-preview/spheres-strip.tsx
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

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
      <div className="space-y-2">
        {visible.map((sphere) => (
          <div key={sphere.id} className="flex items-start gap-3 rounded-xl border border-border/50 bg-card px-3.5 py-3">
            <span className="mt-0.5 flex h-6 w-6 flex-none items-center justify-center rounded-full bg-primary/10 text-[11px] font-semibold text-primary">
              {sphere.rank}
            </span>
            <div className="min-w-0 flex-1">
              <h3 className="text-[14px] font-medium leading-tight text-foreground">
                {sphere.title}
              </h3>
              <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">
                {sphere.description}
              </p>
            </div>
          </div>
        ))}
      </div>
      {spheres.length > 3 && (
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
              Показать все сферы
            </>
          )}
        </button>
      )}
    </section>
  )
}
