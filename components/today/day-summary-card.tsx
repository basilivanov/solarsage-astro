// ############################################################################
// AI_HEADER: MODULE_DAY_SUMMARY_CARD — compact backend-owned daily summary.
// ROLE: Renders legacy facts or the V2 human-first compact summary mode.
// ############################################################################

// START_MODULE_CONTRACT: M-DAY-SUMMARY-CARD
// purpose: Present backend-owned status information without calculating a forecast.
// owns:
//   - components/today/day-summary-card.tsx
// inputs: date, dayStatus, daySummary, humanFirst.
// outputs: data-testid="day-summary-card" section.
// dependencies: lib/contracts/today, lib/icons.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - humanFirst hides facts, technical labels, and duplicate date.
//   - legacy mode keeps backend facts visible.
// failure_policy: use existing safe status fallbacks for missing summary fields.
// END_MODULE_CONTRACT: M-DAY-SUMMARY-CARD

// START_MODULE_MAP: M-DAY-SUMMARY-CARD
// public_entrypoints:
//   - DaySummaryCard
// semantic_blocks:
//   - DAY_SUMMARY_CARD: Day summary status card component
// owned_tests:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// END_MODULE_MAP: M-DAY-SUMMARY-CARD

"use client"

import type { DayStatus, DaySummaryBlock } from "@/lib/contracts/today"
import type { RelativeDayStatus } from "@/lib/api/day"
import { getIcon } from "@/lib/icons"
import { DayZoneIndicator } from "./day-zone-indicator"

type Props = {
  date: Date
  dayStatus: DayStatus
  daySummary: DaySummaryBlock
  humanFirst?: boolean
  relativeStatus?: RelativeDayStatus | null
}

const STATUS_COLOR: Record<DayStatus, string> = {
  steady: "oklch(0.62 0.06 230)",
  supportive: "oklch(0.65 0.13 145)",
  tense: "oklch(0.65 0.15 27)",
}

const STATUS_EMOJI: Record<DayStatus, string> = {
  steady: "🌊",
  supportive: "✨",
  tense: "⚡",
}

const MONTHS = ["ЯНВ", "ФЕВ", "МАР", "АПР", "МАЙ", "ИЮН", "ИЮЛ", "АВГ", "СЕН", "ОКТ", "НОЯ", "ДЕК"]
const WEEKDAYS = ["ВОСКРЕСЕНЬЕ", "ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА"]

// START_BLOCK: DAY_SUMMARY_CARD
export function DaySummaryCard({
  date,
  dayStatus,
  daySummary,
  humanFirst = false,
  relativeStatus,
}: Props) {
  // START_FUNCTION_CONTRACT: F-M-DAY-SUMMARY-CARD.DaySummaryCard
  // purpose: Render the compact human-first or legacy summary presentation.
  // inputs: Props — backend-owned day summary plus optional V2 display mode and relative day status.
  // returns: Summary card JSX.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: existing safe fallbacks are rendered for incomplete summaries.
  // END_FUNCTION_CONTRACT: F-M-DAY-SUMMARY-CARD.DaySummaryCard
  const statusColor = STATUS_COLOR[dayStatus] || "oklch(0.62 0.06 230)"
  const statusEmoji = STATUS_EMOJI[dayStatus] || "🌊"

  const monthStr = MONTHS[date.getMonth()] || "ИЮЛ"
  const weekdayStr = WEEKDAYS[date.getDay()]
  const dateStr = `${date.getDate()} ${monthStr} · ${weekdayStr}`

  // If relative status mode is relative, override statusLabel with human relative label
  const statusLabel =
    relativeStatus && relativeStatus.mode === "relative"
      ? relativeStatus.label
      : daySummary?.statusLabel || "Ровный день"

  const statusLine = daySummary?.statusLine || "Сводка временно недоступна."
  const facts = daySummary?.facts || []
  const SummaryIcon = getIcon("orbit")

  // Helper to map backend icons/planet names to symbols
  const FACT_ICONS: Record<string, string> = {
    Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀", Mars: "♂",
    Jupiter: "♃", Saturn: "♄", Uranus: "♅", Neptune: "♆", Pluto: "♇",
    moon: "🌖", void_moon: "🟡", flag: "📌"
  }

  if (humanFirst) {
    return (
      <section className="px-5" aria-label="Сводка дня" data-testid="day-summary-card">
        <div className="rounded-[24px] border border-border/60 bg-card px-4 py-4 shadow-[0_12px_32px_-26px_rgba(76,29,149,0.35)]">
          <div className="flex min-h-20 items-center gap-3.5">
            <span
              className="flex h-11 w-11 flex-none items-center justify-center rounded-2xl bg-violet-100/70 text-violet-700 dark:bg-violet-500/15 dark:text-violet-200"
              aria-hidden
            >
              <SummaryIcon className="h-5 w-5" strokeWidth={1.7} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[16px] font-semibold leading-snug text-foreground">{statusLabel}</p>
              <p className="mt-1 text-[14px] leading-relaxed text-muted-foreground">{statusLine}</p>
            </div>
          </div>

          <DayZoneIndicator relativeStatus={relativeStatus} />
        </div>
      </section>
    )
  }

  return (
    <section className="px-5" aria-label="Сводка дня" data-testid="day-summary-card">
      <div className="relative overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/20 p-4">
        {/* Card Header matching 3001 visual shell: date/weekday on left, status emoji/label on right */}
        <div className="relative flex items-center justify-between border-b border-border/40 pb-2.5">
          <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground/80">
            {dateStr}
          </span>
          <div className="flex items-center gap-1.5">
            <span className="text-[14px]">{statusEmoji}</span>
            <span className="text-[12.5px] font-bold" style={{ color: statusColor }}>
              {statusLabel}
            </span>
          </div>
        </div>

        {/* One-line status line */}
        <p className="relative mt-2.5 text-[13px] leading-snug text-foreground/85">
          {statusLine}
        </p>

        <DayZoneIndicator relativeStatus={relativeStatus} />

        {/* Fact Rows (only if there is real data) */}
        {facts.length > 0 && (
          <div className="relative mt-3.5 space-y-3 border-t border-border/30 pt-3.5">
            {facts.map((fact, idx) => {
              const icon = FACT_ICONS[fact.iconName] || FACT_ICONS[fact.kind] || "📌"
              return (
                <div key={idx} className="flex items-start gap-2.5">
                  <span className="text-[14px] font-semibold w-5 text-center flex-none mt-0.5" style={{ color: statusColor }}>
                    {icon}
                  </span>
                  <div className="text-[12px] leading-snug text-foreground">
                    <span>{fact.title}</span>
                    {fact.summary ? (
                      <span className="text-muted-foreground block mt-0.5">→ {fact.summary}</span>
                    ) : null}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </section>
  )
}
// END_BLOCK: DAY_SUMMARY_CARD
