import type { SphereScore } from "@/lib/readings/natal-schema"

type Props = {
  spheres: SphereScore[]
  /** Сколько строк показать. По умолчанию все. */
  limit?: number
  /** Заголовок виджета. */
  title?: string
}

const MAX_DOMINANCE = 5

/**
 * Виджет сфер жизни.
 * Каждая сфера — строка с горизонтальным баром, длина которого
 * пропорциональна индексу доминанты (0..5).
 *
 * Структурирован отдельно от нарратива — если контракт сфер
 * поменяется, рендерер глав не сломается.
 */
export function SpheresWidget({
  spheres,
  limit,
  title = "Сферы жизни",
}: Props) {
  if (!spheres || spheres.length === 0) return null

  const list = typeof limit === "number" ? spheres.slice(0, limit) : spheres
  const max = Math.max(...list.map((s) => s.dominance), MAX_DOMINANCE)

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
          {list.length}
        </span>
      </div>

      <ul className="flex flex-col gap-3">
        {list.map((s, i) => {
          const pct = Math.max(2, Math.min(100, (s.dominance / max) * 100))
          const isTop = i < 3
          const isTension = s.tone === "tension"

          return (
            <li key={s.id} className="flex flex-col gap-1.5">
              <div className="flex items-baseline justify-between gap-3">
                <span
                  className={`truncate text-[13.5px] leading-snug ${
                    isTop ? "text-foreground" : "text-foreground/75"
                  }`}
                >
                  {s.title}
                </span>
                <span
                  className={`flex-none font-mono text-[12px] tabular-nums ${
                    isTop ? "text-primary" : "text-muted-foreground"
                  }`}
                >
                  {s.dominance.toFixed(2)}
                </span>
              </div>
              <div
                className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
                aria-hidden
              >
                <div
                  className={`h-full rounded-full transition-[width] ${
                    isTension
                      ? "bg-foreground/30"
                      : isTop
                        ? "bg-primary"
                        : "bg-primary/40"
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
