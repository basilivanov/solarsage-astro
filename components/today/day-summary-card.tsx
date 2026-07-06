import type { CalendarDayReadModel } from "@/lib/contracts/calendar"
import type {
  DayStatus,
  PlanetInfluence,
  SphereScore,
} from "@/lib/contracts/today"

type Props = {
  date: Date
  dayStatus: DayStatus
  lunar?: CalendarDayReadModel["lunar"] | null
  planetInfluences: PlanetInfluence[]
  sphereScores: SphereScore[]
}

const STATUS_LABEL: Record<DayStatus, string> = {
  steady: "Ровный день",
  supportive: "Поддерживающий день",
  tense: "Напряжённый день",
}

const STATUS_COLOR: Record<DayStatus, string> = {
  steady: "oklch(0.62 0.06 230)",
  supportive: "oklch(0.64 0.12 150)",
  tense: "oklch(0.58 0.14 27)",
}

function rankedFirst<T extends { rank: number }>(items: T[]): T | undefined {
  return [...items].sort((a, b) => a.rank - b.rank)[0]
}

export function DaySummaryCard({
  date,
  dayStatus,
  lunar,
  planetInfluences,
  sphereScores,
}: Props) {
  const topPlanet = rankedFirst(planetInfluences)
  const topSphere = rankedFirst(sphereScores)
  const hasLunar = Boolean(
    lunar
    && (
      lunar.phase
      || lunar.illumination != null
      || lunar.moonSign
      || lunar.lunarDay != null
      || lunar.voidOfCourse != null
    ),
  )

  return (
    <section className="px-5" aria-label="Сводка дня" data-testid="day-summary-card">
      <div className="day-summary-surface">
        <div className="flex items-center justify-between gap-3">
          <span className="text-[11px] font-medium uppercase text-muted-foreground">
            {new Intl.DateTimeFormat("ru-RU", {
              day: "numeric",
              month: "short",
            }).format(date)}
          </span>
          <span className="text-xs font-medium" style={{ color: STATUS_COLOR[dayStatus] }}>
            {STATUS_LABEL[dayStatus]}
          </span>
        </div>

        <div className="mt-3 space-y-2 text-xs">
          {hasLunar ? (
            <div className="flex flex-wrap gap-x-2 gap-y-1 text-foreground">
              {lunar?.phase ? <span>{lunar.phase}</span> : null}
              {lunar?.illumination != null ? <span>{lunar.illumination}%</span> : null}
              {lunar?.moonSign ? <span>Луна в {lunar.moonSign}</span> : null}
              {lunar?.lunarDay != null ? <span>{lunar.lunarDay} лунный день</span> : null}
              {lunar?.voidOfCourse === true ? <span>Луна без курса</span> : null}
            </div>
          ) : (
            <p className="text-muted-foreground">Лунные данные недоступны</p>
          )}

          {topPlanet ? (
            <p>
              Ведущее влияние: <strong>{topPlanet.name}</strong>{" "}
              <span className="tabular-nums text-muted-foreground">{topPlanet.score}</span>
            </p>
          ) : null}
          {topSphere ? (
            <p>
              Главная сфера: <strong>{topSphere.key}</strong>{" "}
              <span className="tabular-nums text-muted-foreground">{topSphere.score}</span>
            </p>
          ) : null}
        </div>
      </div>
    </section>
  )
}
