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
//   - @/lib/presentation/today-v2
// side_effects: local expand/collapse state only
// invariants:
//   - 12 product rows are rendered in canonical order
//   - no client-side advice text or verdicts are fabricated
//   - nested row interaction does not toggle the all-12-spheres control
// failure_policy: renders gracefully if block is empty
// END_MODULE_CONTRACT: M-TODAY-CONCRETE-DAY-ADVICE

"use client"

import { useId, useState } from "react"
import { motion } from "framer-motion"
import { Zap, ChevronDown } from "lucide-react"

import type { ConcreteAdviceBlock } from "@/lib/contracts/today"
import { TechniqueChip } from "./technique-chip"
import {
  formatConcreteAdviceEvidenceTitle,
  formatOrb,
} from "@/lib/presentation/today-v2"

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

const ICON_MAP: Record<string, string> = {
  briefcase: "💼",
  building: "💰",
  "list-checks": "📝",
  sparkle: "💖",
  leaf: "🏃",
  telescope: "💬",
  compass: "🌿",
  target: "🎯",
  hourglass: "✈️",
  grid: "🎨",
  layers: "📚",
  zap: "🛍️",
}

export function ConcreteDayAdvice({ concreteAdvice }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [expandedRow, setExpandedRow] = useState<string | null>(null)
  const rowsId = useId()

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
            aria-controls={rowsId}
            className="flex items-center gap-0.5 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
          >
            {expanded ? "свернуть" : "все 12 сфер"}
            <ChevronDown
              className={`h-3 w-3 transition-transform ${expanded ? "rotate-180" : ""}`}
              strokeWidth={2}
            />
          </button>
        </div>

        <div className="divide-y divide-border/30" id={rowsId}>
          {visibleRows.map((row, i) => {
            const meta = VERDICT_META[row.verdict]
            const uniqueTechs = Array.from(
              new Set((row.evidence || []).map((e) => e.technique).filter(Boolean)),
            ) as string[]
            const hasEvidence = (row.evidence || []).length > 0
            const isRowOpen = expandedRow === row.key
            const rowDetailsId = `concrete-advice-evidence-${row.key}`

            return (
              <motion.div
                key={row.key}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.25, delay: i * 0.04 }}
                className="flex flex-col px-4 py-2.5"
                style={{ background: isRowOpen ? meta.bg : undefined }}
                data-testid="concrete-day-advice-row"
                data-status={row.verdict}
              >
                <button
                  type="button"
                  className="flex w-full items-start gap-2.5 text-left transition-colors hover:opacity-95"
                  aria-expanded={hasEvidence ? isRowOpen : undefined}
                  aria-controls={hasEvidence ? rowDetailsId : undefined}
                  onClick={(e) => {
                    // Native <button> already activates on Enter/Space via click.
                    // Do not add a manual key handler — it would double-toggle.
                    e.stopPropagation()
                    if (!hasEvidence) return
                    setExpandedRow((cur) => (cur === row.key ? null : row.key))
                  }}
                >
                  <span className="mt-0.5 text-[14px] leading-none flex-none">
                    {ICON_MAP[row.iconName] || "•"}
                  </span>
                  <span className="w-[68px] flex-none text-[11px] font-medium text-muted-foreground">
                    {row.label}
                  </span>
                  <div className="flex-1 flex flex-col min-w-0">
                    <span className="text-[12.5px] leading-snug text-foreground">{row.text}</span>
                    {uniqueTechs.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {uniqueTechs.map((tech) => (
                          <TechniqueChip key={tech} technique={tech} />
                        ))}
                      </div>
                    )}
                    {hasEvidence && !isRowOpen && (
                      <span className="mt-1 text-[10px] text-muted-foreground">
                        почему именно у вас
                      </span>
                    )}
                  </div>
                  <span
                    className="mt-1 h-1.5 w-1.5 flex-none rounded-full"
                    style={{ background: meta.color }}
                    title={meta.label}
                    aria-hidden
                  />
                </button>

                {isRowOpen && hasEvidence && (
                  <div
                    id={rowDetailsId}
                    data-testid="concrete-day-advice-evidence"
                    className="mt-2.5 ml-8 pl-3 border-l border-violet-200/80 space-y-2 text-[12px] text-foreground/80"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="font-semibold text-[11px] text-muted-foreground mb-1">
                      Почему именно у вас
                    </div>
                    {row.evidence.map((ev, idx) => {
                      const title = formatConcreteAdviceEvidenceTitle({
                        title: ev.title,
                        kind: ev.kind,
                        technique: ev.technique,
                        planet: ev.planet,
                        targetPlanet: ev.targetPlanet,
                        aspectType: ev.aspectType,
                        orb: ev.orb,
                        contributionSourceId: ev.contributionSourceId,
                        activationId: ev.activationId,
                      })
                      const orb = formatOrb(ev.orb)
                      return (
                        <div key={idx} className="space-y-1">
                          <p className="leading-snug">{title}</p>
                          <div className="flex flex-wrap items-center gap-1.5">
                            {ev.technique ? <TechniqueChip technique={ev.technique} /> : null}
                            {orb ? (
                              <span className="text-[11px] text-muted-foreground">орб {orb}</span>
                            ) : null}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </motion.div>
            )
          })}
        </div>

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
