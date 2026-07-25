// ############################################################################
// AI_HEADER: MODULE_TODAY_ASTRO_HISTORY_WIDGET
// ROLE: Astro history widget — curated educational astronomy/space-history events.
// DEPENDENCIES: lucide-react
// ############################################################################

// START_MODULE_CONTRACT: M-ASTRO-HISTORY-WIDGET
// purpose: Render curated space history event for the current day.
// owns:
//   - components/today/astro-history-widget.tsx
// inputs: date (Date | string)
// outputs: AstroHistoryWidget React component
// dependencies: lucide-react
// side_effects: none (pure rendering)
// emitted_logs: none
// failure_policy: fallback event
// END_MODULE_CONTRACT: M-ASTRO-HISTORY-WIDGET

// START_MODULE_MAP: M-ASTRO-HISTORY-WIDGET
// public_entrypoints:
//   - AstroHistoryWidget
// semantic_blocks:
//   - ASTRO_HISTORY_WIDGET: Astronomy history event widget component
// owned_tests:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// END_MODULE_MAP: M-ASTRO-HISTORY-WIDGET

"use client"

import { CalendarDays } from "lucide-react"

type HistoryEvent = {
  year: string
  category: string
  title: string
  description: string
}

const EVENTS: Record<string, HistoryEvent> = {
  "2026-07-05": {
    year: "1997",
    category: "миссия",
    title: "«Марс Пасфайндер» на Марсе",
    description: "Американский зонд «Марс Пасфайндер» успешно посадил марсоход «Соджорнер» — первый rover на Марсе.",
  },
  "2026-07-04": {
    year: "1997",
    category: "миссия",
    title: "«Марс Пасфайндер» на Марсе",
    description: "Американский зонд «Марс Пасфайндер» успешно посадил марсоход «Соджорнер» — первый rover на Марсе.",
  },
}

const DEFAULT_EVENT: HistoryEvent = {
  year: "1969",
  category: "миссия",
  title: "«Аполлон-11» старт к Луне",
  description: "Космический корабль «Аполлон-11» стартовал с мыса Канаверал для первой высадки человека на Луну.",
}

// START_BLOCK: ASTRO_HISTORY_WIDGET
export function AstroHistoryWidget({ date }: { date: Date }) {
  const dateStr = date.toISOString().split("T")[0]
  const event = EVENTS[dateStr] || DEFAULT_EVENT

  return (
    <section className="px-5 space-y-3" data-testid="astro-history-widget">
      {/* Outer Header with divider lines matching 3001 */}
      <div className="flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          <CalendarDays className="h-3 w-3" strokeWidth={1.8} aria-hidden />
          БЛИЖАЙШИЕ ДНИ
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      {/* Curated Single History Card */}
      <div className="rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/10 p-4">
        <div className="flex flex-col gap-1">
          {/* Large Year */}
          <span className="text-[28px] font-bold leading-none tracking-tight text-foreground/90">
            {event.year}
          </span>
          {/* Category */}
          <span className="text-[9px] font-bold uppercase tracking-[0.18em] text-muted-foreground">
            {event.category}
          </span>
          {/* Title */}
          <h4 className="mt-1.5 text-[14px] font-semibold leading-snug text-foreground">
            {event.title}
          </h4>
          {/* Description */}
          <p className="mt-1 text-[12px] leading-relaxed text-muted-foreground">
            {event.description}
          </p>
        </div>
      </div>
    </section>
  )
}
// END_BLOCK: ASTRO_HISTORY_WIDGET
