"use client"

type Props = {
  bullets: string[]
}

export function SalesBullets({ bullets }: Props) {
  if (!bullets.length) return null

  return (
    <section className="rounded-2xl border border-border/70 bg-card p-4">
      <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Что входит
      </div>
      <ul className="mt-3 space-y-2">
        {bullets.map((bullet, index) => (
          <li key={`${bullet}-${index}`} className="flex gap-2 text-[13px] leading-relaxed text-foreground/85">
            <span className="mt-0.5 text-primary">✦</span>
            <span>{bullet}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
