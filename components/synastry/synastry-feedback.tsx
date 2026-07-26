// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_FEEDBACK
// ROLE: Reality check feedback section component for synastry report screen
// DEPENDENCIES: react
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-FEEDBACK
// purpose: Render reality check feedback options with aria-pressed active state and disclaimer text.
// owns:
//   - components/synastry/synastry-feedback.tsx
// inputs: feedbackValue, onSubmitFeedback, submitting
// outputs: SynastryFeedback TSX render
// dependencies: none
// side_effects: none
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-SYNASTRY-FEEDBACK

// START_MODULE_MAP: M-SYNASTRY-FEEDBACK
// public_entrypoints:
//   - SynastryFeedbackBlock
// semantic_blocks: none
// owned_tests: none
// END_MODULE_MAP: M-SYNASTRY-FEEDBACK

"use client"

type Props = {
  feedbackValue: string | null
  onSubmitFeedback: (value: string) => void
  submitting?: boolean
}

const OPTIONS = [
  { id: "accurate", label: "Да, очень" },
  { id: "partial", label: "Частично" },
  { id: "inaccurate", label: "Не похоже" },
]

// START_BLOCK: SYNASTRY_FEEDBACK
export function SynastryFeedbackBlock({
  feedbackValue,
  onSubmitFeedback,
  submitting = false,
}: Props) {
  return (
    <section className="rounded-[24px] border border-border/70 bg-card p-6 shadow-sm space-y-4" data-testid="synastry-feedback">
      <div className="space-y-1">
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          ПРОВЕРКА РЕАЛЬНОСТЬЮ
        </span>
        <p className="text-[14px] text-foreground/85">
          Насколько разбор отозвался в вашем личном опыте?
        </p>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {OPTIONS.map((option) => {
          const isSelected = feedbackValue === option.id
          return (
            <button
              key={option.id}
              type="button"
              aria-pressed={isSelected}
              disabled={submitting}
              onClick={() => onSubmitFeedback(option.id)}
              className={`rounded-[16px] border py-3 text-[13px] font-medium transition active:scale-95 ${
                isSelected
                  ? "border-[#3e3347] bg-[#3e3347] text-[#fffdf9] dark:bg-[#f1e9f4] dark:text-[#3e3347] font-semibold"
                  : "border-border/70 bg-background/60 text-foreground/80 hover:border-primary/50"
              }`}
            >
              {option.label}
            </button>
          )
        })}
      </div>

      <p className="text-[11.5px] text-muted-foreground text-center italic leading-relaxed">
        Синастрия описывает астрологические паттерны, а не выносит приговор вашим отношениям.
      </p>
    </section>
  )
}
// END_BLOCK: SYNASTRY_FEEDBACK
