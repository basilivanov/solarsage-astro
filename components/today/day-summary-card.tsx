// Compact day summary card using real API data only.
// Matches 3001 oracle: compact card, date/status header, one-line status, concise fact rows.
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

const MONTHS = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
const PLANET_SYMBOLS: Record<string, string> = {
  Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀", Mars: "♂",
  Jupiter: "♃", Saturn: "♄", Uranus: "♅", Neptune: "♆", Pluto: "♇",
}

const PLANET_THEME: Record<string, string> = {
  Sun: "тема дня — проявись",
  Moon: "тема дня — чувства и дом",
  Mercury: "тема дня — общение и решения",
  Venus: "тема дня — отношения и красота",
  Mars: "тема дня — действие и смелость",
  Jupiter: "тема дня — удача и масштаб",
  Saturn: "тема дня — дисциплина и итоги",
}

export function DaySummaryCard({ date, dayStatus, lunar, topFlags, planetInfluences }: Props) {
  const meta = STATUS_META[dayStatus]
  const topFlag = topFlags[0]
  const topPlanet = planetInfluences.length > 0 ? [...planetInfluences].sort((a, b) => a.rank - b.rank)[0] : null
  const hasLunar = lunar && (lunar.phase || lunar.illumination != null)

  return (
    <section className="px-5" aria-label="Сводка дня" data-testid="day-summary-card">
      <div className="relative overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/30 p-3.5">
        <div aria-hidden className="pointer-events-none absolute inset-0 opacity-25"
          style={{ background: `radial-gradient(circle at 85% 15%, ${meta.color}18, transparent 50%)` }}
        />
        <div className="relative flex items-center justify-between">
          <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            {date.getDate()} {MONTHS[date.getMonth()]}
          </span>
          <div className="flex items-center gap-1.5">
            <span className="text-[13px]">{meta.emoji}</span>
            <span className="text-[12px] font-medium" style={{ color: meta.color }}>{meta.label}</span>
          </div>
        </div>
        <p className="relative mt-1 text-[12.5px] leading-snug text-foreground/85">{meta.line}</p>

        <div className="relative mt-2.5 space-y-1 border-t border-border/40 pt-2.5">
          {hasLunar && lunar?.phase ? (
            <div className="flex items-baseline gap-2">
              <span className="text-[13px] w-5 text-center flex-none">🌙</span>
              <span className="text-[11.5px] text-foreground">{lunar.phase}{lunar.illumination != null ? ` ${lunar.illumination}%` : ""}</span>
            </div>
          ) : null}
          {topFlag ? (
            <div className="flex items-baseline gap-2">
              <span className="text-[13px] w-5 text-center flex-none">📌</span>
              <span className="text-[11.5px] text-foreground">{topFlag.title}</span>
            </div>
          ) : null}
          {topPlanet ? (
            <div className="flex items-baseline gap-2">
              <span className="text-[13px] w-5 text-center flex-none">{PLANET_SYMBOLS[topPlanet.name] ?? "★"}</span>
              <span className="text-[11.5px] text-foreground">{getPlanetLabel(topPlanet.name)}</span>
              {PLANET_THEME[topPlanet.name] ? (
                <span className="text-[11.5px] text-muted-foreground">→ {PLANET_THEME[topPlanet.name]}</span>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  )
}
