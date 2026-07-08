// Compact day summary card using real API data only.
// Matches 3001 oracle: compact card, date/status header, one-line status, concise fact rows.
"use client"

import type { DayStatus, PlanetInfluence, AdaptedTopFlag } from "@/lib/contracts/today"
import type { CalendarDayReadModel } from "@/lib/contracts/calendar"
import { getPlanetLabel } from "@/lib/display/sphere-labels"

type Props = {
  date: Date
  dayStatus: DayStatus
  lunar?: CalendarDayReadModel["lunar"] | null
  topFlags: AdaptedTopFlag[]
  planetInfluences: PlanetInfluence[]
}

const STATUS_META: Record<DayStatus, { emoji: string; label: string; line: string; color: string }> = {
  steady: { emoji: "🌊", label: "Ровный день", line: "без взлётов — занимайся рутиной", color: "oklch(0.62 0.06 230)" },
  supportive: { emoji: "✨", label: "Поддерживающий день", line: "день на твоей стороне — действуй", color: "oklch(0.65 0.13 145)" },
  tense: { emoji: "⚡", label: "Напряжённый день", line: "не решай на эмоциях — доводи начатое", color: "oklch(0.65 0.15 27)" },
}

const MONTHS = ["ИЮЛ", "АВГ", "СЕН", "ОКТ", "НОЯ", "ДЕК", "ЯНВ", "ФЕВ", "МАР", "АПР", "МАЙ", "ИЮН"]
const WEEKDAYS = ["ВОСКРЕСЕНЬЕ", "ПОНЕДЕЛЬНИК", "ВТОРНИК", "СРЕДА", "ЧЕТВЕРГ", "ПЯТНИЦА", "СУББОТА"]

const PLANET_SYMBOLS: Record<string, string> = {
  Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀", Mars: "♂",
  Jupiter: "♃", Saturn: "♄", Uranus: "♅", Neptune: "♆", Pluto: "♇",
}

const PLANET_THEME: Record<string, string> = {
  Sun: "проявись",
  Moon: "чувства и дом",
  Mercury: "общение и решения",
  Venus: "отношения и красота",
  Mars: "действие и смелость",
  Jupiter: "удача и масштаб",
  Saturn: "дисциплина и итоги",
}

const WEEKDAY_RULERS = [
  { planet: "Sun", symbol: "☉", label: "Солнце управитель", advice: "день самовыражения" },
  { planet: "Moon", symbol: "☽", label: "Луна управитель", advice: "день эмоций и заботы" },
  { planet: "Mars", symbol: "♂", label: "Марс управитель", advice: "день активности и борьбы" },
  { planet: "Mercury", symbol: "☿", label: "Меркурий управитель", advice: "день контактов и информации" },
  { planet: "Jupiter", symbol: "♃", label: "Юпитер управитель", advice: "день масштаба и удачи" },
  { planet: "Venus", symbol: "♀", label: "Венера управитель", advice: "день красоты и выбора" },
  { planet: "Saturn", symbol: "♄", label: "Сатурн управитель", advice: "день дисциплины и порядка" },
]

function getRussianMonth(d: Date): string {
  const m = d.getMonth()
  const map: Record<number, string> = {
    0: "ЯНВ", 1: "ФЕВ", 2: "МАР", 3: "АПР", 4: "МАЙ", 5: "ИЮН",
    6: "ИЮЛ", 7: "АВГ", 8: "СЕН", 9: "ОКТ", 10: "НОЯ", 11: "ДЕК"
  }
  return map[m] || "ИЮЛ"
}

export function DaySummaryCard({ date, dayStatus, lunar, topFlags, planetInfluences }: Props) {
  const meta = STATUS_META[dayStatus]
  const topFlag = topFlags[0]
  const topPlanet = planetInfluences.length > 0 ? [...planetInfluences].sort((a, b) => a.rank - b.rank)[0] : null
  const hasLunar = lunar && (lunar.phase || lunar.illumination != null)

  // Format date header to match 3001: e.g. "5 ИЮЛ · ВОСКРЕСЕНЬЕ"
  const monthStr = getRussianMonth(date)
  const weekdayStr = WEEKDAYS[date.getDay()]
  const dateStr = `${date.getDate()} ${monthStr} · ${weekdayStr}`

  // Ruler info
  const ruler = WEEKDAY_RULERS[date.getDay()]

  return (
    <section className="px-5 space-y-3" aria-label="Сводка дня" data-testid="day-summary-card">
      {/* Date Header outside the card */}
      <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground/80 pl-1">
        {dateStr}
      </div>

      <div className="relative overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/20 p-4">
        {/* Large Status Emoji */}
        <div className="text-[28px] mb-1.5">{meta.emoji}</div>
        
        {/* Title & One-line status */}
        <h2 className="text-[17px] font-bold text-foreground">{meta.label}</h2>
        <p className="mt-1 text-[13px] leading-snug text-muted-foreground">{meta.line}</p>

        {/* Fact Rows */}
        <div className="mt-4 space-y-3 border-t border-border/40 pt-4">
          {/* 1. Top Planet Theme */}
          {topPlanet ? (
            <div className="flex items-start gap-2.5">
              <span className="text-[14px] font-semibold w-5 text-center flex-none mt-0.5" style={{ color: meta.color }}>
                {PLANET_SYMBOLS[topPlanet.name] ?? "☉"}
              </span>
              <div className="text-[12px] leading-snug text-foreground">
                <span>тема дня — {getPlanetLabel(topPlanet.name)}: {PLANET_THEME[topPlanet.name] || "проявись"}</span>
              </div>
            </div>
          ) : null}

          {/* 2. Lunar Phase */}
          {hasLunar && lunar ? (
            <div className="flex items-start gap-2.5">
              <span className="text-[14px] font-semibold w-5 text-center flex-none mt-0.5">🌖</span>
              <div className="text-[12px] leading-snug text-foreground">
                <span>{lunar.phase || "Убывающая"}{lunar.illumination != null ? ` ${lunar.illumination}%` : ""}</span>
                <span className="text-muted-foreground block mt-0.5">
                  → {lunar.phase?.toLowerCase().includes("растущ") ? "накапливай силы" : "подводи итоги"}
                </span>
              </div>
            </div>
          ) : null}

          {/* 3. Weekday Ruler */}
          <div className="flex items-start gap-2.5">
            <span className="text-[14px] font-semibold w-5 text-center flex-none mt-0.5">{ruler.symbol}</span>
            <div className="text-[12px] leading-snug text-foreground">
              <span>{ruler.label}</span>
              <span className="text-muted-foreground block mt-0.5">→ {ruler.advice}</span>
            </div>
          </div>

          {/* 4. Lunar Void of Course */}
          {lunar && lunar.voidOfCourse ? (
            <div className="flex items-start gap-2.5">
              <span className="text-[14px] font-semibold w-5 text-center flex-none mt-0.5">🟡</span>
              <div className="text-[12px] leading-snug text-foreground">
                <span>Луна без курса</span>
                <span className="text-muted-foreground block mt-0.5">→ не подписывай и не начинай</span>
              </div>
            </div>
          ) : null}

          {/* 5. Top Flag (Transit aspect) */}
          {topFlag ? (
            <div className="flex items-start gap-2.5">
              <span className="text-[14px] font-semibold w-5 text-center flex-none mt-0.5">📌</span>
              <div className="text-[12px] leading-snug text-foreground">
                <span>{topFlag.title}</span>
                {topFlag.summary ? (
                  <span className="text-muted-foreground block mt-0.5">→ {topFlag.summary}</span>
                ) : null}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  )
}
