import type { Highlight } from "@/lib/contracts/natal"

type Props = {
  items: Highlight[]
}

/**
 * Горизонтальная "лента" ярлыков карты — ASC, управитель, доминанта и т.п.
 * Скроллится горизонтально на узких экранах. Каждая капсула — самодостаточна.
 */
export function HighlightsStrip({ items }: Props) {
  if (!items || items.length === 0) return null

  return (
    <div
      className="-mx-5 flex gap-2.5 overflow-x-auto px-5 pb-1"
      style={{ scrollbarWidth: "none" }}
      aria-label="Ярлыки натальной карты"
    >
      {items.map((h) => (
        <div
          key={h.id}
          className="flex flex-none flex-col rounded-2xl border border-border/70 bg-card px-4 py-3 min-w-[120px]"
        >
          <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            {h.label}
          </span>
          <span className="mt-1 font-serif text-[18px] leading-tight text-foreground">
            {h.value}
          </span>
          {h.hint ? (
            <span className="mt-0.5 text-[11.5px] leading-snug text-muted-foreground/85">
              {h.hint}
            </span>
          ) : null}
        </div>
      ))}
    </div>
  )
}
