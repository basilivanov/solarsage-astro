// ############################################################################
// AI_HEADER: MODULE_ACTIVATION_EVIDENCE_CARD — human-first personal day story.
// ROLE: Converts backend-owned V2 headline and ranked concrete advice into
//       a progressive, non-technical entry point for the Today screen.
// ############################################################################

// START_MODULE_CONTRACT: M-ACTIVATION-EVIDENCE-CARD
// purpose: Render a personal V2 story card and delegate sphere/why navigation to TodayScreen.
// owns:
//   - components/today/activation-evidence-card.tsx
// inputs: v2, concreteAdvice, onSphereSelect, onWhyOpen, headlineFallback.
// outputs: data-testid="activation-evidence-card" or null.
// dependencies: lib/contracts/today, lib/icons, lucide-react.
// side_effects: invokes parent-owned callbacks on real button activation.
// emitted_logs: none.
// invariants:
//   - never calculates astrology, rank, score, or convergence.
//   - headline comes only from V2 or an explicit backend fallback.
//   - technical evidence is never rendered in this subtree.
// failure_policy: return null when V2 or a safe headline is unavailable.
// END_MODULE_CONTRACT: M-ACTIVATION-EVIDENCE-CARD

// START_MODULE_MAP: M-ACTIVATION-EVIDENCE-CARD
// public_entrypoints:
//   - ActivationEvidenceCard
// semantic_blocks:
//   - ACTIVATION_EVIDENCE_CARD: Human-first personal day story component
// owned_tests:
//   - __tests__/components/ActivationEvidenceCard.personal.test.tsx
// END_MODULE_MAP: M-ACTIVATION-EVIDENCE-CARD

"use client"

import { ChevronRight } from "lucide-react"
import type { ConcreteAdviceBlock, ConcreteAdviceRow, TodayV2Block } from "@/lib/contracts/today"
import { getIcon } from "@/lib/icons"
import { containsBannedAstrologyVocabulary, getHumanSphereLabel } from "@/lib/presentation/today-v2"

type ActivationEvidenceCardProps = {
  v2: TodayV2Block | null | undefined
  concreteAdvice?: ConcreteAdviceBlock
  daySummary?: { mainAdvice?: string | null } | null
  onSphereSelect: (key: string) => void
  headlineFallback?: string | null
}

function getTopAffectedRows(rows: ConcreteAdviceRow[]): ConcreteAdviceRow[] {
  const seen = new Set<string>()
  return [...rows]
    .sort((left, right) => left.rank - right.rank)
    .filter((row) => {
      if (seen.has(row.key)) return false
      seen.add(row.key)
      return true
    })
    .slice(0, 3)
}

// START_BLOCK: ACTIVATION_EVIDENCE_CARD
export function ActivationEvidenceCard({
  v2,
  concreteAdvice = { rows: [], counts: { good: 0, caution: 0, avoid: 0, neutral: 0 } },
  daySummary,
  onSphereSelect,
  headlineFallback,
}: ActivationEvidenceCardProps) {
  // START_FUNCTION_CONTRACT: F-M-ACTIVATION-EVIDENCE-CARD.ActivationEvidenceCard
  // purpose: Render the V2 personal story and delegate navigation through callbacks.
  // inputs: ActivationEvidenceCardProps — backend-owned V2/advice fields and parent handlers.
  // returns: Human-first story card JSX or null.
  // side_effects: Calls onSphereSelect/onWhyOpen from native buttons.
  // emitted_logs: none.
  // error_behavior: hides the card when no safe headline can be shown.
  // END_FUNCTION_CONTRACT: F-M-ACTIVATION-EVIDENCE-CARD.ActivationEvidenceCard
  if (!v2) return null

  const v2Headline = v2.activationSummary.headline?.trim() || ""
  const fallbackHeadline = headlineFallback?.trim() || ""
  const headline = v2Headline && !containsBannedAstrologyVocabulary(v2Headline)
    ? v2Headline
    : fallbackHeadline && !containsBannedAstrologyVocabulary(fallbackHeadline)
      ? fallbackHeadline
      : ""
  if (!headline) return null

  const rankedRows = getTopAffectedRows(concreteAdvice?.rows || [])
  const mainAdvice = daySummary?.mainAdvice?.trim() || null
  const Sparkles = getIcon("sparkle")

  return (
    <section className="px-5" aria-label="Личный сюжет дня">
      <div
        data-testid="activation-evidence-card"
        data-state="ready"
        className="relative overflow-hidden rounded-[24px] border border-violet-200/70 bg-gradient-to-br from-card via-card to-violet-50/70 p-6 shadow-[0_18px_48px_-28px_rgba(109,40,217,0.5)] dark:border-violet-400/25 dark:to-violet-950/20"
      >
        <div className="pointer-events-none absolute -right-10 -top-12 h-36 w-36 rounded-full bg-violet-300/20 blur-3xl" />
        <p className="relative inline-flex rounded-full bg-violet-100/80 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-violet-700 dark:bg-violet-500/15 dark:text-violet-200">
          ИМЕННО ДЛЯ ТЕБЯ
        </p>

        <h2 className="relative mt-4 font-serif text-[28px] leading-[1.12] text-foreground">
          {headline}
        </h2>

        {mainAdvice && !containsBannedAstrologyVocabulary(mainAdvice) ? (
          <div className="relative mt-4 flex items-start gap-3 rounded-2xl border border-violet-200/70 bg-violet-50/55 px-3.5 py-3.5 dark:border-violet-400/20 dark:bg-violet-500/10">
            <span className="mt-0.5 flex h-8 w-8 flex-none items-center justify-center rounded-xl bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-100">
              <Sparkles className="h-4 w-4" strokeWidth={1.9} aria-hidden />
            </span>
            <p className="min-w-0 text-[15px] font-medium leading-snug text-foreground">
              Главное: {mainAdvice}
            </p>
          </div>
        ) : null}

        {rankedRows.length > 0 ? (
          <div className="relative mt-5 border-t border-border/60 pt-4">
            <h3 className="text-[16px] font-semibold text-violet-700 dark:text-violet-200">Где проявится сегодня</h3>
            <div className="mt-3 space-y-2">
              {rankedRows.map((row) => {
                const Icon = getIcon(row.iconName)
                const label = getHumanSphereLabel(row)
                return (
                  <button
                    key={row.key}
                    type="button"
                    data-testid="personal-story-sphere-link"
                    data-sphere-key={row.key}
                    aria-label={`Открыть сферу ${label}`}
                    onClick={() => onSphereSelect(row.key)}
                    className="flex min-h-[56px] w-full items-center gap-3 rounded-2xl border border-violet-200/70 bg-card/70 px-3.5 text-left text-foreground transition hover:border-violet-400 hover:bg-violet-50/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2 dark:border-violet-400/25 dark:hover:bg-violet-500/10 cursor-pointer"
                  >
                    <span className="flex h-9 w-9 flex-none items-center justify-center rounded-xl bg-violet-100/80 text-violet-700 dark:bg-violet-500/20 dark:text-violet-100">
                      <Icon className="h-4 w-4" strokeWidth={1.8} aria-hidden />
                    </span>
                    <span className="min-w-0 flex-1 text-[15px] font-medium leading-snug">{label}</span>
                    <ChevronRight className="h-4 w-4 flex-none text-violet-700 dark:text-violet-200" aria-hidden />
                  </button>
                )
              })}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  )
}
// END_BLOCK: ACTIVATION_EVIDENCE_CARD
