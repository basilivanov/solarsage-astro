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

  const statusLabel = getToneStatusLabel(tone)
  const displayHeadline = verdict || heroTitle || statusLabel
  const displaySummary = summary || heroDescription || "Анализ взаимодействия завершён."
  const showStatusPill = displayHeadline.trim() !== statusLabel

  return (
    <section
      data-testid="synastry-score"
      data-status={status}
      className="mx-4 rounded-[26px] border border-[#e8e0e8] bg-[#fffdf9]/94 dark:bg-[#2d2233]/94 p-[18px] shadow-[0_8px_26px_rgba(73,51,82,0.055)] space-y-4"
    >
      {/* Top Section: Score box + Verdict & Summary */}
      <div className="flex flex-row items-start gap-4">
        {/* Score Box (78x78 lavender square) */}
        <div className="flex h-[78px] w-[78px] flex-none flex-col items-center justify-center rounded-[20px] bg-[#f1e9f4] dark:bg-[#3e3347] border border-[#795a86]/10">
          <span className="syn-serif text-[36px] font-normal leading-none text-[#3e3347] dark:text-[#f1e9f4]">
            {score}
          </span>
          <span className="font-sans text-[10px] font-bold text-[#7d7284] uppercase tracking-wider mt-0.5">
            из 100
          </span>
        </div>

        {/* Headline & Summary */}
        <div className="space-y-1 min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="font-sans text-[21px] font-bold leading-snug text-[#3e3347] dark:text-[#f1e9f4]">
              {displayHeadline}
            </h2>
            {showStatusPill && (
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                  tone === "good"
                    ? "bg-[#eaf5f0] text-[#43806d] dark:bg-[#1c2b25] dark:text-[#63a893]"
                    : tone === "bad"
                    ? "bg-[#fae9ec] text-[#a64d59] dark:bg-[#2d1c20] dark:text-[#c96b77]"
                    : "bg-[#fbf1de] text-[#b07b36] dark:bg-[#2d261a] dark:text-[#d49a4f]"
                }`}
              >
                {statusLabel}
              </span>
            )}
          </div>

          <p className="text-[13px] leading-[1.45] text-[#7d7284] dark:text-muted-foreground">
            {displaySummary}
          </p>
        </div>
      </div>

      {/* Bottom: 3 Tone Counter Blocks (Number + Label stacked) */}
      <div className="grid grid-cols-3 gap-[7px] pt-1" data-testid="synastry-score-counters">
        <div className="rounded-[14px] bg-[#eaf5f0] dark:bg-[#1c2b25] px-[7px] py-[10px] text-center">
          <strong className="block font-sans text-[18px] font-[760] text-[#43806d] dark:text-[#63a893] leading-none mb-0.5">
            {counters.good || 0}
          </strong>
          <span className="block text-[10px] font-[760] text-[#43806d] dark:text-[#63a893]">
            поддерживают
          </span>
        </div>
        <div className="rounded-[14px] bg-[#fbf1de] dark:bg-[#2d261a] px-[7px] py-[10px] text-center">
          <strong className="block font-sans text-[18px] font-[760] text-[#b07b36] dark:text-[#d49a4f] leading-none mb-0.5">
            {counters.mid || 0}
          </strong>
          <span className="block text-[10px] font-[760] text-[#b07b36] dark:text-[#d49a4f]">
            неоднозначны
          </span>
        </div>
        <div className="rounded-[14px] bg-[#fae9ec] dark:bg-[#2d1c20] px-[7px] py-[10px] text-center">
          <strong className="block font-sans text-[18px] font-[760] text-[#a64d59] dark:text-[#c96b77] leading-none mb-0.5">
            {counters.bad || 0}
          </strong>
          <span className="block text-[10px] font-[760] text-[#a64d59] dark:text-[#c96b77]">
            напрягают
          </span>
        </div>
      </div>
    </section>
  )
}
// END_BLOCK: SYNASTRY_SCORE_PANEL
