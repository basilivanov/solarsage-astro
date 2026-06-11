
// ############################################################################
// AI_HEADER: MODULE_SHARED_COSMIC_LOADER
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: UI cosmic-loader — component
// owns:
//   - components/shared/cosmic-loader.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { useEffect, useRef, useState } from "react"
import { Moon, Sparkles, Star } from "lucide-react"
import {
  DEFAULT_MESSAGES,
  DONE_MESSAGE,
  MESSAGE_INTERVAL,
  nextMessageIndex,
  captionFor,
  PROGRESS_START,
  PROGRESS_TICK,
  DONE_STEP,
  PROGRESS_CEILING,
  progressEase,
} from "@/lib/loader-progress"

type Props = {
  /** Когда true — прогресс дожимается до 100% и анимация замирает. */
  done?: boolean
  /** Ожидаемая длительность ожидания, мс. Влияет на скорость заполнения. */
  durationHint?: number
  /** Свои подписи. По умолчанию — фирменный набор. */
  messages?: string[]
}

export function CosmicLoader({
  done = false,
  durationHint = 12000,
  messages = DEFAULT_MESSAGES,
}: Props) {
  const [progress, setProgress] = useState(PROGRESS_START)
  const [msgIndex, setMsgIndex] = useState(0)
  const doneRef = useRef(done)
  doneRef.current = done

  // Прогресс: асимптотически приближаемся к 92%, пока не пришёл `done`.
  useEffect(() => {
    const ease = progressEase(durationHint)

    const id = setInterval(() => {
      setProgress((p) => {
        if (doneRef.current) return Math.min(100, p + DONE_STEP)
        if (p >= PROGRESS_CEILING) return PROGRESS_CEILING
        return p + (PROGRESS_CEILING - p) * ease
      })
    }, PROGRESS_TICK)

    return () => clearInterval(id)
  }, [durationHint])

  // Ротация подписей
  useEffect(() => {
    if (done) return
    const id = setInterval(() => {
      setMsgIndex((i) => nextMessageIndex(i, messages.length))
    }, MESSAGE_INTERVAL)
    return () => clearInterval(id)
  }, [done, messages.length])

  const message = done ? DONE_MESSAGE : captionFor(false, msgIndex, messages)
  const pct = Math.round(progress)

  return (
    <div
      className="flex min-h-[60vh] w-full flex-col items-center justify-center px-10"
      role="status"
      aria-live="polite"
      aria-label="Загружаем разбор дня"
      data-testid="cosmic-loader"
    >
      {/* --- Небесная сцена --------------------------------------------- */}
      <div className="relative mb-10 h-40 w-40">
        {STAR_FIELD.map((s, i) => (
          <span
            key={i}
            className="lumen-twinkle absolute rounded-full bg-primary"
            style={{
              top: s.top,
              left: s.left,
              width: s.size,
              height: s.size,
              animationDuration: `${s.dur}ms`,
              animationDelay: `${s.delay}ms`,
            }}
          />
        ))}

        <Ring durationMs={9000}>
          <Sparkles className="size-4 text-primary/70" strokeWidth={2} />
        </Ring>

        <Ring durationMs={6000} reverse inset={28}>
          <Star className="size-3 fill-primary/40 text-primary/70" strokeWidth={2} />
        </Ring>

        <div className="absolute inset-0 flex items-center justify-center">
          <div className="lumen-breathe relative flex size-16 items-center justify-center rounded-full bg-secondary [animation:lumen-breathe_3.4s_ease-in-out_infinite]">
            <span aria-hidden className="absolute inset-0 rounded-full bg-primary/15 blur-md" />
            <Moon className="relative size-7 text-primary" strokeWidth={1.75} />
          </div>
        </div>
      </div>

      {/* --- Подпись ----------------------------------------------------- */}
      <p
        key={message}
        className="mb-6 min-h-[1.6em] text-center font-serif text-[20px] leading-snug text-foreground [animation:lumen-caption-in_0.5s_ease-out]"
      >
        {message}
      </p>

      {/* --- Прогресс ---------------------------------------------------- */}
      <div
        className="h-1.5 w-full max-w-[220px] overflow-hidden rounded-full bg-accent"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="relative h-full rounded-full bg-primary transition-[width] duration-200 ease-out"
          style={{ width: `${pct}%` }}
        >
          <span
            aria-hidden
            className="lumen-shimmer absolute inset-y-0 left-0 w-1/3 bg-primary-foreground/30 blur-sm [animation:lumen-shimmer_1.8s_ease-in-out_infinite]"
          />
        </div>
      </div>
      <span className="mt-3 text-xs tabular-nums text-muted-foreground">{pct}%</span>
    </div>
  )
}

/** Кольцо-орбита: вращающаяся обёртка, ребёнок «приклеен» к верхней точке. */
function Ring({
  children,
  durationMs,
  reverse = false,
  inset = 0,
}: {
  children: React.ReactNode
  durationMs: number
  reverse?: boolean
  inset?: number
}) {
  return (
    <div
      className="lumen-orbit-ring absolute rounded-full border border-primary/15"
      style={{
        top: inset,
        left: inset,
        right: inset,
        bottom: inset,
        animation: `lumen-orbit ${durationMs}ms linear infinite${reverse ? " reverse" : ""}`,
      }}
    >
      <div className="absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/2">{children}</div>
    </div>
  )
}

// Фиксированное поле звёзд — детерминированное, без гидрационных расхождений
const STAR_FIELD = [
  { top: "6%", left: "18%", size: 3, dur: 2600, delay: 0 },
  { top: "14%", left: "80%", size: 4, dur: 3200, delay: 400 },
  { top: "78%", left: "10%", size: 3, dur: 2900, delay: 900 },
  { top: "88%", left: "70%", size: 4, dur: 3400, delay: 200 },
  { top: "40%", left: "2%", size: 2, dur: 2400, delay: 1200 },
  { top: "52%", left: "94%", size: 3, dur: 3000, delay: 600 },
]
