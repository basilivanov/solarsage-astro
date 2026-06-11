
// ############################################################################
// AI_HEADER: MODULE_HORARY_HORARY_PROGRESS
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/readings/horary/horary-progress.tsx
// owns:
//   - components/readings/horary/horary-progress.tsx
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

"use client"

import { useState, useEffect } from "react"
import { Sparkles, Check } from "lucide-react"

const STEPS = [
  "Фиксируем момент",
  "Строим карту",
  "Формулируем ответ",
]

export function HoraryProgress() {
  const [progress, setProgress] = useState(0)
  const [stepIndex, setStepIndex] = useState(0)
  const [isLongRunning, setIsLongRunning] = useState(false)

  useEffect(() => {
    // Increment progress and update active steps
    const interval = setInterval(() => {
      setProgress((prev) => {
        const next = prev + 1
        if (next >= 100) {
          clearInterval(interval)
          return 99
        }
        return next
      })
    }, 300) // reaches ~95% in 28 seconds

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    // Map progress to steps
    if (progress < 30) {
      setStepIndex(0)
    } else if (progress < 70) {
      setStepIndex(1)
    } else {
      setStepIndex(2)
    }
  }, [progress])

  useEffect(() => {
    // After 30 seconds show the long running state
    const timer = setTimeout(() => {
      setIsLongRunning(true)
    }, 30000)

    return () => clearTimeout(timer)
  }, [])

  if (isLongRunning) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50dvh] px-6 py-12 text-center max-w-md mx-auto space-y-6">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted text-muted-foreground animate-pulse">
          <Sparkles className="h-6 w-6" />
        </div>
        <div className="space-y-2">
          <h3 className="font-serif text-[22px] font-bold text-foreground">
            Карта рассчитывается
          </h3>
          <p className="text-[14px] leading-relaxed text-muted-foreground">
            Ответ формируется дольше обычного. Мы сохраним вопрос и покажем ответ, когда карта будет готова.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[60dvh] px-6 py-12 text-center max-w-md mx-auto space-y-8">
      {/* Branded Ritual Orbit Animation */}
      <div className="relative h-28 w-28 flex items-center justify-center">
        {/* Outer Orbit Ring */}
        <div className="absolute inset-0 rounded-full border border-primary/15" />
        
        {/* Rotating Moon Dot */}
        <div 
          className="absolute inset-0 animate-spin" 
          style={{ animationDuration: "5s" }}
        >
          <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 h-3 w-3 rounded-full bg-primary shadow-lg shadow-primary/40" />
        </div>

        {/* Center Sparkle */}
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Sparkles className="h-6 w-6 animate-pulse" />
        </div>
      </div>

      {/* Branded Titles */}
      <div className="space-y-2">
        <h3 className="font-serif text-[24px] font-bold leading-tight tracking-tight text-foreground">
          Строим карту вопроса
        </h3>
        <p className="text-[13.5px] leading-relaxed text-muted-foreground px-4">
          Мы учитываем время, место и тему вопроса, чтобы дать точный хорарный ответ.
        </p>
      </div>

      {/* Animated 3 Steps */}
      <div className="w-full max-w-[240px] space-y-3 pt-2">
        {STEPS.map((step, idx) => {
          const isActive = idx === stepIndex
          const isCompleted = idx < stepIndex
          
          return (
            <div 
              key={step} 
              className={`flex items-center gap-3 transition-opacity duration-300 ${
                isActive ? "opacity-100" : isCompleted ? "opacity-75" : "opacity-35"
              }`}
            >
              <div 
                className={`flex h-5 w-5 items-center justify-center rounded-full border text-[10px] font-medium transition-colors ${
                  isCompleted 
                    ? "bg-emerald-500/10 border-emerald-500/25 text-emerald-500" 
                    : isActive 
                    ? "bg-primary/10 border-primary/25 text-primary animate-pulse" 
                    : "border-border bg-card text-muted-foreground/50"
                }`}
              >
                {isCompleted ? (
                  <Check className="h-3 w-3" strokeWidth={3} />
                ) : (
                  <span>{idx + 1}</span>
                )}
              </div>
              <span 
                className={`text-[14px] transition-colors ${
                  isActive ? "font-medium text-foreground" : "text-muted-foreground"
                }`}
              >
                {step}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
