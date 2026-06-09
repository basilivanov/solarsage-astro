"use client"

import type { NatalPreviewChapter } from "@/lib/contracts/natal"

type Props = {
  chapters: NatalPreviewChapter[]
}

export function LockedChapters({ chapters }: Props) {
  if (!chapters.length) return null

  return (
    <section className="space-y-3">
      <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Полный отчёт
      </div>
      <div className="space-y-3">
        {chapters.map((chapter) => (
          <div key={chapter.id} className="rounded-2xl border border-border/70 bg-card p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                  {chapter.eyebrow}
                </div>
                <h2 className="mt-1 font-serif text-[20px] leading-tight text-foreground">{chapter.title}</h2>
              </div>
              <span className="text-[18px] text-muted-foreground">{chapter.locked ? "🔒" : "✦"}</span>
            </div>
            <p className="mt-2 text-[13px] leading-relaxed text-muted-foreground">{chapter.description}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
