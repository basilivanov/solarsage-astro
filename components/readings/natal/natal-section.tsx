
// ############################################################################
// AI_HEADER: MODULE_NATAL_NATAL_SECTION
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/readings/natal/natal-section.tsx
// owns:
//   - components/readings/natal/natal-section.tsx
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

import Link from "next/link"
import { ArrowLeft, ChevronLeft, ChevronRight } from "lucide-react"

import type { NatalReport, ReportSection } from "@/lib/contracts/natal"
import { BlockRenderer } from "./block-renderer"

type Props = {
  report: NatalReport
  section: ReportSection
  prev: ReportSection | null
  next: ReportSection | null
  index: number
  total: number
}

/**
 * Страница одной главы натального разбора.
 *
 * Структура:
 *   1. Sticky-хедер: back к /readings/natal + прогресс главы;
 *   2. Заголовок главы (eyebrow + title);
 *   3. Сама "плёнка" блоков — рендерится через BlockRenderer;
 *   4. Навигация prev / next в подвале.
 *
 * Каждая глава — отдельная страница, чтобы native back в Telegram
 * работал предсказуемо и scroll-restoration возвращал на ту же позицию
 * в TOC, с которой открыли главу.
 */
export function NatalSectionView({
  report,
  section,
  prev,
  next,
  index,
  total,
}: Props) {
  return (
    <div className="flex h-full w-full flex-col">
      {/* Sticky compact header */}
      <header
        className="sticky top-0 z-10 flex flex-none items-center gap-2 border-b border-border/60 bg-background/85 px-3 py-3 backdrop-blur-md"
        style={{ paddingTop: "max(env(safe-area-inset-top), 0.75rem)" }}
      >
        <Link
          href="/readings/natal"
          aria-label="Назад к оглавлению"
          className="flex h-9 w-9 items-center justify-center rounded-full text-foreground/70 transition active:scale-95 active:bg-muted/60"
        >
          <ArrowLeft className="h-4 w-4" strokeWidth={1.75} />
        </Link>
        <div className="min-w-0 flex-1">
          <div className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            {section.eyebrow ?? `Глава ${index + 1}`}
          </div>
          <div className="truncate text-[14px] font-medium text-foreground">
            {section.title}
          </div>
        </div>
        <div className="flex-none rounded-full border border-border/70 bg-card px-2.5 py-1 font-mono text-[11px] tabular-nums text-muted-foreground">
          {index + 1}/{total}
        </div>
      </header>

      <article className="flex-1 overflow-y-auto px-5 pb-10">
        {/* Заголовок главы */}
        <div className="pt-6">
          <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            {section.eyebrow ?? `Глава ${index + 1}`}
          </div>
          <h1 className="mt-1 font-serif text-[28px] leading-[1.1] tracking-tight text-foreground text-balance">
            {section.title}
          </h1>
          {section.summary ? (
            <p className="mt-2 text-[13.5px] leading-relaxed text-muted-foreground text-pretty">
              {section.summary}
            </p>
          ) : null}
        </div>

        <div className="mt-7 flex flex-col gap-5">
          {section.blocks.map((block, i) => (
            <BlockRenderer key={i} block={block} report={report} />
          ))}
        </div>

        {/* Prev / Next */}
        <nav
          className="mt-10 flex items-stretch gap-2"
          aria-label="Навигация по главам"
        >
          {prev ? (
            <Link
              href={`/readings/natal/${prev.id}`}
              prefetch
              className="group flex flex-1 flex-col items-start gap-1 rounded-2xl border border-border/70 bg-card px-4 py-3 transition active:scale-[0.99]"
            >
              <span className="flex items-center gap-1 text-[10.5px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                <ChevronLeft className="h-3 w-3" strokeWidth={1.8} />
                Назад
              </span>
              <span className="line-clamp-2 font-serif text-[14px] leading-snug text-foreground">
                {prev.title}
              </span>
            </Link>
          ) : (
            <span className="flex-1" />
          )}
          {next ? (
            <Link
              href={`/readings/natal/${next.id}`}
              prefetch
              className="group flex flex-1 flex-col items-end gap-1 rounded-2xl border border-border/70 bg-card px-4 py-3 text-right transition active:scale-[0.99]"
            >
              <span className="flex items-center gap-1 text-[10.5px] font-medium uppercase tracking-[0.14em] text-primary">
                Дальше
                <ChevronRight className="h-3 w-3" strokeWidth={1.8} />
              </span>
              <span className="line-clamp-2 font-serif text-[14px] leading-snug text-foreground">
                {next.title}
              </span>
            </Link>
          ) : (
            <Link
              href="/readings/natal"
              className="flex flex-1 flex-col items-end gap-1 rounded-2xl border border-primary/30 bg-primary/[0.06] px-4 py-3 text-right transition active:scale-[0.99]"
            >
              <span className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-primary">
                К оглавлению
              </span>
              <span className="font-serif text-[14px] leading-snug text-foreground">
                Все главы
              </span>
            </Link>
          )}
        </nav>
      </article>
    </div>
  )
}
