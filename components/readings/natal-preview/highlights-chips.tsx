
// ############################################################################
// AI_HEADER: MODULE_NATAL-PREVIEW_HIGHLIGHTS_CHIPS
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/readings/natal-preview/highlights-chips.tsx
// owns:
//   - components/readings/natal-preview/highlights-chips.tsx
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

export function HighlightsChips({ highlights }: Props) {
  if (!highlights.length) return null

  return (
    <section className="space-y-3">
      <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Что уже видно по карте
      </div>
      <div className="grid grid-cols-3 gap-2.5">
        {highlights.slice(0, 3).map((item) => (
          <div
            key={item.id}
            className="rounded-2xl border border-border/60 bg-card p-3 text-center"
          >
            <div className="text-[10px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
              {item.title}
            </div>
            <div className="mt-1 font-serif text-[18px] leading-tight text-foreground">
              {item.value}
            </div>
            {item.description ? (
              <p className="mt-1 text-[11px] leading-snug text-muted-foreground/80">
                {item.description}
              </p>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  )
}
