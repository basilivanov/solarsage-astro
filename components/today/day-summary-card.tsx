// Compact day summary card using backend-owned summary facts only.
// Matches 3001 oracle: compact card, date/status header, one-line status, concise fact rows.
"use client"

import type { DayStatus, DaySummaryBlock } from "@/lib/contracts/today"

type Props = {
  date: Date
  dayStatus: DayStatus
  daySummary: DaySummaryBlock
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

export function DaySummaryCard({ date, dayStatus, daySummary }: Props) {
  const statusColor = STATUS_COLOR[dayStatus] || "oklch(0.62 0.06 230)"
  const statusEmoji = STATUS_EMOJI[dayStatus] || "🌊"

  const monthStr = MONTHS[date.getMonth()] || "ИЮЛ"
  const weekdayStr = WEEKDAYS[date.getDay()]
  const dateStr = `${date.getDate()} ${monthStr} · ${weekdayStr}`

  const statusLabel = daySummary?.statusLabel || "Ровный день"
  const statusLine = daySummary?.statusLine || "Сводка временно недоступна."
  const facts = daySummary?.facts || []

  // Helper to map backend icons/planet names to symbols
  const FACT_ICONS: Record<string, string> = {
    Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀", Mars: "♂",
    Jupiter: "♃", Saturn: "♄", Uranus: "♅", Neptune: "♆", Pluto: "♇",
    moon: "🌖", void_moon: "🟡", flag: "📌"
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
