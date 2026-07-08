// ############################################################################
// AI_HEADER: MODULE_TODAY_CONCRETE_DAY_ADVICE — backend-owned sphere advice list.
// ROLE: Renders the oracle-style "Конкретно сегодня" section from backend-owned
//       concreteAdvice contract. No local forecast-copy or client-side astrology.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONCRETE-DAY-ADVICE
// purpose: Render concrete sphere advice rows and counts provided by the backend.
//          Maintains the exact visual presentation shell and expand/collapse states.
// owns:
//   - components/today/concrete-day-advice.tsx
// inputs:
//   - concreteAdvice: ConcreteAdviceBlock backend-owned data
// outputs: TSX section with data-testid="concrete-day-advice"
// dependencies:
//   - framer-motion
//   - lucide-react
//   - @/lib/contracts/today
// side_effects: local expand/collapse state only
// invariants:
//   - 12 product rows are rendered in canonical order
//   - no client-side advice text or verdicts are fabricated
// failure_policy: renders gracefully if block is empty
// END_MODULE_CONTRACT: M-TODAY-CONCRETE-DAY-ADVICE

"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { Zap, ChevronDown } from "lucide-react"

import type { ConcreteAdviceBlock } from "@/lib/contracts/today"

type Props = {
  concreteAdvice: ConcreteAdviceBlock
}

type Verdict = "good" | "caution" | "avoid" | "neutral"

const COMPACT_ROW_COUNT = 6

const VERDICT_META: Record<Verdict, { label: string; color: string; bg: string }> = {
  good: { label: "да", color: "oklch(0.65 0.13 145)", bg: "oklch(0.65 0.13 145 / 0.08)" },
  caution: { label: "осторожно", color: "oklch(0.70 0.13 85)", bg: "oklch(0.70 0.13 85 / 0.08)" },
  avoid: { label: "нет", color: "oklch(0.58 0.14 27)", bg: "oklch(0.58 0.14 27 / 0.08)" },
  neutral: { label: "ровно", color: "oklch(0.55 0.06 295)", bg: "oklch(0.55 0.06 295 / 0.05)" },
}

export function ConcreteDayAdvice({ concreteAdvice }: Props) {
  const [expanded, setExpanded] = useState(false)

  const rows = concreteAdvice?.rows || []
  const counts = concreteAdvice?.counts || { good: 0, caution: 0, avoid: 0, neutral: 0 }

  const visibleRows = expanded ? rows : rows.slice(0, COMPACT_ROW_COUNT)
  const hiddenCount = Math.max(rows.length - COMPACT_ROW_COUNT, 0)

  const goodCount = counts.good
  const avoidCount = counts.caution + counts.avoid

  return (
    <section className="px-6" aria-label="Конкретно по сферам" data-testid="concrete-day-advice">
      <div className="mb-3 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground text-center">
          <Zap className="h-3 w-3" strokeWidth={1.8} />
          Конкретно сегодня
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <div className="overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/20">
        {/* Summary header */}
        <div className="flex items-center justify-between border-b border-border/50 px-4 py-3">
          <div className="flex items-center gap-3 text-[11px]">
            <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              {goodCount} благоприятно
            </span>
            <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
              {avoidCount} осторожно
            </span>
          </div>
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
            aria-controls="concrete-day-advice-rows"
            className="flex items-center gap-0.5 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
          >
            {expanded ? "свернуть" : "все 12 сфер"}
            <ChevronDown
              className={`h-3 w-3 transition-transform ${expanded ? "rotate-180" : ""}`}
              strokeWidth={2}
            />
          </button>
        </div>

        {/* Advice list */}
        <div className="divide-y divide-border/30" id="concrete-day-advice-rows">
          {visibleRows.map((row, i) => {
            const meta = VERDICT_META[row.verdict]
            return (
              <motion.div
                key={row.key}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.25, delay: i * 0.04 }}
                className="flex items-start gap-2.5 px-4 py-2.5"
                style={{ background: expanded ? meta.bg : undefined }}
                data-testid="concrete-day-advice-row"
                data-status={row.verdict}
              >
                <span className="mt-0.5 text-[14px] leading-none flex-none">{row.iconName}</span>
                <span className="w-[68px] flex-none text-[11px] font-medium text-muted-foreground">
                  {row.label}
                </span>
                <span className="flex-1 text-[12.5px] leading-snug text-foreground">
                  {row.text}
                </span>
                <span
                  className="mt-1 h-1.5 w-1.5 flex-none rounded-full"
                  style={{ background: meta.color }}
                  title={meta.label}
                  aria-hidden
                />
              </motion.div>
            )
          })}
        </div>

        {/* Expand hint when collapsed */}
        {!expanded && hiddenCount > 0 && (
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="w-full py-2 text-center text-[11px] text-muted-foreground transition-colors hover:bg-muted/30 hover:text-foreground"
          >
            Показать ещё {hiddenCount} сфер ▾
          </button>
        )}
      </div>
    </section>
  )
}
