// ############################################################################
// AI_HEADER: MODULE_ELECTION_PROCESSING_CARD
// ROLE: Processing card for election search
// ############################################################################

"use client"

import { useEffect, useState } from "react"
import { Sparkles } from "lucide-react"

export function ElectionProcessingCard() {
  const [stepIndex, setStepIndex] = useState(0)
  const [isDelayed, setIsDelayed] = useState(false)

  const steps = [
    "Смотрим Луну и планеты...",
    "Считаем фазы и период без курса...",
    "Выбираем лучшие даты для твоего события...",
  ]

  useEffect(() => {
    const stepTimer = setInterval(() => {
      setStepIndex((prev) => (prev < steps.length - 1 ? prev + 1 : prev))
    }, 4000)

    const delayTimer = setTimeout(() => {
      setIsDelayed(true)
    }, 30000)

    return () => {
      clearInterval(stepTimer)
      clearTimeout(delayTimer)
    }
  }, [])

  return (
    <div
      className="rounded-2xl border border-border/70 bg-card p-6 flex flex-col items-center text-center gap-4 animate-pulse"
      data-testid="election-processing-card"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
        <Sparkles className="h-6 w-6 animate-spin" />
      </div>
      <div>
        <h3 className="font-serif text-[18px] font-semibold text-foreground">
          {steps[stepIndex]}
        </h3>
        {isDelayed && (
          <p className="text-[13px] text-muted-foreground mt-2">
            Готовится дольше обычного, пожалуйста подождите...
          </p>
        )}
      </div>
    </div>
  )
}
