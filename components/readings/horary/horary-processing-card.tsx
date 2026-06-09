"use client"

import { useEffect, useMemo, useState } from "react"
import { Check, Sparkles } from "lucide-react"
import { HORARY_CATEGORIES } from "@/lib/contracts/horary"

type Props = {
  questionText: string
  createdAt: string
  category?: string | null
  startedAt?: number
}

const STEPS = [
  "Фиксируем момент вопроса",
  "Строим карту",
  "Сверяем сигнификаторы",
  "Собираем ответ",
]

export function HoraryProcessingCard({
  questionText,
  createdAt,
  category,
  startedAt,
}: Props) {
  const [progress, setProgress] = useState(6)
  const [isLongRunning, setIsLongRunning] = useState(false)

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress((prev) => Math.min(prev + 1, 95))
    }, 420)

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (!startedAt) return

    const remaining = 30000 - (Date.now() - startedAt)
    if (remaining <= 0) {
      setIsLongRunning(true)
      return
    }

    const timer = setTimeout(() => {
      setIsLongRunning(true)
    }, remaining)

    return () => clearTimeout(timer)
  }, [startedAt])

  const stepIndex = useMemo(() => {
    if (progress < 25) return 0
    if (progress < 50) return 1
    if (progress < 75) return 2
    return 3
  }, [progress])

  const catMeta = HORARY_CATEGORIES.find((item) => item.key === category)

  const formatDisplayDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleString("ru-RU", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      })
    } catch {
      return iso
    }
  }

  return (
    <div className="overflow-hidden rounded-3xl border border-primary/10 bg-gradient-to-br from-primary/[0.07] via-background to-primary/[0.03] p-4 shadow-sm shadow-primary/5">
      <div className="flex items-start gap-3.5">
        <div className="relative mt-0.5 flex h-12 w-12 flex-none items-center justify-center">
          <div className="absolute inset-0 rounded-full border border-primary/15" />
          <div className="absolute inset-[5px] rounded-full border border-primary/10" />
          <div className="absolute inset-0 animate-spin" style={{ animationDuration: "5s" }}>
            <div className="absolute left-1/2 top-0 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/90 shadow-md shadow-primary/30" />
          </div>
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/12 text-primary">
            <Sparkles className="h-3.5 w-3.5 animate-pulse" />
          </div>
        </div>

        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex items-center gap-2 flex-wrap">
            {catMeta && (
              <span className="inline-flex items-center gap-1 rounded-full border border-border/60 bg-background/75 px-2.5 py-0.5 text-[11px] text-foreground/75">
                <span>{catMeta.emoji}</span>
                <span>{catMeta.label}</span>
              </span>
            )}
            <span className="text-[12px] text-muted-foreground">
              {formatDisplayDate(createdAt)}
            </span>
          </div>

          <div className="space-y-1.5">
            <p className="font-serif text-[15px] leading-snug text-foreground/90 line-clamp-2">
              {questionText}
            </p>
            <p className="text-[12.5px] leading-relaxed text-muted-foreground">
              Бережно собираем карту и формулируем ответ без спешки.
            </p>
          </div>

          <div className="space-y-2">
            {STEPS.map((step, idx) => {
              const isCompleted = idx < stepIndex
              const isActive = idx === stepIndex

              return (
                <div
                  key={step}
                  className={`flex items-center gap-2.5 transition-opacity ${
                    isActive ? "opacity-100" : isCompleted ? "opacity-75" : "opacity-40"
                  }`}
                >
                  <div
                    className={`flex h-4.5 w-4.5 items-center justify-center rounded-full border text-[9px] transition-colors ${
                      isCompleted
                        ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-500"
                        : isActive
                          ? "border-primary/25 bg-primary/10 text-primary animate-pulse"
                          : "border-border/70 bg-background/70 text-muted-foreground/60"
                    }`}
                  >
                    {isCompleted ? <Check className="h-3 w-3" strokeWidth={3} /> : <span>{idx + 1}</span>}
                  </div>
                  <span className={`text-[12.5px] ${isActive ? "text-foreground" : "text-muted-foreground"}`}>
                    {step}
                  </span>
                </div>
              )
            })}
          </div>

          <div className="space-y-2 pt-0.5">
            <div className="h-2 overflow-hidden rounded-full bg-primary/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-primary/55 via-primary/80 to-primary transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-[12px]">
              <span className="text-muted-foreground">Ответ готовится</span>
              <span className="font-medium text-primary/85">{progress}%</span>
            </div>
          </div>

          {isLongRunning ? (
            <p className="rounded-2xl border border-primary/10 bg-background/60 px-3 py-2 text-[12.5px] leading-relaxed text-muted-foreground">
              Ответ готовится дольше обычного. Можно закрыть экран — ответ появится в истории.
            </p>
          ) : null}
        </div>
      </div>
    </div>
  )
}
