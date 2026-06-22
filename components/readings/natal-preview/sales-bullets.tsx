
// ############################################################################
// AI_HEADER: MODULE_NATAL-PREVIEW_SALES_BULLETS
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Module: sales-bullets.tsx
// owns:
//   - components/readings/natal-preview/sales-bullets.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

type Props = {
  bullets: string[]
}

export function SalesBullets({ bullets }: Props) {
  if (!bullets.length) return null

  return (
    <section className="rounded-2xl border border-primary/10 bg-primary/[0.03] px-4 py-4">
      <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Что ты получишь
      </div>
      <p className="mt-2 text-[13px] text-foreground/70">Ты:</p>
      <ul className="mt-1.5 space-y-2">
        {bullets.map((bullet, index) => (
          <li key={`${bullet}-${index}`} className="flex gap-2 text-[13.5px] leading-relaxed text-foreground/85">
            <span className="mt-0.5 text-primary">✦</span>
            <span>{bullet}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
