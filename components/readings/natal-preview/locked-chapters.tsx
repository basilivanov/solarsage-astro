
// ############################################################################
// AI_HEADER: MODULE_NATAL-PREVIEW_LOCKED_CHAPTERS
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Module: locked-chapters.tsx
// owns:
//   - components/readings/natal-preview/locked-chapters.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { Lock } from "lucide-react"
import type { NatalPreviewChapter } from "@/lib/contracts/natal"

type Props = {
  chapters: NatalPreviewChapter[]
}

export function LockedChapters({ chapters }: Props) {
  if (!chapters.length) return null

  return (
    <section className="space-y-3">
      <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Что войдёт в полный отчёт
      </div>
      <div className="grid grid-cols-2 gap-2">
        {chapters.map((chapter) => (
          <div
            key={chapter.id}
            className="relative rounded-xl border border-border/50 bg-card px-3 py-2.5"
          >
            <Lock className="absolute right-2.5 top-2.5 h-3 w-3 text-muted-foreground/35" />
            {chapter.eyebrow ? (
              <div className="text-[9px] font-medium uppercase tracking-[0.1em] text-muted-foreground/60">
                {chapter.eyebrow}
              </div>
            ) : null}
            <p className="mt-0.5 text-[12.5px] font-medium leading-snug text-foreground/85 pr-4">
              {chapter.title}
            </p>
            {chapter.description ? (
              <p className="mt-0.5 text-[10.5px] leading-relaxed text-muted-foreground/70 line-clamp-2">
                {chapter.description}
              </p>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  )
}
