
// ############################################################################
// AI_HEADER: MODULE_NATAL-PREVIEW_HIGHLIGHTS_STRIP
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/readings/natal-preview/highlights-strip.tsx
// owns:
//   - components/readings/natal-preview/highlights-strip.tsx
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

import type { NatalPreviewHighlight } from "@/lib/contracts/natal"

type Props = {
  highlights: NatalPreviewHighlight[]
}

export function HighlightsStrip({ highlights }: Props) {
  if (!highlights.length) return null

  return (
    <section className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {highlights.slice(0, 3).map((item) => (
        <div key={item.id} className="rounded-2xl border border-border/70 bg-card p-4">
          <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            {item.title}
          </div>
          <div className="mt-1 font-serif text-[22px] leading-tight text-foreground">{item.value}</div>
          {item.description ? (
            <p className="mt-2 text-[12.5px] leading-relaxed text-muted-foreground">{item.description}</p>
          ) : null}
        </div>
      ))}
    </section>
  )
}
