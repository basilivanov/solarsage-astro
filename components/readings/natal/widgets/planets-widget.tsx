import type { PlanetScore } from "@/lib/contracts/natal"

type Props = {
  planets: PlanetScore[]
  title?: string
}

/**
 * Виджет планетарных функций.
 * Каждая планета — карточка с знаком/домом и композитным баллом.
 * Цвет балла: положительный → primary, отрицательный → muted.
 *
 * Отделён от нарратива: смена структуры PlanetScore трогает только этот файл.
 */
export function PlanetsWidget({ planets, title = "Планеты" }: Props) {
  if (!planets || planets.length === 0) return null

  return (
    <section
      className="rounded-2xl border border-border/70 bg-card p-4"
      aria-label={title}
    >
      <div className="mb-3 flex items-baseline justify-between">
        <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          {title}
        </h3>
        <span className="text-[11px] text-muted-foreground/70">
          композит
        </span>
      </div>

      <ul className="grid grid-cols-2 gap-2">
        {planets.map((p) => {
          const composite = typeof p.composite === "number" ? p.composite : null
          const positive = composite !== null && composite >= 0
          return (
            <li
              key={p.id}
              className="flex flex-col gap-1 rounded-xl border border-border/60 bg-background/60 p-3"
            >
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-serif text-[15px] leading-tight text-foreground">
                  {p.name}
                </span>
                {composite !== null ? (
                  <span
                    className={`flex-none rounded-full px-1.5 py-0.5 font-mono text-[11px] tabular-nums ${
                      positive
                        ? "bg-primary/10 text-primary"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {composite > 0 ? `+${composite}` : composite}
                  </span>
                ) : null}
              </div>
              <span className="text-[12px] leading-snug text-muted-foreground">
                {p.sign}
                {p.house ? ` · ${p.house} дом` : ""}
              </span>
              {p.note ? (
                <span className="mt-0.5 text-[11.5px] leading-snug text-foreground/55">
                  {p.note}
                </span>
              ) : null}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
