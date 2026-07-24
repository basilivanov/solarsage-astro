// ############################################################################
// AI_HEADER: MODULE_ELECTION_PROCESSING_CARD
// ROLE: Processing card for election search with animated Moon SVG & 3 steps
// ############################################################################

"use client"

import { useEffect, useState } from "react"

export function ElectionProcessingCard() {
  const [stepIndex, setStepIndex] = useState(0)
  const [isDelayed, setIsDelayed] = useState(false)

  const steps = [
    "Смотрим Луну на твоё окно…",
    "Считаем фазы, знаки и холостой курс…",
    "Выбираем лучшие дни лично для тебя…",
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
  }, [steps.length])

  return (
    <div
      className="rounded-2xl border border-border/70 bg-card p-8 flex flex-col items-center text-center gap-5 shadow-sm"
      data-testid="election-processing-card"
    >
      {/* Animated Moon SVG */}
      <div className="relative flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary animate-pulse">
        <svg
          className="h-10 w-10 text-primary animate-spin"
          style={{ animationDuration: "12s" }}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
        </svg>
      </div>

      <div className="flex flex-col gap-2">
        <h3 className="font-serif text-[20px] font-semibold text-foreground">
          {steps[stepIndex]}
        </h3>
        <p className="text-[13px] text-muted-foreground">
          Расчёт точного астрологического окна
        </p>
        {isDelayed && (
          <p className="text-[13px] text-amber-500 font-medium mt-2" role="status">
            Готовится дольше обычного, пожалуйста подождите...
          </p>
        )}
      </div>
    </div>
  )
}
