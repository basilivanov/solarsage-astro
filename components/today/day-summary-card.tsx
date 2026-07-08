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

function getRussianMonth(d: Date): string {
  const m = d.getMonth()
  const map: Record<number, string> = {
    0: "ИЮЛ", 1: "ФЕВ", 2: "МАР", 3: "АПР", 4: "МАЙ", 5: "ИЮН",
    6: "ИЮЛ", 7: "АВГ", 8: "СЕН", 9: "ОКТ", 10: "НОЯ", 11: "ДЕК"
  }
  // Standard Russian calendar months. July is 6. The previous code mapped 0 to ИЮЛ by mistake in static list,
  // but let us map all months correctly for calendar correctness.
  const correctMap: Record<number, string> = {
    0: "ЯНВ", 1: "ФЕВ", 2: "МАР", 3: "АПР", 4: "МАЙ", 5: "ИЮН",
    6: "ИЮЛ", 7: "АВГ", 8: "СЕН", 9: "ОКТ", 10: "НОЯ", 11: "ДЕК"
  }
  return correctMap[m] || "ИЮЛ"
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

  return (
    <section className="px-5" aria-label="Сводка дня" data-testid="day-summary-card">
      <div className="relative overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/20 p-4">
        {/* Card Header matching 3001 visual shell: date/weekday on left, status emoji/label on right */}
        <div className="relative flex items-center justify-between border-b border-border/40 pb-2.5">
          <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground/80">
            {dateStr}
          </span>
          <div className="flex items-center gap-1.5">
            <span className="text-[14px]">{meta.emoji}</span>
            <span className="text-[12.5px] font-bold" style={{ color: meta.color }}>
              {meta.label}
            </span>
          </div>
        </div>

        {/* One-line status line */}
        <p className="relative mt-2.5 text-[13px] leading-snug text-foreground/85">
          {meta.line}
        </p>

        {/* Fact Rows (only if there is real data) */}
        <div className="relative mt-3.5 space-y-3 border-t border-border/30 pt-3.5">
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

          {/* 3. Lunar Void of Course */}
          {lunar && lunar.voidOfCourse ? (
            <div className="flex items-start gap-2.5">
              <span className="text-[14px] font-semibold w-5 text-center flex-none mt-0.5">🟡</span>
              <div className="text-[12px] leading-snug text-foreground">
                <span>Луна без курса</span>
                <span className="text-muted-foreground block mt-0.5">→ не подписывай и не начинай</span>
              </div>
            </div>
          ) : null}

          {/* 4. Top Flag (Transit aspect) */}
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
