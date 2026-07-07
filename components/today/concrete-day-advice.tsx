// ############################################################################
// AI_HEADER: MODULE_TODAY_CONCRETE_DAY_ADVICE — real-data sphere advice list.
// ROLE: Renders the oracle-style "Конкретно сегодня" section from adapted
//       TodayPayload fields only. No local astrology, demos, or runtime mocks.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONCRETE-DAY-ADVICE
// purpose: Build a dense concrete advice section from sphereScores enriched by
//          topFlags and notes. The component provides stable DOM selectors for
//          e2e and visual evidence on /day/[date].
// owns:
//   - components/today/concrete-day-advice.tsx
// inputs:
//   - sphereScores: SphereScore[] sorted by backend rank
//   - topFlags: AdaptedTopFlag[] real day signals
//   - notes: TodayNote[] adapted note cards
// outputs: TSX section with data-testid="concrete-day-advice"
// dependencies:
//   - lucide-react
//   - @/lib/contracts/today
//   - @/lib/display/sphere-labels
//   - @/lib/icons
// side_effects: local expand/collapse state only
// emitted_logs: none
// invariants:
//   - rows are derived from real sphereScores, topFlags, or notes
//   - unknown sphere keys are labeled through getSphereLabel
//   - missing sphere rows produce at most one graceful unavailable row
// failure_policy: renders a graceful unavailable row instead of inventing data
// END_MODULE_CONTRACT: M-TODAY-CONCRETE-DAY-ADVICE

"use client"

import { useMemo, useState } from "react"
import { ChevronDown, Zap } from "lucide-react"

import { getIcon } from "@/lib/icons"
import type { AdaptedTopFlag, SphereScore, TodayNote } from "@/lib/contracts/today"
import { getSphereLabel } from "@/lib/display/sphere-labels"

type Props = {
  topFlags: AdaptedTopFlag[]
  notes: TodayNote[]
  sphereScores: SphereScore[]
}

type Verdict = "good" | "caution" | "neutral" | "unavailable"

type AdviceRow = {
  id: string
  iconName: string
  label: string
  text: string
  verdict: Verdict
  score?: number
}

const COMPACT_ROW_COUNT = 6

const VERDICT_META: Record<Verdict, { label: string; color: string; bg: string }> = {
  good: {
    label: "благоприятно",
    color: "oklch(0.65 0.13 145)",
    bg: "oklch(0.65 0.13 145 / 0.08)",
  },
  caution: {
    label: "осторожно",
    color: "oklch(0.70 0.13 85)",
    bg: "oklch(0.70 0.13 85 / 0.08)",
  },
  neutral: {
    label: "ровно",
    color: "oklch(0.55 0.06 295)",
    bg: "oklch(0.55 0.06 295 / 0.05)",
  },
  unavailable: {
    label: "ожидается",
    color: "oklch(0.60 0.03 260)",
    bg: "oklch(0.60 0.03 260 / 0.05)",
  },
}

function verdictForScore(score: number): Verdict {
  if (score >= 6) return "good"
  if (score <= 3) return "caution"
  return "neutral"
}

function adviceTextFor(score: number, topFlag: AdaptedTopFlag | undefined, note: TodayNote | undefined): string {
  if (topFlag?.summary) return topFlag.summary
  if (note && note.id !== "no-data") return note.description
  if (score >= 6) return "Сфера поддержана: можно действовать спокойно и последовательно."
  if (score <= 3) return "Сфера требует осторожности: снизь темп и проверь детали."
  return "Ровный фон: держи обычный темп без лишнего давления."
}

function iconForSphere(key: string, verdict: Verdict): string {
  if (key.includes("money") || key.includes("finance")) return "building"
  if (key.includes("work") || key.includes("career") || key.includes("status")) return "briefcase"
  if (key.includes("relationship") || key.includes("partnership")) return "sparkle"
  if (key.includes("body") || key.includes("health")) return "leaf"
  if (key.includes("thinking") || key.includes("learning") || key.includes("communication")) return "telescope"
  if (key.includes("home") || key.includes("family")) return "layers"
  return verdict === "good" ? "trending-up" : "compass"
}

