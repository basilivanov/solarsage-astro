// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_SCORE_PANEL
// ROLE: Score panel card with compatibility verdict, summary, and aspect counters
// DEPENDENCIES: react, components/synastry/synastry-tone
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-SCORE-PANEL
// purpose: Render prominent score panel with score box, verdict, deduplicated summary narrative, and 3 tone counters.
// owns:
//   - components/synastry/synastry-score-panel.tsx
// inputs: score, status, verdict, summary, heroTitle, heroDescription, counters
// outputs: SynastryScorePanel TSX render
// dependencies: components/synastry/synastry-tone
// side_effects: none
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-SYNASTRY-SCORE-PANEL

// START_MODULE_MAP: M-SYNASTRY-SCORE-PANEL
// public_entrypoints:
//   - SynastryScorePanel
// semantic_blocks: none
// owned_tests: none
// END_MODULE_MAP: M-SYNASTRY-SCORE-PANEL

"use client"

import {
  getToneStatusLabel,
  normalizeSynastryTone,
} from "./synastry-tone"

type Props = {
  score: number
  status: "good" | "mid" | "bad"
  verdict: string
  summary: string
  heroTitle?: string | null
  heroDescription?: string | null
  counters: { good: number; mid: number; bad: number }
}

// START_BLOCK: SYNASTRY_SCORE_PANEL
export function SynastryScorePanel({
  score,
  status,
  verdict,
  summary,
  heroTitle,
  heroDescription,
  counters,
}: Props) {
  const tone = normalizeSynastryTone(status)

  // Deduplication & fallback chain for text fields
  const statusLabel = getToneStatusLabel(tone)
  const displayHeadline = verdict || heroTitle || statusLabel
  const displaySummary = summary || heroDescription || "Анализ взаимодействия завершён."
  // The pill is redundant when the headline already IS the status label (макет §6.3/§6.4).
  const showStatusPill = displayHeadline.trim() !== statusLabel

  return (
    <section
      data-testid="synastry-score"
      data-status={status}
      className="rounded-[24px] border border-border/70 bg-card p-6 shadow-sm space-y-5"
    >
      {/* Top Section: Score box + Verdict & Summary */}
      <div className="flex flex-col sm:flex-row items-start gap-4">
        {/* Score Box (78x78 lavender square) */}
        <div className="flex h-[78px] w-[78px] flex-none flex-col items-center justify-center rounded-[20px] bg-[var(--syn-lavender)] border border-primary/10">
          <span className="font-serif text-[36px] font-normal leading-none text-foreground">
            {score}
          </span>
          <span className="text-[10px] font-medium text-muted-foreground/70 uppercase tracking-wider mt-0.5">
            из 100
          </span>
        </div>

        {/* Headline & Summary */}
        <div className="space-y-1.5 min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="font-serif text-[20px] font-semibold text-foreground leading-snug">
              {displayHeadline}
            </h2>
            {showStatusPill && (
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                  tone === "good"
                    ? "bg-[var(--syn-good-bg)] text-[var(--syn-good)]"
                    : tone === "bad"
                    ? "bg-[var(--syn-bad-bg)] text-[var(--syn-bad)]"
                    : "bg-[var(--syn-mid-bg)] text-[var(--syn-mid)]"
                }`}
              >
                {statusLabel}
              </span>
            )}
          </div>

          <p className="text-[14px] leading-relaxed text-muted-foreground">
            {displaySummary}
          </p>
        </div>
      </div>

      {/* Bottom: 3 Tone Counter Blocks */}
      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-border/40" data-testid="synastry-score-counters">
        <div className="rounded-[14px] bg-[var(--syn-good-bg)] px-3 py-2 text-center">
          <span className="text-[12px] font-semibold text-[var(--syn-good)]">
            {counters.good || 0} поддерживают
          </span>
        </div>
        <div className="rounded-[14px] bg-[var(--syn-mid-bg)] px-3 py-2 text-center">
          <span className="text-[12px] font-semibold text-[var(--syn-mid)]">
            {counters.mid || 0} неоднозначны
          </span>
        </div>
        <div className="rounded-[14px] bg-[var(--syn-bad-bg)] px-3 py-2 text-center">
          <span className="text-[12px] font-semibold text-[var(--syn-bad)]">
            {counters.bad || 0} напрягают
          </span>
        </div>
      </div>
    </section>
  )
}
// END_BLOCK: SYNASTRY_SCORE_PANEL
