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
      <div className="grid grid-cols-1 gap-2">
        {chapters.map((chapter) => (
          <div
            key={chapter.id}
            className="flex items-center gap-3 rounded-xl border border-border/60 bg-card px-4 py-3"
          >
            <Lock className="h-3.5 w-3.5 flex-none text-muted-foreground/50" />
            <span className="text-[13.5px] leading-snug text-foreground/85">
              {chapter.title}
            </span>
          </div>
        ))}
      </div>
    </section>
  )
}
