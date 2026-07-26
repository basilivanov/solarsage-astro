// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_FEEDBACK
// ROLE: Reality check feedback section component for synastry report screen
// DEPENDENCIES: react, hooks/use-toast
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-FEEDBACK
// purpose: Render reality check feedback options with aria-pressed active state, toast notification, and disclaimer text.
// owns:
//   - components/synastry/synastry-feedback.tsx
// inputs: feedbackValue, onSubmitFeedback, submitting
// outputs: SynastryFeedback TSX render
// dependencies: hooks/use-toast
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

import { useToast } from "@/hooks/use-toast"

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
  const { toast } = useToast()

  function handleSelect(option: { id: string; label: string }) {
    onSubmitFeedback(option.id)
    toast({ title: `Сохранили: ${option.label}` })
  }

  return (
    <section
      className="mx-4 rounded-[26px] border border-[#e8e0e8] bg-[#fffdf9]/94 dark:bg-[#2d2233]/94 p-[18px] shadow-[0_8px_26px_rgba(73,51,82,0.055)] space-y-3"
      data-testid="synastry-feedback"
    >
      <div className="space-y-0.5">
        <span className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#795a86]">
          ПРОВЕРКА РЕАЛЬНОСТЬЮ
        </span>
        <p className="font-sans text-[14px] text-[#3e3347] dark:text-[#f1e9f4]">
          Насколько разбор отозвался в вашем личном опыте?
        </p>
      </div>

      <div className="grid grid-cols-3 gap-[7px]">
        {OPTIONS.map((option) => {
          const isSelected = feedbackValue === option.id
          return (
            <button
              key={option.id}
              type="button"
              aria-pressed={isSelected}
              disabled={submitting}
              onClick={() => handleSelect(option)}
              className={`rounded-[14px] border p-[10px_6px] text-[11px] font-[760] transition active:scale-95 text-center ${
                isSelected
                  ? "border-[#3e3347] bg-[#3e3347] text-white dark:bg-[#f1e9f4] dark:text-[#3e3347]"
                  : "border-[#e8e0e8] bg-white text-[#3e3347] dark:bg-[#2d2233] dark:text-[#f1e9f4] dark:border-[#795a86]/30 hover:border-[#795a86]/50"
              }`}
            >
              {option.label}
            </button>
          )
        })}
      </div>

      <p className="text-[11.5px] text-[#7d7284] dark:text-muted-foreground text-center italic leading-relaxed m-0 pt-1">
        Синастрия описывает астрологические паттерны, а не выносит приговор вашим отношениям.
      </p>
    </section>
  )
}
// END_BLOCK: SYNASTRY_FEEDBACK
