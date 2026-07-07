// Compact day summary card using real API data only.
// No local astrology calculations — all data comes from TodayPayload/CalendarPayload adapters.

import type { DayStatus, PlanetInfluence, SphereScore, AdaptedTopFlag } from "@/lib/contracts/today"
import type { CalendarDayReadModel } from "@/lib/contracts/calendar"

type Props = {
  date: Date
  dayStatus: DayStatus
  lunar?: CalendarDayReadModel["lunar"] | null
  topFlags: AdaptedTopFlag[]
  planetInfluences: PlanetInfluence[]
}

const STATUS_META: Record<DayStatus, { emoji: string; label: string; line: string; color: string }> = {
  steady: { emoji: "🌊", label: "Ровный", line: "без взлётов — занимайся рутиной", color: "oklch(0.62 0.06 230)" },
  supportive: { emoji: "✨", label: "Поддерживающий", line: "день на твоей стороне — действуй", color: "oklch(0.65 0.13 145)" },
  tense: { emoji: "⚡", label: "Напряжённый", line: "не решай на эмоциях — доводи начатое", color: "oklch(0.65 0.15 27)" },
}

const MONTHS = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]

function formatDate(d: Date): string {
  return `${d.getDate()} ${MONTHS[d.getMonth()]}`
}

function rankedFirst<T extends { rank?: number }>(items: T[]): T | undefined {
  const sorted = [...items].sort((a, b) => (a.rank ?? 999) - (b.rank ?? 999))
  return sorted[0]
}

export function DaySummaryCard({ date, dayStatus, lunar, topFlags, planetInfluences }: Props) {
  const meta = STATUS_META[dayStatus]
  const topFlag = topFlags[0]
  const topPlanet = rankedFirst(planetInfluences)
  const hasLunar = lunar && (lunar.phase || lunar.illumination != null || lunar.moonSign || lunar.lunarDay != null)

  return (
    <section className="px-5" aria-label="Сводка дня" data-testid="day-summary-card">
      <div className="relative overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/30 p-3.5">
        {/* Subtle glow */}
        <div aria-hidden className="pointer-events-none absolute inset-0 opacity-25"
          style={{ background: `radial-gradient(circle at 85% 15%, ${meta.color}18, transparent 50%)` }}
        />

        {/* Header: date + status */}
        <div className="relative flex items-center justify-between">
          <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            {formatDate(date)}
          </span>
          <div className="flex items-center gap-1.5">
            <span className="text-[13px]">{meta.emoji}</span>
            <span className="text-[12px] font-medium" style={{ color: meta.color }}>{meta.label}</span>
          </div>
        </div>

        {/* Status one-liner */}
        <p className="relative mt-1 text-[12.5px] leading-snug text-foreground/85">{meta.line}</p>

        {/* Data rows from real API fields */}
        <div className="relative mt-2.5 space-y-1 border-t border-border/40 pt-2.5">
          {hasLunar && lunar?.phase ? (
            <div className="flex items-baseline gap-2">
              <span className="text-[13px] w-5 text-center flex-none">🌙</span>
              <span className="text-[11.5px] font-medium text-foreground flex-none">{lunar.phase}{lunar.illumination != null ? ` ${lunar.illumination}%` : ""}</span>
              {lunar.moonSign ? <span className="text-[11.5px] text-muted-foreground">→ Луна в {lunar.moonSign}</span> : null}
            </div>
          ) : null}

          {topFlag ? (
            <div className="flex items-baseline gap-2">
              <span className="text-[13px] w-5 text-center flex-none">📌</span>
              <span className="text-[11.5px] font-medium text-foreground flex-none">{topFlag.title}</span>
              <span className="text-[11.5px] text-muted-foreground">→ {topFlag.summary}</span>
            </div>
          ) : null}

          {topPlanet ? (
            <div className="flex items-baseline gap-2">
              <span className="text-[13px] w-5 text-center flex-none">★</span>
              <span className="text-[11.5px] font-medium text-foreground flex-none">{topPlanet.name}</span>
              <span className="text-[11.5px] text-muted-foreground">→ влияние {topPlanet.score}</span>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  )
}
