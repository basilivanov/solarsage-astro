"use client"

import { useState, useEffect } from "react"
import { Sparkles } from "lucide-react"
import { Progress } from "@/components/ui/progress"

const STAGES = [
  "Определяю момент вопроса...",
  "Строю хорарную карту...",
  "Анализирую аспекты...",
  "Формулирую ответ...",
]

export function HoraryProgress() {
  const [progress, setProgress] = useState(0)
  const [stageIndex, setStageIndex] = useState(0)

  useEffect(() => {
    // Smooth progress bar increment (0 to 95 over 8 seconds)
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 95) {
          clearInterval(interval)
          return 95
        }
        return prev + 1.2
      })
    }, 100)

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    // Stage updates every 2 seconds
    const interval = setInterval(() => {
      setStageIndex((prev) => {
        if (prev < STAGES.length - 1) {
          return prev + 1
        }
        return prev
      })
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex flex-col items-center justify-center min-h-[50dvh] px-6 py-12 text-center max-w-md mx-auto">
      <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary animate-pulse">
        <Sparkles className="h-7 w-7" />
      </div>

      <h3 className="font-serif text-[24px] font-bold leading-tight tracking-tight text-foreground mb-2">
        Созвездия выстраиваются...
      </h3>

      <p className="text-[14px] text-muted-foreground mb-6 h-5">
        {STAGES[stageIndex]}
      </p>

      <div className="w-full max-w-[280px]">
        <Progress value={progress} className="h-1.5 w-full bg-border/40" />
        <div className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-[0.14em] mt-2 text-right">
          {Math.round(progress)}%
        </div>
      </div>
    </div>
  )
}
