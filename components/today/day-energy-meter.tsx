import type { DayStatus, PlanetInfluence, SphereScore } from "@/lib/contracts/today"

type Props = {
  planetInfluences: PlanetInfluence[]
  sphereScores: SphereScore[]
  dayStatus: DayStatus
}

const STATUS_LABEL: Record<DayStatus, string> = {
  steady: "Ровный день",
  supportive: "Поддерживающий день",
  tense: "Напряжённый день",
}

function ScoreRow({ label, score, rank }: { label: string; score: number; rank: number }) {
  const width = Math.min(100, Math.abs(score) * 20)
  const positive = score >= 0

  return (
    <div className="grid grid-cols-[minmax(0,1fr)_5rem_3rem] items-center gap-2 text-xs">
      <span className="truncate text-foreground">
        {rank}. {label}
      </span>
      <span className="h-1.5 overflow-hidden rounded-full bg-muted">
        <span
          className="block h-full rounded-full"
          style={{
            width: `${width}%`,
            background: positive ? "oklch(0.64 0.12 150)" : "oklch(0.58 0.14 27)",
          }}
        />
      </span>
      <span className="text-right tabular-nums text-muted-foreground">{score}</span>
    </div>
  )
}

export function DayEnergyMeter({ planetInfluences, sphereScores, dayStatus }: Props) {
  const hasData = planetInfluences.length > 0 || sphereScores.length > 0

  return (
    <section className="px-5" aria-label="Влияния дня" data-testid="day-energy-meter">
      <div className="day-energy-surface">
        <div className="day-section-heading">
          <span>Энергия дня</span>
          <span>{STATUS_LABEL[dayStatus]}</span>
        </div>

        {!hasData ? (
          <p className="py-3 text-center text-xs text-muted-foreground">
            Оценки влияний недоступны
          </p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {planetInfluences.length > 0 ? (
              <div>
                <h3 className="mb-2 text-[11px] font-medium uppercase text-muted-foreground">
                  Планеты
                </h3>
                <div className="space-y-2">
                  {[...planetInfluences]
                    .sort((a, b) => a.rank - b.rank)
                    .map((item) => (
                      <ScoreRow
                        key={`${item.rank}-${item.name}`}
                        label={item.name}
                        score={item.score}
                        rank={item.rank}
                      />
                    ))}
                </div>
              </div>
            ) : null}

            {sphereScores.length > 0 ? (
              <div>
                <h3 className="mb-2 text-[11px] font-medium uppercase text-muted-foreground">
                  Сферы
                </h3>
                <div className="space-y-2">
                  {[...sphereScores]
                    .sort((a, b) => a.rank - b.rank)
                    .map((item) => (
                      <ScoreRow
                        key={`${item.rank}-${item.key}`}
                        label={item.key}
                        score={item.score}
                        rank={item.rank}
                      />
                    ))}
                </div>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </section>
  )
}