// START_BLOCK: BUILD_ADVICE_ROWS
function buildAdviceRows(topFlags: AdaptedTopFlag[], notes: TodayNote[], sphereScores: SphereScore[]): AdviceRow[] {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONCRETE-DAY-ADVICE.buildAdviceRows
  // purpose: Converts backend sphere scores into deterministic UI advice rows.
  // inputs: topFlags, notes, sphereScores — adapted real payload fields.
  // returns: AdviceRow[] — ranked rows plus one graceful unavailable row if needed.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: Never throws intentionally; empty inputs return unavailable row.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONCRETE-DAY-ADVICE.buildAdviceRows
  const rows = [...sphereScores]
    .sort((a, b) => a.rank - b.rank)
    .map((sphere, index): AdviceRow => {
      const verdict = verdictForScore(sphere.score)
      return {
        id: `sphere-${sphere.key}`,
        iconName: iconForSphere(sphere.key, verdict),
        label: getSphereLabel(sphere.key),
        text: adviceTextFor(sphere.score, topFlags[index], notes[index]),
        verdict,
        score: sphere.score,
      }
    })

  if (rows.length < 12) {
    rows.push({
      id: "sphere-data-pending",
      iconName: "hourglass",
      label: "Остальные сферы",
      text: "Данные появятся после расчёта.",
      verdict: "unavailable",
    })
  }

  return rows
}
// END_BLOCK: BUILD_ADVICE_ROWS

// START_BLOCK: CONCRETE_DAY_ADVICE_COMPONENT
export function ConcreteDayAdvice({ topFlags, notes, sphereScores }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONCRETE-DAY-ADVICE.ConcreteDayAdvice
  // purpose: Render the compact/expandable oracle-style sphere advice section.
  // inputs: Props — real adapted today payload arrays.
  // returns: JSX.Element.
  // side_effects: Stores expanded state in React.
  // emitted_logs: none.
  // error_behavior: Renders graceful unavailable row when arrays are empty.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONCRETE-DAY-ADVICE.ConcreteDayAdvice
  const [expanded, setExpanded] = useState(false)
  const rows = useMemo(
    () => buildAdviceRows(topFlags, notes, sphereScores),
    [topFlags, notes, sphereScores],
  )
  const visibleRows = expanded ? rows : rows.slice(0, COMPACT_ROW_COUNT)
  const hiddenCount = Math.max(rows.length - COMPACT_ROW_COUNT, 0)
  const goodCount = rows.filter((row) => row.verdict === "good").length
  const cautionCount = rows.filter((row) => row.verdict === "caution").length

  return (
    <section className="px-5" aria-label="Конкретно по сферам" data-testid="concrete-day-advice">
      <div className="mb-3 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          <Zap className="h-3 w-3" strokeWidth={1.8} aria-hidden />
          Конкретно сегодня
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <div className="overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/20">
        <div className="flex items-center justify-between gap-3 border-b border-border/50 px-4 py-3">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px]">
            <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden />
              {goodCount} благоприятно
            </span>
            <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" aria-hidden />
              {cautionCount} осторожно
            </span>
          </div>
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            aria-expanded={expanded}
            aria-controls="concrete-day-advice-rows"
            className="flex flex-none items-center gap-0.5 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
          >
            {expanded ? "свернуть" : "все 12 сфер"}
            <ChevronDown
              className={`h-3 w-3 transition-transform ${expanded ? "rotate-180" : ""}`}
              strokeWidth={2}
              aria-hidden
            />
          </button>
        </div>

        <div id="concrete-day-advice-rows" className="divide-y divide-border/30">
          {visibleRows.map((row) => {
            const Icon = getIcon(row.iconName)
            const meta = VERDICT_META[row.verdict]
            return (
              <div
                key={row.id}
                className="flex items-start gap-2.5 px-4 py-2.5"
                style={{ background: expanded ? meta.bg : undefined }}
                data-testid="concrete-day-advice-row"
                data-status={row.verdict}
              >
                <span className="mt-0.5 flex h-5 w-5 flex-none items-center justify-center text-muted-foreground">
                  <Icon className="h-3.5 w-3.5" strokeWidth={1.8} aria-hidden />
                </span>
                <span className="w-[88px] flex-none text-[11px] font-medium leading-snug text-muted-foreground">
                  {row.label}
                </span>
                <span className="min-w-0 flex-1 text-[12.5px] leading-snug text-foreground">
                  {row.text}
                  {row.score != null ? (
                    <span className="ml-1 whitespace-nowrap text-[11px] text-muted-foreground">
                      {row.score.toFixed(1)}
                    </span>
                  ) : null}
                </span>
                <span
                  className="mt-1 h-1.5 w-1.5 flex-none rounded-full"
                  style={{ background: meta.color }}
                  title={meta.label}
                  aria-hidden
                />
              </div>
            )
          })}
        </div>

        {!expanded && hiddenCount > 0 ? (
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="w-full py-2 text-center text-[11px] text-muted-foreground transition-colors hover:bg-muted/30 hover:text-foreground"
          >
            Показать ещё {hiddenCount} сфер
          </button>
        ) : null}
      </div>
    </section>
  )
}
// END_BLOCK: CONCRETE_DAY_ADVICE_COMPONENT
