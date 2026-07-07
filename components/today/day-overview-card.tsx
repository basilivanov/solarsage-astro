// ############################################################################
// AI_HEADER: MODULE_TODAY_DAY_OVERVIEW_CARD
// ROLE: UI component — Large calm day card composition for the oracle's
//       day overview block. Shows day status, lunar info, top influences.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-DAY-OVERVIEW-CARD
// purpose: Render a prominent day-status card that composes the day status,
//          lunar phase, top planet influence, and top sphere score into a
//          single visual block. Matches the mock-preview oracle's "day overview".
// owns:
//   - components/today/day-overview-card.tsx
// inputs:
//   - dayStatus: DayStatus — supportive | steady | tense
//   - lunar: optional lunar data
//   - planetInfluences: ranked planet influence list
//   - sphereScores: ranked sphere score list
// outputs:
//   - JSX section with data-testid="day-overview-card" and data-status={dayStatus}
// dependencies:
//   - @/lib/contracts/today (types)
//   - @/lib/display/sphere-labels (getSphereLabel)
// side_effects: none
// invariants:
//   - Sphere keys are mapped via getSphereLabel (never shown raw)
//   - data-status reflects the real dayStatus from the API
//   - Top influence is derived from rank:1 items, not hardcoded
// failure_policy: gracefully shows "данные недоступны" when fields are absent
// END_MODULE_CONTRACT: M-TODAY-DAY-OVERVIEW-CARD

import type { CalendarDayReadModel } from "@/lib/contracts/calendar"
import type { DayStatus, PlanetInfluence, SphereScore } from "@/lib/contracts/today"
import { getSphereLabel } from "@/lib/display/sphere-labels"

type Props = {
  dayStatus: DayStatus
  lunar?: CalendarDayReadModel["lunar"] | null
  planetInfluences: PlanetInfluence[]
  sphereScores: SphereScore[]
}

const STATUS_LABEL: Record<DayStatus, string> = {
  steady: "Ровный",
  supportive: "Поддерживающий",
  tense: "Напряжённый",
}

const STATUS_BG: Record<DayStatus, string> = {
  steady: "bg-sky-500/10 border-sky-500/20",
  supportive: "bg-emerald-500/10 border-emerald-500/20",
  tense: "bg-amber-500/10 border-amber-500/20",
}

const STATUS_GLOW: Record<DayStatus, string> = {
  steady: "bg-sky-500/8",
  supportive: "bg-emerald-500/8",
  tense: "bg-amber-500/8",
}

const STATUS_TEXT: Record<DayStatus, string> = {
  steady: "text-sky-600 dark:text-sky-400",
  supportive: "text-emerald-600 dark:text-emerald-400",
  tense: "text-amber-600 dark:text-amber-400",
}

function rankedFirst<T extends { rank: number }>(items: T[]): T | undefined {
  return [...items].sort((a, b) => a.rank - b.rank)[0]
}

export function DayOverviewCard({ dayStatus, lunar, planetInfluences, sphereScores }: Props) {
  const topPlanet = rankedFirst(planetInfluences)
  const topSphere = rankedFirst(sphereScores)
  const hasLunar = Boolean(
    lunar &&
      (lunar.phase || lunar.illumination != null || lunar.moonSign || lunar.lunarDay != null || lunar.voidOfCourse != null),
  )

  return (
    <section
      data-testid="day-overview-card"
      data-status={dayStatus}
      className={`mx-5 overflow-hidden rounded-3xl border ${STATUS_BG[dayStatus]} relative`}
      aria-label="Обзор дня"
    >
      {/* Subtle glow effect */}
      <div
        aria-hidden
        className={`pointer-events-none absolute -right-12 -top-12 h-40 w-40 rounded-full blur-3xl ${STATUS_GLOW[dayStatus]}`}
      />

      <div className="relative px-5 py-5">
        {/* Status badge */}
        <div className="mb-3 flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-wider ${STATUS_BG[dayStatus]} ${STATUS_TEXT[dayStatus]}`}
          >
            <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-current" />
            {STATUS_LABEL[dayStatus]}
          </span>
        </div>

        {/* Lunar phase — large visual element */}
        {hasLunar ? (
          <div className="mb-4">
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
              {lunar?.phase ? (
                <span className="font-serif text-[28px] leading-tight tracking-tight text-foreground">
                  {lunar.phase}
                </span>
              ) : null}
              {lunar?.illumination != null ? (
                <span className="text-[13px] font-medium text-muted-foreground">
                  {lunar.illumination}%
                </span>
              ) : null}
            </div>
            <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-[13px] text-muted-foreground">
              {lunar?.moonSign ? <span>Луна в {lunar.moonSign}</span> : null}
              {lunar?.lunarDay != null ? <span>{lunar.lunarDay} лд</span> : null}
              {lunar?.voidOfCourse === true ? <span className="font-medium text-amber-600 dark:text-amber-400">Луна без курса</span> : null}
            </div>
          </div>
        ) : (
          <div className="mb-4">
            <p className="font-serif text-[22px] leading-tight text-foreground/80">Доброе утро</p>
            <p className="mt-0.5 text-[13px] text-muted-foreground">Лунные данные загружаются</p>
          </div>
        )}

        {/* Divider */}
        <div aria-hidden className="mb-4 h-px bg-border/60" />

        {/* Top influences grid */}
        <div className="grid grid-cols-2 gap-4">
          {topPlanet ? (
            <div>
              <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Планета</p>
              <p className="mt-0.5 font-serif text-[18px] leading-tight text-foreground">{topPlanet.name}</p>
              <p className="text-[12px] text-muted-foreground">
                влияние <span className="tabular-nums">{topPlanet.score}</span>
              </p>
            </div>
          ) : null}

          {topSphere ? (
            <div>
              <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">Сфера</p>
              <p className="mt-0.5 font-serif text-[18px] leading-tight text-foreground">{getSphereLabel(topSphere.key)}</p>
              <p className="text-[12px] text-muted-foreground">
                активность <span className="tabular-nums">{topSphere.score}</span>
              </p>
            </div>
          ) : null}

          {!topPlanet && !topSphere ? (
            <div className="col-span-2">
              <p className="text-[12px] text-muted-foreground">Оценки влияний загружаются</p>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  )
}
