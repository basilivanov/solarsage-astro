"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"

import { getYesterdayCheckin } from "@/lib/api/checkin"
import type { YesterdayCheckinResponse } from "@/packages/contracts"

const MOOD_EMOJI: Record<number, string> = {
  1: "😫",
  2: "😕",
  3: "😐",
  4: "🙂",
  5: "🤩",
}

const ACCURACY_LABEL: Record<number, string> = {
  1: "мимо",
  2: "частично",
  3: "попал",
}

type Props = {
  echo: YesterdayCheckinResponse | null
}

export function YesterdayEchoBlock({ echo }: Props) {
  const router = useRouter()

  if (!echo || !echo.hadCheckin || !echo.checkin) {
    return (
      <div
        className="rounded-2xl border border-border/60 bg-card p-4"
        data-testid="yesterday-echo-cta"
      >
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[13px] font-medium text-foreground">
              Вчерашний прогноз без оценки
            </div>
            <div className="mt-0.5 text-[12px] text-muted-foreground">
              Отметь настроение за несколько секунд
            </div>
          </div>
          <button
            type="button"
            onClick={() => router.push("/checkin?target=yesterday")}
            className="flex-none rounded-full bg-foreground px-4 py-2 text-[12px] font-medium text-background"
          >
            Оценить
          </button>
        </div>
      </div>
    )
  }

  const checkin = echo.checkin
  const moodEmoji = MOOD_EMOJI[checkin.mood] ?? "😐"
  const accuracy =
    checkin.accuracy === null || checkin.accuracy === undefined
      ? null
      : ACCURACY_LABEL[checkin.accuracy]

  return (
    <div
      className="rounded-2xl border border-border/60 bg-card p-4"
      data-testid="yesterday-echo-block"
    >
      <div className="flex items-start gap-3">
        <div className="text-2xl leading-none">{moodEmoji}</div>
        <div className="min-w-0 flex-1">
          <div className="text-[13px] font-medium text-foreground">
            Вчера ты отметил: {moodEmoji}
          </div>
          <div className="mt-1 text-[12px] text-muted-foreground">
            Серия: {checkin.streak}
            {accuracy ? ` · Прогноз ${accuracy}` : ""}
          </div>
          {checkin.note ? (
            <p className="mt-2 rounded-lg bg-secondary/40 px-3 py-2 text-[12px] leading-relaxed text-foreground/80">
              {checkin.note}
            </p>
          ) : null}
        </div>
      </div>
    </div>
  )
}

export function YesterdayEchoLoader() {
  const [echo, setEcho] = useState<YesterdayCheckinResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    getYesterdayCheckin()
      .then((value) => {
        if (active) setEcho(value)
      })
      .catch((reason: unknown) => {
        if (!active) return
        setError(
          reason instanceof Error
            ? reason.message
            : "Не удалось загрузить вчерашнюю оценку",
        )
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

  if (loading) {
    return (
      <div className="rounded-2xl border border-border/60 bg-card p-4 text-[13px] text-muted-foreground">
        Загружаем вчерашнюю оценку...
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-border/60 bg-card p-4 text-[13px] text-muted-foreground">
        {error}
      </div>
    )
  }

  return <YesterdayEchoBlock echo={echo} />
}
